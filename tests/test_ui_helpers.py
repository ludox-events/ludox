# Copyright (C) 2026 Matteo Sassi
# SPDX-License-Identifier: AGPL-3.0-only

"""Tests for selectable date/time values passed to the Event service."""

from datetime import date, datetime

import pytest

from ludox import events, organizations
from ludox.ui_helpers import (
    HOUR_VALUES,
    MINUTE_VALUES,
    TIMEZONE_VALUES,
    canonical_timezone,
    compose_picker_datetime,
    detect_local_timezone,
    filter_timezone_values,
    split_picker_datetime,
)


def test_date_hour_and_minute_are_composed_without_requesting_seconds():
    assert compose_picker_datetime(date(2027, 6, 1), "09", "05") == (
        "2027-06-01T09:05:00"
    )
    assert compose_picker_datetime(
        datetime(2027, 6, 3, 0, 0), "20", "30"
    ) == "2027-06-03T20:30:00"
    assert HOUR_VALUES == tuple(f"{value:02d}" for value in range(24))
    assert MINUTE_VALUES == tuple(f"{value:02d}" for value in range(60))


@pytest.mark.parametrize(
    "selected_date,hour,minute",
    [("2027-06-01", "09", "00"), (date(2027, 6, 1), "24", "00"),
     (date(2027, 6, 1), "09", "60")],
)
def test_invalid_picker_values_are_rejected(selected_date, hour, minute):
    with pytest.raises(ValueError):
        compose_picker_datetime(selected_date, hour, minute)


def test_existing_datetime_is_split_for_event_modification():
    assert split_picker_datetime("2027-06-03T20:45:00") == (
        date(2027, 6, 3), "20", "45"
    )


def test_timezone_selector_uses_the_system_iana_catalog_with_common_choices_first():
    assert TIMEZONE_VALUES[:2] == ("Europe/Rome", "UTC")
    assert "America/New_York" in TIMEZONE_VALUES
    assert len(TIMEZONE_VALUES) > 100


def test_timezone_search_filters_and_canonicalizes_valid_choices():
    assert filter_timezone_values("rome") == ("Europe/Rome",)
    europe = filter_timezone_values("europe/")
    assert europe[0] == "Europe/Rome"
    assert "Europe/Amsterdam" in europe
    assert canonical_timezone(" europe/rome ") == "Europe/Rome"
    with pytest.raises(ValueError, match="valid timezone"):
        canonical_timezone("Rome")


def test_local_timezone_detection_matches_windows_offsets(monkeypatch):
    from ludox import ui_helpers

    rome = ui_helpers.ZoneInfo("Europe/Rome")
    monkeypatch.setattr(
        ui_helpers,
        "_system_offset_at",
        lambda value: value.replace(tzinfo=rome).utcoffset(),
    )
    monkeypatch.setattr(ui_helpers, "_local_timezone_key", lambda: None)
    assert detect_local_timezone() == "Europe/Rome"


def test_composed_picker_values_create_update_and_validate_event(db):
    organization = organizations.crea_organizzazione("Ludoteca")
    start = compose_picker_datetime(date(2027, 6, 1), "09", "15")
    end = compose_picker_datetime(date(2027, 6, 1), "18", "45")
    event = events.create_event(
        organization.id,
        name="Evento",
        slug="evento",
        start_datetime=start,
        end_datetime=end,
        timezone="Europe/Rome",
    )
    assert (event.start_datetime, event.end_datetime, event.timezone) == (
        start, end, "Europe/Rome"
    )

    updated_start = compose_picker_datetime(date(2027, 6, 2), "10", "00")
    updated_end = compose_picker_datetime(date(2027, 6, 2), "19", "30")
    updated = events.update_event(
        event.id,
        name=event.name,
        start_datetime=updated_start,
        end_datetime=updated_end,
        timezone="UTC",
        status=event.status,
    )
    assert (updated.start_datetime, updated.end_datetime, updated.timezone) == (
        updated_start, updated_end, "UTC"
    )

    with pytest.raises(events.InvalidEvent):
        events.update_event(
            event.id,
            name=event.name,
            start_datetime=updated_end,
            end_datetime=updated_start,
            timezone="UTC",
            status=event.status,
        )
