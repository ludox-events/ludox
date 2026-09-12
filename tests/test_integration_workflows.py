# Copyright (C) 2026 Matteo Sassi
# SPDX-License-Identifier: AGPL-3.0-only

"""Integration tests across services and real temporary SQLite persistence."""

from datetime import datetime

import pytest

from ludox import (
    catalog,
    config,
    database,
    lending,
    migrations,
    organizations,
    reporting,
    workspace,
)


def imposta_orologio(monkeypatch, *timestamp):
    valori = iter(timestamp)
    monkeypatch.setattr(database, "now_iso", lambda: next(valori))


def salva_workspace(database_testo):
    return workspace.salva_impostazioni(
        lingua="it",
        max_tokens_testo="20",
        database_testo=database_testo,
        nome_proprietario_predefinito="Organizzazione",
    )


def test_migration_legacy_preserva_catalogo_e_avvia_contesto_organizzazione(
    isolated_files,
    tmp_path,
):
    database.initialize_current_schema("Proprietario legacy")
    proprietario_id = catalog.elenco_proprietari()[0]["id"]
    gioco_id = catalog.aggiungi_gioco("Gioco legacy")
    catalog.imposta_quantita(gioco_id, proprietario_id, "2")

    with database.get_db() as connection:
        assert migrations.schema_version(connection) == 0
        assert connection.execute(
            "SELECT name FROM sqlite_schema WHERE name = 'organizations'"
        ).fetchone() is None

    risultato = database.init_db(
        migration_authorized=True,
        now=datetime(2026, 9, 12, 18, 30),
    )

    assert risultato.migration_result.applied_versions == (1,)
    assert risultato.backup_path.is_file()
    assert organizations.elenco_organizzazioni() == []
    assert [row["nome"] for row in catalog.elenco_proprietari()] == [
        "Proprietario legacy"
    ]
    assert catalog.gioco_per_id(gioco_id)["nome"] == "Gioco legacy"
    assert catalog.totale_copie_proprietario(proprietario_id) == 2

    percorso_configurazione = tmp_path / "config.ini"
    prima = organizations.crea_organizzazione("Ludoteca Centro")
    contesto = organizations.sincronizza_contesto(
        config.AppConfig(),
        percorso_configurazione,
    )
    assert contesto.organizzazione == prima
    assert config.load_config(percorso_configurazione) == contesto.configurazione

    seconda = organizations.crea_organizzazione("Ludoteca Nord")
    contesto = organizations.seleziona_organizzazione(
        seconda.id,
        contesto.configurazione,
        percorso_configurazione,
    )
    assert contesto.organizzazione == seconda

    organizations.imposta_stato(seconda.id, attiva=False)
    contesto = organizations.sincronizza_contesto(
        contesto.configurazione,
        percorso_configurazione,
    )
    assert contesto.organizzazione == prima
    assert config.load_config(percorso_configurazione) == contesto.configurazione


