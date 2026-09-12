# Copyright (C) 2026 Matteo Sassi
# SPDX-License-Identifier: AGPL-3.0-only

"""Characterization tests for statistics and reporting services."""

import codecs
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

from ludox import reporting


def inserisci_documenti_e_prestiti(db):
    db.executemany(
        "INSERT INTO documenti(id, token, ingresso, uscita) VALUES (?, ?, ?, ?)",
        [
            (1, 10, "2026-09-10T10:00:00", "2026-09-10T13:00:00"),
            (2, 11, "2026-09-10T11:00:00", None),
            (3, 12, "2026-09-11T00:00:00", "2026-09-11T01:00:00"),
        ],
    )
    db.executemany(
        """INSERT INTO prestiti(id, documento_id, gioco_id, uscita, rientro)
           VALUES (?, ?, ?, ?, ?)""",
        [
            (1, 1, 1, "2026-09-10T10:15:00", "2026-09-10T11:15:00"),
            (2, 1, 2, "2026-09-10T11:30:00", "2026-09-10T13:00:00"),
            (3, 2, 1, "2026-09-10T12:00:00", None),
            (4, 3, 1, "2026-09-11T00:15:00", "2026-09-11T00:45:00"),
        ],
    )
    db.commit()


def test_intervallo_statistiche_usa_bucket_completi():
    riferimento = datetime(2026, 9, 10, 13, 44)

    inizio, fine = reporting.intervallo_statistiche(riferimento, 12, 15)

    assert inizio == datetime(2026, 9, 10, 1, 30)
    assert fine == datetime(2026, 9, 10, 13, 45)


def test_statistiche_contano_e_distribuiscono_nei_bucket(catalog):
    inserisci_documenti_e_prestiti(catalog)

    risultato = reporting.statistiche_periodo(
        datetime(2026, 9, 10, 13, 0), 3, 60
    )

    assert (risultato.prestiti, risultato.documenti) == (3, 2)
    assert [(p["prestiti"], p["documenti"]) for p in risultato.punti] == [
        (1, 1), (1, 1), (1, 0)
    ]


def test_statistiche_ignorano_timestamp_non_interpretabili(db, monkeypatch):
    monkeypatch.setattr(
        reporting.data,
        "conta_attivita_periodo",
        lambda inizio, fine: (1, 0),
    )
    monkeypatch.setattr(
        reporting.data,
        "timestamp_attivita_periodo",
        lambda inizio, fine: ([{"uscita": "timestamp non valido"}], []),
    )

    risultato = reporting.statistiche_periodo(
        datetime(2026, 9, 10, 13, 0), 1, 15
    )

    assert risultato.prestiti == 1
    assert sum(p["prestiti"] for p in risultato.punti) == 0


def test_storici_restituiscono_totali_attivi_e_ordine(catalog):
    inserisci_documenti_e_prestiti(catalog)

    prestiti = reporting.storico_prestiti()
    documenti = reporting.storico_documenti()

    assert (prestiti.totale, prestiti.attivi) == (4, 1)
    assert [row["prestito_id"] for row in prestiti.righe] == [4, 3, 2, 1]
    assert prestiti.righe[0]["uscita_testo"] == "11/09/2026 00:15:00"
    assert prestiti.righe[1]["rientro_testo"] == "—"
    assert (documenti.totale, documenti.attivi) == (3, 1)
    assert [row["id"] for row in documenti.righe] == [3, 2, 1]
    assert [row["numero_prestiti"] for row in documenti.righe] == [1, 1, 2]
    assert documenti.righe[0]["ingresso_testo"] == "11/09/2026 00:00:00"
    assert documenti.righe[1]["uscita_testo"] == "—"


