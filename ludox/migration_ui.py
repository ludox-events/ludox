# Copyright (C) 2026 Matteo Sassi
# SPDX-License-Identifier: AGPL-3.0-only

"""Tkinter dialogs for the database migration startup flow."""

from tkinter import messagebox

from . import bootstrap, migrations
from .i18n import tr


def chiedi_autorizzazione(plan, *, parent=None):
    return messagebox.askyesno(
        tr("migration.required_title"),
        tr(
            "migration.required_message_tpl",
            current=plan.state.version,
            required=plan.target_version,
        ),
        parent=parent,
    )


def mostra_errore(error, *, parent=None):
    if isinstance(error, migrations.UnsupportedSchemaVersion):
        title = tr("migration.future_title")
        message = tr(
            "migration.future_message_tpl",
            current=error.found_version,
            supported=error.supported_version,
        )
    elif isinstance(error, bootstrap.BackupCreationFailed):
        title = tr("migration.backup_failed_title")
        message = tr(
            "migration.backup_failed_message_tpl",
            path=error.backup_path,
            error=error.detail,
        )
    elif isinstance(error, bootstrap.MigrationExecutionFailed):
        title = tr("migration.failed_title")
        if error.backup_path is None:
            message = tr(
                "migration.failed_no_backup_message_tpl",
                error=error.detail,
            )
        else:
            message = tr(
                "migration.failed_message_tpl",
                path=error.backup_path,
                error=error.detail,
            )
    else:
        title = tr("migration.invalid_title")
        message = tr("migration.invalid_message_tpl", error=error)

    messagebox.showerror(title, message, parent=parent)
