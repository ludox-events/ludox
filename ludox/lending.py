# Copyright (C) 2026 Matteo Sassi
# SPDX-License-Identifier: AGPL-3.0-only

"""Current lending workflows, independent of Tkinter.

Preserve the legacy validation order and transaction boundaries. In particular,
opening checks stock before its transaction, while changing checks under a lock.
Confirmation dialogs and translation belong to the caller.
"""

from dataclasses import dataclass

from . import copy_identifiers
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


class ModalitaIdentificazioneNonValida(Exception):
    pass


class CopiaInattiva(Exception):
    pass


class GiocoInattivo(Exception):
    pass


class CopiaGiaInPrestito(Exception):
    pass


class PrestitoCopiaAssente(Exception):
    pass


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
    copy_id: int | None = None
    copy_identifier: str | None = None

    @property
    def slot(self):
        return self.token


@dataclass(frozen=True)
class RiepilogoHome:
    prestiti: int
    documenti: int
    documenti_attivi: int


@dataclass(frozen=True)
class SituazioneChiusura:
    documenti_attivi: int
    token: tuple[int, ...]


@dataclass(frozen=True)
class SituazionePrestitoCopia:
    event_id: int
    session_id: int
    loan_id: int
    slot: int
    copy_id: int
    copy_identifier: str
    game_id: int
    game_name: str


@dataclass(frozen=True)
class CambioCopiaPreparato:
    corrente: SituazionePrestitoCopia
    new_copy_id: int
    new_copy_identifier: str
    new_game_id: int
    new_game_name: str


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
    if event_id is not None:
        settings = data.impostazioni_game_library(event_id)
        if settings is None:
            raise ErrorePersistenza("Il modulo Prestiti Ludoteca non è configurato.")
        if settings["identification_mode"] != "token":
            raise ModalitaIdentificazioneNonValida(
                "L'Event corrente usa la modalità copy_identifier."
            )
    disponibili, _ = disponibilita_gioco(gioco_id, event_id=event_id)
    if disponibili <= 0:
        raise GiocoNonDisponibile("Non ci sono copie disponibili.")
    if event_id is not None:
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


def nuovo_prestito_da_identificatore(
    copy_identifier: str, *, event_id: int
) -> PrestitoCreato:
    """Open a copy-specific session atomically from keyboard/HID input."""
    identifier = copy_identifiers.normalize_identifier(copy_identifier)
    timestamp = data.now_iso()
    with data.transazione_prestiti(immediata=True) as db:
        settings = data.impostazioni_game_library_in_transazione(db, event_id)
        if settings is None:
            raise ErrorePersistenza("Il modulo Prestiti Ludoteca non è configurato.")
        if settings["identification_mode"] != "copy_identifier":
            raise ModalitaIdentificazioneNonValida(
                "L'Event corrente usa la modalità token."
            )
        copy = data.copia_da_identificatore_in_transazione(
            db, event_id, identifier
        )
        if copy is None:
            raise copy_identifiers.UnknownCopyIdentifier(
                "Identificatore sconosciuto nell'Event corrente."
            )
        if not copy["copy_active"]:
            raise CopiaInattiva("La copia identificata non è attiva.")
        if not copy["game_active"]:
            raise GiocoInattivo("Il gioco associato alla copia non è attivo.")
        if data.copia_in_prestito_in_transazione(
            db, event_id, copy["copy_id"]
        ):
            raise CopiaGiaInPrestito("La copia risulta già in prestito.")
        slot = data.slot_libero_in_transazione(
            db, event_id, settings["max_slots"]
        )
        if slot is None:
            raise TokenEsauriti("Non ci sono posizioni documento libere.")
        session_id = data.inserisci_sessione(db, event_id, slot, timestamp)
        loan_id = data.inserisci_prestito_evento(
            db,
            event_id,
            session_id,
            copy["game_id"],
            timestamp,
            copy_id=copy["copy_id"],
        )
    return PrestitoCreato(
        session_id,
        loan_id,
        slot,
        copy["game_name"],
        copy["copy_id"],
        copy["copy_identifier"],
    )


def consulta_copia_in_prestito(
    copy_identifier: str, *, event_id: int
) -> SituazionePrestitoCopia:
    settings = data.impostazioni_game_library(event_id)
    if settings is None:
        raise ErrorePersistenza("Il modulo Prestiti Ludoteca non è configurato.")
    if settings["identification_mode"] != "copy_identifier":
        raise ModalitaIdentificazioneNonValida(
            "L'Event corrente usa la modalità token."
        )
    copy = copy_identifiers.resolve(event_id, copy_identifier)
    loan = data.prestito_aperto_per_copia(event_id, copy["copy_id"])
    if loan is None:
        raise PrestitoCopiaAssente(
            "La copia identificata non risulta in un prestito aperto."
        )
    return SituazionePrestitoCopia(
        event_id,
        loan["session_id"],
        loan["loan_id"],
        loan["slot"],
        copy["copy_id"],
        copy["copy_identifier"],
        loan["game_id"],
        loan["game_name"],
    )


