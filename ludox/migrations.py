# Copyright (C) 2026 Matteo Sassi
# SPDX-License-Identifier: AGPL-3.0-only

"""SQLite schema version checks and migration execution."""

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable, Iterable


LEGACY_SCHEMA_VERSION = 0
CURRENT_SCHEMA_VERSION = 4


class MigrationError(sqlite3.DatabaseError):
    """Base error for invalid or unsupported migration operations."""


class UnsupportedSchemaVersion(MigrationError):
    def __init__(self, found_version, supported_version):
        self.found_version = found_version
        self.supported_version = supported_version
        super().__init__(
            f"Database schema version {found_version} is newer than supported "
            f"version {supported_version}"
        )


class MissingMigration(MigrationError):
    def __init__(self, version):
        self.version = version
        super().__init__(f"Missing migration for schema version {version}")


class BackupRequired(MigrationError):
    """A pending migration requires an explicit backup destination."""


class DatabaseKind(Enum):
    EMPTY_UNVERSIONED = "empty_unversioned"
    LEGACY_UNVERSIONED = "legacy_unversioned"
    VERSIONED_SUPPORTED = "versioned_supported"
    FUTURE_UNSUPPORTED = "future_unsupported"


@dataclass(frozen=True)
class DatabaseState:
    kind: DatabaseKind
    version: int


@dataclass(frozen=True)
class Migration:
    version: int
    apply: Callable[[sqlite3.Connection], None]


@dataclass(frozen=True)
class MigrationPlan:
    database_path: Path
    state: DatabaseState
    target_version: int
    pending_versions: tuple[int, ...]

    @property
    def migration_required(self):
        return bool(self.pending_versions) and (
            self.state.kind is not DatabaseKind.EMPTY_UNVERSIONED
        )


@dataclass(frozen=True)
class MigrationResult:
    initial_version: int
    final_version: int
    applied_versions: tuple[int, ...]
    backup_path: Path | None


def _migrate_to_version_1(connection):
    connection.execute("""
        CREATE TABLE organizations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL CHECK(length(trim(name)) > 0),
            active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0, 1))
        )
    """)


def _migrate_to_version_2(connection):
    statements = (
        """CREATE TABLE events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            organization_id INTEGER NOT NULL,
            name TEXT NOT NULL CHECK(length(trim(name)) > 0),
            slug TEXT NOT NULL CHECK(
                length(slug) > 0
                AND slug NOT GLOB '*[^a-z0-9_-]*'
            ),
            start_datetime TEXT NOT NULL,
            end_datetime TEXT NOT NULL,
            timezone TEXT NOT NULL CHECK(length(trim(timezone)) > 0),
            status TEXT NOT NULL DEFAULT 'draft' CHECK(
                status IN ('draft', 'active', 'archived', 'cancelled')
            ),
            FOREIGN KEY(organization_id) REFERENCES organizations(id),
            UNIQUE(organization_id, slug)
        )""",
        """CREATE TRIGGER events_organization_immutable
        BEFORE UPDATE OF organization_id ON events
        WHEN NEW.organization_id <> OLD.organization_id
        BEGIN
            SELECT RAISE(ABORT, 'event organization is immutable');
        END""",
        """CREATE TRIGGER events_slug_immutable
        BEFORE UPDATE OF slug ON events
        WHEN NEW.slug <> OLD.slug
        BEGIN
            SELECT RAISE(ABORT, 'event slug is immutable');
        END""",
        """CREATE TABLE event_modules (
            event_id INTEGER NOT NULL,
            module_id TEXT NOT NULL CHECK(
                module_id IN ('game_library', 'activities')
            ),
            enabled INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0, 1)),
            PRIMARY KEY(event_id, module_id),
            FOREIGN KEY(event_id) REFERENCES events(id) ON DELETE CASCADE
        )""",
    )
    for statement in statements:
        connection.execute(statement)


