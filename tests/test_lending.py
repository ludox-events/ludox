"""Exercise the actual lending service with isolated SQLite databases."""

import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from ludox import database as data, lending


@pytest.fixture
def clock(monkeypatch):
    value = ["2026-09-11T10:00:00"]
    monkeypatch.setattr(data, "now_iso", lambda: value[0])
    return value


def change(loan, game=2, **overrides):
    args = dict(token=loan.token, documento_id=loan.documento_id,
                prestito_id=loan.prestito_id, gioco_id_atteso=1, nuovo_gioco_id=game)
    args.update(overrides)
    return lending.cambia_gioco(**args)


def snapshot(db):
    return tuple(
        [tuple(row) for row in db.execute(f"SELECT * FROM {table} ORDER BY id")]
        for table in ("documenti", "prestiti")
    )


def test_open_change_return_and_reuse_preserve_history(catalog, clock):
    first = lending.nuovo_prestito(1, 2)
    assert (first.token, first.gioco_nome) == (1, "Azul")
    situation = lending.consulta_token(1)
    assert type(situation.documento) is dict
    assert type(situation.prestito) is dict
    assert situation.documento["id"] == first.documento_id
    assert situation.prestito["id"] == first.prestito_id
    assert situation.documento["ingresso"] == situation.prestito["uscita"] == clock[0]
    assert data.disponibilita_gioco(1) == (2, 3)

    clock[0] = "2026-09-11T11:00:00"
    assert change(first) == "Cascadia"
    after_change = lending.consulta_token(1)
    assert after_change.documento == situation.documento
    assert after_change.prestito["id"] != first.prestito_id
    assert after_change.prestito["uscita"] == clock[0]
    old = catalog.execute("SELECT * FROM prestiti WHERE id=?", (first.prestito_id,)).fetchone()
    assert old["rientro"] == clock[0]
    assert data.conta_documenti() == data.conta_documenti_attivi() == 1
    assert data.conta_prestiti() == 2
    assert data.disponibilita_gioco(1) == (3, 3)
    assert data.disponibilita_gioco(2) == (0, 1)

    # Consultation itself never closes the loan or frees the token.
    before = snapshot(catalog)
    lending.consulta_token(1)
    assert snapshot(catalog) == before
    assert data.token_libero(1) is None

    clock[0] = "2026-09-11T12:00:00"
    lending.restituzione_finale(
        documento_id=first.documento_id, prestito_id=after_change.prestito["id"]
    )
    closed = catalog.execute("SELECT uscita FROM documenti WHERE id=?", (first.documento_id,)).fetchone()
    returned = catalog.execute("SELECT rientro FROM prestiti WHERE id=?", (after_change.prestito["id"],)).fetchone()
    assert closed[0] == returned[0] == clock[0]
    assert data.conta_documenti_attivi() == 0
    assert data.disponibilita_gioco(2) == (1, 1)
    with pytest.raises(lending.TokenLibero):
        lending.consulta_token(1)
    reused = lending.nuovo_prestito(2, 2)
    assert reused.token == first.token
    assert reused.documento_id != first.documento_id
    assert data.conta_documenti() == 2
    assert data.conta_prestiti() == 3


def test_consultation_distinguishes_free_token_and_missing_loan(catalog):
    with pytest.raises(lending.TokenLibero):
        lending.consulta_token(1)
    with catalog:
        catalog.execute("INSERT INTO documenti(token, ingresso) VALUES (1, '2026-09-11T10:00:00')")
    before = snapshot(catalog)
    with pytest.raises(lending.PrestitoAssente):
        lending.consulta_token(1)
    assert snapshot(catalog) == before


def test_home_search_and_availability_use_lending_service(catalog, clock):
    assert lending.riepilogo_home() == lending.RiepilogoHome(0, 0, 0)
    assert [
        (row["nome"], row["disponibili"], row["copie_totali"])
        for row in lending.cerca_giochi_con_disponibilita()
    ] == [("Azul", 3, 3), ("Cascadia", 1, 1)]

    lending.nuovo_prestito(1, 10)

    assert lending.riepilogo_home() == lending.RiepilogoHome(1, 1, 1)
    assert lending.disponibilita_gioco(1) == (2, 3)
    assert [
        row["nome"] for row in lending.cerca_giochi_con_disponibilita("cas")
    ] == ["Cascadia"]
    assert [
        row["nome"]
        for row in lending.cerca_giochi_con_disponibilita(
            gioco_da_escludere=1
        )
    ] == ["Cascadia"]


