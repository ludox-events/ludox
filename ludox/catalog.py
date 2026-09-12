# Copyright (C) 2026 Matteo Sassi
# SPDX-License-Identifier: AGPL-3.0-only

"""Current catalog operations, without Tkinter or SQL.

Checks intentionally precede writes as in the original callbacks. Confirmation
of owner deactivation belongs to the UI; it can retry with explicit consent.
"""

from dataclasses import dataclass

from . import database as data

NomeDuplicato = data.NomeDuplicato


class NomeMancante(Exception):
    """A catalog name is empty after trimming."""


class ConfermaDisattivazione(Exception):
    """Owner still has copies; no write was performed."""


class GiocoInPrestito(Exception):
    """A game with open loans cannot be deactivated."""


class ProprietarioNonSelezionato(Exception):
    """No owner was selected for the quantity update."""


class QuantitaNonValida(Exception):
    """Quantity is not a nonnegative integer."""


class CopieInsufficienti(Exception):
    def __init__(self, fuori, nuovo_totale):
        self.fuori = fuori
        self.nuovo_totale = nuovo_totale
        super().__init__(
            f"Ci sono attualmente {fuori} copie di questo gioco in prestito.\n\n"
            f"Il totale non può essere ridotto a {nuovo_totale}."
        )


class ConfigurazioneNonValida(Exception):
    pass


def _nome_valido(nome):
    nome = nome.strip()
    if not nome:
        raise NomeMancante()
    return nome


def _chiave_nome(nome):
    return nome.casefold()


def aggiungi_proprietario(nome: str, *, event_id=None) -> int:
    nome = _nome_valido(nome)
    if event_id is not None:
        return data.inserisci_owner_label(event_id, nome, _chiave_nome(nome))
    return data.inserisci_proprietario(nome)


def modifica_proprietario(proprietario_id: int, nome: str, attivo: bool,
                         *, conferma_disattivazione=False, event_id=None) -> None:
    nome = _nome_valido(nome)
    if not conferma_disattivazione and not attivo:
        totale = (
            data.totale_copie_owner_label(event_id, proprietario_id)
            if event_id is not None
            else data.totale_copie_proprietario(proprietario_id)
        )
        if totale > 0:
            raise ConfermaDisattivazione()
    if event_id is not None:
        data.aggiorna_owner_label(
            event_id, proprietario_id, nome, _chiave_nome(nome),
            1 if attivo else 0,
        )
        return
    data.aggiorna_proprietario(proprietario_id, nome, 1 if attivo else 0)


def aggiungi_gioco(nome: str, *, event_id=None) -> int:
    nome = _nome_valido(nome)
    if event_id is not None:
        return data.inserisci_gioco_evento(event_id, nome, _chiave_nome(nome))
    return data.inserisci_gioco(nome)


def modifica_gioco(gioco_id: int, nome: str, attivo: bool, *, event_id=None) -> None:
    nome = _nome_valido(nome)
    fuori = (
        data.copie_in_prestito_evento(event_id, gioco_id)
        if event_id is not None else data.copie_in_prestito(gioco_id)
    )
    if not attivo and fuori > 0:
        raise GiocoInPrestito()
    if event_id is not None:
        data.aggiorna_gioco_evento(
            event_id, gioco_id, nome, _chiave_nome(nome), 1 if attivo else 0
        )
        return
    data.aggiorna_gioco(gioco_id, nome, 1 if attivo else 0)


