# Copyright (C) 2026 Matteo Sassi
# SPDX-License-Identifier: AGPL-3.0-only

import sqlite3

from ludox import bootstrap, migration_ui, migrations, organizations
from ludox.config import ensure_config
from ludox.database import init_db, set_db_path
from ludox.i18n import set_language, tr


MIGRATION_STARTUP_ERRORS = (
    bootstrap.BackupCreationFailed,
    bootstrap.MigrationExecutionFailed,
    migrations.MigrationError,
    sqlite3.Error,
    OSError,
)


def prepara_database_per_avvio(default_owner_name):
    try:
        init_db(default_owner_name=default_owner_name)
    except bootstrap.MigrationApprovalRequired as request:
        if not migration_ui.chiedi_autorizzazione(request.plan):
            return False
        try:
            init_db(
                default_owner_name=default_owner_name,
                migration_authorized=True,
            )
        except MIGRATION_STARTUP_ERRORS as error:
            migration_ui.mostra_errore(error)
            return False
    except MIGRATION_STARTUP_ERRORS as error:
        migration_ui.mostra_errore(error)
        return False
    return True


def main():
    config = ensure_config()
    set_language(config.language)
    set_db_path(config.database)
    if not prepara_database_per_avvio(tr("owner.default")):
        return
    organization_context = organizations.sincronizza_contesto(config)
    from ludox.ui import PrestitiApp

    app = PrestitiApp(
        organization_context.configurazione,
        organization_context,
    )
    app.mainloop()


if __name__ == "__main__":
    main()
