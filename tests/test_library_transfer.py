# Copyright (C) 2026 Matteo Sassi
# SPDX-License-Identifier: AGPL-3.0-only

"""Legacy library export tests with temporary SQLite databases."""

import csv

from ludox import library_transfer


def seed_legacy_library(db):
    db.executemany(
        "INSERT INTO giochi(id, nome) VALUES (?, ?)",
        [(1, "Kingdomino"), (2, "Azul, edizione blu"), (3, 'Nome "citato"')],
    )
    db.executemany(
        "INSERT INTO proprietari(id, nome) VALUES (?, ?)",
        [(2, "Matteo"), (3, "Biblioteca, Centro"), (4, 'Gruppo "A"')],
    )
    db.executemany(
        "INSERT INTO copie_gioco(gioco_id, proprietario_id, quantita) VALUES (?, ?, ?)",
        [(1, 2, 1), (1, 3, 2), (2, 3, 3), (3, 4, 1), (2, 4, 0)],
    )
    db.commit()


def snapshot(db):
    return tuple(db.iterdump())


def test_legacy_rows_exclude_zero_and_have_deterministic_order(db):
    seed_legacy_library(db)

    assert library_transfer.legacy_library_rows() == [
        {
            "game_name": "Azul, edizione blu",
            "owner_label": "Biblioteca, Centro",
            "quantity": 3,
        },
        {
            "game_name": "Kingdomino",
            "owner_label": "Biblioteca, Centro",
            "quantity": 2,
        },
        {
            "game_name": "Kingdomino",
            "owner_label": "Matteo",
            "quantity": 1,
        },
        {
            "game_name": 'Nome "citato"',
            "owner_label": 'Gruppo "A"',
            "quantity": 1,
        },
    ]


def test_csv_is_utf8_readable_and_does_not_change_database(db, tmp_path):
    seed_legacy_library(db)
    before = snapshot(db)
    destination = tmp_path / "ludoteca.csv"

    count = library_transfer.export_legacy_library_csv(destination)

    assert count == 4
    assert snapshot(db) == before
    raw = destination.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")
    with destination.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0] == {
        "game_name": "Azul, edizione blu",
        "owner_label": "Biblioteca, Centro",
        "quantity": "3",
    }
    assert rows[-1] == {
        "game_name": 'Nome "citato"',
        "owner_label": 'Gruppo "A"',
        "quantity": "1",
    }
