# Copyright (C) 2026 Matteo Sassi
# SPDX-License-Identifier: AGPL-3.0-only

"""Current lending workflows, independent of Tkinter.

Preserve the legacy validation order and transaction boundaries. In particular,
opening checks stock before its transaction, while changing checks under a lock.
Confirmation dialogs and translation belong to the caller.
"""

from dataclasses import dataclass

from . import database as data

ErrorePersistenza = data.ErrorePersistenza


class TokenLibero(Exception):
    """No open document is associated with the token."""


class PrestitoAssente(Exception):
    """The open document has no open loan."""


class TokenEsauriti(Exception):
    """No token is available within the configured limit."""


class GiocoNonDisponibile(Exception):
    """No copy is available for the requested operation."""


class CambioNonValido(Exception):
    """The displayed loan or the selected game is no longer valid."""


@dataclass(frozen=True)
class SituazionePrestito:
    documento: dict
    prestito: dict


@dataclass(frozen=True)
class PrestitoCreato:
    documento_id: int
    prestito_id: int
    token: int
    gioco_nome: str


def consulta_token(token: int) -> SituazionePrestito:
    documento = data.documento_aperto_da_token(token)
    if not documento:
        raise TokenLibero()
    prestito = data.prestito_aperto_documento(documento["id"])
    if not prestito:
        raise PrestitoAssente()
    return SituazionePrestito(dict(documento), dict(prestito))


def nuovo_prestito(gioco_id: int, max_tokens: int) -> PrestitoCreato:
    disponibili, _ = data.disponibilita_gioco(gioco_id)
    if disponibili <= 0:
        raise GiocoNonDisponibile("Non ci sono copie disponibili.")
    token = data.token_libero(max_tokens)
    if token is None:
        raise TokenEsauriti("Non ci sono posizioni documento libere.")

    timestamp = data.now_iso()
    with data.transazione_prestiti() as db:
        documento_id = data.inserisci_documento(db, token, timestamp)
        prestito_id = data.inserisci_prestito(db, documento_id, gioco_id, timestamp)
        gioco = data.nome_gioco_in_transazione(db, gioco_id)
    return PrestitoCreato(documento_id, prestito_id, token, gioco["nome"])


def cambia_gioco(
    *, token: int, documento_id: int, prestito_id: int,
    gioco_id_atteso: int, nuovo_gioco_id: int,
) -> str:
    timestamp = data.now_iso()
    with data.transazione_prestiti(immediata=True) as db:
        if not data.documento_per_cambio(db, documento_id, token):
            raise CambioNonValido(
                "Il documento non risulta più aperto. "
                "Il cambio non è stato registrato."
            )
        corrente = data.prestito_per_cambio(db, prestito_id, documento_id)
        if not corrente:
            raise CambioNonValido(
                "Il prestito è cambiato o è già stato chiuso. "
                "Il cambio non è stato registrato."
            )
        if corrente["gioco_id"] != gioco_id_atteso:
            raise CambioNonValido(
                "Il gioco associato al token è cambiato. "
                "Riapri la procedura di cambio."
            )
        nuovo = data.gioco_per_cambio(db, nuovo_gioco_id)
        if not nuovo or nuovo["attivo"] != 1:
            raise CambioNonValido(
                "Il gioco selezionato non è più disponibile "
                "nel catalogo attivo."
            )
        totali, fuori = data.conteggi_copie_in_transazione(db, nuovo_gioco_id)
        if totali - fuori <= 0:
            raise GiocoNonDisponibile(
                "Nel frattempo l'ultima copia disponibile "
                "è stata assegnata. Scegli un altro gioco."
            )
        if data.chiudi_prestito_per_cambio(db, prestito_id, documento_id, timestamp) != 1:
            raise CambioNonValido(
                "Non è stato possibile chiudere il prestito "
                "precedente. Nessuna modifica è stata salvata."
            )
        data.inserisci_prestito(db, documento_id, nuovo_gioco_id, timestamp)
    return nuovo["nome"]


def restituzione_finale(*, documento_id: int, prestito_id: int) -> None:
    """Call only after physical document return has been confirmed.

    As in the original callback, IDs are updated independently, with no new
    relationship checks; both updates precede the row-count checks.
    """
    timestamp = data.now_iso()
    with data.transazione_prestiti() as db:
        prestiti = data.chiudi_prestito_per_restituzione(db, prestito_id, timestamp)
        documenti = data.chiudi_documento_per_restituzione(db, documento_id, timestamp)
        if prestiti != 1:
            raise ErrorePersistenza("Il prestito non risulta più aperto.")
        if documenti != 1:
            raise ErrorePersistenza("Il documento non risulta più depositato.")
