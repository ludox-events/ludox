# Copyright (C) 2026 Matteo Sassi
# SPDX-License-Identifier: AGPL-3.0-only

"""Safe database startup tests using temporary SQLite files only."""

import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

from ludox import bootstrap, database, migrations


MOMENT = datetime(2026, 9, 12, 17, 59, 0)


def legacy_database(path):
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE legacy_data(value TEXT)")
        connection.execute("INSERT INTO legacy_data VALUES ('preserved')")


def test_database_corrente_prosegue_senza_backup(db):
    result = database.init_db(now=MOMENT)

    assert result.plan.pending_versions == ()
    assert result.backup_path is None
    assert list(database.get_db_path().parent.glob("*.backup-*.db")) == []


def test_database_nuovo_viene_inizializzato_senza_backup(isolated_files):
    path = database.get_db_path()

    result = database.init_db(now=MOMENT)

    assert result.plan.state.kind is migrations.DatabaseKind.EMPTY_UNVERSIONED
    assert result.plan.migration_required is False
    assert result.migration_result.applied_versions == (1,)
    assert result.backup_path is None
    with sqlite3.connect(path) as connection:
        assert migrations.schema_version(connection) == 1


def test_database_legacy_richiede_consenso_senza_modificarlo(isolated_files):
    path = database.get_db_path()
    legacy_database(path)

    with pytest.raises(bootstrap.MigrationApprovalRequired) as request:
        database.init_db(now=MOMENT)

    assert request.value.plan.state.version == 0
    assert request.value.plan.target_version == 1
    with sqlite3.connect(path) as connection:
        assert migrations.schema_version(connection) == 0
        assert connection.execute(
            "SELECT value FROM legacy_data"
        ).fetchone()[0] == "preserved"
        assert connection.execute(
            "SELECT name FROM sqlite_schema WHERE name = 'organizations'"
        ).fetchone() is None
    assert list(path.parent.glob("*.backup-*.db")) == []


def test_consenso_crea_backup_prima_della_migration(isolated_files):
    path = database.get_db_path()
    legacy_database(path)

    result = database.init_db(migration_authorized=True, now=MOMENT)

    assert result.backup_path == path.with_name(
        "test.backup-v0-to-v1-20260912-175900.db"
    )
    with sqlite3.connect(result.backup_path) as backup:
        assert migrations.schema_version(backup) == 0
        assert backup.execute(
            "SELECT name FROM sqlite_schema WHERE name = 'organizations'"
        ).fetchone() is None
    with sqlite3.connect(path) as connection:
        assert migrations.schema_version(connection) == 1
        assert connection.execute(
            "SELECT name FROM sqlite_schema WHERE name = 'organizations'"
        ).fetchone() is not None


def test_backup_fallito_impedisce_la_migration(isolated_files, monkeypatch):
    path = database.get_db_path()
    legacy_database(path)

    def backup_fallito(source, destination):
        raise OSError("cartella non scrivibile")

    monkeypatch.setattr(migrations, "create_backup", backup_fallito)

    with pytest.raises(
        bootstrap.BackupCreationFailed,
        match="cartella non scrivibile",
    ):
        database.init_db(migration_authorized=True, now=MOMENT)

    with sqlite3.connect(path) as connection:
        assert migrations.schema_version(connection) == 0
        assert connection.execute(
            "SELECT name FROM sqlite_schema WHERE name = 'organizations'"
        ).fetchone() is None


def test_migration_fallita_fa_rollback_e_conserva_backup(isolated_files):
    path = database.get_db_path()
    legacy_database(path)

    def migration_one(connection):
        connection.execute("CREATE TABLE migration_test(value TEXT)")
        raise RuntimeError("migration simulata fallita")

    with pytest.raises(bootstrap.MigrationExecutionFailed) as error:
        bootstrap.prepare_database(
            path,
            migration_authorized=True,
            target_version=1,
            migration_steps=(migrations.Migration(1, migration_one),),
            now=MOMENT,
        )

    assert error.value.backup_path.exists()
    with sqlite3.connect(path) as connection:
        assert migrations.schema_version(connection) == 0
        assert connection.execute(
            "SELECT name FROM sqlite_schema WHERE name = 'migration_test'"
        ).fetchone() is None


def test_schema_futuro_viene_rifiutato_senza_inizializzazione(isolated_files):
    path = database.get_db_path()
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE future_data(value TEXT)")
        connection.execute("PRAGMA user_version = 2")

    with pytest.raises(migrations.UnsupportedSchemaVersion):
        database.init_db()

    with sqlite3.connect(path) as connection:
        assert migrations.schema_version(connection) == 2
        assert connection.execute(
            "SELECT name FROM sqlite_schema WHERE name = 'proprietari'"
        ).fetchone() is None


def test_piu_migration_usano_un_solo_backup(isolated_files):
    path = database.get_db_path()
    legacy_database(path)
    expected_backup = path.with_name(
        "test.backup-v0-to-v2-20260912-175900.db"
    )

    def migration_one(connection):
        assert expected_backup.exists()
        connection.execute("CREATE TABLE first_step(value TEXT)")

    def migration_two(connection):
        connection.execute("CREATE TABLE second_step(value TEXT)")

    result = bootstrap.prepare_database(
        path,
        migration_authorized=True,
        target_version=2,
        migration_steps=(
            migrations.Migration(1, migration_one),
            migrations.Migration(2, migration_two),
        ),
        now=MOMENT,
    )

    assert result.migration_result.applied_versions == (1, 2)
    assert result.backup_path.exists()
    assert len(list(path.parent.glob("*.backup-*.db"))) == 1
    with sqlite3.connect(result.backup_path) as backup:
        assert backup.execute(
            "SELECT name FROM sqlite_schema WHERE name = 'first_step'"
        ).fetchone() is None


def test_bootstrap_non_richiede_dipendenze_gui():
    root = Path(__file__).resolve().parents[1]
    code = """
import sys
class NoGUI:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('tkinter', 'ttkbootstrap', 'matplotlib'):
            raise AssertionError('GUI dependency: ' + fullname)
sys.meta_path.insert(0, NoGUI())
from ludox import bootstrap
assert 'ludox.ui' not in sys.modules
"""
    subprocess.run(
        [sys.executable, "-B", "-c", code],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
