# Copyright (C) 2026 Matteo Sassi
# SPDX-License-Identifier: AGPL-3.0-only

"""Small presentation helpers that do not depend on Tkinter."""

from datetime import date, datetime, time
from zoneinfo import ZoneInfo, available_timezones


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
_TIMEZONE_BY_CASEFOLD = {
    timezone.casefold(): timezone for timezone in TIMEZONE_VALUES
}


def _system_offset_at(value):
    return value.astimezone().utcoffset()


def _local_timezone_key():
    return getattr(datetime.now().astimezone().tzinfo, "key", None)


def detect_local_timezone():
    """Return the local IANA timezone, including on Windows when possible."""
    local_key = _local_timezone_key()
    if local_key in _KNOWN_TIMEZONES:
        return local_key

    current_year = datetime.now().year
    probes = tuple(
        datetime(year, month, 15, 12)
        for year in range(current_year - 1, current_year + 2)
        for month in range(1, 13)
    )
    system_offsets = tuple(_system_offset_at(probe) for probe in probes)
    for timezone in TIMEZONE_VALUES:
        candidate = ZoneInfo(timezone)
        candidate_offsets = tuple(
            probe.replace(tzinfo=candidate).utcoffset() for probe in probes
        )
        if candidate_offsets == system_offsets:
            return timezone
    return "UTC"


def filter_timezone_values(query):
    normalized = str(query or "").strip().casefold()
    if not normalized:
        return TIMEZONE_VALUES
    starts_with = tuple(
        timezone for timezone in TIMEZONE_VALUES
        if timezone.casefold().startswith(normalized)
    )
    contains = tuple(
        timezone for timezone in TIMEZONE_VALUES
        if normalized in timezone.casefold() and timezone not in starts_with
    )
    return starts_with + contains


def canonical_timezone(value):
    try:
        return _TIMEZONE_BY_CASEFOLD[str(value).strip().casefold()]
    except KeyError as exc:
        raise ValueError("Select a valid timezone") from exc


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
