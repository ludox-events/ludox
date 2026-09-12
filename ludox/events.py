# Copyright (C) 2026 Matteo Sassi
# SPDX-License-Identifier: AGPL-3.0-only

"""Event management and workstation event context, without Tkinter."""

from __future__ import annotations

import re
import sqlite3
import unicodedata
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from . import config
from . import database as data


EVENT_STATES = ("draft", "active", "archived", "cancelled")
SELECTABLE_STATES = ("draft", "active")
MODULE_IDS = ("game_library", "activities")
SLUG_PATTERN = re.compile(r"^[a-z0-9_-]+$")


class EventError(Exception):
    pass


class OrganizationRequired(EventError):
    pass


class EventNotFound(EventError):
    pass


class InvalidEvent(EventError):
    pass


class DuplicateSlug(EventError):
    pass


class EventNotSelectable(EventError):
    pass


class UnknownModule(EventError):
    pass


class EventDeletionBlocked(EventError):
    pass


@dataclass(frozen=True)
class Event:
    id: int
    organization_id: int
    name: str
    slug: str
    start_datetime: str
    end_datetime: str
    timezone: str
    status: str
    modules: dict[str, bool]


@dataclass(frozen=True)
class EventContext:
    event: Event | None
    configuration: config.AppConfig
    selection_required: bool


def suggested_slug(name):
    ascii_name = unicodedata.normalize("NFKD", str(name)).encode(
        "ascii", "ignore"
    ).decode("ascii")
    slug = re.sub(r"[^a-z0-9_-]+", "-", ascii_name.casefold()).strip("-_")
    return slug or "event"


def _valid_name(value):
    value = value.strip() if isinstance(value, str) else ""
    if not value:
        raise InvalidEvent("Event name is required")
    return value


def _valid_slug(value):
    value = value.strip() if isinstance(value, str) else ""
    if not SLUG_PATTERN.fullmatch(value):
        raise InvalidEvent("Invalid Event slug")
    return value


def _valid_dates(start, end):
    try:
        start_value = datetime.fromisoformat(str(start).strip())
        end_value = datetime.fromisoformat(str(end).strip())
        if end_value <= start_value:
            raise ValueError
    except (TypeError, ValueError) as exc:
        raise InvalidEvent("Event end must be after its start") from exc
    return (
        start_value.isoformat(timespec="seconds"),
        end_value.isoformat(timespec="seconds"),
    )


def _valid_timezone(value):
    value = value.strip() if isinstance(value, str) else ""
    try:
        ZoneInfo(value)
    except (ValueError, ZoneInfoNotFoundError) as exc:
        raise InvalidEvent("Invalid Event timezone") from exc
    return value


def _valid_status(value):
    if value not in EVENT_STATES:
        raise InvalidEvent("Invalid Event status")
    return value


def _modules(event_id):
    configured = {
        row["module_id"]: bool(row["enabled"])
        for row in data.moduli_evento(event_id)
    }
    return {module_id: configured.get(module_id, False) for module_id in MODULE_IDS}


def _from_row(row):
    return Event(
        id=row["id"],
        organization_id=row["organization_id"],
        name=row["name"],
        slug=row["slug"],
        start_datetime=row["start_datetime"],
        end_datetime=row["end_datetime"],
        timezone=row["timezone"],
        status=row["status"],
        modules=_modules(row["id"]),
    )


def get_event(event_id):
    row = data.evento_per_id(event_id)
    return _from_row(row) if row is not None else None


def list_events(organization_id, *, selectable_only=False):
    if organization_id is None:
        return []
    return [
        _from_row(row)
        for row in data.elenco_eventi(organization_id, selectable_only)
    ]


def create_event(
    organization_id,
    *,
    name,
    slug,
    start_datetime,
    end_datetime,
    timezone="UTC",
    modules=(),
):
    if organization_id is None:
        raise OrganizationRequired()
    name = _valid_name(name)
    slug = _valid_slug(slug)
    start_datetime, end_datetime = _valid_dates(start_datetime, end_datetime)
    timezone = _valid_timezone(timezone)
    module_ids = tuple(dict.fromkeys(modules))
    if any(module_id not in MODULE_IDS for module_id in module_ids):
        raise UnknownModule()
    try:
        event_id = data.inserisci_evento(
            organization_id,
            name,
            slug,
            start_datetime,
            end_datetime,
            timezone,
        )
        for module_id in module_ids:
            data.imposta_modulo_evento(event_id, module_id, True)
    except sqlite3.IntegrityError as exc:
        if "events.organization_id, events.slug" in str(exc):
            raise DuplicateSlug() from exc
        raise
    return get_event(event_id)


def update_event(
    event_id,
    *,
    name,
    start_datetime,
    end_datetime,
    timezone,
    status,
):
    if get_event(event_id) is None:
        raise EventNotFound()
    name = _valid_name(name)
    start_datetime, end_datetime = _valid_dates(start_datetime, end_datetime)
    timezone = _valid_timezone(timezone)
    status = _valid_status(status)
    data.aggiorna_evento(
        event_id, name, start_datetime, end_datetime, timezone, status
    )
    return get_event(event_id)


def set_event_status(event_id, status):
    event = get_event(event_id)
    if event is None:
        raise EventNotFound()
    return update_event(
        event_id,
        name=event.name,
        start_datetime=event.start_datetime,
        end_datetime=event.end_datetime,
        timezone=event.timezone,
        status=status,
    )


def set_module_enabled(event_id, module_id, enabled):
    if module_id not in MODULE_IDS:
        raise UnknownModule()
    if get_event(event_id) is None:
        raise EventNotFound()
    data.imposta_modulo_evento(event_id, module_id, bool(enabled))
    return get_event(event_id)


def delete_event(event_id):
    if get_event(event_id) is None:
        raise EventNotFound()
    if data.evento_ha_storico(event_id):
        raise EventDeletionBlocked()
    data.elimina_evento(event_id)


def _with_reference(configuration, event):
    return replace(
        configuration,
        active_event_id=event.id if event is not None else None,
        active_event_slug=event.slug if event is not None else None,
    )


def resolve_context(configuration, organization_id):
    selectable = list_events(organization_id, selectable_only=True)
    if not selectable:
        return EventContext(None, _with_reference(configuration, None), False)
    if len(selectable) == 1:
        event = selectable[0]
        return EventContext(event, _with_reference(configuration, event), False)
    event = next(
        (
            candidate
            for candidate in selectable
            if candidate.id == configuration.active_event_id
            and candidate.slug == configuration.active_event_slug
        ),
        None,
    )
    return EventContext(
        event,
        _with_reference(configuration, event),
        event is None,
    )


def sync_context(configuration, organization_id, configuration_path=None):
    context = resolve_context(configuration, organization_id)
    if context.configuration != configuration:
        config.save_config(
            context.configuration,
            configuration_path or config.CONFIG_PATH,
        )
    return context


def select_event(event_id, organization_id, configuration, configuration_path=None):
    event = get_event(event_id)
    if event is None:
        raise EventNotFound()
    if event.organization_id != organization_id or event.status not in SELECTABLE_STATES:
        raise EventNotSelectable()
    updated = _with_reference(configuration, event)
    config.save_config(updated, configuration_path or config.CONFIG_PATH)
    return EventContext(event, updated, False)
