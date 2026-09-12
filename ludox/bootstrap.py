# Copyright (C) 2026 Matteo Sassi
# SPDX-License-Identifier: AGPL-3.0-only

"""Technical database startup flow, independent of the user interface."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable

from . import migrations


class MigrationApprovalRequired(Exception):
    def __init__(self, plan):
        self.plan = plan
        super().__init__(
            f"Migration approval required from version {plan.state.version} "
            f"to {plan.target_version}"
        )


class BackupCreationFailed(Exception):
    def __init__(self, backup_path, error):
        self.backup_path = backup_path
        self.detail = str(error)
        super().__init__(self.detail)


class MigrationExecutionFailed(Exception):
    def __init__(self, backup_path, error):
        self.backup_path = backup_path
        self.detail = str(error)
        super().__init__(self.detail)


@dataclass(frozen=True)
class DatabaseStartupResult:
    plan: migrations.MigrationPlan
    migration_result: migrations.MigrationResult
    backup_path: Path | None


def prepare_database(
    database_path,
    *,
    migration_authorized=False,
    initialize_schema: Callable[[], None] | None = None,
    target_version=migrations.CURRENT_SCHEMA_VERSION,
    migration_steps: Iterable[migrations.Migration] = migrations.MIGRATIONS,
    now: datetime | None = None,
):
    """Prepare one database for use, stopping before unsafe migration work."""
    plan = migrations.plan_database(
        database_path,
        target_version=target_version,
        migration_steps=migration_steps,
    )
    if plan.state.kind is migrations.DatabaseKind.FUTURE_UNSUPPORTED:
        raise migrations.UnsupportedSchemaVersion(
            plan.state.version,
            plan.target_version,
        )
    if plan.migration_required and not migration_authorized:
        raise MigrationApprovalRequired(plan)

    backup_path = None
    if plan.migration_required:
        backup_path = migrations.automatic_backup_path(plan, now)
        try:
            migrations.create_backup(plan.database_path, backup_path)
        except Exception as exc:
            raise BackupCreationFailed(backup_path, exc) from exc

    try:
        migration_result = migrations.migrate_database(
            plan.database_path,
            target_version=target_version,
            migration_steps=migration_steps,
            backup_path=backup_path,
        )
    except Exception as exc:
        raise MigrationExecutionFailed(backup_path, exc) from exc

    if initialize_schema is not None:
        initialize_schema()

    return DatabaseStartupResult(plan, migration_result, backup_path)