def test_flusso_completo_alimenta_storici_statistiche_e_report(db, monkeypatch):
    imposta_orologio(
        monkeypatch,
        "2026-09-12T10:00:00",
        "2026-09-12T11:00:00",
        "2026-09-12T12:30:00",
    )
    proprietario_id = catalog.aggiungi_proprietario("Biblioteca")
    azul_id = catalog.aggiungi_gioco("Azul")
    cascadia_id = catalog.aggiungi_gioco("Cascadia")
    catalog.imposta_quantita(azul_id, proprietario_id, "2")
    catalog.imposta_quantita(cascadia_id, proprietario_id, "1")

    inventario = catalog.inventario_proprietario(proprietario_id)
    assert (inventario.totale_titoli, inventario.totale_copie) == (2, 3)

    prestito = lending.nuovo_prestito(azul_id, max_tokens=20)
    assert (prestito.token, prestito.gioco_nome) == (1, "Azul")
    assert lending.riepilogo_home() == lending.RiepilogoHome(1, 1, 1)
    assert lending.situazione_chiusura().token == (1,)
    assert lending.disponibilita_gioco(azul_id) == (1, 2)

    nuovo_nome = lending.cambia_gioco(
        token=prestito.token,
        documento_id=prestito.documento_id,
        prestito_id=prestito.prestito_id,
        gioco_id_atteso=azul_id,
        nuovo_gioco_id=cascadia_id,
    )
    situazione = lending.consulta_token(prestito.token)
    assert nuovo_nome == "Cascadia"
    assert situazione.prestito["gioco_id"] == cascadia_id
    assert lending.disponibilita_gioco(azul_id) == (2, 2)
    assert lending.disponibilita_gioco(cascadia_id) == (0, 1)

    lending.restituzione_finale(
        documento_id=prestito.documento_id,
        prestito_id=situazione.prestito["id"],
    )
    assert lending.riepilogo_home() == lending.RiepilogoHome(2, 1, 0)
    assert lending.situazione_chiusura() == lending.SituazioneChiusura(0, ())
    assert lending.disponibilita_gioco(azul_id) == (2, 2)
    assert lending.disponibilita_gioco(cascadia_id) == (1, 1)
    with pytest.raises(lending.TokenLibero):
        lending.consulta_token(prestito.token)

    storico_prestiti = reporting.storico_prestiti()
    storico_documenti = reporting.storico_documenti()
    assert (storico_prestiti.totale, storico_prestiti.attivi) == (2, 0)
    assert [row["gioco"] for row in storico_prestiti.righe] == [
        "Cascadia",
        "Azul",
    ]
    assert (storico_documenti.totale, storico_documenti.attivi) == (1, 0)
    assert storico_documenti.righe[0]["numero_prestiti"] == 2

    statistiche = reporting.statistiche_periodo(
        datetime(2026, 9, 12, 13, 0),
        ore=3,
        minuti_bucket=60,
    )
    assert (statistiche.prestiti, statistiche.documenti) == (2, 1)
    assert [
        (punto["prestiti"], punto["documenti"])
        for punto in statistiche.punti
    ] == [(1, 1), (1, 0), (0, 0)]

    report_documenti = reporting.report_documenti(
        datetime(2026, 9, 12),
        datetime(2026, 9, 12),
    )
    assert (report_documenti.totale_documenti, report_documenti.totale_prestiti) == (
        1,
        2,
    )
    assert report_documenti.righe[0]["tempo_documento_secondi"] == 150 * 60
    assert report_documenti.durata_mediana_prestito_secondi == 75 * 60

    report_utilizzo = reporting.report_utilizzo(
        datetime(2026, 9, 12),
        datetime(2026, 9, 12),
        proprietario_id=proprietario_id,
    )
    assert [row["gioco"] for row in report_utilizzo.righe] == ["Azul", "Cascadia"]
    assert [row["prestiti"] for row in report_utilizzo.righe] == [1, 1]
    assert report_utilizzo.totale_prestiti == 2
    assert report_utilizzo.tempo_totale_fuori_secondi == 150 * 60
    assert report_utilizzo.durata_mediana_prestito_secondi == 75 * 60


def test_cambio_workspace_isola_e_ripristina_i_dati(db, monkeypatch):
    imposta_orologio(
        monkeypatch,
        "2026-09-12T09:00:00",
        "2026-09-12T10:00:00",
    )
    primo_workspace = database.get_db_path()
    primo_proprietario = catalog.aggiungi_proprietario("Proprietario A")
    primo_gioco = catalog.aggiungi_gioco("Gioco A")
    catalog.imposta_quantita(primo_gioco, primo_proprietario, "1")
    prestito = lending.nuovo_prestito(primo_gioco, max_tokens=20)
    lending.restituzione_finale(
        documento_id=prestito.documento_id,
        prestito_id=prestito.prestito_id,
    )

    secondo = salva_workspace("secondo.db")
    assert secondo.database_cambiato is True
    assert database.get_db_path() == config.PROJECT_DIR / "secondo.db"
    assert lending.riepilogo_home() == lending.RiepilogoHome(0, 0, 0)
    assert catalog.elenco_giochi_backoffice() == []
    assert reporting.storico_prestiti().totale == 0
    assert reporting.storico_documenti().totale == 0

    secondo_proprietario = catalog.aggiungi_proprietario("Proprietario B")
    secondo_gioco = catalog.aggiungi_gioco("Gioco B")
    catalog.imposta_quantita(secondo_gioco, secondo_proprietario, "3")
    assert [row["nome"] for row in catalog.elenco_giochi_backoffice()] == ["Gioco B"]

    ripristinato = salva_workspace("test.db")
    assert ripristinato.database_cambiato is True
    assert database.get_db_path() == primo_workspace
    assert lending.riepilogo_home() == lending.RiepilogoHome(1, 1, 0)
    assert [row["nome"] for row in catalog.elenco_giochi_backoffice()] == ["Gioco A"]
    assert [row["nome"] for row in catalog.elenco_proprietari()] == [
        "Organizzazione",
        "Proprietario A",
    ]
    assert reporting.storico_prestiti().righe[0]["gioco"] == "Gioco A"

    report = reporting.report_utilizzo(
        datetime(2026, 9, 12),
        datetime(2026, 9, 12),
        proprietario_id=primo_proprietario,
    )
    assert (report.totale_titoli, report.totale_prestiti) == (1, 1)
    assert report.righe[0]["gioco"] == "Gioco A"