def imposta_quantita(gioco_id: int, proprietario_id: int | None, valore: str,
                     *, event_id=None) -> None:
    if proprietario_id is None:
        raise ProprietarioNonSelezionato()
    try:
        quantita = int(valore)
        if quantita < 0:
            raise ValueError
    except ValueError as exc:
        raise QuantitaNonValida() from exc
    if event_id is not None:
        nuovo_totale = data.copie_altri_owner(
            event_id, gioco_id, proprietario_id
        ) + quantita
        fuori = data.copie_in_prestito_evento(event_id, gioco_id)
    else:
        nuovo_totale = data.copie_altri_proprietari(
            gioco_id, proprietario_id
        ) + quantita
        fuori = data.copie_in_prestito(gioco_id)
    if nuovo_totale < fuori:
        raise CopieInsufficienti(fuori, nuovo_totale)
    if event_id is not None:
        data.aggiorna_quantita_copie_evento(
            event_id, gioco_id, proprietario_id, quantita
        )
    else:
        data.aggiorna_quantita_copie(gioco_id, proprietario_id, quantita)


@dataclass(frozen=True)
class InventarioProprietario:
    righe: list[dict]
    totale_titoli: int
    totale_copie: int


def inventario_proprietario(proprietario_id: int, *, event_id=None) -> InventarioProprietario:
    source = (
        data.giochi_per_owner_evento(event_id, proprietario_id)
        if event_id is not None else data.giochi_per_proprietario(proprietario_id)
    )
    righe = [dict(row) for row in source]
    return InventarioProprietario(righe, len(righe), sum(r["copie_proprietario"] for r in righe))


def elenco_proprietari(*, event_id=None):
    source = (
        data.elenco_owner_labels(event_id)
        if event_id is not None else data.elenco_proprietari()
    )
    return [dict(row) for row in source]


def proprietario_per_id(proprietario_id, *, event_id=None):
    row = (
        data.owner_label_per_id(event_id, proprietario_id)
        if event_id is not None else data.proprietario_per_id(proprietario_id)
    )
    return dict(row) if row is not None else None


def totale_copie_proprietario(proprietario_id, *, event_id=None):
    if event_id is not None:
        return data.totale_copie_owner_label(event_id, proprietario_id)
    return data.totale_copie_proprietario(proprietario_id)


def elenco_giochi_backoffice(*, event_id=None):
    source = (
        data.elenco_giochi_evento_backoffice(event_id)
        if event_id is not None else data.elenco_giochi_backoffice()
    )
    return [dict(row) for row in source]


def gioco_per_id(gioco_id, *, event_id=None):
    row = (
        data.gioco_evento_per_id(event_id, gioco_id)
        if event_id is not None else data.gioco_per_id(gioco_id)
    )
    return dict(row) if row is not None else None


def copie_per_proprietario_del_gioco(gioco_id, *, event_id=None):
    source = (
        data.copie_per_owner_del_gioco(event_id, gioco_id)
        if event_id is not None
        else data.copie_per_proprietario_del_gioco(gioco_id)
    )
    return [dict(row) for row in source]


def riepilogo_proprietari_gioco(gioco_id, *, event_id=None):
    if event_id is not None:
        return data.riepilogo_owner_gioco(event_id, gioco_id)
    return data.riepilogo_proprietari_gioco(gioco_id)


def copie_in_prestito(gioco_id, *, event_id=None):
    if event_id is not None:
        return data.copie_in_prestito_evento(event_id, gioco_id)
    return data.copie_in_prestito(gioco_id)


def impostazioni_modulo(event_id):
    row = data.impostazioni_game_library(event_id)
    return dict(row) if row is not None else None


def modifica_impostazioni_modulo(event_id, max_slots, identification_mode="token"):
    try:
        max_slots = int(max_slots)
    except (TypeError, ValueError) as exc:
        raise ConfigurazioneNonValida() from exc
    if max_slots <= 0 or identification_mode not in ("token", "copy_identifier"):
        raise ConfigurazioneNonValida()
    if data.conta_sessioni_attive_evento(event_id):
        massimo_occupato = max(
            (row["token"] for row in data.slot_sessioni_aperte(event_id)),
            default=0,
        )
        if max_slots < massimo_occupato:
            raise ConfigurazioneNonValida()
    data.aggiorna_impostazioni_game_library(
        event_id, max_slots, identification_mode
    )
