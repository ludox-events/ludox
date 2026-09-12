# Copyright (C) 2026 Matteo Sassi
# SPDX-License-Identifier: AGPL-3.0-only

"""Event service and context tests on temporary SQLite databases."""

import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from ludox import config, events, organizations


def make_organization(name="Ludoteca Centro"):
    return organizations.crea_organizzazione(name)


def make_event(organization_id, slug="amigo-2027", **changes):
    values = {
        "name": "AMIGO 2027",
        "slug": slug,
        "start_datetime": "2027-06-01T09:00:00",
        "end_datetime": "2027-06-03T20:00:00",
        "timezone": "Europe/Rome",
        "modules": ("game_library",),
    }
    values.update(changes)
    return events.create_event(organization_id, **values)


def test_create_update_status_and_modules(db):
    organization = make_organization()

    event = make_event(organization.id)

    assert event.organization_id == organization.id
    assert event.status == "draft"
    assert event.modules == {"game_library": True, "activities": False}
    updated = events.update_event(
        event.id,
        name="AMIGO aggiornato",
        start_datetime=event.start_datetime,
        end_datetime=event.end_datetime,
        timezone="UTC",
        status="active",
    )
    assert (updated.name, updated.slug, updated.status) == (
        "AMIGO aggiornato",
        "amigo-2027",
        "active",
    )
    assert events.set_module_enabled(event.id, "activities", True).modules == {
        "game_library": True,
        "activities": True,
    }
    assert events.set_module_enabled(event.id, "game_library", False).modules == {
        "game_library": False,
        "activities": True,
    }


def test_slug_unique_per_organization_and_identity_is_immutable(db):
    first_organization = make_organization("Prima")
    second_organization = make_organization("Seconda")
    first = make_event(first_organization.id)

    with pytest.raises(events.DuplicateSlug):
        make_event(first_organization.id, name="Altro")
    second = make_event(second_organization.id)
    assert second.slug == first.slug

    with pytest.raises(sqlite3.IntegrityError, match="organization is immutable"):
        db.execute(
            "UPDATE events SET organization_id = ? WHERE id = ?",
            (second_organization.id, first.id),
        )
    with pytest.raises(sqlite3.IntegrityError, match="slug is immutable"):
        db.execute(
            "UPDATE events SET slug = 'changed' WHERE id = ?",
            (first.id,),
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"name": " "},
        {"slug": "AMIGO"},
        {"slug": "amigo 2027"},
        {"start_datetime": "invalid"},
        {"end_datetime": "2027-05-31T09:00:00"},
        {"timezone": "Invalid/Timezone"},
        {"modules": ("unknown",)},
    ],
)
def test_creation_validation_does_not_write(db, changes):
    organization = make_organization()
    expected_error = (
        events.UnknownModule if "modules" in changes else events.InvalidEvent
    )

    with pytest.raises(expected_error):
        make_event(organization.id, **changes)

    assert events.list_events(organization.id) == []


def test_context_handles_zero_one_many_and_id_slug_pair(db, tmp_path):
    organization = make_organization()
    path = tmp_path / "config.ini"

    empty = events.resolve_context(config.AppConfig(), organization.id)
    assert empty == events.EventContext(None, config.AppConfig(), False)

    first = make_event(organization.id)
    single = events.sync_context(config.AppConfig(), organization.id, path)
    assert single.event == first
    assert config.load_config(path) == single.configuration

    second = make_event(organization.id, slug="estate-2027", name="Estate")
    valid = events.resolve_context(single.configuration, organization.id)
    invalid = events.resolve_context(
        config.AppConfig(
            active_event_id=first.id,
            active_event_slug="wrong",
        ),
        organization.id,
    )
    assert valid.event == first
    assert invalid.event is None and invalid.selection_required

    selected = events.select_event(
        second.id, organization.id, invalid.configuration, path
    )
    assert selected.event == second
    events.set_event_status(second.id, "archived")
    resolved = events.sync_context(selected.configuration, organization.id, path)
    assert resolved.event == first


def test_context_rejects_event_from_another_organization(db, tmp_path):
    first_organization = make_organization("Prima")
    second_organization = make_organization("Seconda")
    foreign = make_event(first_organization.id)
    make_event(second_organization.id, slug="secondo")

    with pytest.raises(events.EventNotSelectable):
        events.select_event(
            foreign.id,
            second_organization.id,
            config.AppConfig(),
            tmp_path / "config.ini",
        )


def test_delete_event_removes_preparatory_modules(db):
    organization = make_organization()
    event = make_event(organization.id, modules=("game_library", "activities"))

    events.delete_event(event.id)

    assert events.get_event(event.id) is None
    assert db.execute(
        "SELECT * FROM event_modules WHERE event_id = ?", (event.id,)
    ).fetchall() == []


def test_event_service_has_no_gui_dependency():
    root = Path(__file__).resolve().parents[1]
    code = """
import sys
class NoGUI:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('tkinter', 'ttkbootstrap', 'matplotlib'):
            raise AssertionError('GUI dependency: ' + fullname)
sys.meta_path.insert(0, NoGUI())
from ludox import events
assert 'ludox.ui' not in sys.modules
"""
    subprocess.run(
        [sys.executable, "-B", "-c", code],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
