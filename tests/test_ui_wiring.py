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
        },
    )


def test_pulsanti_backoffice_aprono_le_sezioni_previste():
    assert_command(
        "show_backoffice",
        {
            "self.show_gestione_giochi",
            "self.show_gestione_proprietari",
            "self.show_gestione_organizzazioni",
            "self.show_tutti_prestiti",
            "self.show_tutti_documenti",
            "self.show_giochi_per_proprietario",
            "self.show_impostazioni",
            "self.show_report_utilizzo_ludoteca",
            "self.show_report_documenti",
        },
    )


def test_pulsanti_indietro_tornano_alla_schermata_prevista():
    assert command_pulsanti("pulsante_indietro") == ["command"]
    destinazioni = {
        "show_nuovo_prestito": "self.show_home",
        "show_cambio_token": "self.show_home",
        "show_cambio_gioco": "self.show_cambio_token",
        "show_restituzione": "self.show_home",
        "show_statistiche": "self.show_home",
        "show_login_backoffice": "self.show_home",
        "show_backoffice": "self.show_home",
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
    assert "PrestitiApp" in assegnazioni
    assert assegnazioni.index("organizations.sincronizza_contesto") < assegnazioni.index(
        "PrestitiApp"
    )
    assert chiamate_main[-1] == "app.mainloop"