def test_tre_sessioni_intercalate_restano_indipendenti(db, monkeypatch):
    imposta_orologio(
        monkeypatch,
        "2026-09-12T10:00:00",
        "2026-09-12T10:05:00",
        "2026-09-12T10:10:00",
        "2026-09-12T10:30:00",
        "2026-09-12T11:00:00",
    )
    proprietario_id = catalog.aggiungi_proprietario("Biblioteca")
    primo_gioco = catalog.aggiungi_gioco("Azul")
    secondo_gioco = catalog.aggiungi_gioco("Cascadia")
    terzo_gioco = catalog.aggiungi_gioco("Dorfromantik")
    catalog.imposta_quantita(primo_gioco, proprietario_id, "2")
    catalog.imposta_quantita(secondo_gioco, proprietario_id, "2")
    catalog.imposta_quantita(terzo_gioco, proprietario_id, "1")

    prima_sessione = lending.nuovo_prestito(primo_gioco, max_tokens=20)
    seconda_sessione = lending.nuovo_prestito(secondo_gioco, max_tokens=20)
    terza_sessione = lending.nuovo_prestito(terzo_gioco, max_tokens=20)

    assert (
        prima_sessione.token,
        seconda_sessione.token,
        terza_sessione.token,
    ) == (1, 2, 3)
    assert lending.riepilogo_home() == lending.RiepilogoHome(3, 3, 3)
    assert lending.situazione_chiusura() == lending.SituazioneChiusura(
        3, (1, 2, 3)
    )
    assert lending.disponibilita_gioco(primo_gioco) == (1, 2)
    assert lending.disponibilita_gioco(secondo_gioco) == (1, 2)
    assert lending.disponibilita_gioco(terzo_gioco) == (0, 1)

    lending.cambia_gioco(
        token=prima_sessione.token,
        documento_id=prima_sessione.documento_id,
        prestito_id=prima_sessione.prestito_id,
        gioco_id_atteso=primo_gioco,
        nuovo_gioco_id=secondo_gioco,
    )
    prima_dopo_cambio = lending.consulta_token(prima_sessione.token)
    seconda_prima_del_rientro = lending.consulta_token(seconda_sessione.token)
    terza_ancora_aperta = lending.consulta_token(terza_sessione.token)

    assert prima_dopo_cambio.documento["id"] == prima_sessione.documento_id
    assert prima_dopo_cambio.prestito["id"] != prima_sessione.prestito_id
    assert prima_dopo_cambio.prestito["gioco_id"] == secondo_gioco
    assert seconda_prima_del_rientro.prestito["id"] == seconda_sessione.prestito_id
    assert terza_ancora_aperta.prestito["id"] == terza_sessione.prestito_id

    lending.restituzione_finale(
        documento_id=seconda_sessione.documento_id,
        prestito_id=seconda_sessione.prestito_id,
    )

    prima_finale = lending.consulta_token(prima_sessione.token)
    terza_finale = lending.consulta_token(terza_sessione.token)
    with pytest.raises(lending.TokenLibero):
        lending.consulta_token(seconda_sessione.token)

    assert prima_finale.prestito["id"] == prima_dopo_cambio.prestito["id"]
    assert terza_finale.prestito["id"] == terza_sessione.prestito_id
    assert lending.riepilogo_home() == lending.RiepilogoHome(4, 3, 2)
    assert lending.situazione_chiusura() == lending.SituazioneChiusura(2, (1, 3))
    assert lending.disponibilita_gioco(primo_gioco) == (2, 2)
    assert lending.disponibilita_gioco(secondo_gioco) == (1, 2)
    assert lending.disponibilita_gioco(terzo_gioco) == (0, 1)

    storico_prestiti = reporting.storico_prestiti()
    assert (storico_prestiti.totale, storico_prestiti.attivi) == (4, 2)
    prestiti_per_id = {
        row["prestito_id"]: row
        for row in storico_prestiti.righe
    }
    assert prestiti_per_id[prima_sessione.prestito_id]["rientro"] == (
        "2026-09-12T10:30:00"
    )
    assert prestiti_per_id[prima_dopo_cambio.prestito["id"]]["rientro"] is None
    assert prestiti_per_id[seconda_sessione.prestito_id]["rientro"] == (
        "2026-09-12T11:00:00"
    )
    assert prestiti_per_id[terza_sessione.prestito_id]["rientro"] is None

    storico_documenti = reporting.storico_documenti()
    assert (storico_documenti.totale, storico_documenti.attivi) == (3, 2)
    documenti_per_token = {
        row["token"]: row
        for row in storico_documenti.righe
    }
    assert documenti_per_token[1]["uscita"] is None
    assert documenti_per_token[2]["uscita"] == "2026-09-12T11:00:00"
    assert documenti_per_token[3]["uscita"] is None
    assert documenti_per_token[1]["numero_prestiti"] == 2
    assert documenti_per_token[2]["numero_prestiti"] == 1
    assert documenti_per_token[3]["numero_prestiti"] == 1
