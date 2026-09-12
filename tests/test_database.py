"""Characterize existing persistence/query helpers, not Tkinter workflows."""

import sqlite3

import pytest

from ludox import database as data


def test_initialization_creates_current_schema_and_default_owner(isolated_files):
    assert not data.get_db_path().exists()
    data.init_db()
    with data.get_db() as db:
        tables = {r[0] for r in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )}
        indexes = {r[0] for r in db.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        )}
        assert db.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert tables == {
        "organizations", "proprietari", "giochi", "copie_gioco",
        "documenti", "prestiti",
    }
    assert {"idx_token_aperto", "idx_prestito_aperto_documento"} <= indexes
    assert [r["nome"] for r in data.elenco_proprietari()] == ["Organizzazione"]


def test_organization_persistence_lists_reads_and_updates(db):
    first_id = data.inserisci_organizzazione("Ludoteca B")
    second_id = data.inserisci_organizzazione("Associazione A")

    assert [row["id"] for row in data.elenco_organizzazioni()] == [
        second_id, first_id,
    ]
    assert data.organizzazione_per_id(first_id)["name"] == "Ludoteca B"
    assert data.organizzazione_per_id(999) is None

    assert data.aggiorna_organizzazione(first_id, "Ludoteca C", 0) == 1
    assert data.aggiorna_organizzazione(999, "Missing", 1) == 0
    assert [row["id"] for row in data.elenco_organizzazioni(True)] == [second_id]
    assert dict(data.organizzazione_per_id(first_id)) == {
        "id": first_id,
        "name": "Ludoteca C",
        "active": 0,
    }


def test_initialization_preserves_existing_data_and_owner(catalog):
    data.init_db(default_owner_name="Organization")
    assert len(data.elenco_proprietari()) == 3
    assert data.gioco_per_id(1)["nome"] == "Azul"
    assert data.copie_totali_gioco(1) == 3


def test_initialization_uses_requested_owner_only_when_empty(db):
    db.execute("DELETE FROM proprietari")
    db.commit()
    data.init_db(default_owner_name="Biblioteca")
    data.init_db(default_owner_name="Other")
    assert [r["nome"] for r in data.elenco_proprietari()] == ["Biblioteca"]


def test_database_path_selection_does_not_create_file(tmp_path):
    assert data.set_db_path("alternate.db") == tmp_path / "alternate.db"
    assert not data.get_db_path().exists()
    for invalid in (tmp_path, tmp_path / "missing" / "test.db"):
        with pytest.raises(ValueError):
            data.set_db_path(invalid)
        assert data.get_db_path() == tmp_path / "alternate.db"


def test_connection_guard_rejects_outside_temporary_directory(tmp_path):
    with pytest.raises(AssertionError, match="temporary databases"):
        sqlite3.connect(tmp_path.parent / "forbidden.db")


def test_catalog_queries(catalog):
    assert data.gioco_per_id(1)["nome"] == "Azul"
    assert data.gioco_per_id(999) is None
    assert [r["nome"] for r in data.cerca_giochi()] == ["Azul", "Cascadia"]
    assert [r["nome"] for r in data.cerca_giochi("  AZ  ")] == ["Azul"]
    assert data.cerca_giochi("missing") == []
    assert [(r["nome"], r["copie_totali"]) for r in data.elenco_giochi_backoffice()] == [
        ("Azul", 3), ("Cascadia", 1), ("Disattivo", 2), ("Vuoto", 0)
    ]


def test_owner_queries_include_inactive_copies(catalog):
    assert [r["nome"] for r in data.elenco_proprietari()] == [
        "Biblioteca", "Organizzazione", "Privato"
    ]
    assert [r["nome"] for r in data.elenco_proprietari(True)] == [
        "Biblioteca", "Organizzazione"
    ]
    assert data.proprietario_per_id(3)["attivo"] == 0
    assert data.proprietario_per_id(999) is None
    assert data.totale_copie_proprietario(2) == 5
    assert data.totale_copie_proprietario(999) == 0
    assert [(r["proprietario_nome"], r["quantita"]) for r in
            data.copie_per_proprietario_del_gioco(1)] == [
        ("Biblioteca", 2), ("Organizzazione", 0), ("Privato", 1)
    ]
    assert data.riepilogo_proprietari_gioco(1) == "Biblioteca: 2, Privato: 1"
    assert data.riepilogo_proprietari_gioco(4) == "—"
    assert data.disponibilita_gioco(1) == (3, 3)


