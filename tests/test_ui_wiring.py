# Copyright (C) 2026 Matteo Sassi
# SPDX-License-Identifier: AGPL-3.0-only

"""Structural checks for Tkinter button and navigation wiring."""

import ast
from pathlib import Path


UI_PATH = Path(__file__).resolve().parents[1] / "ludox" / "ui.py"
UI_TREE = ast.parse(UI_PATH.read_text(encoding="utf-8"))
APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
APP_TREE = ast.parse(APP_PATH.read_text(encoding="utf-8"))
APP_CLASS = next(
    node
    for node in UI_TREE.body
    if isinstance(node, ast.ClassDef) and node.name == "PrestitiApp"
)


def metodo(nome):
    return next(
        node
        for node in APP_CLASS.body
        if isinstance(node, ast.FunctionDef) and node.name == nome
    )


def chiamate(nome_metodo, funzione):
    return [
        node
        for node in ast.walk(metodo(nome_metodo))
        if isinstance(node, ast.Call) and ast.unparse(node.func) == funzione
    ]


def command_pulsanti(nome_metodo):
    command = []
    for chiamata in chiamate(nome_metodo, "ttk.Button"):
        command.extend(
            ast.unparse(keyword.value)
            for keyword in chiamata.keywords
            if keyword.arg == "command"
        )
    return command


def assert_command(nome_metodo, attesi):
    effettivi = command_pulsanti(nome_metodo)
    assert len(effettivi) == len(attesi)
    assert set(effettivi) == set(attesi)


def test_pulsanti_home_aprono_le_schermate_principali():
    assert_command(
        "show_home",
        {
            "self.show_nuovo_prestito",
            "self.show_cambio_token",
            "self.show_restituzione",
            "self.show_statistiche",
            "self.show_login_backoffice",
            "self.show_selezione_evento",
        },
    )


def test_pulsanti_backoffice_aprono_le_sezioni_previste():
    assert_command(
        "show_backoffice",
        {
            "self.show_gestione_giochi",
            "self.show_gestione_proprietari",
            "self.show_gestione_organizzazioni",
            "self.show_gestione_eventi",
            "self.show_impostazioni_ludoteca",
            "self.show_gestione_copie",
            "self.esporta_ludoteca_legacy",
            "self.importa_ludoteca_evento",
            "self.esporta_ludoteca_evento",
            "self.show_tutti_prestiti",
            "self.show_tutti_documenti",
            "self.show_giochi_per_proprietario",
            "self.show_impostazioni",
            "self.show_report_utilizzo_ludoteca",
            "self.show_report_documenti",
        },
    )


def test_backoffice_usa_il_contenitore_scrollabile_e_mantiene_gli_export():
    clear_calls = chiamate("show_backoffice", "self.clear")
    assert len(clear_calls) == 1
    assert {
        keyword.arg: ast.unparse(keyword.value)
        for keyword in clear_calls[0].keywords
    } == {"scrollable": "True"}
    assert {
        "self.esporta_ludoteca_legacy",
        "self.esporta_ludoteca_evento",
    } <= set(command_pulsanti("show_backoffice"))

    scroller = next(
        node for node in UI_TREE.body
        if isinstance(node, ast.ClassDef) and node.name == "VerticalScrolledFrame"
    )
    calls = {ast.unparse(node.func) for node in ast.walk(scroller) if isinstance(node, ast.Call)}
    assert {"tk.Canvas", "ttk.Scrollbar", "self.canvas.yview_scroll"} <= calls


def test_pulsanti_indietro_tornano_alla_schermata_prevista():
    assert command_pulsanti("pulsante_indietro") == ["command"]
    destinazioni = {
        "show_nuovo_prestito": "self.show_home",
        "show_nuovo_prestito_copia": "self.show_home",
        "show_cambio_token": "self.show_home",
        "show_cambio_gioco": "self.show_cambio_token",
        "show_restituzione": "self.show_home",
        "show_statistiche": "self.show_home",
        "show_login_backoffice": "self.show_home",
        "show_backoffice": "self.show_home",
        "show_selezione_evento": "self.show_home",
        "show_tutti_prestiti": "self.show_backoffice",
        "show_tutti_documenti": "self.show_backoffice",
        "show_report_documenti": "self.show_backoffice",
        "show_report_utilizzo_ludoteca": "self.show_backoffice",
        "show_giochi_per_proprietario": "self.show_backoffice",
        "show_gestione_proprietari": "self.show_backoffice",
        "show_aggiungi_proprietario": "self.show_gestione_proprietari",
        "show_modifica_proprietario": "self.show_gestione_proprietari",
        "show_gestione_giochi": "self.show_backoffice",
        "show_aggiungi_gioco": "self.show_gestione_giochi",
        "show_modifica_gioco": "self.show_gestione_giochi",
        "show_impostazioni": "self.show_backoffice",
        "show_gestione_organizzazioni": "self.show_backoffice",
        "show_gestione_eventi": "self.show_backoffice",
        "show_impostazioni_ludoteca": "self.show_backoffice",
        "show_gestione_copie": "self.show_backoffice",
    }

    for nome_metodo, destinazione in destinazioni.items():
        collegamenti = chiamate(nome_metodo, "self.pulsante_indietro")
        assert len(collegamenti) == 1
        assert ast.unparse(collegamenti[0].args[1]) == destinazione


