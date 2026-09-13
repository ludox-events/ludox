# Copyright (C) 2026 Matteo Sassi
# SPDX-License-Identifier: AGPL-3.0-only

"""Copy-identifier loan opening and token regression coverage."""

import pytest

from ludox import catalog, copy_identifiers, database, events, lending, organizations


def create_event(slug, *, mode="copy_identifier", max_slots=50):
    available = organizations.elenco_organizzazioni()
    organization = (
        available[0]
        if available
        else organizations.crea_organizzazione("Ludoteca")
    )
    event = events.create_event(
        organization.id,
        name=slug,
        slug=slug,
        start_datetime="2026-09-13T09:00:00",
        end_datetime="2026-09-13T20:00:00",
        timezone="Europe/Rome",
        modules=("game_library",),
    )
    catalog.modifica_impostazioni_modulo(event.id, max_slots, mode)
    return event


def create_identified_copy(event, code, *, game_name="Azul"):
    owners = catalog.elenco_proprietari(event_id=event.id)
    owner_id = (
        owners[0]["id"]
        if owners
        else catalog.aggiungi_proprietario("Biblioteca", event_id=event.id)
    )
    game_id = catalog.aggiungi_gioco(game_name, event_id=event.id)
    catalog.imposta_quantita(game_id, owner_id, "1", event_id=event.id)
    copy_id = copy_identifiers.list_copies(event.id)[-1]["copy_id"]
    copy_identifiers.assign_external(event.id, copy_id, code)
    return game_id, copy_id


def event_snapshot(event_id):
    with database.get_db() as connection:
        return tuple(
            tuple(tuple(row) for row in connection.execute(
                f"SELECT * FROM {table} WHERE event_id = ? ORDER BY id",
                (event_id,),
            ))
            for table in ("game_library_sessions", "game_library_loans")
        )


def test_new_copy_identifier_loan_records_copy_and_first_slot(db, monkeypatch):
    event = create_event("copy-new")
    game_id, copy_id = create_identified_copy(event, "BIB-001")
    monkeypatch.setattr(database, "now_iso", lambda: "2026-09-13T10:00:00")

    result = lending.nuovo_prestito_da_identificatore(
        " BIB-001 ", event_id=event.id
    )

    assert result.slot == 1
    assert result.copy_id == copy_id
    assert result.copy_identifier == "BIB-001"
    assert result.gioco_nome == "Azul"
    with database.get_db() as connection:
        loan = connection.execute("""
            SELECT game_id, copy_id FROM game_library_loans WHERE id = ?
        """, (result.prestito_id,)).fetchone()
    assert tuple(loan) == (game_id, copy_id)
    assert copy_identifiers.list_copies(event.id)[0]["availability"] == "on_loan"


def test_unknown_or_other_event_identifier_does_not_write(db):
    first = create_event("copy-first")
    second = create_event("copy-second")
    create_identified_copy(second, "OTHER-EVENT")
    before = event_snapshot(first.id)

    for value in ("UNKNOWN", "OTHER-EVENT"):
        with pytest.raises(copy_identifiers.UnknownCopyIdentifier):
            lending.nuovo_prestito_da_identificatore(value, event_id=first.id)
        assert event_snapshot(first.id) == before


@pytest.mark.parametrize(
    "target,exception",
    [("copy", lending.CopiaInattiva), ("game", lending.GiocoInattivo)],
)
def test_inactive_copy_or_game_is_rejected_without_writes(db, target, exception):
    event = create_event(f"inactive-{target}")
    game_id, copy_id = create_identified_copy(event, "INACTIVE")
    if target == "copy":
        copy_identifiers.set_active(event.id, copy_id, False)
    else:
        catalog.modifica_gioco(game_id, "Azul", False, event_id=event.id)
    before = event_snapshot(event.id)

    with pytest.raises(exception):
        lending.nuovo_prestito_da_identificatore("INACTIVE", event_id=event.id)
    assert event_snapshot(event.id) == before


def test_copy_already_on_loan_and_exhausted_slots_are_rejected(db):
    event = create_event("copy-busy", max_slots=1)
    create_identified_copy(event, "FIRST", game_name="Azul")
    create_identified_copy(event, "SECOND", game_name="Cascadia")
    lending.nuovo_prestito_da_identificatore("FIRST", event_id=event.id)
    before = event_snapshot(event.id)

    with pytest.raises(lending.CopiaGiaInPrestito):
        lending.nuovo_prestito_da_identificatore("FIRST", event_id=event.id)
    with pytest.raises(lending.TokenEsauriti):
        lending.nuovo_prestito_da_identificatore("SECOND", event_id=event.id)
    assert event_snapshot(event.id) == before


def test_identification_modes_are_alternative_and_token_remains_compatible(db):
    copy_event = create_event("mode-copy")
    game_id, _ = create_identified_copy(copy_event, "COPY")
    with pytest.raises(lending.ModalitaIdentificazioneNonValida):
        lending.nuovo_prestito(game_id, event_id=copy_event.id)

    token_event = create_event("mode-token", mode="token")
    token_game, _ = create_identified_copy(token_event, "OPTIONAL")
    with pytest.raises(lending.ModalitaIdentificazioneNonValida):
        lending.nuovo_prestito_da_identificatore("OPTIONAL", event_id=token_event.id)
    token_loan = lending.nuovo_prestito(token_game, event_id=token_event.id)
    assert token_loan.copy_id is None
    with database.get_db() as connection:
        assert connection.execute("""
            SELECT copy_id FROM game_library_loans WHERE id = ?
        """, (token_loan.prestito_id,)).fetchone()[0] is None
