# Copyright (C) 2026 Matteo Sassi
# SPDX-License-Identifier: AGPL-3.0-only

"""Integration tests across services and real temporary SQLite persistence."""

from datetime import datetime

import pytest

from ludox import catalog, config, database, lending, reporting, workspace


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