def test_conferma_selettore_inoltra_il_gioco_al_callback():
    assert command_pulsanti("crea_selettore_giochi") == ["conferma"]
    selettore = metodo("crea_selettore_giochi")
    conferma = next(
        node
        for node in selettore.body
        if isinstance(node, ast.FunctionDef) and node.name == "conferma"
    )
    callback = [
        node
        for node in ast.walk(conferma)
        if isinstance(node, ast.Call) and ast.unparse(node.func) == "callback"
    ]
    assert len(callback) == 1
    assert [ast.unparse(argomento) for argomento in callback[0].args] == ["gioco_id"]

    doppio_clic = [
        node
        for node in chiamate("crea_selettore_giochi", "tree.bind")
        if ast.unparse(node.args[0]) == "'<Double-1>'"
    ]
    assert len(doppio_clic) == 1
    assert ast.unparse(doppio_clic[0].args[1]) == "lambda event: conferma()"


def test_azioni_locali_importanti_hanno_il_command_previsto():
    assert_command("show_login_backoffice", {"accedi"})
    invio = chiamate("show_login_backoffice", "entry.bind")
    assert any(
        ast.unparse(node.args[0]) == "'<Return>'"
        and ast.unparse(node.args[1]) == "lambda event: accedi()"
        for node in invio
    )

    assert_command(
        "show_impostazioni",
        {"scegli_nuovo_database", "scegli_database_esistente", "salva"},
    )
    for nome_report in (
        "show_report_documenti",
        "show_report_utilizzo_ludoteca",
    ):
        assert_command(
            nome_report,
            {"applica", "esporta_csv", "self.show_backoffice"},
        )

    assert_command(
        "show_gestione_organizzazioni",
        {"nuova", "salva", "usa_selezionata"},
    )
    gestione_eventi = metodo("show_gestione_eventi")
    azioni_eventi = next(
        node
        for node in ast.walk(gestione_eventi)
        if isinstance(node, ast.For)
        and ast.unparse(node.target) == "(text, command, style)"
    )
    assert {
        ast.unparse(element.elts[1])
        for element in azioni_eventi.iter.elts
    } == {"nuovo", "salva", "elimina"}
    assert_command("show_selezione_evento", {"conferma"})


def test_gestione_copie_collega_scanner_azioni_e_qr_png():
    assert_command("show_gestione_copie", {"command", "esporta_qr"})
    gestione = metodo("show_gestione_copie")
    actions = next(
        node
        for node in ast.walk(gestione)
        if isinstance(node, ast.For)
        and ast.unparse(node.target) == "(column, (label, command, style))"
    )
    assert {
        ast.unparse(element.elts[1]) for element in actions.iter.args[0].elts
    } == {"assegna_esterno", "genera_ludox", "rimuovi", "cambia_stato"}
    invio = chiamate("show_gestione_copie", "entry.bind")
    assert any(
        ast.unparse(node.args[0]) == "'<Return>'"
        and ast.unparse(node.args[1]) == "lambda event: assegna_esterno()"
        for node in invio
    )
    assert len(chiamate("show_gestione_copie", "copy_identifiers.export_ludox_qr_png")) == 1
    clear_calls = chiamate("show_gestione_copie", "self.clear")
    assert {
        keyword.arg: ast.unparse(keyword.value)
        for keyword in clear_calls[0].keywords
    } == {"scrollable": "True"}