def test_situazione_chiusura_restituisce_token_ordinati(catalog):
    catalog.executemany(
        "INSERT INTO documenti(token, ingresso, uscita) VALUES (?, ?, ?)",
        [
            (7, "2026-09-12T10:00:00", None),
            (2, "2026-09-12T10:05:00", None),
            (5, "2026-09-12T09:00:00", "2026-09-12T09:30:00"),
        ],
    )
    catalog.commit()

    assert lending.situazione_chiusura() == lending.SituazioneChiusura(
        documenti_attivi=2,
        token=(2, 7),
    )


@pytest.mark.parametrize("game", [4, 999], ids=["no-copies", "missing-game"])
def test_open_unavailable_game_does_not_write(catalog, game):
    with pytest.raises(lending.GiocoNonDisponibile, match="Non ci sono copie disponibili"):
        lending.nuovo_prestito(game, 2)
    assert snapshot(catalog) == ([], [])


def test_open_checks_stock_before_token_limit(catalog):
    lending.nuovo_prestito(2, 1)
    before = snapshot(catalog)
    with pytest.raises(lending.GiocoNonDisponibile):
        lending.nuovo_prestito(2, 1)
    with pytest.raises(lending.TokenEsauriti, match="Non ci sono posizioni documento libere"):
        lending.nuovo_prestito(1, 1)
    assert snapshot(catalog) == before


def test_open_preserves_inactive_game_behavior(catalog):
    # The UI selector filters inactive titles; the original write callback did not.
    loan = lending.nuovo_prestito(3, 1)
    assert lending.consulta_token(loan.token).prestito["gioco_id"] == 3


def test_open_rolls_back_document_when_loan_insert_fails(catalog):
    # A trigger on this temporary DB also applies to service connections.
    catalog.execute("""CREATE TRIGGER reject_loan BEFORE INSERT ON prestiti
        BEGIN SELECT RAISE(ABORT, 'loan insert rejected'); END""")
    catalog.commit()
    with pytest.raises(lending.ErrorePersistenza, match="loan insert rejected"):
        lending.nuovo_prestito(1, 2)
    assert snapshot(catalog) == ([], [])


def test_open_occupied_token_race_keeps_existing_document(catalog, monkeypatch):
    lending.nuovo_prestito(1, 2)
    before = snapshot(catalog)
    # Simulate the pre-transaction token lookup becoming stale.
    monkeypatch.setattr(data, "token_libero", lambda limit: 1)
    with pytest.raises(lending.ErrorePersistenza, match="UNIQUE"):
        lending.nuovo_prestito(1, 2)
    assert snapshot(catalog) == before


@pytest.mark.parametrize("overrides, message", [
    ({"token": 99}, "Il documento non risulta più aperto"),
    ({"documento_id": 999}, "Il documento non risulta più aperto"),
    ({"prestito_id": 999}, "Il prestito è cambiato o è già stato chiuso"),
    ({"gioco_id_atteso": 2}, "Il gioco associato al token è cambiato"),
    ({"nuovo_gioco_id": 999}, "nel catalogo attivo"),
    ({"nuovo_gioco_id": 3}, "nel catalogo attivo"),
], ids=["wrong-token", "missing-document", "missing-loan", "unexpected-game", "missing-game", "inactive-game"])
def test_change_rejects_invalid_selection_without_writes(catalog, overrides, message):
    loan = lending.nuovo_prestito(1, 3)
    before = snapshot(catalog)
    with pytest.raises(lending.CambioNonValido, match=message):
        change(loan, **overrides)
    assert snapshot(catalog) == before


@pytest.mark.parametrize("closed", ["document", "loan"])
def test_change_rejects_closed_records(catalog, closed):
    loan = lending.nuovo_prestito(1, 3)
    with catalog:
        if closed == "document":
            catalog.execute("UPDATE documenti SET uscita='2026-09-11T11:00:00'")
        else:
            catalog.execute("UPDATE prestiti SET rientro='2026-09-11T11:00:00'")
    before = snapshot(catalog)
    with pytest.raises(lending.CambioNonValido):
        change(loan)
    assert snapshot(catalog) == before


def test_change_rejects_a_loan_from_another_document(catalog):
    loan = lending.nuovo_prestito(1, 3)
    other = lending.nuovo_prestito(1, 3)
    before = snapshot(catalog)
    with pytest.raises(lending.CambioNonValido, match="Il prestito è cambiato"):
        change(loan, prestito_id=other.prestito_id)
    assert snapshot(catalog) == before


@pytest.mark.parametrize("game", [2, 4], ids=["exhausted", "no-copies"])
def test_change_rechecks_stock(catalog, game):
    loan = lending.nuovo_prestito(1, 3)
    lending.nuovo_prestito(2, 3)
    before = snapshot(catalog)
    with pytest.raises(lending.GiocoNonDisponibile, match="ultima copia disponibile"):
        change(loan, game)
    assert snapshot(catalog) == before


