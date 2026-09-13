# Copyright (C) 2026 Matteo Sassi
# SPDX-License-Identifier: AGPL-3.0-only

"""Domain and persistence coverage for event-scoped copy identifiers."""

import pytest

from ludox import catalog, copy_identifiers, database, events, organizations


def create_event(slug):
    organizations_available = organizations.elenco_organizzazioni()
    organization = (
        organizations_available[0]
        if organizations_available
        else organizations.crea_organizzazione("Ludoteca")
    )
    return events.create_event(
        organization.id,
        name=slug,
        slug=slug,
        start_datetime="2026-09-13T09:00:00",
        end_datetime="2026-09-13T20:00:00",
        timezone="Europe/Rome",
        modules=("game_library",),
    )


def create_copy(event, game_name="Azul"):
    owner = catalog.aggiungi_proprietario("Biblioteca", event_id=event.id)
    game = catalog.aggiungi_gioco(game_name, event_id=event.id)
    catalog.imposta_quantita(game, owner, "1", event_id=event.id)
    with database.get_db() as connection:
        return connection.execute("""
            SELECT id FROM game_library_game_copies
            WHERE event_id = ? AND game_id = ?
        """, (event.id, game)).fetchone()[0]


def test_external_identifier_is_trimmed_case_sensitive_and_event_scoped(db):
    first = create_event("first-identifiers")
    second = create_event("second-identifiers")
    first_copy = create_copy(first)
    second_copy = create_copy(second)

    assigned = copy_identifiers.assign_external(first.id, first_copy, "  Bib-01  ")
    copy_identifiers.assign_external(second.id, second_copy, "Bib-01")

    assert assigned["value"] == "Bib-01"
    assert assigned["source"] == "external"
    assert copy_identifiers.resolve(first.id, " Bib-01 ")["copy_id"] == first_copy
    with pytest.raises(copy_identifiers.UnknownCopyIdentifier):
        copy_identifiers.resolve(first.id, "bib-01")


def test_duplicates_and_second_identifier_are_rejected_without_writes(db):
    event = create_event("duplicate-identifiers")
    first_copy = create_copy(event, "Azul")
    owner = catalog.elenco_proprietari(event_id=event.id)[0]
    second_game = catalog.aggiungi_gioco("Cascadia", event_id=event.id)
    catalog.imposta_quantita(
        second_game, owner["id"], "1", event_id=event.id
    )
    with database.get_db() as connection:
        second_copy = connection.execute("""
            SELECT id FROM game_library_game_copies
            WHERE event_id = ? AND game_id = ?
        """, (event.id, second_game)).fetchone()[0]
    copy_identifiers.assign_external(event.id, first_copy, "BIB-01")

    with pytest.raises(copy_identifiers.IdentifierAlreadyAssigned):
        copy_identifiers.assign_external(event.id, first_copy, "BIB-02")
    with pytest.raises(copy_identifiers.DuplicateCopyIdentifier):
        copy_identifiers.assign_external(event.id, second_copy, "BIB-01")
    assert copy_identifiers.identifier_for_copy(event.id, second_copy) is None


@pytest.mark.parametrize("value", ["", "  ", "A\nB", "A\rB"])
def test_invalid_identifiers_are_rejected_without_writes(db, value):
    event = create_event("invalid-identifiers")
    copy_id = create_copy(event)

    with pytest.raises(copy_identifiers.InvalidCopyIdentifier):
        copy_identifiers.assign_external(event.id, copy_id, value)
    assert copy_identifiers.identifier_for_copy(event.id, copy_id) is None


def test_ludox_generation_replace_remove_and_lendability(db):
    event = create_event("ludox-identifiers")
    copy_id = create_copy(event)

    assert not copy_identifiers.is_lendable(event.id, copy_id)
    generated = copy_identifiers.generate_ludox(event.id, copy_id)
    assert generated["value"] == f"LX-C-{copy_id:06d}"
    assert generated["source"] == "ludox"
    assert copy_identifiers.is_lendable(event.id, copy_id)

    replaced = copy_identifiers.replace(event.id, copy_id, " EXT-2 ")
    assert (replaced["value"], replaced["source"]) == ("EXT-2", "external")
    assert copy_identifiers.remove(event.id, copy_id) == 1
    assert not copy_identifiers.is_lendable(event.id, copy_id)


def test_identifier_service_does_not_require_tkinter():
    import ast
    from pathlib import Path

    source = Path(copy_identifiers.__file__).read_text(encoding="utf-8")
    imports = {
        alias.name
        for node in ast.walk(ast.parse(source))
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert "tkinter" not in imports
