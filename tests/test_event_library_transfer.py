# Copyright (C) 2026 Matteo Sassi
# SPDX-License-Identifier: AGPL-3.0-only

"""Import/export integration tests for one Event game library."""

import csv
import sqlite3

import pytest

from ludox import (
    catalog,
    copy_identifiers,
    database,
    events,
    lending,
    library_transfer,
    organizations,
)


def new_event(slug):
    organizations_available = organizations.elenco_organizzazioni()
    organization = (
        organizations_available[0]
        if organizations_available
        else organizations.crea_organizzazione("Ludoteca")
    )
    return events.create_event(
        organization.id,
        name=slug,
        slug=slug,
        start_datetime="2026-09-13T09:00:00",
        end_datetime="2026-09-13T20:00:00",
        timezone="Europe/Rome",
        modules=("game_library",),
    )


def write_csv(path, rows, columns=library_transfer.CSV_COLUMNS):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def test_legacy_csv_import_creates_individual_copies_and_preview_is_read_only(
    db, tmp_path,
):
    db.execute("INSERT INTO giochi(id, nome) VALUES (1, 'Azul')")
    db.execute("INSERT INTO proprietari(id, nome) VALUES (2, 'Biblioteca')")
    db.execute("""
        INSERT INTO copie_gioco(gioco_id, proprietario_id, quantita)
        VALUES (1, 2, 3)
    """)
    db.commit()
    source = tmp_path / "legacy.csv"
    library_transfer.export_legacy_library_csv(source)
    event = new_event("legacy-import")
    before = tuple(db.iterdump())

    preview = library_transfer.preview_import(source, event.id)

    assert preview.can_apply
    assert preview.valid_count == 1
    assert preview.new_owner_labels == ("Biblioteca",)
    assert tuple(db.iterdump()) == before
    result = library_transfer.apply_import(preview)
    assert result == library_transfer.ImportResult(1, 1, 1, 3)
    with database.get_db() as connection:
        assert connection.execute("""
            SELECT COUNT(*) FROM game_library_game_copies WHERE event_id = ?
        """, (event.id,)).fetchone()[0] == 3


def test_import_is_additive_and_reuses_trimmed_casefolded_titles(db, tmp_path):
    event = new_event("additive")
    owner = catalog.aggiungi_proprietario("Biblioteca", event_id=event.id)
    game = catalog.aggiungi_gioco("Kingdomino", event_id=event.id)
    catalog.imposta_quantita(game, owner, "1", event_id=event.id)
    source = tmp_path / "more.csv"
    write_csv(source, [
        {"game_name": " KINGDOMINO ", "owner_label": " biblioteca ", "quantity": 2},
        {"game_name": "King Domino", "owner_label": "LAM", "quantity": 1},
    ])

    preview = library_transfer.preview_import(source, event.id)
    assert preview.existing_titles == ("Kingdomino",)
    assert preview.new_owner_labels == ("LAM",)
    result = library_transfer.apply_import(preview)

    assert result == library_transfer.ImportResult(2, 1, 1, 3)
    assert [(row["nome"], row["copie_totali"]) for row in
            catalog.elenco_giochi_backoffice(event_id=event.id)] == [
        ("King Domino", 1), ("Kingdomino", 3)
    ]


def test_ownerless_import_uses_one_selected_owner_and_invalid_rows_block_all_writes(
    db, tmp_path,
):
    event = new_event("ownerless")
    source = tmp_path / "ownerless.csv"
    write_csv(source, [
        {"game_name": "Azul", "quantity": 2},
        {"game_name": "Cascadia", "quantity": 0},
    ], columns=("game_name", "quantity"))

    missing_owner = library_transfer.preview_import(source, event.id)
    assert not missing_owner.can_apply
    assert missing_owner.invalid_count == 1
    preview = library_transfer.preview_import(
        source, event.id, owner_label=" Biblioteca "
    )
    assert preview.valid_count == preview.invalid_count == 1
    with pytest.raises(library_transfer.ImportNotValid):
        library_transfer.apply_import(preview)
    assert catalog.elenco_giochi_backoffice(event_id=event.id) == []


def test_import_database_error_rolls_back_games_owners_and_copies(db, tmp_path):
    event = new_event("rollback")
    source = tmp_path / "library.csv"
    write_csv(source, [
        {"game_name": "Azul", "owner_label": "Biblioteca", "quantity": 2}
    ])
    preview = library_transfer.preview_import(source, event.id)
    db.execute("""
        CREATE TRIGGER reject_event_copies
        BEFORE INSERT ON game_library_game_copies
        BEGIN SELECT RAISE(ABORT, 'copy rejected'); END
    """)
    db.commit()

    with pytest.raises(sqlite3.IntegrityError, match="copy rejected"):
        library_transfer.apply_import(preview)
    assert catalog.elenco_giochi_backoffice(event_id=event.id) == []
    assert catalog.elenco_proprietari(event_id=event.id) == []