def test_change_rolls_back_old_loan_when_new_insert_fails(catalog):
    loan = lending.nuovo_prestito(1, 3)
    before = snapshot(catalog)
    catalog.execute("""CREATE TRIGGER reject_change BEFORE INSERT ON prestiti
        BEGIN SELECT RAISE(ABORT, 'change insert rejected'); END""")
    catalog.commit()
    with pytest.raises(lending.ErrorePersistenza, match="change insert rejected"):
        change(loan)
    assert snapshot(catalog) == before


def test_change_does_not_insert_if_old_loan_update_is_ignored(catalog):
    loan = lending.nuovo_prestito(1, 3)
    before = snapshot(catalog)
    catalog.execute("""CREATE TRIGGER ignore_close BEFORE UPDATE ON prestiti
        BEGIN SELECT RAISE(IGNORE); END""")
    catalog.commit()
    with pytest.raises(lending.CambioNonValido, match="Non è stato possibile chiudere"):
        change(loan)
    assert snapshot(catalog) == before


def test_change_locks_before_checks_and_releases_after_commit(catalog, monkeypatch):
    loan = lending.nuovo_prestito(1, 3)
    read_document = data.documento_per_cambio

    def check_lock(db, document_id, token):
        with sqlite3.connect(data.get_db_path(), timeout=0) as competitor:
            with pytest.raises(sqlite3.OperationalError, match="locked"):
                competitor.execute("BEGIN IMMEDIATE")
        return read_document(db, document_id, token)

    monkeypatch.setattr(data, "documento_per_cambio", check_lock)
    change(loan)
    with sqlite3.connect(data.get_db_path(), timeout=0) as competitor:
        competitor.execute("BEGIN IMMEDIATE")


@pytest.mark.parametrize("invalid", ["missing-loan", "missing-document", "closed-loan", "closed-document"])
def test_return_rolls_back_both_updates_on_invalid_state(catalog, invalid):
    loan = lending.nuovo_prestito(1, 3)
    args = dict(documento_id=loan.documento_id, prestito_id=loan.prestito_id)
    with catalog:
        if invalid == "missing-loan":
            args["prestito_id"] = 999
        elif invalid == "missing-document":
            args["documento_id"] = 999
        elif invalid == "closed-loan":
            catalog.execute("UPDATE prestiti SET rientro='2026-09-11T11:00:00'")
        else:
            catalog.execute("UPDATE documenti SET uscita='2026-09-11T11:00:00'")
    before = snapshot(catalog)
    message = "Il prestito non risulta più aperto" if "loan" in invalid else "Il documento non risulta più depositato"
    with pytest.raises(lending.ErrorePersistenza, match=message):
        lending.restituzione_finale(**args)
    assert snapshot(catalog) == before


def test_return_rolls_back_loan_when_document_write_fails(catalog):
    loan = lending.nuovo_prestito(1, 3)
    before = snapshot(catalog)
    catalog.execute("""CREATE TRIGGER reject_return BEFORE UPDATE ON documenti
        BEGIN SELECT RAISE(ABORT, 'document update rejected'); END""")
    catalog.commit()
    with pytest.raises(lending.ErrorePersistenza, match="document update rejected"):
        lending.restituzione_finale(documento_id=loan.documento_id, prestito_id=loan.prestito_id)
    assert snapshot(catalog) == before


def test_return_preserves_independent_id_updates(catalog):
    # Characterization of the original callback, not a recommended API usage:
    # it did not cross-check that the supplied loan belonged to the document.
    first = lending.nuovo_prestito(1, 3)
    second = lending.nuovo_prestito(1, 3)
    lending.restituzione_finale(documento_id=first.documento_id, prestito_id=second.prestito_id)
    assert data.documento_aperto_da_token(first.token) is None
    assert data.prestito_aperto_documento(first.documento_id) is not None
    assert data.documento_aperto_da_token(second.token) is not None
    assert data.prestito_aperto_documento(second.documento_id) is None


def test_service_import_does_not_require_tkinter():
    root = Path(__file__).resolve().parents[1]
    code = """
import sys
class NoGUI:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('tkinter', 'ttkbootstrap', 'matplotlib'):
            raise AssertionError('GUI dependency: ' + fullname)
sys.meta_path.insert(0, NoGUI())
from ludox import lending
assert 'ludox.ui' not in sys.modules
"""
    subprocess.run([sys.executable, "-B", "-c", code], cwd=root, check=True,
                   capture_output=True, text=True)
