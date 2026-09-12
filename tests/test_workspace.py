# Copyright (C) 2026 Matteo Sassi
# SPDX-License-Identifier: AGPL-3.0-only

"""Workspace switching and settings tests with temporary files only."""

import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from ludox import config, database as data, workspace


def salva(
    database,
    max_tokens="50",
    lingua="it",
    organizzazione_attiva_id=None,
    organizzazione_attiva_nome=None,
):
    return workspace.salva_impostazioni(
        lingua=lingua,
        max_tokens_testo=max_tokens,
        database_testo=database,
        nome_proprietario_predefinito="Biblioteca",
        organizzazione_attiva_id=organizzazione_attiva_id,
        organizzazione_attiva_nome=organizzazione_attiva_nome,
    )


def inserisci_documento_aperto(db, token):
    db.execute(
        "INSERT INTO documenti(token, ingresso) VALUES (?, '2026-09-12T10:00:00')",
        (token,),
    )
    db.commit()


def test_salvataggio_sullo_stesso_database_non_cambia_workspace(db):
    risultato = salva("test.db", max_tokens="23", lingua="en")

    assert risultato == workspace.ImpostazioniSalvate(
        config.AppConfig("en", 23, "test.db"), False
    )
    assert data.get_db_path() == config.PROJECT_DIR / "test.db"
    assert config.load_config(config.CONFIG_PATH) == risultato.configurazione


def test_salvataggio_preserva_il_contesto_organizzazione(db):
    risultato = salva(
        "test.db",
        organizzazione_attiva_id=3,
        organizzazione_attiva_nome="Ludoteca Centro",
    )

    assert risultato.configurazione.active_organization_id == 3
    assert risultato.configurazione.active_organization_name == "Ludoteca Centro"
    assert config.load_config(config.CONFIG_PATH) == risultato.configurazione


@pytest.mark.parametrize("valore", ["", "abc", "0", "-1"])
def test_token_non_validi_non_modificano_file_o_workspace(db, valore):
    precedente = data.get_db_path()

    with pytest.raises(workspace.TokenNonValidi):
        salva("test.db", max_tokens=valore)

    assert data.get_db_path() == precedente
    assert not config.CONFIG_PATH.exists()


def test_percorso_non_valido_non_modifica_file_o_workspace(db):
    precedente = data.get_db_path()

    with pytest.raises(workspace.DatabaseNonValido):
        salva("cartella-assente/evento.db")

    assert data.get_db_path() == precedente
    assert not config.CONFIG_PATH.exists()


def test_documenti_aperti_impediscono_il_cambio_database(db):
    inserisci_documento_aperto(db, 4)
    precedente = data.get_db_path()

    with pytest.raises(workspace.DatabaseInUso):
        salva("nuovo.db")

    assert data.get_db_path() == precedente
    assert not (config.PROJECT_DIR / "nuovo.db").exists()
    assert not config.CONFIG_PATH.exists()


def test_limite_incompatibile_nel_database_corrente_non_viene_salvato(db):
    inserisci_documento_aperto(db, 8)

    with pytest.raises(workspace.LimiteTokenCorrente) as errore:
        salva("test.db", max_tokens="7")

    assert errore.value.token == 8
    assert not config.CONFIG_PATH.exists()


def test_cambio_inizializza_database_e_salva_configurazione(db):
    risultato = salva("nuovo.db", max_tokens="17", lingua="en")
    destinazione = config.PROJECT_DIR / "nuovo.db"

    assert risultato.database_cambiato is True
    assert data.get_db_path() == destinazione
    assert destinazione.exists()
    assert data.proprietario_per_id(1)["nome"] == "Biblioteca"
    assert config.load_config(config.CONFIG_PATH) == config.AppConfig(
        "en", 17, "nuovo.db"
    )


def test_limite_incompatibile_nella_destinazione_ripristina_workspace(db):
    precedente = data.get_db_path()
    destinazione = config.PROJECT_DIR / "destinazione.db"
    data.set_db_path(destinazione)
    data.init_db()
    with data.get_db() as destinazione_db:
        inserisci_documento_aperto(destinazione_db, 9)
    data.set_db_path(precedente)

    with pytest.raises(workspace.LimiteTokenDestinazione) as errore:
        salva("destinazione.db", max_tokens="8")

    assert errore.value.token == 9
    assert data.get_db_path() == precedente
    assert not config.CONFIG_PATH.exists()


def test_errore_apertura_destinazione_ripristina_workspace(db, monkeypatch):
    precedente = data.get_db_path()

    def init_fallita(default_owner_name):
        raise sqlite3.DatabaseError("database non leggibile")

    monkeypatch.setattr(data, "init_db", init_fallita)

    with pytest.raises(workspace.CambioDatabaseFallito, match="non leggibile"):
        salva("destinazione.db")

    assert data.get_db_path() == precedente
    assert not config.CONFIG_PATH.exists()


def test_errore_salvataggio_ripristina_workspace(db, monkeypatch):
    precedente = data.get_db_path()

    def salvataggio_fallito(candidate, path):
        raise OSError("config non scrivibile")

    monkeypatch.setattr(config, "save_config", salvataggio_fallito)

    with pytest.raises(
        workspace.SalvataggioConfigurazioneFallito,
        match="non scrivibile",
    ):
        salva("destinazione.db")

    assert data.get_db_path() == precedente


def test_conversione_percorso_usa_la_configurazione_locale(tmp_path):
    percorso = tmp_path / "evento.db"
    assert workspace.impostazione_database_da_percorso(percorso) == "evento.db"


def test_workspace_non_richiede_dipendenze_gui():
    root = Path(__file__).resolve().parents[1]
    code = """
import sys
class NoGUI:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('tkinter', 'ttkbootstrap', 'matplotlib'):
            raise AssertionError('GUI dependency: ' + fullname)
sys.meta_path.insert(0, NoGUI())
from ludox import workspace
assert 'ludox.ui' not in sys.modules
"""
    subprocess.run(
        [sys.executable, "-B", "-c", code],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