def test_event_export_is_isolated_quoted_and_round_trips(db, tmp_path):
    first = new_event("first-export")
    second = new_event("second-export")
    first_owner = catalog.aggiungi_proprietario('Gruppo "A", Centro', event_id=first.id)
    first_game = catalog.aggiungi_gioco('Azul, "Blu"', event_id=first.id)
    catalog.imposta_quantita(first_game, first_owner, "2", event_id=first.id)
    second_owner = catalog.aggiungi_proprietario("Altro", event_id=second.id)
    second_game = catalog.aggiungi_gioco("Non esportare", event_id=second.id)
    catalog.imposta_quantita(second_game, second_owner, "5", event_id=second.id)
    source = tmp_path / "event.csv"

    assert library_transfer.export_event_library(source, first.id) == 1
    with source.open(encoding="utf-8", newline="") as handle:
        assert list(csv.DictReader(handle)) == [{
            "game_name": 'Azul, "Blu"',
            "owner_label": 'Gruppo "A", Centro',
            "quantity": "2",
            "copy_identifier": "",
            "identifier_source": "",
        }]
    target = new_event("round-trip")
    library_transfer.apply_import(
        library_transfer.preview_import(source, target.id)
    )
    assert library_transfer.event_library_rows(target.id) == [
        {
            "game_name": 'Azul, "Blu"',
            "owner_label": 'Gruppo "A", Centro',
            "quantity": 2,
            "copy_identifier": "",
            "identifier_source": "",
        }
    ]


def test_xlsx_uses_the_same_logical_columns_for_export_and_import(db, tmp_path):
    source_event = new_event("xlsx-source")
    owner = catalog.aggiungi_proprietario("LAM", event_id=source_event.id)
    game = catalog.aggiungi_gioco("Cascadia", event_id=source_event.id)
    catalog.imposta_quantita(game, owner, "2", event_id=source_event.id)
    path = tmp_path / "library.xlsx"

    library_transfer.export_event_library(path, source_event.id)
    target_event = new_event("xlsx-target")
    preview = library_transfer.preview_import(path, target_event.id)
    result = library_transfer.apply_import(preview)

    assert result.copies_created == 2
    assert library_transfer.event_library_rows(target_event.id) == [
        {
            "game_name": "Cascadia",
            "owner_label": "LAM",
            "quantity": 2,
            "copy_identifier": "",
            "identifier_source": "",
        }
    ]


def test_extended_import_creates_identified_copies_and_defaults_source(db, tmp_path):
    event = new_event("identified-import")
    source = tmp_path / "identified.csv"
    write_csv(source, [
        {
            "game_name": "Azul",
            "owner_label": "Biblioteca",
            "quantity": 1,
            "copy_identifier": " EXT-001 ",
            "identifier_source": "",
        },
        {
            "game_name": "Azul",
            "owner_label": "Biblioteca",
            "quantity": 1,
            "copy_identifier": "LX-C-999999",
            "identifier_source": "ludox",
        },
        {
            "game_name": "Azul",
            "owner_label": "Biblioteca",
            "quantity": 2,
            "copy_identifier": "",
            "identifier_source": "",
        },
    ])

    preview = library_transfer.preview_import(source, event.id)
    assert preview.can_apply
    assert [row["identifier_source"] for row in preview.rows] == [
        "external", "ludox", ""
    ]
    result = library_transfer.apply_import(preview)

    assert result.copies_created == 4
    assert library_transfer.event_library_rows(event.id) == [
        {
            "game_name": "Azul", "owner_label": "Biblioteca", "quantity": 1,
            "copy_identifier": "EXT-001", "identifier_source": "external",
        },
        {
            "game_name": "Azul", "owner_label": "Biblioteca", "quantity": 1,
            "copy_identifier": "LX-C-999999", "identifier_source": "ludox",
        },
        {
            "game_name": "Azul", "owner_label": "Biblioteca", "quantity": 2,
            "copy_identifier": "", "identifier_source": "",
        },
    ]