def _migrate_to_version_3(connection):
    statements = (
        """CREATE TABLE game_library_settings (
            event_id INTEGER PRIMARY KEY,
            max_slots INTEGER NOT NULL DEFAULT 50 CHECK(max_slots > 0),
            identification_mode TEXT NOT NULL DEFAULT 'token' CHECK(
                identification_mode IN ('token', 'copy_identifier')
            ),
            FOREIGN KEY(event_id) REFERENCES events(id) ON DELETE CASCADE
        )""",
        """CREATE TABLE game_library_owner_labels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            name TEXT NOT NULL CHECK(length(trim(name)) > 0),
            name_key TEXT NOT NULL CHECK(length(name_key) > 0),
            active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0, 1)),
            FOREIGN KEY(event_id) REFERENCES events(id) ON DELETE CASCADE,
            UNIQUE(event_id, name_key),
            UNIQUE(event_id, id)
        )""",
        """CREATE TABLE game_library_games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            name TEXT NOT NULL CHECK(length(trim(name)) > 0),
            name_key TEXT NOT NULL CHECK(length(name_key) > 0),
            active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0, 1)),
            external_id TEXT,
            difficulty REAL,
            difficulty_source TEXT,
            notes TEXT,
            FOREIGN KEY(event_id) REFERENCES events(id) ON DELETE CASCADE,
            UNIQUE(event_id, name_key),
            UNIQUE(event_id, id)
        )""",
        """CREATE TABLE game_library_game_copies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            game_id INTEGER NOT NULL,
            owner_label_id INTEGER NOT NULL,
            active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0, 1)),
            FOREIGN KEY(event_id, game_id)
                REFERENCES game_library_games(event_id, id) ON DELETE CASCADE,
            FOREIGN KEY(event_id, owner_label_id)
                REFERENCES game_library_owner_labels(event_id, id),
            UNIQUE(event_id, id)
        )""",
        """CREATE INDEX game_library_copies_event_game
            ON game_library_game_copies(event_id, game_id)""",
        """CREATE TABLE game_library_copy_identifiers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            copy_id INTEGER NOT NULL,
            identifier_type TEXT NOT NULL CHECK(
                identifier_type IN ('LUDOX_QR', 'EXTERNAL_BARCODE')
            ),
            value TEXT NOT NULL CHECK(length(trim(value)) > 0),
            FOREIGN KEY(event_id, copy_id)
                REFERENCES game_library_game_copies(event_id, id)
                ON DELETE CASCADE
        )""",
        """CREATE TABLE game_library_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            slot INTEGER NOT NULL CHECK(slot > 0),
            opened_at TEXT NOT NULL,
            closed_at TEXT,
            FOREIGN KEY(event_id) REFERENCES events(id) ON DELETE RESTRICT,
            UNIQUE(event_id, id)
        )""",
        """CREATE UNIQUE INDEX game_library_open_session_slot
            ON game_library_sessions(event_id, slot)
            WHERE closed_at IS NULL""",
        """CREATE TABLE game_library_loans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            session_id INTEGER NOT NULL,
            game_id INTEGER NOT NULL,
            copy_id INTEGER,
            checked_out_at TEXT NOT NULL,
            returned_at TEXT,
            FOREIGN KEY(event_id, session_id)
                REFERENCES game_library_sessions(event_id, id)
                ON DELETE RESTRICT,
            FOREIGN KEY(event_id, game_id)
                REFERENCES game_library_games(event_id, id)
                ON DELETE RESTRICT,
            FOREIGN KEY(event_id, copy_id)
                REFERENCES game_library_game_copies(event_id, id)
                ON DELETE RESTRICT
        )""",
        """CREATE UNIQUE INDEX game_library_open_loan_session
            ON game_library_loans(event_id, session_id)
            WHERE returned_at IS NULL""",
        """INSERT INTO game_library_settings(event_id)
            SELECT event_id FROM event_modules
            WHERE module_id = 'game_library' AND enabled = 1""",
    )
    for statement in statements:
        connection.execute(statement)


