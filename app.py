# Copyright (C) 2026 Matteo Sassi
# SPDX-License-Identifier: AGPL-3.0-only
#
# LudoX - Gestione eventi ludici
# Vedi LICENSE, NOTICE e CONTRIBUTING.md.

import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import messagebox

import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.widgets import DateEntry

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


# ============================================================
# CONFIGURAZIONE
# ============================================================

APP_TITLE = "LudoX - Gestione eventi ludici"
APP_THEME = "flatly"

# Numero massimo di token / posizioni fisiche per i documenti.
MAX_TOKEN = 100

# Password del backoffice.
BACKOFFICE_PASSWORD = "ludox"

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "ludox.db"


# ============================================================
# DATABASE
# ============================================================

def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS proprietari (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE COLLATE NOCASE,
                attivo INTEGER NOT NULL DEFAULT 1
                    CHECK(attivo IN (0, 1))
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS giochi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE COLLATE NOCASE,
                attivo INTEGER NOT NULL DEFAULT 1
                    CHECK(attivo IN (0, 1))
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS copie_gioco (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gioco_id INTEGER NOT NULL,
                proprietario_id INTEGER NOT NULL,
                quantita INTEGER NOT NULL DEFAULT 0
                    CHECK(quantita >= 0),
                FOREIGN KEY(gioco_id) REFERENCES giochi(id),
                FOREIGN KEY(proprietario_id) REFERENCES proprietari(id),
                UNIQUE(gioco_id, proprietario_id)
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS documenti (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token INTEGER NOT NULL,
                ingresso TEXT NOT NULL,
                uscita TEXT
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS prestiti (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                documento_id INTEGER NOT NULL,
                gioco_id INTEGER NOT NULL,
                uscita TEXT NOT NULL,
                rientro TEXT,
                FOREIGN KEY(documento_id) REFERENCES documenti(id),
                FOREIGN KEY(gioco_id) REFERENCES giochi(id)
            )
        """)

        # Un token non può essere associato a due documenti aperti.
        db.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_token_aperto
            ON documenti(token)
            WHERE uscita IS NULL
        """)

        # Un documento può avere un solo gioco attualmente in prestito.
        db.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_prestito_aperto_documento
            ON prestiti(documento_id)
            WHERE rientro IS NULL
        """)

        # Proprietario iniziale utile per partire subito.
        db.execute("""
            INSERT OR IGNORE INTO proprietari (nome, attivo)
            VALUES ('Organizzazione', 1)
        """)


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def formatta_data_ora(valore):
    """Formatta una data ISO per la visualizzazione nelle tabelle."""
    if not valore:
        return "—"

    try:
        return datetime.fromisoformat(valore).strftime("%d/%m/%Y %H:%M:%S")
    except (ValueError, TypeError):
        return str(valore)


# ============================================================
# FUNZIONI DATI - CONTATORI E PRESTITI
# ============================================================

def conta_prestiti():
    with get_db() as db:
        return db.execute(
            "SELECT COUNT(*) FROM prestiti"
        ).fetchone()[0]


def conta_documenti():
    with get_db() as db:
        return db.execute(
            "SELECT COUNT(*) FROM documenti"
        ).fetchone()[0]


def conta_documenti_attivi():
    with get_db() as db:
        return db.execute("""
            SELECT COUNT(*)
            FROM documenti
            WHERE uscita IS NULL
        """).fetchone()[0]


def token_libero():
    with get_db() as db:
        occupati = {
            row["token"]
            for row in db.execute("""
                SELECT token
                FROM documenti
                WHERE uscita IS NULL
            """)
        }

    for token in range(1, MAX_TOKEN + 1):
        if token not in occupati:
            return token

    return None


def documento_aperto_da_token(token):
    with get_db() as db:
        return db.execute("""
            SELECT *
            FROM documenti
            WHERE token = ?
              AND uscita IS NULL
        """, (token,)).fetchone()


def prestito_aperto_documento(documento_id):
    with get_db() as db:
        return db.execute("""
            SELECT
                p.*,
                g.nome AS gioco_nome
            FROM prestiti p
            JOIN giochi g
              ON g.id = p.gioco_id
            WHERE p.documento_id = ?
              AND p.rientro IS NULL
        """, (documento_id,)).fetchone()


def copie_totali_gioco(gioco_id):
    with get_db() as db:
        return db.execute("""
            SELECT COALESCE(SUM(quantita), 0)
            FROM copie_gioco
            WHERE gioco_id = ?
        """, (gioco_id,)).fetchone()[0]


def copie_in_prestito(gioco_id):
    with get_db() as db:
        return db.execute("""
            SELECT COUNT(*)
            FROM prestiti
            WHERE gioco_id = ?
              AND rientro IS NULL
        """, (gioco_id,)).fetchone()[0]


def disponibilita_gioco(gioco_id):
    totali = copie_totali_gioco(gioco_id)
    fuori = copie_in_prestito(gioco_id)
    return max(0, totali - fuori), totali


def cerca_giochi(testo=""):
    testo = testo.strip()

    with get_db() as db:
        return db.execute("""
            SELECT
                g.id,
                g.nome,
                COALESCE(SUM(cg.quantita), 0) AS copie_totali
            FROM giochi g
            LEFT JOIN copie_gioco cg
              ON cg.gioco_id = g.id
            WHERE g.attivo = 1
              AND g.nome LIKE ?
            GROUP BY g.id, g.nome
            HAVING COALESCE(SUM(cg.quantita), 0) > 0
            ORDER BY g.nome
        """, (f"%{testo}%",)).fetchall()


# ============================================================
# FUNZIONI DATI - PROPRIETARI
# ============================================================

def elenco_proprietari(solo_attivi=False):
    with get_db() as db:
        if solo_attivi:
            return db.execute("""
                SELECT *
                FROM proprietari
                WHERE attivo = 1
                ORDER BY nome
            """).fetchall()

        return db.execute("""
            SELECT *
            FROM proprietari
            ORDER BY nome
        """).fetchall()


def proprietario_per_id(proprietario_id):
    with get_db() as db:
        return db.execute("""
            SELECT *
            FROM proprietari
            WHERE id = ?
        """, (proprietario_id,)).fetchone()


def totale_copie_proprietario(proprietario_id):
    with get_db() as db:
        return db.execute("""
            SELECT COALESCE(SUM(quantita), 0)
            FROM copie_gioco
            WHERE proprietario_id = ?
        """, (proprietario_id,)).fetchone()[0]


# ============================================================
# FUNZIONI DATI - GIOCHI / COPIE
# ============================================================

def gioco_per_id(gioco_id):
    with get_db() as db:
        return db.execute("""
            SELECT *
            FROM giochi
            WHERE id = ?
        """, (gioco_id,)).fetchone()


def elenco_giochi_backoffice():
    with get_db() as db:
        return db.execute("""
            SELECT
                g.id,
                g.nome,
                g.attivo,
                COALESCE(SUM(cg.quantita), 0) AS copie_totali
            FROM giochi g
            LEFT JOIN copie_gioco cg
              ON cg.gioco_id = g.id
            GROUP BY g.id, g.nome, g.attivo
            ORDER BY g.nome
        """).fetchall()


def copie_per_proprietario_del_gioco(gioco_id):
    with get_db() as db:
        return db.execute("""
            SELECT
                p.id AS proprietario_id,
                p.nome AS proprietario_nome,
                p.attivo AS proprietario_attivo,
                COALESCE(cg.quantita, 0) AS quantita
            FROM proprietari p
            LEFT JOIN copie_gioco cg
              ON cg.proprietario_id = p.id
             AND cg.gioco_id = ?
            ORDER BY p.nome
        """, (gioco_id,)).fetchall()


def riepilogo_proprietari_gioco(gioco_id):
    with get_db() as db:
        righe = db.execute("""
            SELECT
                p.nome,
                cg.quantita
            FROM copie_gioco cg
            JOIN proprietari p
              ON p.id = cg.proprietario_id
            WHERE cg.gioco_id = ?
              AND cg.quantita > 0
            ORDER BY p.nome
        """, (gioco_id,)).fetchall()

    if not righe:
        return "—"

    return ", ".join(
        f"{row['nome']}: {row['quantita']}"
        for row in righe
    )


# ============================================================
# APPLICAZIONE
# ============================================================

class PrestitiApp(ttk.Window):

    def __init__(self):
        super().__init__(
            title=APP_TITLE,
            themename=APP_THEME
        )

        self.geometry("1160x800")
        self.minsize(950, 680)

        self.current_frame = None

        self.protocol(
            "WM_DELETE_WINDOW",
            self.chiudi_app
        )

        self.show_home()

    # ========================================================
    # HELPERS GRAFICI
    # ========================================================

    def clear(self):
        if self.current_frame:
            self.current_frame.destroy()

        self.current_frame = ttk.Frame(
            self,
            padding=30
        )
        self.current_frame.pack(
            fill=BOTH,
            expand=YES
        )
        return self.current_frame

    def titolo_pagina(self, parent, titolo, sottotitolo=None):
        ttk.Label(
            parent,
            text=titolo,
            font=("Arial", 28, "bold"),
            bootstyle="primary"
        ).pack(pady=(5, 4))

        if sottotitolo:
            ttk.Label(
                parent,
                text=sottotitolo,
                font=("Arial", 13),
                bootstyle="secondary"
            ).pack(pady=(0, 20))

    def pulsante_indietro(self, parent, command):
        ttk.Button(
            parent,
            text="←  INDIETRO",
            command=command,
            bootstyle="secondary-outline"
        ).pack(
            anchor=W,
            pady=(0, 15)
        )

    def crea_card(self, parent, colonna, numero, testo, colore):
        card = ttk.Labelframe(
            parent,
            padding=20,
            bootstyle=colore
        )
        card.grid(
            row=0,
            column=colonna,
            padx=10,
            sticky=NSEW
        )

        ttk.Label(
            card,
            text=str(numero),
            font=("Arial", 34, "bold"),
            bootstyle=colore
        ).pack()

        ttk.Label(
            card,
            text=testo,
            font=("Arial", 11, "bold"),
            bootstyle="secondary"
        ).pack(pady=(4, 0))

    # ========================================================
    # HOME
    # ========================================================

    def show_home(self):
        frame = self.clear()

        self.titolo_pagina(
            frame,
            "PRESTITI LUDOTECA",
            "Gestione prestiti e documenti"
        )

        cards = ttk.Frame(frame)
        cards.pack(
            fill=X,
            pady=(15, 35)
        )

        for col in range(3):
            cards.columnconfigure(col, weight=1)

        self.crea_card(
            cards,
            0,
            conta_prestiti(),
            "PRESTITI EFFETTUATI",
            "primary"
        )

        self.crea_card(
            cards,
            1,
            conta_documenti(),
            "PERSONE / DOCUMENTI",
            "info"
        )

        self.crea_card(
            cards,
            2,
            conta_documenti_attivi(),
            "PRESTITI ATTIVI",
            "success"
        )

        azioni = ttk.Frame(frame)
        azioni.pack(
            fill=X,
            padx=90
        )

        for col in range(2):
            azioni.columnconfigure(col, weight=1)

        ttk.Button(
            azioni,
            text="＋  NUOVO PRESTITO",
            command=self.show_nuovo_prestito,
            bootstyle="success"
        ).grid(
            row=0,
            column=0,
            padx=12,
            pady=12,
            ipady=18,
            sticky=EW
        )

        ttk.Button(
            azioni,
            text="↔  CAMBIO GIOCO",
            command=self.show_cambio_token,
            bootstyle="primary"
        ).grid(
            row=0,
            column=1,
            padx=12,
            pady=12,
            ipady=18,
            sticky=EW
        )

        ttk.Button(
            azioni,
            text="✓  RESTITUZIONE FINALE",
            command=self.show_restituzione,
            bootstyle="warning"
        ).grid(
            row=1,
            column=0,
            padx=12,
            pady=12,
            ipady=18,
            sticky=EW
        )

        ttk.Button(
            azioni,
            text="▥  STATISTICHE",
            command=self.show_statistiche,
            bootstyle="info"
        ).grid(
            row=1,
            column=1,
            padx=12,
            pady=12,
            ipady=18,
            sticky=EW
        )

        ttk.Separator(frame).pack(
            fill=X,
            padx=90,
            pady=(35, 20)
        )

        ttk.Button(
            frame,
            text="⚙  BACKOFFICE",
            command=self.show_login_backoffice,
            bootstyle="secondary-outline"
        ).pack(
            pady=5,
            ipadx=18,
            ipady=7
        )

    # ========================================================
    # SELETTORE GIOCHI
    # ========================================================

    def crea_selettore_giochi(
        self,
        parent,
        callback,
        gioco_da_escludere=None
    ):
        ricerca_var = tk.StringVar()

        box = ttk.Frame(parent)
        box.pack(
            fill=BOTH,
            expand=YES,
            padx=30
        )

        ttk.Label(
            box,
            text="Cerca gioco",
            font=("Arial", 14, "bold")
        ).pack(
            anchor=W,
            pady=(5, 5)
        )

        entry = ttk.Entry(
            box,
            textvariable=ricerca_var,
            font=("Arial", 17),
            bootstyle="primary"
        )
        entry.pack(
            fill=X,
            ipady=7,
            pady=(0, 15)
        )
        entry.focus_set()

        tree_frame = ttk.Frame(box)
        tree_frame.pack(
            fill=BOTH,
            expand=YES
        )

        tree = ttk.Treeview(
            tree_frame,
            columns=("nome", "disponibili"),
            show="headings",
            height=12,
            bootstyle="primary"
        )

        tree.heading("nome", text="GIOCO")
        tree.heading("disponibili", text="DISPONIBILITÀ")

        tree.column("nome", width=680)
        tree.column(
            "disponibili",
            width=180,
            anchor=CENTER
        )

        scrollbar = ttk.Scrollbar(
            tree_frame,
            orient=VERTICAL,
            command=tree.yview
        )
        tree.configure(
            yscrollcommand=scrollbar.set
        )

        tree.pack(
            side=LEFT,
            fill=BOTH,
            expand=YES
        )
        scrollbar.pack(
            side=RIGHT,
            fill=Y
        )

        def aggiorna(*args):
            for item in tree.get_children():
                tree.delete(item)

            giochi = cerca_giochi(
                ricerca_var.get()
            )

            for gioco in giochi:
                if gioco_da_escludere == gioco["id"]:
                    continue

                disponibili, totali = disponibilita_gioco(
                    gioco["id"]
                )

                tree.insert(
                    "",
                    END,
                    iid=str(gioco["id"]),
                    values=(
                        gioco["nome"],
                        f"{disponibili} / {totali}"
                    )
                )

        ricerca_var.trace_add(
            "write",
            aggiorna
        )
        aggiorna()

        def conferma():
            selezione = tree.selection()

            if not selezione:
                messagebox.showwarning(
                    "Seleziona un gioco",
                    "Devi selezionare un gioco."
                )
                return

            gioco_id = int(selezione[0])
            disponibili, _ = disponibilita_gioco(
                gioco_id
            )

            if disponibili <= 0:
                messagebox.showwarning(
                    "Gioco non disponibile",
                    "Non ci sono copie disponibili."
                )
                aggiorna()
                return

            callback(gioco_id)

        ttk.Button(
            box,
            text="CONFERMA",
            command=conferma,
            bootstyle="success"
        ).pack(
            pady=20,
            ipadx=40,
            ipady=10
        )

        tree.bind(
            "<Double-1>",
            lambda event: conferma()
        )

    # ========================================================
    # NUOVO PRESTITO
    # ========================================================

    def show_nuovo_prestito(self):
        frame = self.clear()

        self.pulsante_indietro(
            frame,
            self.show_home
        )

        self.titolo_pagina(
            frame,
            "NUOVO PRESTITO",
            "Seleziona il gioco da consegnare"
        )

        self.crea_selettore_giochi(
            frame,
            self.crea_nuovo_prestito
        )

    def crea_nuovo_prestito(self, gioco_id):
        disponibili, _ = disponibilita_gioco(
            gioco_id
        )

        if disponibili <= 0:
            messagebox.showwarning(
                "Non disponibile",
                "Non ci sono copie disponibili."
            )
            return

        token = token_libero()

        if token is None:
            messagebox.showerror(
                "Token esauriti",
                "Non ci sono posizioni documento libere."
            )
            return

        timestamp = now_iso()

        try:
            with get_db() as db:
                cursor = db.execute("""
                    INSERT INTO documenti (
                        token,
                        ingresso
                    )
                    VALUES (?, ?)
                """, (
                    token,
                    timestamp
                ))

                documento_id = cursor.lastrowid

                db.execute("""
                    INSERT INTO prestiti (
                        documento_id,
                        gioco_id,
                        uscita
                    )
                    VALUES (?, ?, ?)
                """, (
                    documento_id,
                    gioco_id,
                    timestamp
                ))

                gioco = db.execute("""
                    SELECT nome
                    FROM giochi
                    WHERE id = ?
                """, (
                    gioco_id,
                )).fetchone()

        except sqlite3.Error as e:
            messagebox.showerror(
                "Errore database",
                str(e)
            )
            return

        self.show_token_assegnato(
            token,
            gioco["nome"]
        )

    def show_token_assegnato(self, token, gioco_nome):
        frame = self.clear()

        self.titolo_pagina(
            frame,
            "PRESTITO REGISTRATO"
        )

        card = ttk.Labelframe(
            frame,
            padding=30,
            bootstyle="success"
        )
        card.pack(
            padx=100,
            pady=25,
            fill=X
        )

        ttk.Label(
            card,
            text="POSIZIONE DOCUMENTO",
            font=("Arial", 15, "bold"),
            bootstyle="secondary"
        ).pack()

        ttk.Label(
            card,
            text=str(token),
            font=("Arial", 72, "bold"),
            bootstyle="success"
        ).pack(pady=10)

        ttk.Label(
            card,
            text=f"Metti il documento nella posizione {token}",
            font=("Arial", 20)
        ).pack(pady=5)

        ttk.Separator(card).pack(
            fill=X,
            pady=20
        )

        ttk.Label(
            card,
            text=f"CONSEGNA: {gioco_nome}",
            font=("Arial", 22, "bold")
        ).pack()

        ttk.Button(
            frame,
            text="COMPLETATO — TORNA ALLA HOME",
            command=self.show_home,
            bootstyle="success"
        ).pack(
            pady=30,
            ipadx=30,
            ipady=12
        )

    # ========================================================
    # CAMBIO GIOCO
    # ========================================================

    def show_cambio_token(self):
        frame = self.clear()

        self.pulsante_indietro(
            frame,
            self.show_home
        )

        self.titolo_pagina(
            frame,
            "CAMBIO GIOCO",
            "Inserisci il numero del token"
        )

        token_var = tk.StringVar()

        ttk.Label(
            frame,
            text="TOKEN",
            font=("Arial", 14, "bold"),
            bootstyle="secondary"
        ).pack(pady=(35, 5))

        entry = ttk.Entry(
            frame,
            textvariable=token_var,
            font=("Arial", 36, "bold"),
            width=7,
            justify=CENTER,
            bootstyle="primary"
        )
        entry.pack(ipady=10)
        entry.focus_set()

        def continua():
            try:
                token = int(token_var.get())
            except ValueError:
                messagebox.showwarning(
                    "Token non valido",
                    "Inserisci un numero valido."
                )
                return

            documento = documento_aperto_da_token(
                token
            )

            if not documento:
                messagebox.showwarning(
                    "Token libero",
                    f"Il token {token} non ha un prestito aperto."
                )
                return

            prestito = prestito_aperto_documento(
                documento["id"]
            )

            if not prestito:
                messagebox.showerror(
                    "Errore",
                    "Non risulta un gioco aperto."
                )
                return

            self.show_cambio_gioco(
                token,
                documento,
                prestito
            )

        ttk.Button(
            frame,
            text="CONTINUA",
            command=continua,
            bootstyle="primary"
        ).pack(
            pady=25,
            ipadx=40,
            ipady=12
        )

        entry.bind(
            "<Return>",
            lambda event: continua()
        )

    def show_cambio_gioco(
        self,
        token,
        documento,
        prestito
    ):
        frame = self.clear()

        self.pulsante_indietro(
            frame,
            self.show_cambio_token
        )

        self.titolo_pagina(
            frame,
            f"CAMBIO GIOCO — TOKEN {token}"
        )

        info = ttk.Labelframe(
            frame,
            padding=15,
            bootstyle="primary"
        )
        info.pack(
            fill=X,
            padx=80,
            pady=(5, 20)
        )

        ttk.Label(
            info,
            text="GIOCO ATTUALE",
            bootstyle="secondary",
            font=("Arial", 11, "bold")
        ).pack()

        ttk.Label(
            info,
            text=prestito["gioco_nome"],
            font=("Arial", 22, "bold"),
            bootstyle="primary"
        ).pack(pady=4)

        def cambia(nuovo_gioco_id):
            disponibili, _ = disponibilita_gioco(
                nuovo_gioco_id
            )

            if disponibili <= 0:
                messagebox.showwarning(
                    "Non disponibile",
                    "Non ci sono copie disponibili."
                )
                return

            timestamp = now_iso()

            try:
                with get_db() as db:
                    db.execute("""
                        UPDATE prestiti
                        SET rientro = ?
                        WHERE id = ?
                          AND rientro IS NULL
                    """, (
                        timestamp,
                        prestito["id"]
                    ))

                    db.execute("""
                        INSERT INTO prestiti (
                            documento_id,
                            gioco_id,
                            uscita
                        )
                        VALUES (?, ?, ?)
                    """, (
                        documento["id"],
                        nuovo_gioco_id,
                        timestamp
                    ))

                    nuovo = db.execute("""
                        SELECT nome
                        FROM giochi
                        WHERE id = ?
                    """, (
                        nuovo_gioco_id,
                    )).fetchone()

            except sqlite3.Error as e:
                messagebox.showerror(
                    "Errore database",
                    str(e)
                )
                return

            self.show_cambio_completato(
                token,
                prestito["gioco_nome"],
                nuovo["nome"]
            )

        self.crea_selettore_giochi(
            frame,
            cambia,
            gioco_da_escludere=prestito["gioco_id"]
        )

    def show_cambio_completato(
        self,
        token,
        vecchio,
        nuovo
    ):
        frame = self.clear()

        self.titolo_pagina(
            frame,
            "CAMBIO REGISTRATO"
        )

        card = ttk.Labelframe(
            frame,
            padding=30,
            bootstyle="primary"
        )
        card.pack(
            fill=X,
            padx=120,
            pady=30
        )

        ttk.Label(
            card,
            text=f"TOKEN {token}",
            font=("Arial", 34, "bold"),
            bootstyle="primary"
        ).pack(pady=10)

        ttk.Label(
            card,
            text=f"Restituito: {vecchio}",
            font=("Arial", 16)
        ).pack(pady=5)

        ttk.Label(
            card,
            text=f"Consegnare: {nuovo}",
            font=("Arial", 22, "bold")
        ).pack(pady=10)

        ttk.Label(
            card,
            text=f"Il documento rimane nella posizione {token}",
            font=("Arial", 15),
            bootstyle="secondary"
        ).pack(pady=10)

        ttk.Button(
            frame,
            text="TORNA ALLA HOME",
            command=self.show_home,
            bootstyle="primary"
        ).pack(
            ipadx=30,
            ipady=10
        )

    # ========================================================
    # RESTITUZIONE
    # ========================================================

    def show_restituzione(self):
        frame = self.clear()

        self.pulsante_indietro(
            frame,
            self.show_home
        )

        self.titolo_pagina(
            frame,
            "RESTITUZIONE FINALE",
            "Inserisci il token consegnato dalla persona"
        )

        token_var = tk.StringVar()

        ttk.Label(
            frame,
            text="TOKEN",
            font=("Arial", 14, "bold"),
            bootstyle="secondary"
        ).pack(pady=(35, 5))

        entry = ttk.Entry(
            frame,
            textvariable=token_var,
            font=("Arial", 36, "bold"),
            width=7,
            justify=CENTER,
            bootstyle="warning"
        )
        entry.pack(ipady=10)
        entry.focus_set()

        def continua():
            try:
                token = int(token_var.get())
            except ValueError:
                messagebox.showwarning(
                    "Token non valido",
                    "Inserisci un numero valido."
                )
                return

            documento = documento_aperto_da_token(
                token
            )

            if not documento:
                messagebox.showwarning(
                    "Token libero",
                    f"Il token {token} non risulta occupato."
                )
                return

            prestito = prestito_aperto_documento(
                documento["id"]
            )

            if not prestito:
                messagebox.showerror(
                    "Errore",
                    "Non risulta un gioco aperto per questo token."
                )
                return

            # PRIMA CONFERMA
            conferma = messagebox.askyesno(
                "Conferma restituzione",
                f"TOKEN {token}\n\n"
                f"Gioco: {prestito['gioco_nome']}\n\n"
                "Il gioco è stato restituito?"
            )

            if not conferma:
                return

            # Non chiudiamo ancora nulla nel DB:
            # il token resta occupato fino alla conferma
            # della restituzione fisica del documento.
            self.show_documento_da_restituire(
                token,
                documento,
                prestito
            )

        ttk.Button(
            frame,
            text="CONTINUA",
            command=continua,
            bootstyle="warning"
        ).pack(
            pady=25,
            ipadx=40,
            ipady=12
        )

        entry.bind(
            "<Return>",
            lambda event: continua()
        )

    def show_documento_da_restituire(
        self,
        token,
        documento,
        prestito
    ):
        frame = self.clear()

        self.titolo_pagina(
            frame,
            "RESTITUZIONE DOCUMENTO"
        )

        card = ttk.Labelframe(
            frame,
            padding=35,
            bootstyle="danger"
        )
        card.pack(
            fill=X,
            padx=80,
            pady=25
        )

        ttk.Label(
            card,
            text="PRELEVA IL DOCUMENTO",
            font=("Arial", 18, "bold"),
            bootstyle="danger"
        ).pack()

        ttk.Label(
            card,
            text=str(token),
            font=("Arial", 84, "bold"),
            bootstyle="danger"
        ).pack(pady=5)

        ttk.Label(
            card,
            text=f"POSIZIONE {token}",
            font=("Arial", 24, "bold")
        ).pack(pady=5)

        ttk.Label(
            card,
            text=f"Gioco restituito: {prestito['gioco_nome']}",
            font=("Arial", 15),
            bootstyle="secondary"
        ).pack(pady=(15, 5))

        ttk.Label(
            card,
            text=(
                "Il token è ancora occupato.\n"
                "Liberalo solo dopo aver restituito fisicamente il documento."
            ),
            justify=CENTER,
            font=("Arial", 13)
        ).pack(pady=15)

        def documento_restituito():
            # SECONDA CONFERMA
            conferma = messagebox.askyesno(
                "Conferma documento",
                f"Hai materialmente restituito "
                f"il documento della posizione {token}?"
            )

            if not conferma:
                return

            timestamp = now_iso()

            try:
                with get_db() as db:
                    prestito_update = db.execute("""
                        UPDATE prestiti
                        SET rientro = ?
                        WHERE id = ?
                          AND rientro IS NULL
                    """, (
                        timestamp,
                        prestito["id"]
                    ))

                    documento_update = db.execute("""
                        UPDATE documenti
                        SET uscita = ?
                        WHERE id = ?
                          AND uscita IS NULL
                    """, (
                        timestamp,
                        documento["id"]
                    ))

                    if prestito_update.rowcount != 1:
                        raise sqlite3.Error(
                            "Il prestito non risulta più aperto."
                        )

                    if documento_update.rowcount != 1:
                        raise sqlite3.Error(
                            "Il documento non risulta più depositato."
                        )

            except sqlite3.Error as e:
                messagebox.showerror(
                    "Errore database",
                    str(e)
                )
                return

            self.show_restituzione_completata(
                token
            )

        ttk.Button(
            frame,
            text="✓  DOCUMENTO RESTITUITO",
            command=documento_restituito,
            bootstyle="success"
        ).pack(
            pady=(20, 10),
            ipadx=50,
            ipady=18
        )

        ttk.Button(
            frame,
            text="ANNULLA",
            command=self.show_home,
            bootstyle="secondary-outline"
        ).pack(pady=5)

    def show_restituzione_completata(self, token):
        frame = self.clear()

        self.titolo_pagina(
            frame,
            "RESTITUZIONE COMPLETATA"
        )

        card = ttk.Labelframe(
            frame,
            padding=40,
            bootstyle="success"
        )
        card.pack(
            fill=X,
            padx=140,
            pady=40
        )

        ttk.Label(
            card,
            text="TOKEN",
            font=("Arial", 15, "bold"),
            bootstyle="secondary"
        ).pack()

        ttk.Label(
            card,
            text=str(token),
            font=("Arial", 72, "bold"),
            bootstyle="success"
        ).pack()

        ttk.Label(
            card,
            text="NUOVAMENTE DISPONIBILE",
            font=("Arial", 22, "bold"),
            bootstyle="success"
        ).pack(pady=15)

        ttk.Button(
            frame,
            text="TORNA ALLA HOME",
            command=self.show_home,
            bootstyle="success"
        ).pack(
            ipadx=35,
            ipady=12
        )

    # ========================================================
    # STATISTICHE
    # ========================================================

    @staticmethod
    def arrotonda_giu_bucket(dt, minuti_bucket):
        """Arrotonda un datetime verso il basso al confine del bucket."""
        mezzanotte = dt.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )

        secondi_trascorsi = int(
            (dt - mezzanotte).total_seconds()
        )
        secondi_bucket = minuti_bucket * 60
        secondi_allineati = (
            secondi_trascorsi
            // secondi_bucket
            * secondi_bucket
        )

        return mezzanotte + timedelta(
            seconds=secondi_allineati
        )

    @classmethod
    def arrotonda_su_bucket(cls, dt, minuti_bucket):
        """Arrotonda un datetime verso l'alto al confine del bucket."""
        arrotondato = cls.arrotonda_giu_bucket(
            dt,
            minuti_bucket
        )

        if dt == arrotondato:
            return arrotondato

        return arrotondato + timedelta(
            minutes=minuti_bucket
        )

    @classmethod
    def intervallo_statistiche(
        cls,
        riferimento,
        ore,
        minuti_bucket
    ):
        """
        Restituisce l'intervallo effettivamente visualizzato.

        L'inizio viene arrotondato verso il basso e la fine verso l'alto
        in modo da utilizzare sempre bucket temporali completi.
        """
        inizio_nominale = riferimento - timedelta(
            hours=ore
        )

        inizio = cls.arrotonda_giu_bucket(
            inizio_nominale,
            minuti_bucket
        )
        fine = cls.arrotonda_su_bucket(
            riferimento,
            minuti_bucket
        )

        return inizio, fine

    def show_statistiche(
        self,
        ore=12,
        riferimento=None,
        minuti_bucket=15
    ):
        # Valori ammessi per la risoluzione temporale.
        risoluzioni = [5, 10, 15, 20, 25, 30]

        if minuti_bucket not in risoluzioni:
            minuti_bucket = 15

        if riferimento is None:
            # Manteniamo il minuto reale corrente.
            # In questo modo, ad esempio alle 13:44 con bucket da 15 minuti,
            # l'intervallo delle ultime 12 ore resta 01:30 -> 13:45.
            riferimento = datetime.now().replace(
                second=0,
                microsecond=0
            )

        frame = self.clear()

        self.pulsante_indietro(
            frame,
            self.show_home
        )

        self.titolo_pagina(
            frame,
            "STATISTICHE",
            "Analisi dei giochi consegnati e delle nuove persone per intervallo temporale"
        )

        # ----------------------------------------------------
        # CONTROLLI: PERIODO
        # ----------------------------------------------------

        controlli = ttk.Labelframe(
            frame,
            text="Intervallo di analisi",
            padding=12,
            bootstyle="secondary"
        )
        controlli.pack(
            fill=X,
            padx=35,
            pady=(0, 10)
        )

        riga_periodo = ttk.Frame(controlli)
        riga_periodo.pack(
            fill=X,
            pady=(0, 8)
        )

        ttk.Label(
            riga_periodo,
            text="Periodo:",
            font=("Arial", 11, "bold")
        ).pack(
            side=LEFT,
            padx=(0, 10)
        )

        ora_var = tk.StringVar(
            value=riferimento.strftime("%H")
        )
        minuto_var = tk.StringVar(
            value=riferimento.strftime("%M")
        )
        risoluzione_var = tk.StringVar(
            value=f"{minuti_bucket} min"
        )

        def valori_minuti(minuto_corrente):
            """
            Mostra normalmente minuti a passi di 5.
            Se il riferimento corrente è, ad esempio, 13:44,
            aggiunge anche 44 per non alterare automaticamente il periodo.
            """
            valori = list(range(0, 60, 5))

            if minuto_corrente not in valori:
                valori.append(minuto_corrente)
                valori.sort()

            return [
                f"{m:02d}"
                for m in valori
            ]

        # ----------------------------------------------------
        # CONTROLLI: DATA, ORA E RISOLUZIONE
        # ----------------------------------------------------

        riga_riferimento = ttk.Frame(controlli)
        riga_riferimento.pack(
            fill=X
        )

        ttk.Label(
            riga_riferimento,
            text="Data:",
            font=("Arial", 11, "bold")
        ).pack(
            side=LEFT,
            padx=(0, 6)
        )

        # Compatibilità con versioni diverse di ttkbootstrap:
        # le versioni recenti usano date_format / first_weekday / start_date,
        # quelle precedenti dateformat / firstweekday / startdate.
        try:
            data_picker = DateEntry(
                riga_riferimento,
                date_format="%d/%m/%Y",
                first_weekday=0,
                start_date=riferimento,
                bootstyle="primary",
                width=12
            )
        except TypeError:
            data_picker = DateEntry(
                riga_riferimento,
                dateformat="%d/%m/%Y",
                firstweekday=0,
                startdate=riferimento,
                bootstyle="primary",
                width=12
            )

        data_picker.pack(
            side=LEFT,
            padx=(0, 14)
        )

        ttk.Label(
            riga_riferimento,
            text="Ora:",
            font=("Arial", 11, "bold")
        ).pack(
            side=LEFT,
            padx=(0, 6)
        )

        combo_ora = ttk.Combobox(
            riga_riferimento,
            textvariable=ora_var,
            values=[
                f"{h:02d}"
                for h in range(24)
            ],
            state="readonly",
            width=3,
            justify=CENTER
        )
        combo_ora.pack(
            side=LEFT,
            padx=(0, 2),
            ipady=2
        )

        ttk.Label(
            riga_riferimento,
            text=":",
            font=("Arial", 12, "bold")
        ).pack(
            side=LEFT,
            padx=1
        )

        combo_minuto = ttk.Combobox(
            riga_riferimento,
            textvariable=minuto_var,
            values=valori_minuti(
                riferimento.minute
            ),
            state="readonly",
            width=3,
            justify=CENTER
        )
        combo_minuto.pack(
            side=LEFT,
            padx=(2, 14),
            ipady=2
        )

        ttk.Label(
            riga_riferimento,
            text="Risoluzione:",
            font=("Arial", 11, "bold")
        ).pack(
            side=LEFT,
            padx=(0, 6)
        )

        combo_risoluzione = ttk.Combobox(
            riga_riferimento,
            textvariable=risoluzione_var,
            values=[
                f"{m} min"
                for m in risoluzioni
            ],
            state="readonly",
            width=8
        )
        combo_risoluzione.pack(
            side=LEFT,
            padx=(0, 12),
            ipady=2
        )

        def leggi_parametri():
            try:
                # Leggiamo direttamente il testo del DateEntry:
                # funziona sia con una data digitata sia con il calendario popup.
                data_testo = data_picker.entry.get().strip()
                data_selezionata = datetime.strptime(
                    data_testo,
                    "%d/%m/%Y"
                )

                ora = int(
                    ora_var.get()
                )
                minuto = int(
                    minuto_var.get()
                )

                if not 0 <= ora <= 23:
                    raise ValueError

                if not 0 <= minuto <= 59:
                    raise ValueError

                nuovo_riferimento = data_selezionata.replace(
                    hour=ora,
                    minute=minuto,
                    second=0,
                    microsecond=0
                )

            except (ValueError, AttributeError):
                messagebox.showwarning(
                    "Data o ora non valida",
                    "Seleziona una data valida e un orario compreso "
                    "tra 00:00 e 23:59."
                )
                return None

            try:
                nuova_risoluzione = int(
                    risoluzione_var.get().split()[0]
                )
            except (ValueError, IndexError):
                nuova_risoluzione = 15

            if nuova_risoluzione not in risoluzioni:
                nuova_risoluzione = 15

            return nuovo_riferimento, nuova_risoluzione

        def aggiorna(nuove_ore=None):
            parametri = leggi_parametri()

            if parametri is None:
                return

            nuovo_riferimento, nuova_risoluzione = parametri

            self.show_statistiche(
                ore=ore if nuove_ore is None else nuove_ore,
                riferimento=nuovo_riferimento,
                minuti_bucket=nuova_risoluzione
            )

        for h in [12, 6, 4, 2, 1]:
            stile = (
                "primary"
                if h == ore
                else "secondary-outline"
            )

            testo = (
                "1 ORA"
                if h == 1
                else f"{h} ORE"
            )

            ttk.Button(
                riga_periodo,
                text=testo,
                command=lambda h=h: aggiorna(h),
                bootstyle=stile
            ).pack(
                side=LEFT,
                padx=3
            )

        ttk.Button(
            riga_riferimento,
            text="APPLICA",
            command=aggiorna,
            bootstyle="primary"
        ).pack(
            side=LEFT,
            padx=3
        )

        def usa_adesso():
            adesso = datetime.now().replace(
                second=0,
                microsecond=0
            )

            try:
                data_picker.set_date(
                    adesso
                )
            except (AttributeError, TypeError):
                data_picker.entry.delete(
                    0,
                    END
                )
                data_picker.entry.insert(
                    0,
                    adesso.strftime("%d/%m/%Y")
                )

            ora_var.set(
                adesso.strftime("%H")
            )

            combo_minuto.configure(
                values=valori_minuti(
                    adesso.minute
                )
            )
            minuto_var.set(
                adesso.strftime("%M")
            )

            aggiorna()

        ttk.Button(
            riga_riferimento,
            text="ADESSO",
            command=usa_adesso,
            bootstyle="secondary-outline"
        ).pack(
            side=LEFT,
            padx=3
        )

        # La risoluzione si applica subito.
        # Data e ora vengono invece confermate con APPLICA.
        combo_risoluzione.bind(
            "<<ComboboxSelected>>",
            lambda event: aggiorna()
        )

        # ----------------------------------------------------
        # INTERVALLO E CONTATORI
        # ----------------------------------------------------

        inizio, fine = self.intervallo_statistiche(
            riferimento,
            ore,
            minuti_bucket
        )

        inizio_iso = inizio.isoformat(
            timespec="seconds"
        )
        fine_iso = fine.isoformat(
            timespec="seconds"
        )

        with get_db() as db:
            prestiti_periodo = db.execute("""
                SELECT COUNT(*)
                FROM prestiti
                WHERE uscita >= ?
                  AND uscita < ?
            """, (
                inizio_iso,
                fine_iso
            )).fetchone()[0]

            persone_periodo = db.execute("""
                SELECT COUNT(*)
                FROM documenti
                WHERE ingresso >= ?
                  AND ingresso < ?
            """, (
                inizio_iso,
                fine_iso
            )).fetchone()[0]

        intervallo_testo = (
            f"Periodo visualizzato: "
            f"{inizio.strftime('%d/%m/%Y %H:%M')} → "
            f"{fine.strftime('%d/%m/%Y %H:%M')}  •  "
            f"Risoluzione: {minuti_bucket} min"
        )

        ttk.Label(
            frame,
            text=intervallo_testo,
            font=("Arial", 11, "bold"),
            bootstyle="secondary"
        ).pack(
            pady=(2, 6)
        )

        cards = ttk.Frame(frame)
        cards.pack(
            fill=X,
            padx=160,
            pady=(5, 10)
        )

        for col in range(2):
            cards.columnconfigure(
                col,
                weight=1
            )

        self.crea_card(
            cards,
            0,
            prestiti_periodo,
            "GIOCHI CONSEGNATI — PERIODO",
            "primary"
        )

        self.crea_card(
            cards,
            1,
            persone_periodo,
            "NUOVE PERSONE — PERIODO",
            "info"
        )

        self.crea_grafico(
            frame,
            inizio,
            fine,
            minuti_bucket
        )

    def crea_grafico(
        self,
        parent,
        inizio,
        fine,
        minuti_bucket
    ):
        delta = timedelta(
            minutes=minuti_bucket
        )

        punti = []
        t = inizio

        while t < fine:
            punti.append({
                "inizio": t,
                "fine": t + delta,
                "prestiti": 0,
                "documenti": 0
            })
            t += delta

        inizio_iso = inizio.isoformat(
            timespec="seconds"
        )
        fine_iso = fine.isoformat(
            timespec="seconds"
        )

        with get_db() as db:
            righe_prestiti = db.execute("""
                SELECT uscita
                FROM prestiti
                WHERE uscita >= ?
                  AND uscita < ?
            """, (
                inizio_iso,
                fine_iso
            )).fetchall()

            righe_documenti = db.execute("""
                SELECT ingresso
                FROM documenti
                WHERE ingresso >= ?
                  AND ingresso < ?
            """, (
                inizio_iso,
                fine_iso
            )).fetchall()

        secondi_bucket = delta.total_seconds()

        for row in righe_prestiti:
            try:
                dt = datetime.fromisoformat(
                    row["uscita"]
                )
                indice = int(
                    (dt - inizio).total_seconds()
                    // secondi_bucket
                )

                if 0 <= indice < len(punti):
                    punti[indice]["prestiti"] += 1
            except (ValueError, TypeError):
                continue

        for row in righe_documenti:
            try:
                dt = datetime.fromisoformat(
                    row["ingresso"]
                )
                indice = int(
                    (dt - inizio).total_seconds()
                    // secondi_bucket
                )

                if 0 <= indice < len(punti):
                    punti[indice]["documenti"] += 1
            except (ValueError, TypeError):
                continue

        giochi_consegnati = [
            p["prestiti"]
            for p in punti
        ]

        nuove_persone = [
            p["documenti"]
            for p in punti
        ]

        x = list(
            range(len(punti))
        )

        fig = Figure(
            figsize=(9, 3.6),
            dpi=100
        )

        ax = fig.add_subplot(111)

        ax.plot(
            x,
            giochi_consegnati,
            marker="o",
            label="Giochi consegnati"
        )

        ax.plot(
            x,
            nuove_persone,
            marker="o",
            label="Nuove persone"
        )

        # Le due serie sono conteggi omogenei e condividono volutamente
        # la stessa scala verticale.
        ax.set_ylabel(
            f"Conteggio per {minuti_bucket} min"
        )
        ax.set_xlabel("Ora")
        ax.legend()
        ax.grid(
            True,
            alpha=0.2
        )

        # Mostriamo al massimo circa 12-13 etichette,
        # indipendentemente dalla risoluzione scelta.
        if punti:
            salto = max(
                1,
                (len(punti) + 11) // 12
            )

            ticks = list(
                range(
                    0,
                    len(punti),
                    salto
                )
            )

            if ticks[-1] != len(punti) - 1:
                ticks.append(
                    len(punti) - 1
                )

            piu_giorni = (
                inizio.date()
                != (
                    fine
                    - timedelta(seconds=1)
                ).date()
            )

            if piu_giorni:
                tick_labels = [
                    punti[i]["inizio"].strftime(
                        "%d/%m\n%H:%M"
                    )
                    for i in ticks
                ]
            else:
                tick_labels = [
                    punti[i]["inizio"].strftime(
                        "%H:%M"
                    )
                    for i in ticks
                ]

            ax.set_xticks(
                ticks
            )
            ax.set_xticklabels(
                tick_labels
            )

        ax.set_title(
            f"{inizio.strftime('%d/%m/%Y %H:%M')} → "
            f"{fine.strftime('%d/%m/%Y %H:%M')} "
            f"• bucket {minuti_bucket} min",
            fontsize=10
        )

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(
            fig,
            master=parent
        )
        canvas.draw()

        canvas.get_tk_widget().pack(
            fill=BOTH,
            expand=YES,
            padx=40,
            pady=(5, 10)
        )

    # ========================================================
    # LOGIN BACKOFFICE
    # ========================================================

    def show_login_backoffice(self):
        frame = self.clear()

        self.pulsante_indietro(
            frame,
            self.show_home
        )

        self.titolo_pagina(
            frame,
            "BACKOFFICE",
            "Area riservata"
        )

        card = ttk.Labelframe(
            frame,
            padding=30,
            bootstyle="secondary"
        )
        card.pack(
            padx=250,
            pady=40,
            fill=X
        )

        password_var = tk.StringVar()

        ttk.Label(
            card,
            text="Password",
            font=("Arial", 14, "bold")
        ).pack(pady=(0, 8))

        entry = ttk.Entry(
            card,
            textvariable=password_var,
            show="●",
            font=("Arial", 18),
            justify=CENTER
        )
        entry.pack(
            fill=X,
            ipady=7
        )
        entry.focus_set()

        def accedi():
            if password_var.get() == BACKOFFICE_PASSWORD:
                self.show_backoffice()
            else:
                messagebox.showerror(
                    "Accesso negato",
                    "Password non corretta."
                )

        ttk.Button(
            card,
            text="ACCEDI",
            command=accedi,
            bootstyle="primary"
        ).pack(
            pady=(20, 0),
            ipadx=30,
            ipady=8
        )

        entry.bind(
            "<Return>",
            lambda event: accedi()
        )

    # ========================================================
    # BACKOFFICE HOME
    # ========================================================

    def show_backoffice(self):
        frame = self.clear()

        self.pulsante_indietro(
            frame,
            self.show_home
        )

        self.titolo_pagina(
            frame,
            "BACKOFFICE",
            "Catalogo, proprietari e consultazione dello storico"
        )

        area = ttk.Frame(frame)
        area.pack(
            fill=X,
            padx=120,
            pady=35
        )

        for col in range(2):
            area.columnconfigure(col, weight=1)

        ttk.Button(
            area,
            text="🎲  GESTIONE GIOCHI",
            command=self.show_gestione_giochi,
            bootstyle="primary"
        ).grid(
            row=0,
            column=0,
            padx=15,
            pady=15,
            ipady=22,
            sticky=EW
        )

        ttk.Button(
            area,
            text="👤  GESTIONE PROPRIETARI",
            command=self.show_gestione_proprietari,
            bootstyle="info"
        ).grid(
            row=0,
            column=1,
            padx=15,
            pady=15,
            ipady=22,
            sticky=EW
        )

        ttk.Button(
            area,
            text="📋  TUTTI I PRESTITI",
            command=self.show_tutti_prestiti,
            bootstyle="success"
        ).grid(
            row=1,
            column=0,
            padx=15,
            pady=15,
            ipady=22,
            sticky=EW
        )

        ttk.Button(
            area,
            text="🪪  DOCUMENTI / PERSONE",
            command=self.show_tutti_documenti,
            bootstyle="warning"
        ).grid(
            row=1,
            column=1,
            padx=15,
            pady=15,
            ipady=22,
            sticky=EW
        )

        ttk.Button(
            area,
            text="📦  GIOCHI PER PROPRIETARIO",
            command=self.show_giochi_per_proprietario,
            bootstyle="secondary"
        ).grid(
            row=2,
            column=0,
            columnspan=2,
            padx=15,
            pady=15,
            ipady=22,
            sticky=EW
        )

    # ========================================================
    # BACKOFFICE - TUTTI I PRESTITI
    # ========================================================

    def show_tutti_prestiti(self):
        frame = self.clear()

        self.pulsante_indietro(
            frame,
            self.show_backoffice
        )

        self.titolo_pagina(
            frame,
            "TUTTI I PRESTITI",
            "Ogni cambio gioco genera un nuovo record di prestito"
        )

        with get_db() as db:
            totale = db.execute("""
                SELECT COUNT(*)
                FROM prestiti
            """).fetchone()[0]

            attivi = db.execute("""
                SELECT COUNT(*)
                FROM prestiti
                WHERE rientro IS NULL
            """).fetchone()[0]

            righe = db.execute("""
                SELECT
                    p.id AS prestito_id,
                    d.id AS documento_id,
                    d.token,
                    g.nome AS gioco,
                    p.uscita,
                    p.rientro
                FROM prestiti p
                JOIN documenti d
                  ON d.id = p.documento_id
                JOIN giochi g
                  ON g.id = p.gioco_id
                ORDER BY p.uscita DESC, p.id DESC
            """).fetchall()

        riepilogo = ttk.Frame(frame)
        riepilogo.pack(
            fill=X,
            padx=180,
            pady=(0, 20)
        )

        for col in range(2):
            riepilogo.columnconfigure(col, weight=1)

        self.crea_card(
            riepilogo,
            0,
            totale,
            "PRESTITI TOTALI",
            "primary"
        )

        self.crea_card(
            riepilogo,
            1,
            attivi,
            "PRESTITI ATTIVI",
            "success"
        )

        tabella_frame = ttk.Frame(frame)
        tabella_frame.pack(
            fill=BOTH,
            expand=YES
        )

        tree = ttk.Treeview(
            tabella_frame,
            columns=(
                "id",
                "token",
                "documento",
                "gioco",
                "uscita",
                "rientro",
                "stato"
            ),
            show="headings",
            height=17,
            bootstyle="success"
        )

        tree.heading("id", text="ID")
        tree.heading("token", text="TOKEN")
        tree.heading("documento", text="DOC.")
        tree.heading("gioco", text="GIOCO")
        tree.heading("uscita", text="INIZIO PRESTITO")
        tree.heading("rientro", text="RIENTRO")
        tree.heading("stato", text="STATO")

        tree.column("id", width=65, anchor=CENTER)
        tree.column("token", width=80, anchor=CENTER)
        tree.column("documento", width=75, anchor=CENTER)
        tree.column("gioco", width=300)
        tree.column("uscita", width=165, anchor=CENTER)
        tree.column("rientro", width=165, anchor=CENTER)
        tree.column("stato", width=105, anchor=CENTER)

        scrollbar = ttk.Scrollbar(
            tabella_frame,
            orient=VERTICAL,
            command=tree.yview
        )
        tree.configure(
            yscrollcommand=scrollbar.set
        )

        tree.pack(
            side=LEFT,
            fill=BOTH,
            expand=YES
        )
        scrollbar.pack(
            side=RIGHT,
            fill=Y
        )

        for row in righe:
            tree.insert(
                "",
                END,
                values=(
                    row["prestito_id"],
                    row["token"],
                    row["documento_id"],
                    row["gioco"],
                    formatta_data_ora(row["uscita"]),
                    formatta_data_ora(row["rientro"]),
                    "ATTIVO" if row["rientro"] is None else "CHIUSO"
                )
            )

    # ========================================================
    # BACKOFFICE - DOCUMENTI / PERSONE
    # ========================================================

    def show_tutti_documenti(self):
        frame = self.clear()

        self.pulsante_indietro(
            frame,
            self.show_backoffice
        )

        self.titolo_pagina(
            frame,
            "DOCUMENTI / PERSONE",
            "Registro anonimo: il software non memorizza dati personali"
        )

        with get_db() as db:
            totale = db.execute("""
                SELECT COUNT(*)
                FROM documenti
            """).fetchone()[0]

            attivi = db.execute("""
                SELECT COUNT(*)
                FROM documenti
                WHERE uscita IS NULL
            """).fetchone()[0]

            righe = db.execute("""
                SELECT
                    d.id,
                    d.token,
                    d.ingresso,
                    d.uscita,
                    COUNT(p.id) AS numero_prestiti
                FROM documenti d
                LEFT JOIN prestiti p
                  ON p.documento_id = d.id
                GROUP BY
                    d.id,
                    d.token,
                    d.ingresso,
                    d.uscita
                ORDER BY d.ingresso DESC, d.id DESC
            """).fetchall()

        riepilogo = ttk.Frame(frame)
        riepilogo.pack(
            fill=X,
            padx=180,
            pady=(0, 20)
        )

        for col in range(2):
            riepilogo.columnconfigure(col, weight=1)

        self.crea_card(
            riepilogo,
            0,
            totale,
            "PERSONE / DOCUMENTI TOTALI",
            "info"
        )

        self.crea_card(
            riepilogo,
            1,
            attivi,
            "DOCUMENTI DEPOSITATI ORA",
            "warning"
        )

        tabella_frame = ttk.Frame(frame)
        tabella_frame.pack(
            fill=BOTH,
            expand=YES
        )

        tree = ttk.Treeview(
            tabella_frame,
            columns=(
                "id",
                "token",
                "ingresso",
                "uscita",
                "prestiti",
                "stato"
            ),
            show="headings",
            height=17,
            bootstyle="warning"
        )

        tree.heading("id", text="ID")
        tree.heading("token", text="TOKEN")
        tree.heading("ingresso", text="DEPOSITO DOCUMENTO")
        tree.heading("uscita", text="RESTITUZIONE DOCUMENTO")
        tree.heading("prestiti", text="N. PRESTITI")
        tree.heading("stato", text="STATO")

        tree.column("id", width=75, anchor=CENTER)
        tree.column("token", width=90, anchor=CENTER)
        tree.column("ingresso", width=210, anchor=CENTER)
        tree.column("uscita", width=220, anchor=CENTER)
        tree.column("prestiti", width=120, anchor=CENTER)
        tree.column("stato", width=120, anchor=CENTER)

        scrollbar = ttk.Scrollbar(
            tabella_frame,
            orient=VERTICAL,
            command=tree.yview
        )
        tree.configure(
            yscrollcommand=scrollbar.set
        )

        tree.pack(
            side=LEFT,
            fill=BOTH,
            expand=YES
        )
        scrollbar.pack(
            side=RIGHT,
            fill=Y
        )

        for row in righe:
            tree.insert(
                "",
                END,
                values=(
                    row["id"],
                    row["token"],
                    formatta_data_ora(row["ingresso"]),
                    formatta_data_ora(row["uscita"]),
                    row["numero_prestiti"],
                    "DEPOSITATO" if row["uscita"] is None else "RESTITUITO"
                )
            )

    # ========================================================
    # BACKOFFICE - GIOCHI PER PROPRIETARIO
    # ========================================================

    def show_giochi_per_proprietario(self):
        frame = self.clear()

        self.pulsante_indietro(
            frame,
            self.show_backoffice
        )

        self.titolo_pagina(
            frame,
            "GIOCHI PER PROPRIETARIO",
            "Inventario delle copie messe a disposizione da ciascun proprietario"
        )

        proprietari = elenco_proprietari()
        proprietari_by_name = {
            row["nome"]: row["id"]
            for row in proprietari
        }

        selezione_frame = ttk.Frame(frame)
        selezione_frame.pack(
            fill=X,
            padx=100,
            pady=(5, 20)
        )

        ttk.Label(
            selezione_frame,
            text="Proprietario:",
            font=("Arial", 13, "bold")
        ).pack(
            side=LEFT,
            padx=(0, 10)
        )

        proprietario_var = tk.StringVar()

        combo = ttk.Combobox(
            selezione_frame,
            textvariable=proprietario_var,
            values=list(proprietari_by_name.keys()),
            state="readonly",
            width=38,
            font=("Arial", 13)
        )
        combo.pack(
            side=LEFT,
            fill=X,
            expand=YES,
            ipady=4
        )

        riepilogo_var = tk.StringVar(
            value="Seleziona un proprietario"
        )

        ttk.Label(
            frame,
            textvariable=riepilogo_var,
            font=("Arial", 14, "bold"),
            bootstyle="secondary"
        ).pack(
            pady=(0, 12)
        )

        tabella_frame = ttk.Frame(frame)
        tabella_frame.pack(
            fill=BOTH,
            expand=YES
        )

        tree = ttk.Treeview(
            tabella_frame,
            columns=(
                "gioco",
                "copie_proprietario",
                "copie_totali",
                "prestiti_attivi_titolo",
                "gioco_attivo"
            ),
            show="headings",
            height=18,
            bootstyle="secondary"
        )

        tree.heading("gioco", text="GIOCO")
        tree.heading(
            "copie_proprietario",
            text="COPIE PROPRIETARIO"
        )
        tree.heading(
            "copie_totali",
            text="COPIE TOTALI"
        )
        tree.heading(
            "prestiti_attivi_titolo",
            text="PRESTITI ATTIVI TITOLO"
        )
        tree.heading(
            "gioco_attivo",
            text="ATTIVO"
        )

        tree.column("gioco", width=440)
        tree.column(
            "copie_proprietario",
            width=170,
            anchor=CENTER
        )
        tree.column(
            "copie_totali",
            width=140,
            anchor=CENTER
        )
        tree.column(
            "prestiti_attivi_titolo",
            width=180,
            anchor=CENTER
        )
        tree.column(
            "gioco_attivo",
            width=100,
            anchor=CENTER
        )

        scrollbar = ttk.Scrollbar(
            tabella_frame,
            orient=VERTICAL,
            command=tree.yview
        )
        tree.configure(
            yscrollcommand=scrollbar.set
        )

        tree.pack(
            side=LEFT,
            fill=BOTH,
            expand=YES
        )
        scrollbar.pack(
            side=RIGHT,
            fill=Y
        )

        nota = ttk.Label(
            frame,
            text=(
                "Nota: i prestiti sono registrati per titolo e non per singola copia; "
                "quindi i prestiti attivi mostrati non sono attribuiti a uno specifico proprietario."
            ),
            font=("Arial", 10),
            bootstyle="secondary",
            wraplength=950,
            justify=CENTER
        )
        nota.pack(
            pady=(10, 0)
        )

        def aggiorna(event=None):
            for item in tree.get_children():
                tree.delete(item)

            nome = proprietario_var.get()

            if not nome:
                riepilogo_var.set(
                    "Seleziona un proprietario"
                )
                return

            proprietario_id = proprietari_by_name[nome]

            with get_db() as db:
                righe = db.execute("""
                    SELECT
                        g.id AS gioco_id,
                        g.nome AS gioco,
                        g.attivo AS gioco_attivo,
                        cg.quantita AS copie_proprietario,
                        (
                            SELECT COALESCE(SUM(cg2.quantita), 0)
                            FROM copie_gioco cg2
                            WHERE cg2.gioco_id = g.id
                        ) AS copie_totali,
                        (
                            SELECT COUNT(*)
                            FROM prestiti pr
                            WHERE pr.gioco_id = g.id
                              AND pr.rientro IS NULL
                        ) AS prestiti_attivi_titolo
                    FROM copie_gioco cg
                    JOIN giochi g
                      ON g.id = cg.gioco_id
                    WHERE cg.proprietario_id = ?
                      AND cg.quantita > 0
                    ORDER BY g.nome
                """, (
                    proprietario_id,
                )).fetchall()

            totale_titoli = len(righe)
            totale_copie = sum(
                row["copie_proprietario"]
                for row in righe
            )

            riepilogo_var.set(
                f"{nome}  •  Titoli: {totale_titoli}  •  Copie: {totale_copie}"
            )

            for row in righe:
                tree.insert(
                    "",
                    END,
                    values=(
                        row["gioco"],
                        row["copie_proprietario"],
                        row["copie_totali"],
                        row["prestiti_attivi_titolo"],
                        "SÌ" if row["gioco_attivo"] else "NO"
                    )
                )

        combo.bind(
            "<<ComboboxSelected>>",
            aggiorna
        )

        if proprietari:
            # Preferisce il proprietario generico se presente, altrimenti il primo proprietario.
            default_name = (
                "Organizzazione"
                if "Organizzazione" in proprietari_by_name
                else proprietari[0]["nome"]
            )
            proprietario_var.set(default_name)
            aggiorna()

    # ========================================================
    # BACKOFFICE - PROPRIETARI
    # ========================================================

    def show_gestione_proprietari(self):
        frame = self.clear()

        self.pulsante_indietro(
            frame,
            self.show_backoffice
        )

        self.titolo_pagina(
            frame,
            "GESTIONE PROPRIETARI",
            "Persone o enti che mettono giochi a disposizione"
        )

        barra = ttk.Frame(frame)
        barra.pack(
            fill=X,
            pady=(5, 15)
        )

        ttk.Button(
            barra,
            text="＋ AGGIUNGI PROPRIETARIO",
            command=self.show_aggiungi_proprietario,
            bootstyle="success"
        ).pack(side=RIGHT)

        tree = ttk.Treeview(
            frame,
            columns=(
                "nome",
                "copie",
                "attivo"
            ),
            show="headings",
            height=17,
            bootstyle="info"
        )

        tree.heading("nome", text="PROPRIETARIO")
        tree.heading("copie", text="COPIE TOTALI")
        tree.heading("attivo", text="ATTIVO")

        tree.column("nome", width=650)
        tree.column(
            "copie",
            width=160,
            anchor=CENTER
        )
        tree.column(
            "attivo",
            width=120,
            anchor=CENTER
        )

        tree.pack(
            fill=BOTH,
            expand=YES
        )

        for proprietario in elenco_proprietari():
            tree.insert(
                "",
                END,
                iid=str(proprietario["id"]),
                values=(
                    proprietario["nome"],
                    totale_copie_proprietario(
                        proprietario["id"]
                    ),
                    "SÌ" if proprietario["attivo"] else "NO"
                )
            )

        def modifica():
            selezione = tree.selection()

            if not selezione:
                messagebox.showwarning(
                    "Seleziona un proprietario",
                    "Seleziona prima un proprietario."
                )
                return

            self.show_modifica_proprietario(
                int(selezione[0])
            )

        ttk.Button(
            frame,
            text="MODIFICA PROPRIETARIO SELEZIONATO",
            command=modifica,
            bootstyle="info"
        ).pack(
            pady=15,
            ipadx=25,
            ipady=8
        )

        tree.bind(
            "<Double-1>",
            lambda event: modifica()
        )

    def show_aggiungi_proprietario(self):
        frame = self.clear()

        self.pulsante_indietro(
            frame,
            self.show_gestione_proprietari
        )

        self.titolo_pagina(
            frame,
            "AGGIUNGI PROPRIETARIO"
        )

        card = ttk.Labelframe(
            frame,
            padding=30,
            bootstyle="info"
        )
        card.pack(
            padx=230,
            pady=35,
            fill=X
        )

        nome_var = tk.StringVar()

        ttk.Label(
            card,
            text="Nome proprietario",
            font=("Arial", 13, "bold")
        ).pack(anchor=W)

        entry = ttk.Entry(
            card,
            textvariable=nome_var,
            font=("Arial", 16)
        )
        entry.pack(
            fill=X,
            ipady=6,
            pady=(5, 20)
        )
        entry.focus_set()

        def salva():
            nome = nome_var.get().strip()

            if not nome:
                messagebox.showwarning(
                    "Nome mancante",
                    "Inserisci il nome del proprietario."
                )
                return

            try:
                with get_db() as db:
                    db.execute("""
                        INSERT INTO proprietari (
                            nome,
                            attivo
                        )
                        VALUES (?, 1)
                    """, (nome,))

            except sqlite3.IntegrityError:
                messagebox.showerror(
                    "Proprietario già presente",
                    "Esiste già un proprietario con questo nome."
                )
                return

            self.show_gestione_proprietari()

        ttk.Button(
            card,
            text="SALVA PROPRIETARIO",
            command=salva,
            bootstyle="success"
        ).pack(
            pady=10,
            ipadx=25,
            ipady=8
        )

        entry.bind(
            "<Return>",
            lambda event: salva()
        )

    def show_modifica_proprietario(self, proprietario_id):
        proprietario = proprietario_per_id(
            proprietario_id
        )

        if not proprietario:
            self.show_gestione_proprietari()
            return

        frame = self.clear()

        self.pulsante_indietro(
            frame,
            self.show_gestione_proprietari
        )

        self.titolo_pagina(
            frame,
            "MODIFICA PROPRIETARIO"
        )

        card = ttk.Labelframe(
            frame,
            padding=30,
            bootstyle="info"
        )
        card.pack(
            padx=230,
            pady=35,
            fill=X
        )

        nome_var = tk.StringVar(
            value=proprietario["nome"]
        )

        attivo_var = tk.BooleanVar(
            value=bool(proprietario["attivo"])
        )

        ttk.Label(
            card,
            text="Nome proprietario",
            font=("Arial", 13, "bold")
        ).pack(anchor=W)

        ttk.Entry(
            card,
            textvariable=nome_var,
            font=("Arial", 16)
        ).pack(
            fill=X,
            ipady=6,
            pady=(5, 20)
        )

        ttk.Label(
            card,
            text=(
                f"Copie associate: "
                f"{totale_copie_proprietario(proprietario_id)}"
            ),
            font=("Arial", 12),
            bootstyle="secondary"
        ).pack(
            anchor=W,
            pady=(0, 15)
        )

        ttk.Checkbutton(
            card,
            text="Proprietario attivo",
            variable=attivo_var,
            bootstyle="success-round-toggle"
        ).pack(
            anchor=W,
            pady=10
        )

        def salva():
            nome = nome_var.get().strip()

            if not nome:
                messagebox.showwarning(
                    "Nome mancante",
                    "Inserisci il nome del proprietario."
                )
                return

            if (
                not attivo_var.get()
                and totale_copie_proprietario(
                    proprietario_id
                ) > 0
            ):
                conferma = messagebox.askyesno(
                    "Proprietario con copie associate",
                    "Questo proprietario ha ancora copie "
                    "associate ai giochi.\n\n"
                    "Vuoi comunque disattivarlo?"
                )

                if not conferma:
                    return

            try:
                with get_db() as db:
                    db.execute("""
                        UPDATE proprietari
                        SET
                            nome = ?,
                            attivo = ?
                        WHERE id = ?
                    """, (
                        nome,
                        1 if attivo_var.get() else 0,
                        proprietario_id
                    ))

            except sqlite3.IntegrityError:
                messagebox.showerror(
                    "Nome duplicato",
                    "Esiste già un proprietario con questo nome."
                )
                return

            self.show_gestione_proprietari()

        ttk.Button(
            card,
            text="SALVA MODIFICHE",
            command=salva,
            bootstyle="success"
        ).pack(
            pady=20,
            ipadx=25,
            ipady=8
        )

    # ========================================================
    # BACKOFFICE - GIOCHI
    # ========================================================

    def show_gestione_giochi(self):
        frame = self.clear()

        self.pulsante_indietro(
            frame,
            self.show_backoffice
        )

        self.titolo_pagina(
            frame,
            "GESTIONE GIOCHI",
            "Catalogo e quantità per proprietario"
        )

        barra = ttk.Frame(frame)
        barra.pack(
            fill=X,
            pady=(5, 15)
        )

        ttk.Button(
            barra,
            text="＋ AGGIUNGI GIOCO",
            command=self.show_aggiungi_gioco,
            bootstyle="success"
        ).pack(side=RIGHT)

        tree = ttk.Treeview(
            frame,
            columns=(
                "nome",
                "proprietari",
                "copie",
                "fuori",
                "attivo"
            ),
            show="headings",
            height=16,
            bootstyle="primary"
        )

        tree.heading("nome", text="GIOCO")
        tree.heading("proprietari", text="PROPRIETARI / COPIE")
        tree.heading("copie", text="COPIE")
        tree.heading("fuori", text="FUORI")
        tree.heading("attivo", text="ATTIVO")

        tree.column("nome", width=330)
        tree.column("proprietari", width=430)
        tree.column(
            "copie",
            width=90,
            anchor=CENTER
        )
        tree.column(
            "fuori",
            width=90,
            anchor=CENTER
        )
        tree.column(
            "attivo",
            width=90,
            anchor=CENTER
        )

        tree.pack(
            fill=BOTH,
            expand=YES
        )

        for gioco in elenco_giochi_backoffice():
            tree.insert(
                "",
                END,
                iid=str(gioco["id"]),
                values=(
                    gioco["nome"],
                    riepilogo_proprietari_gioco(
                        gioco["id"]
                    ),
                    gioco["copie_totali"],
                    copie_in_prestito(
                        gioco["id"]
                    ),
                    "SÌ" if gioco["attivo"] else "NO"
                )
            )

        def modifica():
            selezione = tree.selection()

            if not selezione:
                messagebox.showwarning(
                    "Seleziona un gioco",
                    "Seleziona prima un gioco."
                )
                return

            self.show_modifica_gioco(
                int(selezione[0])
            )

        ttk.Button(
            frame,
            text="MODIFICA GIOCO SELEZIONATO",
            command=modifica,
            bootstyle="primary"
        ).pack(
            pady=15,
            ipadx=25,
            ipady=8
        )

        tree.bind(
            "<Double-1>",
            lambda event: modifica()
        )

    def show_aggiungi_gioco(self):
        frame = self.clear()

        self.pulsante_indietro(
            frame,
            self.show_gestione_giochi
        )

        self.titolo_pagina(
            frame,
            "AGGIUNGI GIOCO",
            "Dopo il salvataggio potrai assegnare le copie ai proprietari"
        )

        card = ttk.Labelframe(
            frame,
            padding=30,
            bootstyle="primary"
        )
        card.pack(
            padx=220,
            pady=35,
            fill=X
        )

        nome_var = tk.StringVar()

        ttk.Label(
            card,
            text="Nome gioco",
            font=("Arial", 13, "bold")
        ).pack(anchor=W)

        entry = ttk.Entry(
            card,
            textvariable=nome_var,
            font=("Arial", 16)
        )
        entry.pack(
            fill=X,
            ipady=6,
            pady=(5, 20)
        )
        entry.focus_set()

        def salva():
            nome = nome_var.get().strip()

            if not nome:
                messagebox.showwarning(
                    "Nome mancante",
                    "Inserisci il nome del gioco."
                )
                return

            try:
                with get_db() as db:
                    cursor = db.execute("""
                        INSERT INTO giochi (
                            nome,
                            attivo
                        )
                        VALUES (?, 1)
                    """, (nome,))

                    gioco_id = cursor.lastrowid

            except sqlite3.IntegrityError:
                messagebox.showerror(
                    "Gioco già presente",
                    "Esiste già un gioco con questo nome."
                )
                return

            self.show_modifica_gioco(
                gioco_id
            )

        ttk.Button(
            card,
            text="SALVA E ASSEGNA COPIE",
            command=salva,
            bootstyle="success"
        ).pack(
            pady=10,
            ipadx=25,
            ipady=8
        )

        entry.bind(
            "<Return>",
            lambda event: salva()
        )

    def show_modifica_gioco(self, gioco_id):
        gioco = gioco_per_id(
            gioco_id
        )

        if not gioco:
            self.show_gestione_giochi()
            return

        frame = self.clear()

        self.pulsante_indietro(
            frame,
            self.show_gestione_giochi
        )

        self.titolo_pagina(
            frame,
            "MODIFICA GIOCO",
            "Modifica titolo, stato e quantità per proprietario"
        )

        top = ttk.Labelframe(
            frame,
            padding=20,
            bootstyle="primary"
        )
        top.pack(
            fill=X,
            padx=70,
            pady=(5, 20)
        )

        nome_var = tk.StringVar(
            value=gioco["nome"]
        )

        attivo_var = tk.BooleanVar(
            value=bool(gioco["attivo"])
        )

        ttk.Label(
            top,
            text="Nome gioco",
            font=("Arial", 12, "bold")
        ).grid(
            row=0,
            column=0,
            sticky=W,
            padx=(0, 10)
        )

        nome_entry = ttk.Entry(
            top,
            textvariable=nome_var,
            font=("Arial", 15)
        )
        nome_entry.grid(
            row=0,
            column=1,
            sticky=EW,
            padx=10,
            ipady=5
        )

        ttk.Checkbutton(
            top,
            text="Gioco attivo",
            variable=attivo_var,
            bootstyle="success-round-toggle"
        ).grid(
            row=0,
            column=2,
            sticky=E,
            padx=(20, 0)
        )

        top.columnconfigure(
            1,
            weight=1
        )

        # ----------------------------------------------------
        # QUANTITÀ PER PROPRIETARIO
        # ----------------------------------------------------

        ttk.Label(
            frame,
            text="COPIE PER PROPRIETARIO",
            font=("Arial", 14, "bold")
        ).pack(
            anchor=W,
            padx=75,
            pady=(0, 8)
        )

        corpo = ttk.Frame(frame)
        corpo.pack(
            fill=BOTH,
            expand=YES,
            padx=70
        )

        tree = ttk.Treeview(
            corpo,
            columns=(
                "proprietario",
                "quantita",
                "stato"
            ),
            show="headings",
            height=11,
            bootstyle="primary"
        )

        tree.heading(
            "proprietario",
            text="PROPRIETARIO"
        )
        tree.heading(
            "quantita",
            text="COPIE"
        )
        tree.heading(
            "stato",
            text="STATO"
        )

        tree.column(
            "proprietario",
            width=600
        )
        tree.column(
            "quantita",
            width=140,
            anchor=CENTER
        )
        tree.column(
            "stato",
            width=140,
            anchor=CENTER
        )

        tree.pack(
            fill=BOTH,
            expand=YES
        )

        def aggiorna_lista():
            for item in tree.get_children():
                tree.delete(item)

            righe = copie_per_proprietario_del_gioco(
                gioco_id
            )

            for row in righe:
                tree.insert(
                    "",
                    END,
                    iid=str(row["proprietario_id"]),
                    values=(
                        row["proprietario_nome"],
                        row["quantita"],
                        "ATTIVO"
                        if row["proprietario_attivo"]
                        else "DISATTIVO"
                    )
                )

        aggiorna_lista()

        # ----------------------------------------------------
        # MODIFICA QUANTITÀ
        # ----------------------------------------------------

        modifica_box = ttk.Labelframe(
            frame,
            text="Modifica quantità",
            padding=15,
            bootstyle="secondary"
        )
        modifica_box.pack(
            fill=X,
            padx=70,
            pady=15
        )

        selezionato_var = tk.StringVar(
            value="Nessun proprietario selezionato"
        )

        ttk.Label(
            modifica_box,
            textvariable=selezionato_var,
            font=("Arial", 12, "bold")
        ).grid(
            row=0,
            column=0,
            padx=10,
            sticky=W
        )

        quantita_var = tk.StringVar(
            value="0"
        )

        quantita_entry = ttk.Entry(
            modifica_box,
            textvariable=quantita_var,
            width=8,
            font=("Arial", 14),
            justify=CENTER
        )
        quantita_entry.grid(
            row=0,
            column=1,
            padx=10,
            ipady=4
        )

        proprietario_selezionato = {
            "id": None
        }

        def seleziona_proprietario(event=None):
            selezione = tree.selection()

            if not selezione:
                return

            proprietario_id = int(
                selezione[0]
            )

            valori = tree.item(
                selezione[0],
                "values"
            )

            proprietario_selezionato["id"] = proprietario_id
            selezionato_var.set(
                valori[0]
            )
            quantita_var.set(
                str(valori[1])
            )

        tree.bind(
            "<<TreeviewSelect>>",
            seleziona_proprietario
        )

        def salva_quantita():
            proprietario_id = proprietario_selezionato["id"]

            if proprietario_id is None:
                messagebox.showwarning(
                    "Seleziona un proprietario",
                    "Seleziona prima un proprietario nella tabella."
                )
                return

            try:
                quantita = int(
                    quantita_var.get()
                )

                if quantita < 0:
                    raise ValueError

            except ValueError:
                messagebox.showwarning(
                    "Quantità non valida",
                    "Inserisci un numero intero maggiore o uguale a zero."
                )
                return

            # Il totale complessivo non può scendere
            # sotto le copie attualmente in prestito.
            with get_db() as db:
                altre_copie = db.execute("""
                    SELECT COALESCE(SUM(quantita), 0)
                    FROM copie_gioco
                    WHERE gioco_id = ?
                      AND proprietario_id <> ?
                """, (
                    gioco_id,
                    proprietario_id
                )).fetchone()[0]

            nuovo_totale = altre_copie + quantita
            fuori = copie_in_prestito(
                gioco_id
            )

            if nuovo_totale < fuori:
                messagebox.showwarning(
                    "Copie insufficienti",
                    f"Ci sono attualmente {fuori} copie "
                    f"di questo gioco in prestito.\n\n"
                    f"Il totale non può essere ridotto "
                    f"a {nuovo_totale}."
                )
                return

            with get_db() as db:
                if quantita == 0:
                    db.execute("""
                        DELETE FROM copie_gioco
                        WHERE gioco_id = ?
                          AND proprietario_id = ?
                    """, (
                        gioco_id,
                        proprietario_id
                    ))
                else:
                    db.execute("""
                        INSERT INTO copie_gioco (
                            gioco_id,
                            proprietario_id,
                            quantita
                        )
                        VALUES (?, ?, ?)
                        ON CONFLICT(
                            gioco_id,
                            proprietario_id
                        )
                        DO UPDATE SET
                            quantita = excluded.quantita
                    """, (
                        gioco_id,
                        proprietario_id,
                        quantita
                    ))

            aggiorna_lista()

        ttk.Button(
            modifica_box,
            text="SALVA QUANTITÀ",
            command=salva_quantita,
            bootstyle="success"
        ).grid(
            row=0,
            column=2,
            padx=10,
            ipadx=15,
            ipady=5
        )

        modifica_box.columnconfigure(
            0,
            weight=1
        )

        # ----------------------------------------------------
        # SALVA DATI GENERALI GIOCO
        # ----------------------------------------------------

        def salva_gioco():
            nome = nome_var.get().strip()

            if not nome:
                messagebox.showwarning(
                    "Nome mancante",
                    "Inserisci il nome del gioco."
                )
                return

            fuori = copie_in_prestito(
                gioco_id
            )

            if (
                not attivo_var.get()
                and fuori > 0
            ):
                messagebox.showwarning(
                    "Gioco in prestito",
                    "Non puoi disattivare un gioco "
                    "mentre ci sono copie in prestito."
                )
                return

            try:
                with get_db() as db:
                    db.execute("""
                        UPDATE giochi
                        SET
                            nome = ?,
                            attivo = ?
                        WHERE id = ?
                    """, (
                        nome,
                        1 if attivo_var.get() else 0,
                        gioco_id
                    ))

            except sqlite3.IntegrityError:
                messagebox.showerror(
                    "Nome duplicato",
                    "Esiste già un gioco con questo nome."
                )
                return

            self.show_gestione_giochi()

        fondo = ttk.Frame(frame)
        fondo.pack(
            pady=(5, 0)
        )

        ttk.Button(
            fondo,
            text="SALVA GIOCO",
            command=salva_gioco,
            bootstyle="primary"
        ).pack(
            side=LEFT,
            padx=5,
            ipadx=30,
            ipady=8
        )

        ttk.Button(
            fondo,
            text="TORNA ALL'ELENCO",
            command=self.show_gestione_giochi,
            bootstyle="secondary-outline"
        ).pack(
            side=LEFT,
            padx=5,
            ipadx=20,
            ipady=8
        )

    # ========================================================
    # CHIUSURA PROGRAMMA
    # ========================================================

    def chiudi_app(self):
        attivi = conta_documenti_attivi()

        if attivi > 0:
            with get_db() as db:
                token = db.execute("""
                    SELECT token
                    FROM documenti
                    WHERE uscita IS NULL
                    ORDER BY token
                """).fetchall()

            token_str = ", ".join(
                str(row["token"])
                for row in token
            )

            conferma = messagebox.askyesno(
                "Prestiti ancora aperti",
                f"Ci sono ancora {attivi} "
                f"documenti depositati.\n\n"
                f"Token: {token_str}\n\n"
                "Vuoi davvero chiudere il programma?"
            )

            if not conferma:
                return

        self.destroy()


# ============================================================
# AVVIO
# ============================================================

if __name__ == "__main__":
    init_db()

    app = PrestitiApp()
    app.mainloop()