def test_identifier_import_validation_blocks_all_writes(db, tmp_path):
    event = new_event("identifier-validation")
    owner = catalog.aggiungi_proprietario("Biblioteca", event_id=event.id)
    game = catalog.aggiungi_gioco("Existing", event_id=event.id)
    catalog.imposta_quantita(game, owner, "1", event_id=event.id)
    copy_id = copy_identifiers.list_copies(event.id)[0]["copy_id"]
    copy_identifiers.assign_external(event.id, copy_id, "EXISTS")
    source = tmp_path / "invalid-identifiers.csv"
    write_csv(source, [
        {"game_name": "One", "owner_label": "LAM", "quantity": 2,
         "copy_identifier": "QTY", "identifier_source": "external"},
        {"game_name": "Two", "owner_label": "LAM", "quantity": 1,
         "copy_identifier": "DUP", "identifier_source": "external"},
        {"game_name": "Three", "owner_label": "LAM", "quantity": 1,
         "copy_identifier": "DUP", "identifier_source": "external"},
        {"game_name": "Four", "owner_label": "LAM", "quantity": 1,
         "copy_identifier": "EXISTS", "identifier_source": "external"},
        {"game_name": "Five", "owner_label": "LAM", "quantity": 1,
         "copy_identifier": "BAD-SOURCE", "identifier_source": "vendor"},
        {"game_name": "Six", "owner_label": "LAM", "quantity": 1,
         "copy_identifier": "", "identifier_source": "ludox"},
        {"game_name": "Seven", "owner_label": "LAM", "quantity": 1,
         "copy_identifier": "LINE\nBREAK", "identifier_source": "external"},
    ])
    before = tuple(db.iterdump())

    preview = library_transfer.preview_import(source, event.id)

    assert preview.invalid_count == 6
    assert not preview.can_apply
    with pytest.raises(library_transfer.ImportNotValid):
        library_transfer.apply_import(preview)
    assert tuple(db.iterdump()) == before


def test_identifier_import_uniqueness_is_event_scoped_and_round_trips(db, tmp_path):
    first = new_event("identifier-first")
    second = new_event("identifier-second")
    source = tmp_path / "same-code.csv"
    write_csv(source, [{
        "game_name": "Azul", "owner_label": "LAM", "quantity": 1,
        "copy_identifier": "SAME", "identifier_source": "external",
    }])

    library_transfer.apply_import(library_transfer.preview_import(source, first.id))
    second_preview = library_transfer.preview_import(source, second.id)

    assert second_preview.can_apply
    library_transfer.apply_import(second_preview)
    exported = tmp_path / "round-trip-identifiers.xlsx"
    library_transfer.export_event_library(exported, first.id)
    target = new_event("identifier-target")
    library_transfer.apply_import(
        library_transfer.preview_import(exported, target.id)
    )
    assert library_transfer.event_library_rows(target.id) == [
        {
            "game_name": "Azul", "owner_label": "LAM", "quantity": 1,
            "copy_identifier": "SAME", "identifier_source": "external",
        }
    ]


def test_identifier_insert_failure_rolls_back_whole_import(db, tmp_path):
    event = new_event("identifier-rollback")
    source = tmp_path / "identifier-rollback.csv"
    write_csv(source, [{
        "game_name": "Azul", "owner_label": "LAM", "quantity": 1,
        "copy_identifier": "ROLLBACK", "identifier_source": "external",
    }])
    preview = library_transfer.preview_import(source, event.id)
    db.execute("""
        CREATE TRIGGER reject_import_identifier
        BEFORE INSERT ON game_library_copy_identifiers
        BEGIN SELECT RAISE(ABORT, 'identifier rejected'); END
    """)
    db.commit()

    with pytest.raises(sqlite3.IntegrityError, match="identifier rejected"):
        library_transfer.apply_import(preview)
    assert catalog.elenco_giochi_backoffice(event_id=event.id) == []
    assert catalog.elenco_proprietari(event_id=event.id) == []


def test_reset_is_allowed_only_before_any_loan(db, tmp_path, monkeypatch):
    event = new_event("reset")
    owner = catalog.aggiungi_proprietario("LAM", event_id=event.id)
    game = catalog.aggiungi_gioco("Azul", event_id=event.id)
    catalog.imposta_quantita(game, owner, "2", event_id=event.id)
    library_transfer.reset_event_library(event.id)
    assert library_transfer.event_library_rows(event.id) == []

    owner = catalog.aggiungi_proprietario("LAM", event_id=event.id)
    game = catalog.aggiungi_gioco("Azul", event_id=event.id)
    catalog.imposta_quantita(game, owner, "1", event_id=event.id)
    monkeypatch.setattr(database, "now_iso", lambda: "2026-09-13T12:00:00")
    loan = lending.nuovo_prestito(game, event_id=event.id)
    lending.restituzione_finale(
        documento_id=loan.documento_id,
        prestito_id=loan.prestito_id,
        event_id=event.id,
    )
    with pytest.raises(library_transfer.LibraryResetBlocked):
        library_transfer.reset_event_library(event.id)
