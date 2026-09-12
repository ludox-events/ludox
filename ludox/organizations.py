# Copyright (C) 2026 Matteo Sassi
# SPDX-License-Identifier: AGPL-3.0-only

"""Organization operations and active organization context."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from . import config
from . import database as data


class NomeOrganizzazioneMancante(Exception):
    """The organization name is empty."""


class OrganizzazioneNonTrovata(Exception):
    """The requested organization does not exist."""


class OrganizzazioneNonAttiva(Exception):
    """The requested organization cannot be selected because it is inactive."""


@dataclass(frozen=True)
class Organizzazione:
    id: int
    nome: str
    attiva: bool


@dataclass(frozen=True)
class ContestoOrganizzazione:
    organizzazione: Organizzazione | None
    configurazione: config.AppConfig
    selezione_richiesta: bool


def _da_riga(riga) -> Organizzazione:
    return Organizzazione(
        id=riga["id"],
        nome=riga["name"],
        attiva=bool(riga["active"]),
    )


def _nome_valido(nome: str) -> str:
    valore = nome.strip() if isinstance(nome, str) else ""
    if not valore:
        raise NomeOrganizzazioneMancante()
    return valore


def elenco_organizzazioni(*, solo_attive: bool = False) -> list[Organizzazione]:
    return [
        _da_riga(riga)
        for riga in data.elenco_organizzazioni(solo_attive=solo_attive)
    ]


def organizzazione_per_id(organizzazione_id: int) -> Organizzazione | None:
    riga = data.organizzazione_per_id(organizzazione_id)
    return _da_riga(riga) if riga is not None else None


def crea_organizzazione(nome: str) -> Organizzazione:
    organizzazione_id = data.inserisci_organizzazione(_nome_valido(nome))
    return organizzazione_per_id(organizzazione_id)


def modifica_organizzazione(
    organizzazione_id: int,
    *,
    nome: str,
    attiva: bool,
) -> Organizzazione:
    if organizzazione_per_id(organizzazione_id) is None:
        raise OrganizzazioneNonTrovata()
    data.aggiorna_organizzazione(
        organizzazione_id,
        nome=_nome_valido(nome),
        attiva=bool(attiva),
    )
    return organizzazione_per_id(organizzazione_id)


def imposta_stato(
    organizzazione_id: int,
    *,
    attiva: bool,
) -> Organizzazione:
    organizzazione = organizzazione_per_id(organizzazione_id)
    if organizzazione is None:
        raise OrganizzazioneNonTrovata()
    return modifica_organizzazione(
        organizzazione_id,
        nome=organizzazione.nome,
        attiva=attiva,
    )


def _con_riferimento(
    configurazione: config.AppConfig,
    organizzazione: Organizzazione | None,
) -> config.AppConfig:
    return replace(
        configurazione,
        active_organization_id=(
            organizzazione.id if organizzazione is not None else None
        ),
        active_organization_name=(
            organizzazione.nome if organizzazione is not None else None
        ),
    )


def risolvi_contesto(
    configurazione: config.AppConfig,
) -> ContestoOrganizzazione:
    attive = elenco_organizzazioni(solo_attive=True)
    if not attive:
        return ContestoOrganizzazione(
            organizzazione=None,
            configurazione=_con_riferimento(configurazione, None),
            selezione_richiesta=False,
        )

    if len(attive) == 1:
        organizzazione = attive[0]
        return ContestoOrganizzazione(
            organizzazione=organizzazione,
            configurazione=_con_riferimento(configurazione, organizzazione),
            selezione_richiesta=False,
        )

    organizzazione = next(
        (
            elemento
            for elemento in attive
            if elemento.id == configurazione.active_organization_id
            and elemento.nome == configurazione.active_organization_name
        ),
        None,
    )
    return ContestoOrganizzazione(
        organizzazione=organizzazione,
        configurazione=_con_riferimento(configurazione, organizzazione),
        selezione_richiesta=organizzazione is None,
    )


def sincronizza_contesto(
    configurazione: config.AppConfig,
    percorso_configurazione: Path | None = None,
) -> ContestoOrganizzazione:
    contesto = risolvi_contesto(configurazione)
    if contesto.configurazione != configurazione:
        config.save_config(
            contesto.configurazione,
            percorso_configurazione or config.CONFIG_PATH,
        )
    return contesto


def seleziona_organizzazione(
    organizzazione_id: int,
    configurazione: config.AppConfig,
    percorso_configurazione: Path | None = None,
) -> ContestoOrganizzazione:
    organizzazione = organizzazione_per_id(organizzazione_id)
    if organizzazione is None:
        raise OrganizzazioneNonTrovata()
    if not organizzazione.attiva:
        raise OrganizzazioneNonAttiva()

    aggiornata = _con_riferimento(configurazione, organizzazione)
    config.save_config(
        aggiornata,
        percorso_configurazione or config.CONFIG_PATH,
    )
    return ContestoOrganizzazione(
        organizzazione=organizzazione,
        configurazione=aggiornata,
        selezione_richiesta=False,
    )
