# Copyright (C) 2026 Matteo Sassi
# SPDX-License-Identifier: AGPL-3.0-only

"""Small presentation helpers that do not depend on Tkinter."""

from datetime import date, datetime, time
from zoneinfo import available_timezones


HOUR_VALUES = tuple(f"{value:02d}" for value in range(24))
MINUTE_VALUES = tuple(f"{value:02d}" for value in range(60))
_KNOWN_TIMEZONES = available_timezones()
_PREFERRED_TIMEZONES = tuple(
    timezone
    for timezone in ("Europe/Rome", "UTC")
    if timezone in _KNOWN_TIMEZONES
)
TIMEZONE_VALUES = _PREFERRED_TIMEZONES + tuple(
    sorted(_KNOWN_TIMEZONES.difference(_PREFERRED_TIMEZONES))
)


def compose_picker_datetime(selected_date, hour, minute):
    """Combine selectable date/hour/minute values for the Event service."""
    if isinstance(selected_date, datetime):
        selected_date = selected_date.date()
    if not isinstance(selected_date, date):
        raise ValueError("Invalid date")
    try:
        hour_value = int(hour)
        minute_value = int(minute)
        selected_time = time(hour_value, minute_value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid time") from exc
    return datetime.combine(selected_date, selected_time).isoformat(
        timespec="seconds"
    )


def split_picker_datetime(value, *, fallback=None):
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        parsed = fallback or datetime.now().replace(second=0, microsecond=0)
    return parsed.date(), f"{parsed.hour:02d}", f"{parsed.minute:02d}"
