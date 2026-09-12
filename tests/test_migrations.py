"""Exercise migration infrastructure only against temporary SQLite files."""

import sqlite3

import pytest

from ludox import database
from ludox import migrations


def _read_version(path):
    with sqlite3.connect(path) as connection:
        return migrations.schema_version(connection)


def test_new_empty_database_is_distinguished_from_initialized_legacy(isolated_files):
    path = database.get_db_path()
    with sqlite3.connect(path) as connection:
        assert migrations.inspect_database(connection) == migrations.DatabaseState(
            migrations.DatabaseKind.EMPTY_UNVERSIONED,
            0,
        )

    database.init_db()

    assert path.exists()
    with sqlite3.connect(path) as connection:
        assert migrations.inspect_database(connection) == migrations.DatabaseState(
            migrations.DatabaseKind.LEGACY_UNVERSIONED,
            migrations.LEGACY_SCHEMA_VERSION,
        )


def test_existing_legacy_database_keeps_data_and_version_zero(isolated_files):
    path = database.get_db_path()
    database.init_db()
    with sqlite3.connect(path) as connection:
        connection.execute("INSERT INTO giochi(nome) VALUES ('Azul')")

    database.init_db()

    with sqlite3.connect(path) as connection:
        assert migrations.inspect_database(connection) == migrations.DatabaseState(
            migrations.DatabaseKind.LEGACY_UNVERSIONED,
            0,
        )
        assert connection.execute(
            "SELECT nome FROM giochi"
        ).fetchone()[0] == "Azul"


def test_supported_versioned_database_is_detected_without_migration(isolated_files):
    path = database.get_db_path()
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE versioned_data(value TEXT)")
        connection.execute("PRAGMA user_version = 1")
        assert migrations.inspect_database(
            connection, supported_version=1
        ) == migrations.DatabaseState(
            migrations.DatabaseKind.VERSIONED_SUPPORTED,
            1,
        )

    result = migrations.migrate_database(path, target_version=1)

    assert result == migrations.MigrationResult(1, 1, (), None)


def test_no_migration_is_applied_when_database_is_current(isolated_files):
    path = database.get_db_path()
    called = False

    def unexpected_migration(connection):
        nonlocal called
        called = True

    result = migrations.migrate_database(
        path,
        target_version=0,
        migration_steps=(migrations.Migration(1, unexpected_migration, True),),
    )

    assert called is False
    assert result == migrations.MigrationResult(0, 0, (), None)


def test_successful_migrations_run_in_order_and_update_version_after_each_step(
    isolated_files,
):
    path = database.get_db_path()
    observed = []

    def migration_one(connection):
        observed.append(("one", migrations.schema_version(connection)))
        connection.execute("CREATE TABLE migration_test(value TEXT)")

    def migration_two(connection):
        observed.append(("two", migrations.schema_version(connection)))
        connection.execute("INSERT INTO migration_test VALUES ('done')")

    result = migrations.migrate_database(
        path,
        target_version=2,
        migration_steps=(
            migrations.Migration(1, migration_one),
            migrations.Migration(2, migration_two),
        ),
    )

    assert observed == [("one", 0), ("two", 1)]
    assert result.applied_versions == (1, 2)
    assert result.final_version == 2
    with sqlite3.connect(path) as connection:
        assert migrations.schema_version(connection) == 2
        assert connection.execute(
            "SELECT value FROM migration_test"
        ).fetchone()[0] == "done"


def test_failed_migration_rolls_back_schema_data_and_version(isolated_files):
    path = database.get_db_path()

    def migration_one(connection):
        connection.execute("CREATE TABLE migration_test(value TEXT)")
        connection.execute("INSERT INTO migration_test VALUES ('partial')")

    def migration_two(connection):
        connection.execute("INSERT INTO migration_test VALUES ('failed')")
        raise RuntimeError("simulated migration failure")

    with pytest.raises(RuntimeError, match="simulated migration failure"):
        migrations.migrate_database(
            path,
            target_version=2,
            migration_steps=(
                migrations.Migration(1, migration_one),
                migrations.Migration(2, migration_two),
            ),
        )

    with sqlite3.connect(path) as connection:
        assert migrations.schema_version(connection) == 0
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE name = 'migration_test'"
        ).fetchone() is None


def test_future_database_version_is_rejected_without_changes(isolated_files):
    path = database.get_db_path()
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE existing_data(value TEXT)")
        connection.execute("INSERT INTO existing_data VALUES ('preserved')")
        connection.execute("PRAGMA user_version = 1")
        assert migrations.inspect_database(connection) == migrations.DatabaseState(
            migrations.DatabaseKind.FUTURE_UNSUPPORTED,
            1,
        )

    with pytest.raises(
        migrations.UnsupportedSchemaVersion,
        match="newer than supported version 0",
    ):
        database.init_db()

    with sqlite3.connect(path) as connection:
        assert migrations.schema_version(connection) == 1
        assert connection.execute(
            "SELECT value FROM existing_data"
        ).fetchone()[0] == "preserved"
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE name = 'giochi'"
        ).fetchone() is None


def test_required_backup_is_created_before_migration(isolated_files):
    path = database.get_db_path()
    backup_path = path.with_name("before-migration.db")
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE existing_data(value TEXT)")
        connection.execute("INSERT INTO existing_data VALUES ('preserved')")

    def migration_one(connection):
        connection.execute("CREATE TABLE migrated(value TEXT)")

    result = migrations.migrate_database(
        path,
        target_version=1,
        migration_steps=(migrations.Migration(1, migration_one, True),),
        backup_path=backup_path,
    )

    assert result.backup_path == backup_path
    assert backup_path.exists()
    with sqlite3.connect(backup_path) as backup:
        assert migrations.schema_version(backup) == 0
        assert backup.execute(
            "SELECT value FROM existing_data"
        ).fetchone()[0] == "preserved"
        assert backup.execute(
            "SELECT name FROM sqlite_master WHERE name = 'migrated'"
        ).fetchone() is None
    with sqlite3.connect(path) as connection:
        assert migrations.schema_version(connection) == 1
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE name = 'migrated'"
        ).fetchone() is not None


def test_required_backup_must_be_configured_before_migration(isolated_files):
    path = database.get_db_path()

    def migration_one(connection):
        connection.execute("CREATE TABLE should_not_exist(value TEXT)")

    with pytest.raises(migrations.BackupRequired):
        migrations.migrate_database(
            path,
            target_version=1,
            migration_steps=(migrations.Migration(1, migration_one, True),),
        )

    assert _read_version(path) == 0
    with sqlite3.connect(path) as connection:
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE name = 'should_not_exist'"
        ).fetchone() is None
