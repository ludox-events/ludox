"""Characterize the extracted catalog operations on temporary SQLite data."""

import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from ludox import catalog as service, database as data, lending


def snapshot(db):
    return tuple(
        [tuple(row) for row in db.execute(f"SELECT * FROM {table} ORDER BY id")]
        for table in ("giochi", "proprietari", "copie_gioco", "documenti", "prestiti")
    )


def test_create_names_are_trimmed_and_records_start_active(db):
    owner = service.aggiungi_proprietario("  Biblioteca  ")
    game = service.aggiungi_gioco("  Azul  ")
    assert service.proprietario_per_id(owner) == {"id": owner, "nome": "Biblioteca", "attivo": 1}
    assert service.gioco_per_id(game) == {"id": game, "nome": "Azul", "attivo": 1}
    assert service.totale_copie_proprietario(owner) == 0
    assert service.elenco_giochi_backoffice()[0]["copie_totali"] == 0


@pytest.mark.parametrize("operation", ["add-owner", "add-game", "edit-owner", "edit-game"])
@pytest.mark.parametrize("name", ["", " \t\n"])
def test_empty_name_rejected_without_writes(catalog, operation, name):
    before = snapshot(catalog)
    with pytest.raises(service.NomeMancante):
        if operation == "add-owner":
            service.aggiungi_proprietario(name)
        elif operation == "add-game":
            service.aggiungi_gioco(name)
        elif operation == "edit-owner":
            service.modifica_proprietario(2, name, False)
        else:
            service.modifica_gioco(1, name, False)
    assert snapshot(catalog) == before


@pytest.mark.parametrize("operation", ["add-owner", "add-game", "edit-owner", "edit-game"])
def test_duplicate_name_rejected_without_writes(catalog, operation):
    before = snapshot(catalog)
    with pytest.raises(service.NomeDuplicato):
        if operation == "add-owner":
            service.aggiungi_proprietario(" biblioteca ")
        elif operation == "add-game":
            service.aggiungi_gioco(" AZUL ")
        elif operation == "edit-owner":
            service.modifica_proprietario(1, " biblioteca ", True)
        else:
            service.modifica_gioco(2, " AZUL ", True)
    assert snapshot(catalog) == before


def test_similar_names_are_not_merged(db):
    first = service.aggiungi_gioco("Kingdomino")
    second = service.aggiungi_gioco("King Domino")
    assert first != second
    assert len(service.elenco_giochi_backoffice()) == 2


def test_owner_confirmation_precedes_writes_and_duplicate_check(catalog):
    before = snapshot(catalog)
    with pytest.raises(service.ConfermaDisattivazione):
        service.modifica_proprietario(2, "Organizzazione", False)
    # Declining is represented by not retrying; the first call never writes.
    assert snapshot(catalog) == before
    with pytest.raises(service.NomeDuplicato):
        service.modifica_proprietario(2, "Organizzazione", False, conferma_disattivazione=True)
    assert snapshot(catalog) == before
    service.modifica_proprietario(2, " Biblioteca nuova ", False, conferma_disattivazione=True)
    assert service.proprietario_per_id(2)["attivo"] == 0
    assert service.proprietario_per_id(2)["nome"] == "Biblioteca nuova"
    assert service.totale_copie_proprietario(2) == 5
    assert data.disponibilita_gioco(1) == (3, 3)


def test_owner_without_copies_can_be_deactivated_and_reactivated(catalog):
    service.modifica_proprietario(1, " Organizzazione ", False)
    assert service.proprietario_per_id(1)["attivo"] == 0
    service.modifica_proprietario(1, "Organizzazione", True)
    assert service.proprietario_per_id(1)["attivo"] == 1


def test_already_inactive_owner_with_copies_still_requires_confirmation(catalog):
    with pytest.raises(service.ConfermaDisattivazione):
        service.modifica_proprietario(3, "Privato", False)


def test_open_loans_block_game_deactivation_before_duplicate_check(catalog):
    lending.nuovo_prestito(1, 2)
    before = snapshot(catalog)
    with pytest.raises(service.GiocoInPrestito):
        service.modifica_gioco(1, "Cascadia", False)
    assert snapshot(catalog) == before
    # Renaming an active game remains allowed even with an open loan.
    service.modifica_gioco(1, " Azul nuovo ", True)
    assert service.gioco_per_id(1)["nome"] == "Azul nuovo"
    assert lending.consulta_token(1).prestito["gioco_nome"] == "Azul nuovo"


def test_game_deactivation_preserves_closed_history_and_copies(catalog):
    loan = lending.nuovo_prestito(1, 1)
    lending.restituzione_finale(documento_id=loan.documento_id, prestito_id=loan.prestito_id)
    service.modifica_gioco(1, "Azul", False)
    assert service.gioco_per_id(1)["attivo"] == 0
    assert data.conta_prestiti() == 1
    assert data.copie_totali_gioco(1) == 3
    assert data.cerca_giochi("Azul") == []
    service.modifica_gioco(1, "Azul", True)
    assert service.gioco_per_id(1)["attivo"] == 1


def test_missing_records_keep_update_noop_behavior(catalog):
    before = snapshot(catalog)
    service.modifica_gioco(999, "Missing", False)
    service.modifica_proprietario(999, "Missing", False)
    assert service.gioco_per_id(999) is None
    assert service.proprietario_per_id(999) is None
    assert snapshot(catalog) == before


@pytest.mark.parametrize("quantity", ["", "abc", "1.5", "-1"])
def test_invalid_quantities_leave_copies_unchanged(catalog, quantity):
    before = snapshot(catalog)
    with pytest.raises(service.QuantitaNonValida):
        service.imposta_quantita(1, 2, quantity)
    assert snapshot(catalog) == before


