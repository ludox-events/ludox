# Copyright (C) 2026 Matteo Sassi
# SPDX-License-Identifier: AGPL-3.0-only

"""Integration coverage for the event-specific game library schema and APIs."""

from datetime import datetime

import pytest

from ludox import (
    catalog,
    copy_identifiers,
    database,
    events,
    lending,
    organizations,
    reporting,
)


def create_event(organization_id, slug):
    return events.create_event(
        organization_id,
        name=slug.replace("-", " ").title(),
        slug=slug,
        start_datetime="2026-09-13T09:00:00",
        end_datetime="2026-09-13T20:00:00",
        timezone="Europe/Rome",
        modules=("game_library",),
    )


@pytest.fixture
def event_pair(db):
    organization = organizations.crea_organizzazione("Ludoteca")
    return (
        create_event(organization.id, "spring"),
        create_event(organization.id, "autumn"),
    )


def populate(event_id, game_name="Azul", owner_name="Biblioteca", quantity=2):
    owner_id = catalog.aggiungi_proprietario(owner_name, event_id=event_id)
    game_id = catalog.aggiungi_gioco(game_name, event_id=event_id)
    catalog.imposta_quantita(
        game_id, owner_id, str(quantity), event_id=event_id
    )
    return owner_id, game_id


def test_schema_v4_preserves_legacy_tables_and_starts_new_library_empty(
    isolated_files,
):
    database.initialize_current_schema("Legacy owner")
    legacy_game = catalog.aggiungi_gioco("Legacy only")
    catalog.imposta_quantita(legacy_game, 1, "4")

    database.init_db(
        migration_authorized=True,
        now=datetime(2026, 9, 13, 10, 0),
    )
    organization = organizations.crea_organizzazione("Ludoteca")
    event = create_event(organization.id, "new-event")

    assert catalog.elenco_giochi_backoffice(event_id=event.id) == []
    assert catalog.elenco_proprietari(event_id=event.id) == []
    assert catalog.impostazioni_modulo(event.id) == {
        "event_id": event.id,
        "max_slots": 50,
        "identification_mode": "token",
    }
    assert catalog.gioco_per_id(legacy_game)["nome"] == "Legacy only"
    with database.get_db() as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM copie_gioco"
        ).fetchone()[0] == 1


def test_catalog_owners_physical_copies_and_names_are_isolated_by_event(event_pair):
    first, second = event_pair
    first_owner, first_game = populate(first.id, "Kingdomino", "LAM", 3)
    second_owner, second_game = populate(second.id, "Kingdomino", "Biblioteca", 1)

    assert first_game != second_game
    assert first_owner != second_owner
    assert catalog.totale_copie_proprietario(
        first_owner, event_id=first.id
    ) == 3
    assert catalog.totale_copie_proprietario(
        second_owner, event_id=second.id
    ) == 1
    with database.get_db() as connection:
        copies = connection.execute("""
            SELECT event_id, game_id, owner_label_id, COUNT(*)
            FROM game_library_game_copies
            GROUP BY event_id, game_id, owner_label_id ORDER BY event_id
        """).fetchall()
    assert [tuple(row) for row in copies] == [
        (first.id, first_game, first_owner, 3),
        (second.id, second_game, second_owner, 1),
    ]


def test_sessions_loans_slots_and_availability_do_not_cross_events(
    event_pair, monkeypatch,
):
    first, second = event_pair
    _, first_game = populate(first.id, quantity=2)
    _, second_game = populate(second.id, quantity=2)
    times = iter((
        "2026-09-13T10:00:00", "2026-09-13T10:05:00",
        "2026-09-13T11:00:00",
    ))
    monkeypatch.setattr(database, "now_iso", lambda: next(times))

    first_loan = lending.nuovo_prestito(first_game, event_id=first.id)
    second_loan = lending.nuovo_prestito(second_game, event_id=second.id)

    assert first_loan.token == second_loan.token == 1
    assert lending.riepilogo_home(event_id=first.id) == lending.RiepilogoHome(1, 1, 1)
    assert lending.riepilogo_home(event_id=second.id) == lending.RiepilogoHome(1, 1, 1)
    assert lending.disponibilita_gioco(first_game, event_id=first.id) == (1, 2)
    assert lending.disponibilita_gioco(second_game, event_id=second.id) == (1, 2)

    lending.restituzione_finale(
        documento_id=first_loan.documento_id,
        prestito_id=first_loan.prestito_id,
        event_id=first.id,
    )
    assert lending.situazione_chiusura(event_id=first.id).documenti_attivi == 0
    assert lending.situazione_chiusura(event_id=second.id).token == (1,)
    assert lending.consulta_token(1, event_id=second.id).prestito[
        "id"
    ] == second_loan.prestito_id


def test_max_slots_is_event_specific_and_cannot_hide_an_occupied_slot(
    event_pair, monkeypatch,
):
    first, second = event_pair
    _, first_game = populate(first.id, quantity=2)
    _, second_game = populate(second.id, quantity=2)
    monkeypatch.setattr(database, "now_iso", lambda: "2026-09-13T10:00:00")
    catalog.modifica_impostazioni_modulo(first.id, 1)
    catalog.modifica_impostazioni_modulo(second.id, 3)

    lending.nuovo_prestito(first_game, event_id=first.id)
    with pytest.raises(lending.TokenEsauriti):
        lending.nuovo_prestito(first_game, event_id=first.id)
    first_second = lending.nuovo_prestito(second_game, event_id=second.id)
    second_second = lending.nuovo_prestito(second_game, event_id=second.id)
    assert (first_second.token, second_second.token) == (1, 2)
    with pytest.raises(catalog.ConfigurazioneNonValida):
        catalog.modifica_impostazioni_modulo(second.id, 1)