def _migrate_to_version_4(connection):
    """Consolidate copy identifiers to the single operational V1 model."""
    source_by_legacy_type = {
        "LUDOX_QR": "ludox",
        "EXTERNAL_BARCODE": "external",
    }
    migrated_rows = []
    copies_seen = set()
    values_seen = set()
    rows = connection.execute("""
        SELECT id, event_id, copy_id, identifier_type, value
        FROM game_library_copy_identifiers
        ORDER BY id
    """).fetchall()
    for identifier_id, event_id, copy_id, identifier_type, value in rows:
        source = source_by_legacy_type.get(identifier_type)
        normalized = value.strip() if isinstance(value, str) else ""
        if source is None:
            raise MigrationError(
                f"Unsupported copy identifier type for row {identifier_id}: "
                f"{identifier_type!r}"
            )
        if not normalized or "\n" in normalized or "\r" in normalized:
            raise MigrationError(
                f"Invalid copy identifier value for row {identifier_id}"
            )
        copy_key = (event_id, copy_id)
        value_key = (event_id, normalized)
        if copy_key in copies_seen:
            raise MigrationError(
                "Multiple copy identifiers exist for the same copy in event "
                f"{event_id} (copy {copy_id})"
            )
        if value_key in values_seen:
            raise MigrationError(
                f"Duplicate copy identifier {normalized!r} in event {event_id}"
            )
        copies_seen.add(copy_key)
        values_seen.add(value_key)
        migrated_rows.append(
            (identifier_id, event_id, copy_id, source, normalized)
        )

    connection.execute("""
        CREATE TABLE game_library_copy_identifiers_v4 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            copy_id INTEGER NOT NULL,
            source TEXT NOT NULL CHECK(source IN ('external', 'ludox')),
            value TEXT NOT NULL CHECK(
                length(trim(value)) > 0
                AND instr(value, char(10)) = 0
                AND instr(value, char(13)) = 0
            ),
            FOREIGN KEY(event_id, copy_id)
                REFERENCES game_library_game_copies(event_id, id)
                ON DELETE CASCADE,
            UNIQUE(event_id, copy_id),
            UNIQUE(event_id, value)
        )
    """)
    connection.executemany("""
        INSERT INTO game_library_copy_identifiers_v4(
            id, event_id, copy_id, source, value
        ) VALUES (?, ?, ?, ?, ?)
    """, migrated_rows)
    connection.execute("DROP TABLE game_library_copy_identifiers")
    connection.execute("""
        ALTER TABLE game_library_copy_identifiers_v4
        RENAME TO game_library_copy_identifiers
    """)


MIGRATIONS: tuple[Migration, ...] = (
    Migration(1, _migrate_to_version_1),
    Migration(2, _migrate_to_version_2),
    Migration(3, _migrate_to_version_3),
    Migration(4, _migrate_to_version_4),
)


def schema_version(connection):
    return int(connection.execute("PRAGMA user_version").fetchone()[0])


def inspect_database(connection, supported_version=CURRENT_SCHEMA_VERSION):
    """Classify a database by schema version and application schema presence."""
    version = schema_version(connection)
    if version > supported_version:
        return DatabaseState(DatabaseKind.FUTURE_UNSUPPORTED, version)
    if version > LEGACY_SCHEMA_VERSION:
        return DatabaseState(DatabaseKind.VERSIONED_SUPPORTED, version)

    has_application_schema = connection.execute("""
        SELECT EXISTS (
            SELECT 1
            FROM sqlite_schema
            WHERE name NOT LIKE 'sqlite_%'
        )
    """).fetchone()[0]
    kind = (
        DatabaseKind.LEGACY_UNVERSIONED
        if has_application_schema
        else DatabaseKind.EMPTY_UNVERSIONED
    )
    return DatabaseState(kind, version)


def _pending_migrations(current_version, target_version, migration_steps):
    by_version = {}
    for migration in migration_steps:
        if migration.version in by_version:
            raise MigrationError(
                f"Duplicate migration for schema version {migration.version}"
            )
        by_version[migration.version] = migration

    pending = []
    for version in range(current_version + 1, target_version + 1):
        try:
            pending.append(by_version[version])
        except KeyError as exc:
            raise MissingMigration(version) from exc
    return pending


