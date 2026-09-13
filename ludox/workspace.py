# Copyright (C) 2026 Matteo Sassi
# SPDX-License-Identifier: AGPL-3.0-only

"""Workspace and local-settings operations independent of Tkinter."""

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from . import bootstrap, config
from . import database as data
from . import events, migrations, organizations


class DatabaseNonValido(Exception):
    """The requested database setting cannot be normalized."""

    def __init__(self, errore):
        self.dettaglio = str(errore)
        super().__init__(self.dettaglio)


class DatabaseInUso(Exception):
    """The current workspace still contains deposited documents."""


class CambioDatabaseFallito(Exception):
    def __init__(self, errore):
        self.dettaglio = str(errore)
        super().__init__(self.dettaglio)


class SalvataggioConfigurazioneFallito(Exception):
    def __init__(self, errore):
        self.dettaglio = str(errore)
        super().__init__(self.dettaglio)


@dataclass(frozen=True)
class ImpostazioniSalvate:
    configurazione: config.AppConfig
    database_cambiato: bool


def impostazione_database_da_percorso(percorso: str | Path) -> str:
    return config.database_setting_from_path(percorso)


def salva_impostazioni(
    *,
    lingua: str,
    database_testo: str,
    nome_proprietario_predefinito: str,
    organizzazione_attiva_id: int | None = None,
    organizzazione_attiva_nome: str | None = None,
    evento_attivo_id: int | None = None,
    evento_attivo_slug: str | None = None,
    migrazione_autorizzata: bool = False,
) -> ImpostazioniSalvate:
    try:
        database = config.normalize_database_setting(database_testo)
        percorso_destinazione = config.resolve_database_path(database)
    except (OSError, ValueError) as exc:
        raise DatabaseNonValido(exc) from exc

    percorso_corrente = data.get_db_path().resolve(strict=False)
    database_cambiato = percorso_destinazione != percorso_corrente

    if database_cambiato:
        sessioni_aperte = (
            data.game_library_ha_aperti(evento_attivo_id)
            if evento_attivo_id is not None
            else data.conta_documenti_attivi() > 0
        )
        if sessioni_aperte:
            raise DatabaseInUso()

    percorso_precedente = percorso_corrente
    cambiato = False
    if database_cambiato:
        try:
            data.set_db_path(percorso_destinazione)
            cambiato = True
            data.init_db(
                default_owner_name=nome_proprietario_predefinito,
                migration_authorized=migrazione_autorizzata,
            )
        except (
            bootstrap.MigrationApprovalRequired,
            bootstrap.BackupCreationFailed,
            bootstrap.MigrationExecutionFailed,
            migrations.MigrationError,
        ):
            data.set_db_path(percorso_precedente)
            cambiato = False
            raise
        except (sqlite3.Error, OSError, ValueError) as exc:
            data.set_db_path(percorso_precedente)
            cambiato = False
            raise CambioDatabaseFallito(exc) from exc

    candidato = config.AppConfig(
        language=lingua,
        database=database,
        active_organization_id=organizzazione_attiva_id,
        active_organization_name=organizzazione_attiva_nome,
        active_event_id=evento_attivo_id,
        active_event_slug=evento_attivo_slug,
    )
    try:
        candidato = organizations.risolvi_contesto(candidato).configurazione
        candidato = events.resolve_context(
            candidato,
            candidato.active_organization_id,
        ).configuration
    except sqlite3.Error as exc:
        if cambiato:
            data.set_db_path(percorso_precedente)
        raise CambioDatabaseFallito(exc) from exc

    try:
        config.save_config(candidato, config.CONFIG_PATH)
    except (OSError, ValueError) as exc:
        if cambiato:
            data.set_db_path(percorso_precedente)
        raise SalvataggioConfigurazioneFallito(exc) from exc

    return ImpostazioniSalvate(candidato, database_cambiato)
