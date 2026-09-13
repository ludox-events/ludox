# Copyright (C) 2026 Matteo Sassi
# SPDX-License-Identifier: AGPL-3.0-only

"""Event-scoped operational identifiers for physical game copies."""

from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageFont

from . import database as data


class CopyIdentifierError(Exception):
    """Base error for copy identifier operations."""


class InvalidCopyIdentifier(CopyIdentifierError):
    pass


class CopyNotFound(CopyIdentifierError):
    pass


class IdentifierAlreadyAssigned(CopyIdentifierError):
    pass


class DuplicateCopyIdentifier(CopyIdentifierError):
    pass


class UnknownCopyIdentifier(CopyIdentifierError):
    pass


class IdentifierChangeBlocked(CopyIdentifierError):
    pass


class CopyStateChangeBlocked(CopyIdentifierError):
    pass


def normalize_identifier(value):
    normalized = str(value).strip() if value is not None else ""
    if not normalized or "\n" in normalized or "\r" in normalized:
        raise InvalidCopyIdentifier(
            "L'identificatore deve essere valorizzato e non può contenere "
            "ritorni a capo."
        )
    return normalized


def identifier_for_copy(event_id, copy_id):
    row = data.identificatore_copia(event_id, copy_id)
    return dict(row) if row is not None else None


def list_copies(event_id):
    copies = []
    for row in data.elenco_copie_evento(event_id):
        copy = dict(row)
        if copy["on_loan"]:
            copy["availability"] = "on_loan"
        elif not copy["copy_active"] or not copy["game_active"]:
            copy["availability"] = "inactive"
        elif not copy["copy_identifier"]:
            copy["availability"] = "unidentified"
        else:
            copy["availability"] = "available"
        copies.append(copy)
    return copies


def is_duplicate(event_id, value, *, excluding_copy_id=None):
    normalized = normalize_identifier(value)
    row = data.identificatore_per_valore(event_id, normalized)
    return row is not None and row["copy_id"] != excluding_copy_id


def _require_copy(event_id, copy_id):
    copy = data.copia_evento_per_id(event_id, copy_id)
    if copy is None:
        raise CopyNotFound("La copia non appartiene all'Event corrente.")
    return copy


def _ensure_not_open(event_id, copy_id):
    if data.copia_ha_prestito_aperto(event_id, copy_id):
        raise IdentifierChangeBlocked(
            "L'identificatore non può essere modificato mentre la copia è "
            "in prestito."
        )


def _insert(event_id, copy_id, source, value):
    if is_duplicate(event_id, value, excluding_copy_id=copy_id):
        raise DuplicateCopyIdentifier(
            "L'identificatore è già assegnato a un'altra copia dell'Event."
        )
    try:
        identifier_id = data.inserisci_identificatore_copia(
            event_id, copy_id, source, value
        )
    except data.DuplicateCopyIdentifierValue as exc:
        raise DuplicateCopyIdentifier(str(exc)) from exc
    return identifier_for_copy(event_id, copy_id) | {"id": identifier_id}


def assign_external(event_id, copy_id, value):
    _require_copy(event_id, copy_id)
    normalized = normalize_identifier(value)
    if identifier_for_copy(event_id, copy_id) is not None:
        raise IdentifierAlreadyAssigned(
            "La copia possiede già un identificatore operativo."
        )
    return _insert(event_id, copy_id, "external", normalized)


def generate_ludox(event_id, copy_id):
    _require_copy(event_id, copy_id)
    if identifier_for_copy(event_id, copy_id) is not None:
        raise IdentifierAlreadyAssigned(
            "La copia possiede già un identificatore operativo."
        )
    return _insert(event_id, copy_id, "ludox", f"LX-C-{copy_id:06d}")


def replace(event_id, copy_id, value, *, source="external"):
    _require_copy(event_id, copy_id)
    if source not in {"external", "ludox"}:
        raise InvalidCopyIdentifier("Origine identificatore non valida.")
    normalized = normalize_identifier(value)
    if identifier_for_copy(event_id, copy_id) is None:
        raise UnknownCopyIdentifier("La copia non possiede un identificatore.")
    _ensure_not_open(event_id, copy_id)
    if is_duplicate(event_id, normalized, excluding_copy_id=copy_id):
        raise DuplicateCopyIdentifier(
            "L'identificatore è già assegnato a un'altra copia dell'Event."
        )
    try:
        data.aggiorna_identificatore_copia(
            event_id, copy_id, source, normalized
        )
    except data.DuplicateCopyIdentifierValue as exc:
        raise DuplicateCopyIdentifier(str(exc)) from exc
    return identifier_for_copy(event_id, copy_id)


def remove(event_id, copy_id):
    _require_copy(event_id, copy_id)
    _ensure_not_open(event_id, copy_id)
    return data.elimina_identificatore_copia(event_id, copy_id)


def set_active(event_id, copy_id, active):
    _require_copy(event_id, copy_id)
    if not active and data.copia_ha_prestito_aperto(event_id, copy_id):
        raise CopyStateChangeBlocked(
            "Una copia in prestito non può essere disattivata."
        )
    data.aggiorna_stato_copia(event_id, copy_id, 1 if active else 0)
    return _require_copy(event_id, copy_id)


def resolve(event_id, value):
    normalized = normalize_identifier(value)
    row = data.copia_da_identificatore(event_id, normalized)
    if row is None:
        raise UnknownCopyIdentifier(
            "Identificatore sconosciuto nell'Event corrente."
        )
    return dict(row)


def is_lendable(event_id, copy_id):
    copy = _require_copy(event_id, copy_id)
    return bool(
        copy["copy_active"]
        and copy["game_active"]
        and identifier_for_copy(event_id, copy_id) is not None
        and not data.copia_ha_prestito_aperto(event_id, copy_id)
    )


def export_ludox_qr_png(event_id, copy_id, path):
    """Export a simple printable PNG containing QR and readable value."""
    identifier = identifier_for_copy(event_id, copy_id)
    if identifier is None or identifier["source"] != "ludox":
        raise InvalidCopyIdentifier(
            "Il PNG QR è disponibile soltanto per identificatori LudoX."
        )
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(identifier["value"])
    qr.make(fit=True)
    qr_image = qr.make_image(fill_color="black", back_color="white").convert(
        "RGB"
    )
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 20)
    except OSError:
        font = ImageFont.load_default()
    draw = ImageDraw.Draw(qr_image)
    box = draw.textbbox((0, 0), identifier["value"], font=font)
    text_width = box[2] - box[0]
    text_height = box[3] - box[1]
    padding = 14
    width = max(qr_image.width, text_width + padding * 2)
    output = Image.new(
        "RGB", (width, qr_image.height + text_height + padding * 2), "white"
    )
    output.paste(qr_image, ((width - qr_image.width) // 2, 0))
    output_draw = ImageDraw.Draw(output)
    output_draw.text(
        ((width - text_width) // 2, qr_image.height + padding),
        identifier["value"],
        fill="black",
        font=font,
    )
    destination = Path(path)
    output.save(destination, format="PNG")
    return destination