def plan_database(
    database_path,
    *,
    target_version=CURRENT_SCHEMA_VERSION,
    migration_steps: Iterable[Migration] = MIGRATIONS,
):
    """Inspect a database and validate its complete pending migration chain."""
    path = Path(database_path).resolve(strict=False)
    if path.exists():
        connection = sqlite3.connect(path)
        try:
            state = inspect_database(connection, target_version)
        finally:
            connection.close()
    else:
        state = DatabaseState(DatabaseKind.EMPTY_UNVERSIONED, 0)

    if state.kind is DatabaseKind.FUTURE_UNSUPPORTED:
        pending_versions = ()
    else:
        pending_versions = tuple(
            migration.version
            for migration in _pending_migrations(
                state.version,
                target_version,
                migration_steps,
            )
        )
    return MigrationPlan(path, state, target_version, pending_versions)


def automatic_backup_path(plan, now=None):
    """Return a readable, available backup path beside the source database."""
    moment = now or datetime.now()
    timestamp = moment.strftime("%Y%m%d-%H%M%S")
    suffix = plan.database_path.suffix or ".db"
    base = (
        f"{plan.database_path.stem}.backup-v{plan.state.version}"
        f"-to-v{plan.target_version}-{timestamp}"
    )
    candidate = plan.database_path.with_name(f"{base}{suffix}")
    counter = 2
    while candidate.exists():
        candidate = plan.database_path.with_name(f"{base}-{counter}{suffix}")
        counter += 1
    return candidate


def create_backup(database_path, backup_path):
    """Create one complete SQLite backup without overwriting another file."""
    source_path = Path(database_path)
    destination_path = Path(backup_path)
    if destination_path.resolve(strict=False) == source_path.resolve(strict=False):
        raise ValueError("Backup path must differ from database path")
    if destination_path.exists():
        raise FileExistsError(f"Backup already exists: {destination_path}")

    source = sqlite3.connect(source_path)
    destination = None
    try:
        destination = sqlite3.connect(destination_path)
        source.backup(destination)
    except BaseException:
        if destination is not None:
            destination.close()
            destination = None
        destination_path.unlink(missing_ok=True)
        raise
    finally:
        if destination is not None:
            destination.close()
        source.close()
    return destination_path


def migrate_database(
    database_path,
    *,
    target_version=CURRENT_SCHEMA_VERSION,
    migration_steps: Iterable[Migration] = MIGRATIONS,
    backup_path=None,
):
    """Validate and migrate one SQLite database up to ``target_version``."""
    path = Path(database_path)
    connection = sqlite3.connect(path, isolation_level=None)
    try:
        initial_state = inspect_database(connection, target_version)
        initial_version = initial_state.version
        if initial_state.kind is DatabaseKind.FUTURE_UNSUPPORTED:
            raise UnsupportedSchemaVersion(initial_version, target_version)

        pending = _pending_migrations(
            initial_version, target_version, migration_steps
        )
        if not pending:
            return MigrationResult(
                initial_version, initial_version, (), None
            )

        verified_backup = None
        if pending and initial_state.kind is not DatabaseKind.EMPTY_UNVERSIONED:
            if backup_path is None or not Path(backup_path).is_file():
                raise BackupRequired(
                    "A completed backup is required before migrating an "
                    "existing database"
                )
            verified_backup = Path(backup_path)
            if verified_backup.resolve(strict=False) == path.resolve(strict=False):
                raise BackupRequired("The backup must differ from the database")

        connection.execute("BEGIN IMMEDIATE")
        try:
            for migration in pending:
                migration.apply(connection)
                connection.execute(
                    f"PRAGMA user_version = {migration.version}"
                )
            connection.commit()
        except BaseException:
            connection.rollback()
            raise

        applied_versions = tuple(migration.version for migration in pending)
        return MigrationResult(
            initial_version,
            applied_versions[-1],
            applied_versions,
            verified_backup,
        )
    finally:
        connection.close()
