# Copyright (C) 2026 Matteo Sassi
# SPDX-License-Identifier: AGPL-3.0-only

"""Migration v3 to v4 coverage for operational copy identifiers."""

import sqlite3

import pytest

from ludox import database, migrations


def prepare_v3(path):
    migrations.migrate_database(path, target_version=3)
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        organization_id = connection.execute(
            "INSERT INTO organizations(name) VALUES ('Ludoteca')"
        ).lastrowid
        event_id = connection.execute("""
            INSERT INTO events(
                organization_id, name, slug, start_datetime, end_datetime,
                timezone
            ) VALUES (?, 'Evento', 'evento', '2026-09-13T09:00:00',
                      '2026-09-13T20:00:00', 'Europe/Rome')
        """, (organization_id,)).lastrowid
        owner_id = connection.execute("""
            INSERT INTO game_library_owner_labels(event_id, name, name_key)
            VALUES (?, 'Biblioteca', 'biblioteca')
        """, (event_id,)).lastrowid
        game_id = connection.execute("""
            INSERT INTO game_library_games(event_id, name, name_key)
            VALUES (?, 'Azul', 'azul')
        """, (event_id,)).lastrowid
        copies = [connection.execute("""
            INSERT INTO game_library_game_copies(
                event_id, game_id, owner_label_id
            ) VALUES (?, ?, ?)
        """, (event_id, game_id, owner_id)).lastrowid for _ in range(2)]
    return event_id, copies


def migrate_v3(path):
    backup = path.with_name("before-v4.db")
    migrations.create_backup(path, backup)
    return migrations.migrate_database(path, backup_path=backup)


def test_v3_identifiers_are_mapped_trimmed_and_constrained(isolated_files):
    path = database.get_db_path()
    event_id, copies = prepare_v3(path)
    with sqlite3.connect(path) as connection:
        connection.executemany("""
            INSERT INTO game_library_copy_identifiers(
                event_id, copy_id, identifier_type, value
            ) VALUES (?, ?, ?, ?)
        """, [
            (event_id, copies[0], "LUDOX_QR", " LX-C-000001 "),
            (event_id, copies[1], "EXTERNAL_BARCODE", "BIB-2"),
        ])

    result = migrate_v3(path)

    assert result.applied_versions == (4,)
    with sqlite3.connect(path) as connection:
        rows = connection.execute("""
            SELECT copy_id, source, value
            FROM game_library_copy_identifiers ORDER BY copy_id
        """).fetchall()
        assert rows == [
            (copies[0], "ludox", "LX-C-000001"),
            (copies[1], "external", "BIB-2"),
        ]
        columns = {
            row[1] for row in connection.execute(
                "PRAGMA table_info(game_library_copy_identifiers)"
            )
        }
        assert "source" in columns
        assert "identifier_type" not in columns
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("""
                INSERT INTO game_library_copy_identifiers(
                    event_id, copy_id, source, value
                ) VALUES (?, ?, 'external', 'OTHER')
            """, (event_id, copies[0]))
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("""
                INSERT INTO game_library_copy_identifiers(
                    event_id, copy_id, source, value
                ) VALUES (?, ?, 'invalid', 'OTHER')
            """, (event_id, copies[1]))


@pytest.mark.parametrize("conflict", ["copy", "value"])
def test_v3_conflicts_fail_and_rollback_without_data_loss(isolated_files, conflict):
    path = database.get_db_path()
    event_id, copies = prepare_v3(path)
    rows = [
        (event_id, copies[0], "LUDOX_QR", "FIRST"),
        (
            event_id,
            copies[0] if conflict == "copy" else copies[1],
            "EXTERNAL_BARCODE",
            "SECOND" if conflict == "copy" else " FIRST ",
        ),
    ]
    with sqlite3.connect(path) as connection:
        connection.executemany("""
            INSERT INTO game_library_copy_identifiers(
                event_id, copy_id, identifier_type, value
            ) VALUES (?, ?, ?, ?)
        """, rows)
    backup = path.with_name("before-conflict.db")
    migrations.create_backup(path, backup)

    with pytest.raises(migrations.MigrationError):
        migrations.migrate_database(path, backup_path=backup)

    with sqlite3.connect(path) as connection:
        assert migrations.schema_version(connection) == 3
        assert connection.execute(
            "SELECT COUNT(*) FROM game_library_copy_identifiers"
        ).fetchone()[0] == 2
        assert connection.execute("""
            SELECT name FROM sqlite_schema
            WHERE name = 'game_library_copy_identifiers_v4'
        """).fetchone() is None