def test_reporting_and_history_are_event_scoped(event_pair, monkeypatch):
    first, second = event_pair
    first_owner, first_game = populate(first.id)
    _, second_game = populate(second.id, game_name="Cascadia")
    first_copy = copy_identifiers.list_copies(first.id)[0]["copy_id"]
    copy_identifiers.assign_external(first.id, first_copy, "FIRST-COPY")
    catalog.modifica_impostazioni_modulo(
        first.id, 50, "copy_identifier"
    )
    timestamps = iter((
        "2026-09-13T10:00:00",
        "2026-09-13T11:00:00",
        "2026-09-13T12:00:00",
    ))
    monkeypatch.setattr(database, "now_iso", lambda: next(timestamps))
    first_loan = lending.nuovo_prestito_da_identificatore(
        "FIRST-COPY", event_id=first.id
    )
    lending.nuovo_prestito(second_game, event_id=second.id)

    first_history = reporting.storico_prestiti(event_id=first.id)
    second_history = reporting.storico_prestiti(event_id=second.id)
    assert [row["gioco"] for row in first_history.righe] == ["Azul"]
    assert [row["gioco"] for row in second_history.righe] == ["Cascadia"]
    assert (
        first_history.righe[0]["copy_id"],
        first_history.righe[0]["copy_identifier"],
        first_history.righe[0]["owner_label"],
    ) == (first_copy, "FIRST-COPY", "Biblioteca")
    assert second_history.righe[0]["copy_id"] is None
    report = reporting.report_utilizzo(
        datetime(2026, 9, 13), datetime(2026, 9, 13), event_id=first.id
    )
    assert report.totale_prestiti == 1
    assert [row["gioco"] for row in report.righe] == ["Azul"]
    assert report.righe[0]["copie_prestito"] == (
        f"#{first_copy} · FIRST-COPY · Biblioteca"
    )
    lending.conferma_restituzione_copia(
        lending.consulta_copia_in_prestito("FIRST-COPY", event_id=first.id)
    )
    copy_identifiers.replace(first.id, first_copy, "CURRENT-CODE")
    assert reporting.storico_prestiti(event_id=first.id).righe[0][
        "copy_identifier"
    ] == "CURRENT-CODE"


def test_identification_mode_change_requires_no_open_sessions_or_loans(
    event_pair, monkeypatch,
):
    first, second = event_pair
    _, first_game = populate(first.id, quantity=2)
    _, second_game = populate(second.id, quantity=1)
    monkeypatch.setattr(database, "now_iso", lambda: "2026-09-13T10:00:00")
    first_loan = lending.nuovo_prestito(first_game, event_id=first.id)

    catalog.modifica_impostazioni_modulo(first.id, 60, "token")
    with pytest.raises(catalog.CambioModalitaBloccato):
        catalog.modifica_impostazioni_modulo(first.id, 60, "copy_identifier")
    assert catalog.impostazioni_modulo(first.id)["identification_mode"] == "token"

    lending.restituzione_finale(
        documento_id=first_loan.documento_id,
        prestito_id=first_loan.prestito_id,
        event_id=first.id,
    )
    before_copies = copy_identifiers.list_copies(first.id)
    catalog.modifica_impostazioni_modulo(first.id, 60, "copy_identifier")
    assert catalog.impostazioni_modulo(first.id)["identification_mode"] == (
        "copy_identifier"
    )
    assert copy_identifiers.list_copies(first.id) == before_copies

    second_loan = lending.nuovo_prestito(second_game, event_id=second.id)
    with database.get_db() as connection:
        connection.execute("""
            UPDATE game_library_sessions SET closed_at = ?
            WHERE event_id = ? AND id = ?
        """, ("2026-09-13T10:05:00", second.id, second_loan.documento_id))
    with pytest.raises(catalog.CambioModalitaBloccato):
        catalog.modifica_impostazioni_modulo(
            second.id, 50, "copy_identifier"
        )


def test_open_session_blocks_module_disable_and_history_blocks_event_delete(
    event_pair, monkeypatch,
):
    first, second = event_pair
    _, game_id = populate(first.id)
    monkeypatch.setattr(database, "now_iso", lambda: "2026-09-13T10:00:00")
    loan = lending.nuovo_prestito(game_id, event_id=first.id)

    with pytest.raises(events.ModuleHasOpenSessions):
        events.set_module_enabled(first.id, "game_library", False)
    with pytest.raises(events.EventDeletionBlocked):
        events.delete_event(first.id)

    lending.restituzione_finale(
        documento_id=loan.documento_id,
        prestito_id=loan.prestito_id,
        event_id=first.id,
    )
    events.set_module_enabled(first.id, "game_library", False)
    assert events.get_event(first.id).modules["game_library"] is False
    assert reporting.storico_prestiti(event_id=first.id).totale == 1
    events.delete_event(second.id)
    assert events.get_event(second.id) is None