@pytest.mark.parametrize("sql", [
    "INSERT INTO giochi(nome) VALUES ('AZUL')",
    "INSERT INTO proprietari(nome) VALUES ('BIBLIOTECA')",
    "INSERT INTO giochi(nome, attivo) VALUES ('Invalid', 2)",
    "INSERT INTO proprietari(nome, attivo) VALUES ('Invalid', 2)",
    "INSERT INTO organizations(name) VALUES ('')",
    "INSERT INTO organizations(name, active) VALUES ('Invalid', 2)",
    "INSERT INTO copie_gioco(gioco_id, proprietario_id, quantita) VALUES (4, 2, -1)",
    "INSERT INTO copie_gioco(gioco_id, proprietario_id) VALUES (1, 2)",
    "INSERT INTO copie_gioco(gioco_id, proprietario_id) VALUES (999, 2)",
    "INSERT INTO copie_gioco(gioco_id, proprietario_id) VALUES (1, 999)",
    "INSERT INTO prestiti(documento_id, gioco_id, uscita) VALUES (999, 1, '2026-09-11T10:00:00')",
])
def test_current_integrity_constraints(catalog, sql):
    with pytest.raises(sqlite3.IntegrityError):
        with catalog:
            catalog.execute(sql)


def test_empty_database_queries(db):
    assert data.conta_documenti() == data.conta_documenti_attivi() == data.conta_prestiti() == 0
    assert data.massimo_token_aperto() == 0
    assert data.token_libero(2) == 1
    assert data.token_libero(0) is None
    assert data.documento_aperto_da_token(1) is None
    assert data.prestito_aperto_documento(1) is None
    assert data.disponibilita_gioco(999) == (0, 0)


def test_open_and_closed_records_drive_queries_and_partial_indexes(catalog):
    # Seed states directly: this does not exercise the UI's lending callbacks.
    with catalog:
        catalog.executemany(
            "INSERT INTO documenti(id, token, ingresso, uscita) VALUES (?, ?, ?, ?)",
            [(1, 1, "2026-09-11T10:00:00", None),
             (2, 2, "2026-09-11T10:00:00", None),
             (3, 9, "2026-09-11T09:00:00", "2026-09-11T09:30:00")],
        )
        catalog.executemany(
            "INSERT INTO prestiti(documento_id, gioco_id, uscita, rientro) VALUES (?, ?, ?, ?)",
            [(1, 2, "2026-09-11T10:00:00", None),
             (3, 1, "2026-09-11T09:00:00", "2026-09-11T09:30:00")],
        )
    assert data.conta_documenti() == 3
    assert data.conta_documenti_attivi() == 2
    assert data.conta_prestiti() == 2
    assert data.massimo_token_aperto() == 2
    assert data.token_libero(2) is None
    assert data.token_libero(3) == 3
    assert data.documento_aperto_da_token(1)["id"] == 1
    assert data.documento_aperto_da_token(9) is None
    assert data.prestito_aperto_documento(1)["gioco_nome"] == "Cascadia"
    assert data.prestito_aperto_documento(3) is None
    assert data.copie_in_prestito(1) == 0
    assert data.disponibilita_gioco(2) == (0, 1)
    # Search currently includes titles with every copy on loan.
    assert [r["nome"] for r in data.cerca_giochi("Cascadia")] == ["Cascadia"]
    for sql in (
        "INSERT INTO documenti(token, ingresso) VALUES (1, '2026-09-11T11:00:00')",
        "INSERT INTO prestiti(documento_id, gioco_id, uscita) VALUES (1, 1, '2026-09-11T11:00:00')",
        "INSERT INTO prestiti(documento_id, gioco_id, uscita) VALUES (2, 999, '2026-09-11T11:00:00')",
    ):
        with pytest.raises(sqlite3.IntegrityError):
            with catalog:
                catalog.execute(sql)
    with catalog:
        catalog.execute("UPDATE prestiti SET rientro='2026-09-11T11:00:00' WHERE documento_id=1")
        catalog.execute("UPDATE documenti SET uscita='2026-09-11T11:00:00' WHERE id=1")
    assert data.token_libero(2) == 1
    assert data.disponibilita_gioco(2) == (1, 1)
    with catalog:
        catalog.execute("INSERT INTO documenti(token, ingresso) VALUES (1, '2026-09-11T12:00:00')")
    assert data.documento_aperto_da_token(1)["id"] != 1
    assert data.conta_documenti() == 4


def test_availability_clamps_inconsistent_stock_to_zero(catalog):
    with catalog:
        catalog.execute("INSERT INTO documenti(id, token, ingresso) VALUES (1, 1, '2026-09-11T10:00:00')")
        catalog.execute("INSERT INTO prestiti(documento_id, gioco_id, uscita) VALUES (1, 4, '2026-09-11T10:00:00')")
    assert data.copie_in_prestito(4) == 1
    assert data.disponibilita_gioco(4) == (0, 0)


@pytest.mark.parametrize("value, expected", [
    ("2026-09-11T14:05:09", "11/09/2026 14:05:09"),
    (None, "—"), ("", "—"), ("invalid", "invalid"), (42, "42"),
])
def test_date_formatting(value, expected):
    assert data.formatta_data_ora(value) == expected