def test_owner_selection_is_checked_before_quantity(catalog):
    before = snapshot(catalog)
    with pytest.raises(service.ProprietarioNonSelezionato):
        service.imposta_quantita(1, None, "invalid")
    assert snapshot(catalog) == before


def test_quantity_insert_update_and_zero_deletion(catalog):
    service.imposta_quantita(4, 2, " +2 ")
    row_id = catalog.execute("SELECT id FROM copie_gioco WHERE gioco_id=4").fetchone()[0]
    service.imposta_quantita(4, 2, "5")
    row = catalog.execute("SELECT id, quantita FROM copie_gioco WHERE gioco_id=4").fetchone()
    assert tuple(row) == (row_id, 5)
    service.imposta_quantita(4, 2, "0")
    assert catalog.execute("SELECT * FROM copie_gioco WHERE gioco_id=4").fetchall() == []
    service.imposta_quantita(4, 2, "0")  # Deleting an absent association is a no-op.
    assert data.copie_totali_gioco(4) == 0


def test_quantity_limit_uses_total_stock_across_owners(catalog):
    lending.nuovo_prestito(1, 3)
    lending.nuovo_prestito(1, 3)
    before = snapshot(catalog)
    with pytest.raises(service.CopieInsufficienti) as error:
        service.imposta_quantita(1, 2, "0")
    assert (error.value.fuori, error.value.nuovo_totale) == (2, 1)
    assert str(error.value) == (
        "Ci sono attualmente 2 copie di questo gioco in prestito.\n\n"
        "Il totale non può essere ridotto a 1."
    )
    assert snapshot(catalog) == before
    service.imposta_quantita(1, 2, "1")
    assert data.disponibilita_gioco(1) == (0, 2)
    # Copies can be reassigned between owners when the total stays sufficient.
    service.imposta_quantita(1, 3, "3")
    service.imposta_quantita(1, 2, "0")
    assert data.disponibilita_gioco(1) == (1, 3)


def test_inactive_game_and_owner_do_not_block_quantity_updates(catalog):
    service.imposta_quantita(3, 3, "2")
    assert data.copie_totali_gioco(3) == 4
    assert service.totale_copie_proprietario(3) == 3


def test_quantity_database_failure_does_not_change_stock(catalog):
    before = snapshot(catalog)
    catalog.execute("""CREATE TRIGGER reject_quantity BEFORE UPDATE ON copie_gioco
        BEGIN SELECT RAISE(ABORT, 'quantity rejected'); END""")
    catalog.commit()
    with pytest.raises(sqlite3.IntegrityError, match="quantity rejected"):
        service.imposta_quantita(1, 2, "4")
    assert snapshot(catalog) == before


def test_owner_inventory_includes_inactive_games_and_title_level_loans(catalog):
    loan = lending.nuovo_prestito(1, 2)
    inventory = service.inventario_proprietario(2)
    assert (inventory.totale_titoli, inventory.totale_copie) == (3, 5)
    assert inventory.righe == [
        {"gioco_id": 1, "gioco": "Azul", "gioco_attivo": 1, "copie_proprietario": 2,
         "copie_totali": 3, "prestiti_attivi_titolo": 1},
        {"gioco_id": 2, "gioco": "Cascadia", "gioco_attivo": 1, "copie_proprietario": 1,
         "copie_totali": 1, "prestiti_attivi_titolo": 0},
        {"gioco_id": 3, "gioco": "Disattivo", "gioco_attivo": 0, "copie_proprietario": 2,
         "copie_totali": 2, "prestiti_attivi_titolo": 0},
    ]
    # A loan is counted for the title, not assigned to one of its owners.
    assert service.inventario_proprietario(3).righe[0]["prestiti_attivi_titolo"] == 1
    lending.restituzione_finale(documento_id=loan.documento_id, prestito_id=loan.prestito_id)
    assert service.inventario_proprietario(2).righe[0]["prestiti_attivi_titolo"] == 0
    empty = service.inventario_proprietario(999)
    assert (empty.righe, empty.totale_titoli, empty.totale_copie) == ([], 0, 0)


def test_catalog_read_api_returns_plain_data(catalog):
    assert [r["nome"] for r in service.elenco_proprietari()] == ["Biblioteca", "Organizzazione", "Privato"]
    assert all(type(r) is dict for r in service.elenco_proprietari())
    assert [(r["nome"], r["copie_totali"]) for r in service.elenco_giochi_backoffice()] == [
        ("Azul", 3), ("Cascadia", 1), ("Disattivo", 2), ("Vuoto", 0)
    ]
    assert [(r["proprietario_nome"], r["quantita"]) for r in service.copie_per_proprietario_del_gioco(1)] == [
        ("Biblioteca", 2), ("Organizzazione", 0), ("Privato", 1)
    ]
    assert service.riepilogo_proprietari_gioco(1) == "Biblioteca: 2, Privato: 1"
    assert service.copie_in_prestito(1) == 0


def test_catalog_import_does_not_require_gui():
    root = Path(__file__).resolve().parents[1]
    code = """
import sys
class NoGUI:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('tkinter', 'ttkbootstrap', 'matplotlib'):
            raise AssertionError('GUI dependency: ' + fullname)
sys.meta_path.insert(0, NoGUI())
from ludox import catalog
assert 'ludox.ui' not in sys.modules
"""
    subprocess.run([sys.executable, "-B", "-c", code], cwd=root, check=True,
                   capture_output=True, text=True)