def test_report_documenti_preserva_intervallo_inclusivo_e_metriche(catalog):
    inserisci_documenti_e_prestiti(catalog)

    report = reporting.report_documenti(
        datetime(2026, 9, 10),
        datetime(2026, 9, 10),
        ordina_per="prestiti",
        adesso=datetime(2026, 9, 10, 14, 0),
    )

    assert report.fine_esclusiva == datetime(2026, 9, 11)
    assert (report.totale_documenti, report.totale_prestiti) == (2, 3)
    assert [row["documento_id"] for row in report.righe] == [1, 2]
    assert report.righe[1]["aperto"] is True
    assert report.righe[1]["tempo_documento_secondi"] == 3 * 3600
    assert report.media_prestiti_persona == 1.5
    assert report.mediana_prestiti_persona == 1.5
    assert report.percentuale_almeno_2 == 50
    assert report.durata_mediana_prestito_secondi == 75 * 60
    righe_csv = reporting.righe_csv_documenti(report, "Aperto", "Chiuso")
    assert righe_csv[0] == [
        1, 10, "10/09/2026 10:00:00", "10/09/2026 13:00:00",
        2, "3h 00m", "180,00", "1h 15m", "75,00", "Chiuso",
    ]


def test_report_documenti_salta_ingresso_non_valido(catalog):
    inserisci_documenti_e_prestiti(catalog)
    catalog.execute(
        "INSERT INTO documenti(id, token, ingresso) VALUES (4, 13, '2026-09-10Txx')"
    )
    catalog.commit()

    report = reporting.report_documenti(
        datetime(2026, 9, 10), datetime(2026, 9, 10)
    )

    assert report.totale_documenti == 2


def test_report_utilizzo_include_aperti_e_calcola_durate_solo_sui_chiusi(catalog):
    inserisci_documenti_e_prestiti(catalog)

    report = reporting.report_utilizzo(
        datetime(2026, 9, 10), datetime(2026, 9, 10)
    )

    assert [row["gioco"] for row in report.righe] == ["Azul", "Cascadia", "Disattivo"]
    azul = report.righe[0]
    assert azul["proprietari"] == "Biblioteca (2), Privato (1)"
    assert azul["prestiti"] == 2
    assert azul["tempo_totale_secondi"] == 3600
    assert azul["media_secondi"] == 3600
    assert report.totale_prestiti == 3
    assert report.titoli_utilizzati == 2
    assert report.durata_mediana_prestito_secondi == 75 * 60
    assert reporting.righe_csv_utilizzo(report)[0] == [
        "Azul", "Biblioteca (2), Privato (1)", 3, 2,
        "1h 00m", "60,00", "1h 00m", "60,00", "0m", "0,00",
    ]


def test_report_utilizzo_filtra_proprietario_e_tempo_zero(catalog):
    inserisci_documenti_e_prestiti(catalog)

    report = reporting.report_utilizzo(
        datetime(2026, 9, 10),
        datetime(2026, 9, 10),
        proprietario_id=3,
        escludi_tempo_zero=True,
    )

    assert [row["gioco"] for row in report.righe] == ["Azul"]
    assert report.totale_prestiti == 2


def test_csv_usa_bom_punto_e_virgola_e_decimali_con_virgola(tmp_path):
    percorso = tmp_path / "report.csv"
    reporting.esporta_csv(
        percorso,
        ["Nome", "Minuti"],
        [["Azul", reporting.minuti_csv(90)]],
    )

    contenuto = percorso.read_bytes()
    assert contenuto.startswith(codecs.BOM_UTF8)
    assert contenuto.decode("utf-8-sig") == "Nome;Minuti\r\nAzul;1,50\r\n"


def test_reporting_non_richiede_dipendenze_gui():
    root = Path(__file__).resolve().parents[1]
    code = """
import sys
class NoGUI:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('tkinter', 'ttkbootstrap', 'matplotlib'):
            raise AssertionError('GUI dependency: ' + fullname)
sys.meta_path.insert(0, NoGUI())
from ludox import reporting
assert 'ludox.ui' not in sys.modules
"""
    subprocess.run(
        [sys.executable, "-B", "-c", code],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize(
    ("secondi", "testo"),
    [(None, "—"), (0, "0m"), (3599, "59m"), (-60, "0m")],
)
def test_formattazione_durata_preserva_il_comportamento(secondi, testo):
    assert reporting.formatta_durata(secondi) == testo