def prepara_cambio_copia(
    returned_identifier: str, new_identifier: str, *, event_id: int
) -> CambioCopiaPreparato:
    corrente = consulta_copia_in_prestito(
        returned_identifier, event_id=event_id
    )
    new_copy = copy_identifiers.resolve(event_id, new_identifier)
    if not new_copy["copy_active"]:
        raise CopiaInattiva("La nuova copia identificata non è attiva.")
    if not new_copy["game_active"]:
        raise GiocoInattivo("Il gioco associato alla nuova copia non è attivo.")
    if data.copia_ha_prestito_aperto(event_id, new_copy["copy_id"]):
        raise CopiaGiaInPrestito("La nuova copia risulta già in prestito.")
    return CambioCopiaPreparato(
        corrente,
        new_copy["copy_id"],
        new_copy["copy_identifier"],
        new_copy["game_id"],
        new_copy["game_name"],
    )


def conferma_cambio_copia(prepared: CambioCopiaPreparato) -> str:
    """Apply a fully prepared copy change in one immediate transaction."""
    timestamp = data.now_iso()
    corrente = prepared.corrente
    with data.transazione_prestiti(immediata=True) as db:
        settings = data.impostazioni_game_library_in_transazione(
            db, corrente.event_id
        )
        if settings is None or settings["identification_mode"] != "copy_identifier":
            raise ModalitaIdentificazioneNonValida(
                "La modalità operativa dell'Event è cambiata."
            )
        session = data.sessione_per_cambio(
            db, corrente.event_id, corrente.session_id, corrente.slot
        )
        loan = data.prestito_evento_per_cambio(
            db, corrente.event_id, corrente.loan_id, corrente.session_id
        )
        if not session or not loan or loan["copy_id"] != corrente.copy_id:
            raise CambioNonValido(
                "Il prestito restituito è cambiato o è già stato chiuso."
            )
        new_copy = data.copia_evento_per_id_in_transazione(
            db, corrente.event_id, prepared.new_copy_id
        )
        if (
            new_copy is None
            or new_copy["copy_identifier"] != prepared.new_copy_identifier
            or new_copy["game_id"] != prepared.new_game_id
            or not new_copy["copy_active"]
            or not new_copy["game_active"]
        ):
            raise CambioNonValido(
                "La nuova copia non è più valida o disponibile."
            )
        if data.copia_in_prestito_in_transazione(
            db, corrente.event_id, prepared.new_copy_id
        ):
            raise CopiaGiaInPrestito("La nuova copia risulta già in prestito.")
        if data.chiudi_prestito_evento_per_cambio(
            db,
            corrente.event_id,
            corrente.loan_id,
            corrente.session_id,
            timestamp,
        ) != 1:
            raise CambioNonValido(
                "Non è stato possibile chiudere il prestito precedente."
            )
        data.inserisci_prestito_evento(
            db,
            corrente.event_id,
            corrente.session_id,
            prepared.new_game_id,
            timestamp,
            copy_id=prepared.new_copy_id,
        )
    return prepared.new_game_name


def conferma_restituzione_copia(situation: SituazionePrestitoCopia) -> None:
    """Close the identified-copy loan and its document session atomically."""
    timestamp = data.now_iso()
    with data.transazione_prestiti(immediata=True) as db:
        settings = data.impostazioni_game_library_in_transazione(
            db, situation.event_id
        )
        if settings is None or settings["identification_mode"] != "copy_identifier":
            raise ModalitaIdentificazioneNonValida(
                "La modalita operativa dell'Event e cambiata."
            )
        session = data.sessione_per_cambio(
            db, situation.event_id, situation.session_id, situation.slot
        )
        loan = data.prestito_evento_per_cambio(
            db, situation.event_id, situation.loan_id, situation.session_id
        )
        if not session or not loan or loan["copy_id"] != situation.copy_id:
            raise ErrorePersistenza(
                "Il prestito della copia non risulta piu aperto."
            )
        if data.chiudi_prestito_evento_per_cambio(
            db,
            situation.event_id,
            situation.loan_id,
            situation.session_id,
            timestamp,
        ) != 1:
            raise ErrorePersistenza(
                "Il prestito della copia non risulta piu aperto."
            )
        if data.chiudi_sessione_evento(
            db, situation.event_id, situation.session_id, timestamp
        ) != 1:
            raise ErrorePersistenza(
                "Il documento non risulta piu depositato."
            )


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