def test_nuovo_prestito_per_copia_usa_input_hid_e_service_dedicato():
    nuovo = metodo("show_nuovo_prestito")
    assert len([
        node for node in ast.walk(nuovo)
        if isinstance(node, ast.Call)
        and ast.unparse(node.func) == "self.show_nuovo_prestito_copia"
    ]) == 1
    assert_command("show_nuovo_prestito_copia", {"registra"})
    invio = chiamate("show_nuovo_prestito_copia", "entry.bind")
    assert any(
        ast.unparse(node.args[0]) == "'<Return>'"
        and ast.unparse(node.args[1]) == "lambda event: registra()"
        for node in invio
    )
    assert len(chiamate(
        "show_nuovo_prestito_copia",
        "lending.nuovo_prestito_da_identificatore",
    )) == 1


def test_gestione_eventi_usa_picker_e_timezone_selezionabile_per_create_update():
    assert len(chiamate("crea_datetime_picker", "DateEntry")) == 1
    picker_values = {
        ast.unparse(keyword.value)
        for call in chiamate("crea_datetime_picker", "ttk.Combobox")
        for keyword in call.keywords
        if keyword.arg == "values"
    }
    assert picker_values == {"HOUR_VALUES", "MINUTE_VALUES"}

    picker_calls = chiamate("show_gestione_eventi", "self.crea_datetime_picker")
    assert len(picker_calls) == 2
    assert [ast.unparse(call.args[1]) for call in picker_calls] == [
        "'events.start'", "'events.end'"
    ]
    timezone = chiamate("show_gestione_eventi", "SearchableTimezoneCombobox")
    assert len(timezone) == 1
    assert {
        keyword.arg: ast.unparse(keyword.value)
        for keyword in timezone[0].keywords
    }["values"] == "TIMEZONE_VALUES"
    assert len(chiamate("show_gestione_eventi", "detect_local_timezone")) == 1

    gestione = metodo("show_gestione_eventi")
    carica = next(
        node for node in ast.walk(gestione)
        if isinstance(node, ast.FunctionDef) and node.name == "carica"
    )
    assert len([
        node for node in ast.walk(carica)
        if isinstance(node, ast.Call)
        and ast.unparse(node.func) == "self.imposta_datetime_picker"
    ]) == 2
    salva = next(
        node for node in ast.walk(gestione)
        if isinstance(node, ast.FunctionDef) and node.name == "salva"
    )
    service_calls = {
        ast.unparse(node.func): {
            keyword.arg: ast.unparse(keyword.value) for keyword in node.keywords
        }
        for node in ast.walk(salva)
        if isinstance(node, ast.Call)
        and ast.unparse(node.func) in {"events.create_event", "events.update_event"}
    }
    for keywords in service_calls.values():
        assert keywords["start_datetime"] == "start_datetime"
        assert keywords["end_datetime"] == "end_datetime"
        assert keywords["timezone"] == "timezone"


def test_avvio_risolve_il_contesto_prima_di_creare_la_ui():
    main = next(
        node
        for node in APP_TREE.body
        if isinstance(node, ast.FunctionDef) and node.name == "main"
    )
    chiamate_main = [
        ast.unparse(node.value.func)
        for node in main.body
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
    ]
    assegnazioni = [
        ast.unparse(node.value.func)
        for node in main.body
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)
    ]

    assert "organizations.sincronizza_contesto" in assegnazioni
    assert "events.sync_context" in assegnazioni
    assert "PrestitiApp" in assegnazioni
    assert assegnazioni.index("organizations.sincronizza_contesto") < assegnazioni.index(
        "PrestitiApp"
    )
    assert assegnazioni.index("events.sync_context") < assegnazioni.index(
        "PrestitiApp"
    )
    assert chiamate_main[-1] == "app.mainloop"


def test_impostazioni_collegano_conferma_migration_e_chiusura():
    conferme = chiamate(
        "show_impostazioni",
        "migration_ui.chiedi_autorizzazione",
    )
    chiusure = chiamate("show_impostazioni", "self.destroy")

    assert len(conferme) == 1
    assert len(chiusure) == 2


def test_salvataggio_impostazioni_applica_subito_la_lingua_prima_del_rendering():
    settings = metodo("show_impostazioni")
    salva = next(
        node for node in ast.walk(settings)
        if isinstance(node, ast.FunctionDef) and node.name == "salva"
    )
    expressions = [
        ast.unparse(node.value.func)
        for node in salva.body
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
    ]
    assert expressions.index("set_language") < expressions.index("self.show_backoffice")
