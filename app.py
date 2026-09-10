# Copyright (C) 2026 Matteo Sassi
# SPDX-License-Identifier: AGPL-3.0-only

from ludox.config import ensure_config
from ludox.database import init_db, set_db_path
from ludox.i18n import set_language, tr
from ludox.ui import PrestitiApp


def main():
    config = ensure_config()
    set_language(config.language)
    set_db_path(config.database)
    init_db(default_owner_name=tr("owner.default"))

    app = PrestitiApp(config)
    app.mainloop()


if __name__ == "__main__":
    main()
