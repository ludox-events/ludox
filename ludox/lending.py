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


@dataclass(frozen=True)
class RiepilogoHome:
    prestiti: int
    documenti: int
    documenti_attivi: int


@dataclass(frozen=True)
class SituazioneChiusura:
    documenti_attivi: int
    token: tuple[int, ...]


def riepilogo_home(*, event_id=None) -> RiepilogoHome:
    if event_id is not None:
        return RiepilogoHome(
            prestiti=data.conta_prestiti_evento(event_id),
            documenti=data.conta_sessioni_evento(event_id),
            documenti_attivi=data.conta_sessioni_attive_evento(event_id),
        )
    return RiepilogoHome(
        prestiti=data.conta_prestiti(),
        documenti=data.conta_documenti(),
        documenti_attivi=data.conta_documenti_attivi(),
    )


def cerca_giochi_con_disponibilita(
    testo="", gioco_da_escludere=None, *, event_id=None
) -> list[dict]:
    giochi = []
    source = (
        data.cerca_giochi_evento(event_id, testo)
        if event_id is not None else data.cerca_giochi(testo)
    )
    for row in source:
        gioco = dict(row)
        if gioco["id"] == gioco_da_escludere:
            continue
        disponibili, totali = disponibilita_gioco(
            gioco["id"], event_id=event_id
        )
        gioco["disponibili"] = disponibili
        gioco["copie_totali"] = totali
        giochi.append(gioco)
    return giochi


def disponibilita_gioco(gioco_id: int, *, event_id=None) -> tuple[int, int]:
    if event_id is not None:
        return data.disponibilita_gioco_evento(event_id, gioco_id)
    return data.disponibilita_gioco(gioco_id)


def situazione_chiusura(*, event_id=None) -> SituazioneChiusura:
    if event_id is not None:
        return SituazioneChiusura(
            documenti_attivi=data.conta_sessioni_attive_evento(event_id),
            token=tuple(row["token"] for row in data.slot_sessioni_aperte(event_id)),
        )
    return SituazioneChiusura(
        documenti_attivi=data.conta_documenti_attivi(),
        token=tuple(row["token"] for row in data.token_documenti_aperti()),
    )


def consulta_token(token: int, *, event_id=None) -> SituazionePrestito:
    documento = (
        data.sessione_aperta_da_slot(event_id, token)
        if event_id is not None else data.documento_aperto_da_token(token)
    )
    if not documento:
        raise TokenLibero()
    prestito = (
        data.prestito_aperto_sessione(event_id, documento["id"])
        if event_id is not None
        else data.prestito_aperto_documento(documento["id"])
    )
    if not prestito:
        raise PrestitoAssente()
    return SituazionePrestito(dict(documento), dict(prestito))


def nuovo_prestito(gioco_id: int, max_tokens: int | None = None,
                   *, event_id=None) -> PrestitoCreato:
    disponibili, _ = disponibilita_gioco(gioco_id, event_id=event_id)
    if disponibili <= 0:
        raise GiocoNonDisponibile("Non ci sono copie disponibili.")
    if event_id is not None:
        settings = data.impostazioni_game_library(event_id)
        if settings is None:
            raise ErrorePersistenza("Il modulo Prestiti Ludoteca non è configurato.")
        token = data.slot_libero(event_id, settings["max_slots"])
    else:
        token = data.token_libero(max_tokens)
    if token is None:
        raise TokenEsauriti("Non ci sono posizioni documento libere.")

    timestamp = data.now_iso()
    with data.transazione_prestiti() as db:
        if event_id is not None:
            documento_id = data.inserisci_sessione(db, event_id, token, timestamp)
            prestito_id = data.inserisci_prestito_evento(
                db, event_id, documento_id, gioco_id, timestamp
            )
            gioco = data.nome_gioco_evento_in_transazione(
                db, event_id, gioco_id
            )
        else:
            documento_id = data.inserisci_documento(db, token, timestamp)
            prestito_id = data.inserisci_prestito(
                db, documento_id, gioco_id, timestamp
            )
            gioco = data.nome_gioco_in_transazione(db, gioco_id)
    return PrestitoCreato(documento_id, prestito_id, token, gioco["nome"])


def cambia_gioco(
    *, token: int, documento_id: int, prestito_id: int,
    gioco_id_atteso: int, nuovo_gioco_id: int, event_id=None,
) -> str:
    timestamp = data.now_iso()
    with data.transazione_prestiti(immediata=True) as db:
        documento_valido = (
            data.sessione_per_cambio(db, event_id, documento_id, token)
            if event_id is not None
            else data.documento_per_cambio(db, documento_id, token)
        )
        if not documento_valido:
            raise CambioNonValido(
                "Il documento non risulta più aperto. "
                "Il cambio non è stato registrato."
            )
        corrente = (
            data.prestito_evento_per_cambio(
                db, event_id, prestito_id, documento_id
            )
            if event_id is not None
            else data.prestito_per_cambio(db, prestito_id, documento_id)
        )
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
        nuovo = (
            data.gioco_evento_per_cambio(db, event_id, nuovo_gioco_id)
            if event_id is not None
            else data.gioco_per_cambio(db, nuovo_gioco_id)
        )
        if not nuovo or nuovo["attivo"] != 1:
            raise CambioNonValido(
                "Il gioco selezionato non è più disponibile "
                "nel catalogo attivo."
            )
        if event_id is not None:
            totali, fuori = data.conteggi_copie_evento_in_transazione(
                db, event_id, nuovo_gioco_id
            )
        else:
            totali, fuori = data.conteggi_copie_in_transazione(db, nuovo_gioco_id)
        if totali - fuori <= 0:
            raise GiocoNonDisponibile(
                "Nel frattempo l'ultima copia disponibile "
                "è stata assegnata. Scegli un altro gioco."
            )
        chiusi = (
            data.chiudi_prestito_evento_per_cambio(
                db, event_id, prestito_id, documento_id, timestamp
            )
            if event_id is not None
            else data.chiudi_prestito_per_cambio(
                db, prestito_id, documento_id, timestamp
            )
        )
        if chiusi != 1:
            raise CambioNonValido(
                "Non è stato possibile chiudere il prestito "
                "precedente. Nessuna modifica è stata salvata."
            )
        if event_id is not None:
            data.inserisci_prestito_evento(
                db, event_id, documento_id, nuovo_gioco_id, timestamp
            )
        else:
            data.inserisci_prestito(db, documento_id, nuovo_gioco_id, timestamp)
    return nuovo["nome"]


def restituzione_finale(*, documento_id: int, prestito_id: int,
                        event_id=None) -> None:
    """Call only after physical document return has been confirmed.

    As in the original callback, IDs are updated independently, with no new
    relationship checks; both updates precede the row-count checks.
    """
    timestamp = data.now_iso()
    with data.transazione_prestiti() as db:
        if event_id is not None:
            prestiti = data.chiudi_prestito_evento(
                db, event_id, prestito_id, timestamp
            )
            documenti = data.chiudi_sessione_evento(
                db, event_id, documento_id, timestamp
            )
        else:
            prestiti = data.chiudi_prestito_per_restituzione(
                db, prestito_id, timestamp
            )
            documenti = data.chiudi_documento_per_restituzione(
                db, documento_id, timestamp
            )
        if prestiti != 1:
            raise ErrorePersistenza("Il prestito non risulta più aperto.")
        if documenti != 1:
            raise ErrorePersistenza("Il documento non risulta più depositato.")
