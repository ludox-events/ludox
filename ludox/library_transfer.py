# Copyright (C) 2026 Matteo Sassi
# SPDX-License-Identifier: AGPL-3.0-only

"""Portable game-library files, independent of the graphical interface."""

import csv
from pathlib import Path

from . import database as data


CSV_COLUMNS = ("game_name", "owner_label", "quantity")


def legacy_library_rows():
    """Read the aggregate legacy library without changing its database."""
    return [dict(row) for row in data.righe_export_ludoteca_legacy()]


def write_library_csv(path, rows):
    """Write canonical, comma-delimited UTF-8 library data."""
    with Path(path).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def export_legacy_library_csv(path):
    rows = legacy_library_rows()
    write_library_csv(path, rows)
    return len(rows)
