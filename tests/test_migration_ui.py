# Copyright (C) 2026 Matteo Sassi
# SPDX-License-Identifier: AGPL-3.0-only

"""Stable wiring tests for migration dialogs without creating Tk windows."""

from pathlib import Path

import pytest

import app
from ludox import bootstrap, config, migration_ui, migrations
from ludox.i18n import set_language


@pytest.fixture(autouse=True)
def italian_messages():
    set_language("it")
    yield
    set_language("it")


def legacy_plan(tmp_path):
    return migrations.MigrationPlan(
        tmp_path / "legacy.db",
        migrations.DatabaseState(migrations.DatabaseKind.LEGACY_UNVERSIONED, 0),
        1,
        (1,),
    )


def test_dialogo_conferma_mostra_versioni_e_backup(tmp_path, monkeypatch):
    captured = {}

    def askyesno(title, message, parent=None):
        captured.update(title=title, message=message, parent=parent)
        return True

    monkeypatch.setattr(migration_ui.messagebox, "askyesno", askyesno)

    assert migration_ui.chiedi_autorizzazione(
        legacy_plan(tmp_path), parent="window"
    ) is True
    assert "v0" in captured["message"]
    assert "v1" in captured["message"]
    assert "backup" in captured["message"].lower()
    assert captured["parent"] == "window"


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (migrations.UnsupportedSchemaVersion(2, 1), "v2"),
        (
            bootstrap.BackupCreationFailed(Path("backup.db"), "non scrivibile"),
            "Nessuna migration",
        ),
        (
            bootstrap.MigrationExecutionFailed(Path("backup.db"), "errore SQL"),
            "backup.db",
        ),
    ],
)
def test_dialogo_errore_descrive_la_chiusura(error, expected, monkeypatch):
    captured = {}

    def showerror(title, message, parent=None):
        captured.update(title=title, message=message, parent=parent)

    monkeypatch.setattr(migration_ui.messagebox, "showerror", showerror)

    migration_ui.mostra_errore(error)

    assert expected in captured["message"]
    assert "chiuso" in captured["message"]


def test_avvio_corrente_non_mostra_dialogo(monkeypatch):
    monkeypatch.setattr(app, "init_db", lambda **kwargs: object())
    monkeypatch.setattr(
        app.migration_ui,
        "chiedi_autorizzazione",
        lambda plan: pytest.fail("unexpected migration prompt"),
    )

    assert app.prepara_database_per_avvio("Organizzazione") is True


def test_avvio_legacy_rifiutato_non_esegue_la_migration(tmp_path, monkeypatch):
    calls = []

    def init_db(**kwargs):
        calls.append(kwargs)
        raise bootstrap.MigrationApprovalRequired(legacy_plan(tmp_path))

    monkeypatch.setattr(app, "init_db", init_db)
    monkeypatch.setattr(
        app.migration_ui,
        "chiedi_autorizzazione",
        lambda plan: False,
    )

    assert app.prepara_database_per_avvio("Organizzazione") is False
    assert len(calls) == 1
    assert "migration_authorized" not in calls[0]


def test_avvio_legacy_autorizzato_riprova_esplicitamente(tmp_path, monkeypatch):
    calls = []

    def init_db(**kwargs):
        calls.append(kwargs)
        if not kwargs.get("migration_authorized"):
            raise bootstrap.MigrationApprovalRequired(legacy_plan(tmp_path))
        return object()

    monkeypatch.setattr(app, "init_db", init_db)
    monkeypatch.setattr(
        app.migration_ui,
        "chiedi_autorizzazione",
        lambda plan: True,
    )

    assert app.prepara_database_per_avvio("Organizzazione") is True
    assert len(calls) == 2
    assert calls[1]["migration_authorized"] is True


def test_errore_migration_impedisce_avvio_operativo(monkeypatch):
    error = migrations.UnsupportedSchemaVersion(2, 1)
    shown = []

    def init_fallita(**kwargs):
        raise error

    monkeypatch.setattr(app, "init_db", init_fallita)
    monkeypatch.setattr(app.migration_ui, "mostra_errore", shown.append)

    assert app.prepara_database_per_avvio("Organizzazione") is False
    assert shown == [error]


def test_main_si_ferma_prima_dei_servizi_operativi_se_bootstrap_rifiutato(
    monkeypatch,
):
    monkeypatch.setattr(app, "ensure_config", lambda: config.AppConfig())
    monkeypatch.setattr(app, "set_db_path", lambda path: None)
    monkeypatch.setattr(app, "prepara_database_per_avvio", lambda owner: False)

    def accesso_operativo_inatteso(configuration):
        pytest.fail("organization context accessed before compatible schema")

    monkeypatch.setattr(
        app.organizations,
        "sincronizza_contesto",
        accesso_operativo_inatteso,
    )

    assert app.main() is None
