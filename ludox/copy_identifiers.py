# Copyright (C) 2026 Matteo Sassi
# SPDX-License-Identifier: AGPL-3.0-only

"""Event-scoped operational identifiers for physical game copies."""

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
