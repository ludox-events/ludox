# Copyright (C) 2026 Matteo Sassi
# SPDX-License-Identifier: AGPL-3.0-only

"""Organization service tests with temporary SQLite databases."""

import subprocess
import sys
from pathlib import Path

import pytest

from ludox import config, organizations


def test_crud_senza_eliminazione(db):
    prima = organizations.crea_organizzazione(" Ludoteca Centro ")
    seconda = organizations.crea_organizzazione("Ludoteca Nord")

    assert prima == organizations.Organizzazione(1, "Ludoteca Centro", True)
    assert organizations.elenco_organizzazioni() == [prima, seconda]

    modificata = organizations.modifica_organizzazione(
        prima.id,
        nome="Ludoteca Centrale",
        attiva=False,
    )
    assert modificata == organizations.Organizzazione(
        prima.id, "Ludoteca Centrale", False
    )
    assert organizations.elenco_organizzazioni(solo_attive=True) == [seconda]
    assert not hasattr(organizations, "elimina_organizzazione")


def test_validazioni_creazione_e_modifica(db):
    for nome in ("  ", None):
        with pytest.raises(organizations.NomeOrganizzazioneMancante):
            organizations.crea_organizzazione(nome)
    with pytest.raises(organizations.OrganizzazioneNonTrovata):
        organizations.modifica_organizzazione(999, nome="Nome", attiva=True)


def test_nessuna_organizzazione_attiva_non_crea_un_default(db):
    inattiva = organizations.crea_organizzazione("Ludoteca Chiusa")
    organizations.imposta_stato(inattiva.id, attiva=False)
    configurazione = config.AppConfig(
        active_organization_id=99,
        active_organization_name="Precedente",
    )

    contesto = organizations.risolvi_contesto(configurazione)

    assert contesto.organizzazione is None
    assert contesto.selezione_richiesta is False
    assert contesto.configurazione.active_organization_id is None
    assert organizations.elenco_organizzazioni() == [
        organizations.Organizzazione(inattiva.id, inattiva.nome, False)
    ]


def test_unica_organizzazione_attiva_viene_selezionata_e_salvata(db, tmp_path):
    organizzazione = organizations.crea_organizzazione("Ludoteca Centro")
    percorso = tmp_path / "config.ini"

    contesto = organizations.sincronizza_contesto(config.AppConfig(), percorso)

    assert contesto.organizzazione == organizzazione
    assert contesto.selezione_richiesta is False
    assert config.load_config(percorso) == contesto.configurazione
    assert contesto.configurazione.active_organization_id == organizzazione.id
    assert contesto.configurazione.active_organization_name == organizzazione.nome


def test_piu_organizzazioni_usano_solo_un_riferimento_id_nome_coerente(db):
    prima = organizations.crea_organizzazione("Ludoteca Centro")
    organizations.crea_organizzazione("Ludoteca Nord")

    valido = organizations.risolvi_contesto(
        config.AppConfig(
            active_organization_id=prima.id,
            active_organization_name=prima.nome,
        )
    )
    non_valido = organizations.risolvi_contesto(
        config.AppConfig(
            active_organization_id=prima.id,
            active_organization_name="Altro database",
        )
    )

    assert valido.organizzazione == prima
    assert valido.selezione_richiesta is False
    assert non_valido.organizzazione is None
    assert non_valido.selezione_richiesta is True
    assert non_valido.configurazione.active_organization_id is None


def test_selezione_manual_salva_solo_organizzazioni_attive(db, tmp_path):
    attiva = organizations.crea_organizzazione("Ludoteca Centro")
    inattiva = organizations.crea_organizzazione("Ludoteca Chiusa")
    organizations.imposta_stato(inattiva.id, attiva=False)
    percorso = tmp_path / "config.ini"

    contesto = organizations.seleziona_organizzazione(
        attiva.id, config.AppConfig(), percorso
    )

    assert contesto.organizzazione == attiva
    assert config.load_config(percorso) == contesto.configurazione
    with pytest.raises(organizations.OrganizzazioneNonAttiva):
        organizations.seleziona_organizzazione(
            inattiva.id, contesto.configurazione, percorso
        )
    with pytest.raises(organizations.OrganizzazioneNonTrovata):
        organizations.seleziona_organizzazione(
            999, contesto.configurazione, percorso
        )
    assert config.load_config(percorso) == contesto.configurazione


def test_service_non_richiede_dipendenze_gui():
    root = Path(__file__).resolve().parents[1]
    code = """
import sys
class NoGUI:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('tkinter', 'ttkbootstrap', 'matplotlib'):
            raise AssertionError('GUI dependency: ' + fullname)
sys.meta_path.insert(0, NoGUI())
from ludox import organizations
assert 'ludox.ui' not in sys.modules
"""
    subprocess.run(
        [sys.executable, "-B", "-c", code],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
