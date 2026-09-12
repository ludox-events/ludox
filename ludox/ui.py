# Copyright (C) 2026 Matteo Sassi
# SPDX-License-Identifier: AGPL-3.0-only

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, filedialog

import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.widgets import DateEntry

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from .config import (
    AppConfig, save_config, normalize_database_setting,
    database_setting_from_path, resolve_database_path, PROJECT_DIR,
)
from .database import (
    get_db, formatta_data_ora, conta_prestiti, conta_documenti,
    conta_documenti_attivi,
    disponibilita_gioco, cerca_giochi, elenco_proprietari,
    proprietario_per_id, massimo_token_aperto, init_db,
    set_db_path, get_db_path,
)
from . import catalog, lending, reporting
from .i18n import tr, set_language, get_language, language_display_names

APP_THEME = "flatly"
BACKOFFICE_PASSWORD = "ludox"

class PrestitiApp(ttk.Window):

    def __init__(self, config: AppConfig):
        self.config = config
        super().__init__(
            title=tr("app.title"),
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
            text=tr(titolo),
            font=("Arial", 28, "bold"),
            bootstyle="primary"
        ).pack(pady=(5, 4))

        if sottotitolo:
            ttk.Label(
                parent,
                text=tr(sottotitolo),
                font=("Arial", 13),
                bootstyle="secondary"
            ).pack(pady=(0, 20))

    def pulsante_indietro(self, parent, command):
        ttk.Button(
            parent,
            text=tr("←  INDIETRO"),
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
            text=tr(str(numero)),
            font=("Arial", 34, "bold"),
            bootstyle=colore
        ).pack()

        ttk.Label(
            card,
            text=tr(testo),
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
            text=tr("＋  NUOVO PRESTITO"),
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
            text=tr("↔  CAMBIO GIOCO"),
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
            text=tr("✓  RESTITUZIONE FINALE"),
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
            text=tr("▥  STATISTICHE"),
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
            text=tr("⚙  BACKOFFICE"),
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
            text=tr("Cerca gioco"),
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

        tree.heading("nome", text=tr("GIOCO"))
        tree.heading("disponibili", text=tr("DISPONIBILITÀ"))

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
                    tr("Seleziona un gioco"),
                    tr("Devi selezionare un gioco.")
                )
                return

            gioco_id = int(selezione[0])
            disponibili, _ = disponibilita_gioco(
                gioco_id
            )

            if disponibili <= 0:
                messagebox.showwarning(
                    tr("Gioco non disponibile"),
                    tr("Non ci sono copie disponibili.")
                )
                aggiorna()
                return

            callback(gioco_id)

        ttk.Button(
            box,
            text=tr("CONFERMA"),
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
        try:
            risultato = lending.nuovo_prestito(gioco_id, self.config.max_tokens)
        except lending.GiocoNonDisponibile as e:
            messagebox.showwarning(
                tr("Non disponibile"),
                tr(str(e))
            )
            return
        except lending.TokenEsauriti as e:
            messagebox.showerror(
                tr("Token esauriti"),
                tr(str(e))
            )
            return
        except lending.ErrorePersistenza as e:
            messagebox.showerror(
                tr("Errore database"),
                tr(str(e))
            )
            return

        self.show_token_assegnato(
            risultato.token,
            risultato.gioco_nome
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
            text=tr("POSIZIONE DOCUMENTO"),
            font=("Arial", 15, "bold"),
            bootstyle="secondary"
        ).pack()

        ttk.Label(
            card,
            text=tr(str(token)),
            font=("Arial", 72, "bold"),
            bootstyle="success"
        ).pack(pady=10)

        ttk.Label(
            card,
            text=tr(f"Metti il documento nella posizione {token}"),
            font=("Arial", 20)
        ).pack(pady=5)

        ttk.Separator(card).pack(
            fill=X,
            pady=20
        )

        ttk.Label(
            card,
            text=tr(f"CONSEGNA: {gioco_nome}"),
            font=("Arial", 22, "bold")
        ).pack()

        ttk.Button(
            frame,
            text=tr("COMPLETATO — TORNA ALLA HOME"),
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
            text=tr("TOKEN"),
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
                    tr("Token non valido"),
                    tr("Inserisci un numero valido.")
                )
                return

            try:
                situazione = lending.consulta_token(token)
            except lending.TokenLibero:
                messagebox.showwarning(
                    tr("Token libero"),
                    tr(f"Il token {token} non ha un prestito aperto.")
                )
                return

            except lending.PrestitoAssente:
                messagebox.showerror(
                    tr("Errore"),
                    tr("Non risulta un gioco aperto.")
                )
                return

            documento = situazione.documento
            prestito = situazione.prestito

            self.show_cambio_gioco(
                token,
                documento,
                prestito
            )

        ttk.Button(
            frame,
            text=tr("CONTINUA"),
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
            text=tr("GIOCO ATTUALE"),
            bootstyle="secondary",
            font=("Arial", 11, "bold")
        ).pack()

        ttk.Label(
            info,
            text=tr(prestito["gioco_nome"]),
            font=("Arial", 22, "bold"),
            bootstyle="primary"
        ).pack(pady=4)

        def cambia(nuovo_gioco_id):
            try:
                nuovo_nome = lending.cambia_gioco(
                    token=token,
                    documento_id=documento["id"],
                    prestito_id=prestito["id"],
                    gioco_id_atteso=prestito["gioco_id"],
                    nuovo_gioco_id=nuovo_gioco_id,
                )
            except lending.GiocoNonDisponibile as e:
                messagebox.showwarning(
                    tr("Gioco non disponibile"),
                    tr(str(e))
                )

                # Il prestito corrente non è stato modificato:
                # ricarichiamo il selettore per aggiornare le disponibilità.
                self.show_cambio_gioco(
                    token,
                    documento,
                    prestito
                )
                return

            except lending.CambioNonValido as e:
                messagebox.showwarning(
                    tr("Cambio non registrato"),
                    tr(str(e))
                )

                # Lo stato del token è cambiato: ripartiamo dalla lettura
                # del token invece di lasciare a schermo dati ormai obsoleti.
                self.show_cambio_token()
                return

            except lending.ErrorePersistenza as e:
                messagebox.showerror(
                    tr("Errore database"),
                    tr("Il cambio non è stato registrato.\n\n"
                    f"Dettaglio: {e}")
                )
                return

            self.show_cambio_completato(
                token,
                prestito["gioco_nome"],
                nuovo_nome
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
            text=tr(f"TOKEN {token}"),
            font=("Arial", 34, "bold"),
            bootstyle="primary"
        ).pack(pady=10)

        ttk.Label(
            card,
            text=tr(f"Restituito: {vecchio}"),
            font=("Arial", 16)
        ).pack(pady=5)

        ttk.Label(
            card,
            text=tr(f"Consegnare: {nuovo}"),
            font=("Arial", 22, "bold")
        ).pack(pady=10)

        ttk.Label(
            card,
            text=tr(f"Il documento rimane nella posizione {token}"),
            font=("Arial", 15),
            bootstyle="secondary"
        ).pack(pady=10)

        ttk.Button(
            frame,
            text=tr("TORNA ALLA HOME"),
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
            text=tr("TOKEN"),
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
                    tr("Token non valido"),
                    tr("Inserisci un numero valido.")
                )
                return

            try:
                situazione = lending.consulta_token(token)
            except lending.TokenLibero:
                messagebox.showwarning(
                    tr("Token libero"),
                    tr(f"Il token {token} non risulta occupato.")
                )
                return

            except lending.PrestitoAssente:
                messagebox.showerror(
                    tr("Errore"),
                    tr("Non risulta un gioco aperto per questo token.")
                )
                return

            documento = situazione.documento
            prestito = situazione.prestito

            # PRIMA CONFERMA
            conferma = messagebox.askyesno(
                tr("Conferma restituzione"),
                tr(f"TOKEN {token}\n\n"
                f"Gioco: {prestito['gioco_nome']}\n\n"
                "Il gioco è stato restituito?")
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
            text=tr("CONTINUA"),
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
            text=tr("PRELEVA IL DOCUMENTO"),
            font=("Arial", 18, "bold"),
            bootstyle="danger"
        ).pack()

        ttk.Label(
            card,
            text=tr(str(token)),
            font=("Arial", 84, "bold"),
            bootstyle="danger"
        ).pack(pady=5)

        ttk.Label(
            card,
            text=tr(f"POSIZIONE {token}"),
            font=("Arial", 24, "bold")
        ).pack(pady=5)

        ttk.Label(
            card,
            text=tr(f"Gioco restituito: {prestito['gioco_nome']}"),
            font=("Arial", 15),
            bootstyle="secondary"
        ).pack(pady=(15, 5))

        ttk.Label(
            card,
            text=(
                tr("Il token è ancora occupato.\n"
                "Liberalo solo dopo aver restituito fisicamente il documento.")
            ),
            justify=CENTER,
            font=("Arial", 13)
        ).pack(pady=15)

        def documento_restituito():
            # SECONDA CONFERMA
            conferma = messagebox.askyesno(
                tr("Conferma documento"),
                tr(f"Hai materialmente restituito "
                f"il documento della posizione {token}?")
            )

            if not conferma:
                return

            try:
                lending.restituzione_finale(
                    documento_id=documento["id"],
                    prestito_id=prestito["id"],
                )
            except lending.ErrorePersistenza as e:
                messagebox.showerror(
                    tr("Errore database"),
                    tr(str(e))
                )
                return

            self.show_restituzione_completata(
                token
            )

        ttk.Button(
            frame,
            text=tr("✓  DOCUMENTO RESTITUITO"),
            command=documento_restituito,
            bootstyle="success"
        ).pack(
            pady=(20, 10),
            ipadx=50,
            ipady=18
        )

        ttk.Button(
            frame,
            text=tr("ANNULLA"),
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
            text=tr("TOKEN"),
            font=("Arial", 15, "bold"),
            bootstyle="secondary"
        ).pack()

        ttk.Label(
            card,
            text=tr(str(token)),
            font=("Arial", 72, "bold"),
            bootstyle="success"
        ).pack()

        ttk.Label(
            card,
            text=tr("NUOVAMENTE DISPONIBILE"),
            font=("Arial", 22, "bold"),
            bootstyle="success"
        ).pack(pady=15)

        ttk.Button(
            frame,
            text=tr("TORNA ALLA HOME"),
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
        return reporting.arrotonda_giu_bucket(dt, minuti_bucket)

    @classmethod
    def arrotonda_su_bucket(cls, dt, minuti_bucket):
        """Arrotonda un datetime verso l'alto al confine del bucket."""
        return reporting.arrotonda_su_bucket(dt, minuti_bucket)

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
        return reporting.intervallo_statistiche(riferimento, ore, minuti_bucket)

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
            text=tr("Intervallo di analisi"),
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
            text=tr("Periodo:"),
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
            text=tr("Data:"),
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
            text=tr("Ora:"),
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
            text=tr(":"),
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
            text=tr("Risoluzione:"),
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
                    tr("Data o ora non valida"),
                    tr("Seleziona una data valida e un orario compreso "
                    "tra 00:00 e 23:59.")
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
                text=tr(testo),
                command=lambda h=h: aggiorna(h),
                bootstyle=stile
            ).pack(
                side=LEFT,
                padx=3
            )

        ttk.Button(
            riga_riferimento,
            text=tr("APPLICA"),
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
            text=tr("ADESSO"),
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

        statistiche = reporting.statistiche_periodo(
            riferimento,
            ore,
            minuti_bucket
        )
        inizio = statistiche.inizio
        fine = statistiche.fine
        prestiti_periodo = statistiche.prestiti
        persone_periodo = statistiche.documenti

        intervallo_testo = (
            f"Periodo visualizzato: "
            f"{inizio.strftime('%d/%m/%Y %H:%M')} → "
            f"{fine.strftime('%d/%m/%Y %H:%M')}  •  "
            f"Risoluzione: {minuti_bucket} min"
        )

        ttk.Label(
            frame,
            text=tr(intervallo_testo),
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
            statistiche
        )

    def crea_grafico(
        self,
        parent,
        statistiche
    ):
        inizio = statistiche.inizio
        fine = statistiche.fine
        minuti_bucket = statistiche.minuti_bucket
        punti = statistiche.punti

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
            label=tr("Giochi consegnati")
        )

        ax.plot(
            x,
            nuove_persone,
            marker="o",
            label=tr("Nuove persone")
        )

        # Le due serie sono conteggi omogenei e condividono volutamente
        # la stessa scala verticale.
        ax.set_ylabel(
            tr(f"Conteggio per {minuti_bucket} min")
        )
        ax.set_xlabel(tr("Ora"))
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
            tr(f"{inizio.strftime('%d/%m/%Y %H:%M')} → "
            f"{fine.strftime('%d/%m/%Y %H:%M')} "
            f"• bucket {minuti_bucket} min"),
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
            text=tr("Password"),
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
                    tr("Accesso negato"),
                    tr("Password non corretta.")
                )

        ttk.Button(
            card,
            text=tr("ACCEDI"),
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
            text=tr("🎲  GESTIONE GIOCHI"),
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
            text=tr("👤  GESTIONE PROPRIETARI"),
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
            text=tr("📋  TUTTI I PRESTITI"),
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
            text=tr("🪪  DOCUMENTI / PERSONE"),
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
            text=tr("📦  GIOCHI PER PROPRIETARIO"),
            command=self.show_giochi_per_proprietario,
            bootstyle="secondary"
        ).grid(
            row=2,
            column=0,
            padx=15,
            pady=15,
            ipady=22,
            sticky=EW
        )

        ttk.Button(
            area,
            text=tr("backoffice.settings"),
            command=self.show_impostazioni,
            bootstyle="secondary-outline"
        ).grid(
            row=2,
            column=1,
            padx=15,
            pady=15,
            ipady=22,
            sticky=EW
        )

        ttk.Button(
            area,
            text=tr("📊  REPORT UTILIZZO LUDOTECA"),
            command=self.show_report_utilizzo_ludoteca,
            bootstyle="primary-outline"
        ).grid(
            row=3,
            column=0,
            columnspan=2,
            padx=15,
            pady=15,
            ipady=22,
            sticky=EW
        )

        ttk.Button(
            area,
            text=tr("🧑  REPORT PERSONE / DOCUMENTI"),
            command=self.show_report_documenti,
            bootstyle="info-outline"
        ).grid(
            row=4,
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

        storico = reporting.storico_prestiti()
        totale = storico.totale
        attivi = storico.attivi
        righe = storico.righe

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

        tree.heading("id", text=tr("ID"))
        tree.heading("token", text=tr("TOKEN"))
        tree.heading("documento", text=tr("DOC."))
        tree.heading("gioco", text=tr("GIOCO"))
        tree.heading("uscita", text=tr("INIZIO PRESTITO"))
        tree.heading("rientro", text=tr("RIENTRO"))
        tree.heading("stato", text=tr("STATO"))

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
                    tr("common.active") if row["rientro"] is None else tr("common.closed")
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

        storico = reporting.storico_documenti()
        totale = storico.totale
        attivi = storico.attivi
        righe = storico.righe

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

        tree.heading("id", text=tr("ID"))
        tree.heading("token", text=tr("TOKEN"))
        tree.heading("ingresso", text=tr("DEPOSITO DOCUMENTO"))
        tree.heading("uscita", text=tr("RESTITUZIONE DOCUMENTO"))
        tree.heading("prestiti", text=tr("N. PRESTITI"))
        tree.heading("stato", text=tr("STATO"))

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
                    tr("common.deposited") if row["uscita"] is None else tr("common.returned")
                )
            )

    # ========================================================
    # BACKOFFICE - REPORT PERSONE / DOCUMENTI
    # ========================================================

    def show_report_documenti(
        self,
        data_inizio=None,
        data_fine=None,
        ordina_per="ingresso",
        ordine_desc=True
    ):
        """
        Report storico per documento/persona anonima.

        Il periodo seleziona i documenti in base al momento di ingresso:
        un documento è incluso se il suo deposito è iniziato nell'intervallo.

        Tempo in ludoteca:
        - documento chiuso: uscita - ingresso;
        - documento ancora aperto: adesso - ingresso.

        Durata media del prestito:
        media delle durate dei prestiti conclusi associati al documento.
        Un eventuale prestito ancora aperto non entra nella media.
        """
        frame = self.clear()

        self.pulsante_indietro(
            frame,
            self.show_backoffice
        )

        self.titolo_pagina(
            frame,
            "REPORT PERSONE / DOCUMENTI",
            "Numero di prestiti, permanenza del documento e durata media dei prestiti"
        )

        oggi = datetime.now().replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )

        if data_inizio is None:
            data_inizio = oggi

        if data_fine is None:
            data_fine = oggi

        # ----------------------------------------------------
        # FILTRI
        # ----------------------------------------------------

        filtri = ttk.Labelframe(
            frame,
            text=tr("Filtri"),
            padding=12,
            bootstyle="secondary"
        )
        filtri.pack(
            fill=X,
            padx=35,
            pady=(0, 10)
        )

        riga_filtri = ttk.Frame(
            filtri
        )
        riga_filtri.pack(
            fill=X
        )

        ttk.Label(
            riga_filtri,
            text=tr("Dal:"),
            font=("Arial", 11, "bold")
        ).pack(
            side=LEFT,
            padx=(0, 6)
        )

        try:
            data_da_picker = DateEntry(
                riga_filtri,
                date_format="%d/%m/%Y",
                first_weekday=0,
                start_date=data_inizio,
                bootstyle="primary",
                width=12
            )
        except TypeError:
            data_da_picker = DateEntry(
                riga_filtri,
                dateformat="%d/%m/%Y",
                firstweekday=0,
                startdate=data_inizio,
                bootstyle="primary",
                width=12
            )

        data_da_picker.pack(
            side=LEFT,
            padx=(0, 12)
        )

        ttk.Label(
            riga_filtri,
            text=tr("Al:"),
            font=("Arial", 11, "bold")
        ).pack(
            side=LEFT,
            padx=(0, 6)
        )

        try:
            data_a_picker = DateEntry(
                riga_filtri,
                date_format="%d/%m/%Y",
                first_weekday=0,
                start_date=data_fine,
                bootstyle="primary",
                width=12
            )
        except TypeError:
            data_a_picker = DateEntry(
                riga_filtri,
                dateformat="%d/%m/%Y",
                firstweekday=0,
                startdate=data_fine,
                bootstyle="primary",
                width=12
            )

        data_a_picker.pack(
            side=LEFT,
            padx=(0, 18)
        )

        ttk.Label(
            riga_filtri,
            text=tr("Ordina per:"),
            font=("Arial", 11, "bold")
        ).pack(
            side=LEFT,
            padx=(0, 6)
        )

        mapping_ordinamento = {
            tr("people_report.sort_entry"): "ingresso",
            tr("people_report.sort_loans"): "prestiti",
            tr("people_report.sort_stay"): "tempo_documento_secondi",
            tr("people_report.sort_avg"): "media_partita_secondi"
        }

        mapping_ordinamento_inverso = {
            valore: chiave
            for chiave, valore in mapping_ordinamento.items()
        }

        ordina_var = tk.StringVar(
            value=mapping_ordinamento_inverso.get(
                ordina_per,
                tr("people_report.sort_entry")
            )
        )

        combo_ordina = ttk.Combobox(
            riga_filtri,
            textvariable=ordina_var,
            values=list(mapping_ordinamento.keys()),
            state="readonly",
            width=22
        )
        combo_ordina.pack(
            side=LEFT,
            padx=(0, 12),
            ipady=2
        )

        ttk.Label(
            riga_filtri,
            text=tr("Ordine:"),
            font=("Arial", 11, "bold")
        ).pack(
            side=LEFT,
            padx=(0, 6)
        )

        ordine_var = tk.StringVar(
            value=(
                tr("common.descending")
                if ordine_desc
                else tr("common.ascending")
            )
        )

        combo_ordine = ttk.Combobox(
            riga_filtri,
            textvariable=ordine_var,
            values=[
                tr("common.ascending"),
                tr("common.descending")
            ],
            state="readonly",
            width=13
        )
        combo_ordine.pack(
            side=LEFT,
            padx=(0, 10),
            ipady=2
        )

        def leggi_filtri():
            try:
                da = datetime.strptime(
                    data_da_picker.entry.get().strip(),
                    "%d/%m/%Y"
                ).replace(
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0
                )

                a = datetime.strptime(
                    data_a_picker.entry.get().strip(),
                    "%d/%m/%Y"
                ).replace(
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0
                )

            except (ValueError, AttributeError):
                messagebox.showwarning(
                    tr("Date non valide"),
                    tr("Seleziona due date valide nel formato GG/MM/AAAA.")
                )
                return None

            if a < da:
                messagebox.showwarning(
                    tr("Intervallo non valido"),
                    tr("La data finale non può precedere la data iniziale.")
                )
                return None

            criterio = mapping_ordinamento.get(
                ordina_var.get(),
                "ingresso"
            )

            desc = (
                ordine_var.get()
                == tr("common.descending")
            )

            return da, a, criterio, desc

        def applica():
            parametri = leggi_filtri()

            if parametri is None:
                return

            da, a, criterio, desc = parametri

            self.show_report_documenti(
                data_inizio=da,
                data_fine=a,
                ordina_per=criterio,
                ordine_desc=desc
            )

        ttk.Button(
            riga_filtri,
            text=tr("APPLICA"),
            command=applica,
            bootstyle="primary"
        ).pack(
            side=LEFT,
            padx=3
        )

        combo_ordina.bind(
            "<<ComboboxSelected>>",
            lambda event: applica()
        )

        combo_ordine.bind(
            "<<ComboboxSelected>>",
            lambda event: applica()
        )

        # ----------------------------------------------------
        # DATI DEL REPORT
        # ----------------------------------------------------

        report = reporting.report_documenti(
            data_inizio,
            data_fine,
            ordina_per=ordina_per,
            ordine_desc=ordine_desc,
            adesso=datetime.now()
        )
        inizio = report.inizio
        righe_report = [
            {
                **row,
                "stato": (
                    tr("common.in_progress")
                    if row["aperto"]
                    else tr("common.closed")
                )
            }
            for row in report.righe
        ]
        formatta_durata = reporting.formatta_durata

        criterio_testo = {
            "ingresso": tr("people_report.sort_entry"),
            "prestiti": tr("people_report.sort_loans"),
            "tempo_documento_secondi": tr("people_report.sort_stay"),
            "media_partita_secondi": tr("people_report.sort_avg")
        }.get(
            ordina_per,
            tr("people_report.sort_entry")
        )

        totale_documenti = report.totale_documenti
        totale_prestiti = report.totale_prestiti
        prestiti_per_persona = report.prestiti_per_persona
        media_prestiti_persona = report.media_prestiti_persona
        mediana_prestiti_persona = report.mediana_prestiti_persona
        dev_std_prestiti_persona = report.dev_std_prestiti_persona
        persone_almeno_3 = report.persone_almeno_3
        percentuale_almeno_2 = report.percentuale_almeno_2
        percentuale_almeno_3 = report.percentuale_almeno_3
        permanenza_mediana_secondi = report.permanenza_mediana_secondi
        durata_mediana_prestito_secondi = report.durata_mediana_prestito_secondi

        ttk.Label(
            frame,
            text=(
                tr(f"Periodo di ingresso: {inizio.strftime('%d/%m/%Y')} → "
                f"{data_fine.strftime('%d/%m/%Y')}  •  "
                f"Persone/documenti: {totale_documenti}  •  "
                f"Prestiti: {totale_prestiti}  •  "
                f"Ordine: {criterio_testo} "
                f"({'↓' if ordine_desc else '↑'})")
            ),
            font=("Arial", 11, "bold"),
            bootstyle="secondary"
        ).pack(
            pady=(0, 6)
        )

        kpi = ttk.Frame(
            frame
        )
        kpi.pack(
            fill=X,
            padx=25,
            pady=(0, 7)
        )

        for col in range(6):
            kpi.columnconfigure(
                col,
                weight=1
            )

        kpi_valori = [
            (
                f"{media_prestiti_persona:.2f}",
                "MEDIA PRESTITI / PERSONA"
            ),
            (
                f"{mediana_prestiti_persona:g}",
                "MEDIANA PRESTITI / PERSONA"
            ),
            (
                f"{dev_std_prestiti_persona:.2f}",
                "DEV. STD PRESTITI / PERSONA"
            ),
            (
                f"{percentuale_almeno_2:.1f}%",
                "PERSONE CON ≥ 2 PRESTITI"
            ),
            (
                formatta_durata(
                    permanenza_mediana_secondi
                ),
                "PERMANENZA MEDIANA"
            ),
            (
                formatta_durata(
                    durata_mediana_prestito_secondi
                ),
                "DURATA MEDIANA PRESTITO"
            )
        ]

        for indice, (
            valore,
            etichetta
        ) in enumerate(kpi_valori):
            box = ttk.Frame(
                kpi,
                padding=5
            )
            box.grid(
                row=0,
                column=indice,
                padx=4,
                sticky=NSEW
            )

            ttk.Label(
                box,
                text=tr(valore),
                font=("Arial", 15, "bold"),
                bootstyle="primary"
            ).pack()

            ttk.Label(
                box,
                text=tr(etichetta),
                font=("Arial", 8, "bold"),
                bootstyle="secondary",
                justify=CENTER,
                wraplength=145
            ).pack()

        ttk.Label(
            frame,
            text=(
                tr(f"Persone con almeno 3 prestiti: "
                f"{persone_almeno_3}/{totale_documenti} "
                f"({percentuale_almeno_3:.1f}%).  "
                "Il periodo filtra le persone in base all'ingresso del documento. "
                "La durata dei prestiti considera solo i prestiti conclusi.")
            ),
            font=("Arial", 9),
            bootstyle="secondary",
            wraplength=1050,
            justify=CENTER
        ).pack(
            pady=(0, 4)
        )

        # ----------------------------------------------------
        # GRAFICO DELLE OCCORRENZE: PRESTITI PER PERSONA
        # ----------------------------------------------------

        distribuzione = {}

        for valore in prestiti_per_persona:
            distribuzione[valore] = (
                distribuzione.get(
                    valore,
                    0
                )
                + 1
            )

        if distribuzione:
            valori_x = sorted(
                distribuzione
            )

            valori_y = [
                distribuzione[x]
                for x in valori_x
            ]

            fig = Figure(
                figsize=(9, 2.15),
                dpi=100
            )

            ax = fig.add_subplot(111)

            ax.bar(
                valori_x,
                valori_y
            )

            ax.set_title(
                tr("Distribuzione del numero di prestiti per persona/documento"),
                fontsize=10
            )
            ax.set_xlabel(
                tr("Numero di prestiti")
            )
            ax.set_ylabel(
                tr("Persone")
            )
            ax.grid(
                True,
                axis="y",
                alpha=0.2
            )

            ax.set_xticks(
                valori_x
            )

            massimo = max(
                valori_y
            )

            spazio_testo = max(
                0.2,
                massimo * 0.02
            )

            for x, y in zip(
                valori_x,
                valori_y
            ):
                ax.text(
                    x,
                    y + spazio_testo,
                    str(y),
                    ha="center",
                    va="bottom",
                    fontsize=8
                )

            ax.set_ylim(
                0,
                massimo * 1.15 + 0.5
            )

            fig.tight_layout()

            canvas = FigureCanvasTkAgg(
                fig,
                master=frame
            )
            canvas.draw()

            canvas.get_tk_widget().pack(
                fill=X,
                padx=45,
                pady=(0, 6)
            )

        # ----------------------------------------------------
        # TABELLA
        # ----------------------------------------------------

        tabella_frame = ttk.Frame(
            frame
        )
        tabella_frame.pack(
            fill=BOTH,
            expand=YES,
            padx=10
        )

        tree = ttk.Treeview(
            tabella_frame,
            columns=(
                "documento",
                "token",
                "ingresso",
                "uscita",
                "prestiti",
                "tempo_documento",
                "media_partita",
                "stato"
            ),
            show="headings",
            height=8,
            bootstyle="info"
        )

        tree.heading(
            "documento",
            text=tr("DOC.")
        )
        tree.heading(
            "token",
            text=tr("TOKEN")
        )
        tree.heading(
            "ingresso",
            text=tr("INGRESSO")
        )
        tree.heading(
            "uscita",
            text=tr("USCITA")
        )
        tree.heading(
            "prestiti",
            text=tr("N. PRESTITI")
        )
        tree.heading(
            "tempo_documento",
            text=tr("TEMPO IN LUDOTECA")
        )
        tree.heading(
            "media_partita",
            text=tr("DURATA MEDIA PRESTITO")
        )
        tree.heading(
            "stato",
            text=tr("STATO")
        )

        tree.column(
            "documento",
            width=70,
            anchor=CENTER
        )
        tree.column(
            "token",
            width=75,
            anchor=CENTER
        )
        tree.column(
            "ingresso",
            width=165,
            anchor=CENTER
        )
        tree.column(
            "uscita",
            width=165,
            anchor=CENTER
        )
        tree.column(
            "prestiti",
            width=100,
            anchor=CENTER
        )
        tree.column(
            "tempo_documento",
            width=150,
            anchor=CENTER
        )
        tree.column(
            "media_partita",
            width=165,
            anchor=CENTER
        )
        tree.column(
            "stato",
            width=100,
            anchor=CENTER
        )

        scrollbar_y = ttk.Scrollbar(
            tabella_frame,
            orient=VERTICAL,
            command=tree.yview
        )

        scrollbar_x = ttk.Scrollbar(
            tabella_frame,
            orient=HORIZONTAL,
            command=tree.xview
        )

        tree.configure(
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set
        )

        tree.grid(
            row=0,
            column=0,
            sticky=NSEW
        )
        scrollbar_y.grid(
            row=0,
            column=1,
            sticky=NS
        )
        scrollbar_x.grid(
            row=1,
            column=0,
            sticky=EW
        )

        tabella_frame.rowconfigure(
            0,
            weight=1
        )
        tabella_frame.columnconfigure(
            0,
            weight=1
        )

        for row in righe_report:
            tree.insert(
                "",
                END,
                values=(
                    row["documento_id"],
                    row["token"],
                    row["ingresso"],
                    row["uscita"],
                    row["prestiti"],
                    row["tempo_documento"],
                    row["media_partita"],
                    row["stato"]
                )
            )

        # ----------------------------------------------------
        # ESPORTAZIONE CSV
        # ----------------------------------------------------

        def esporta_csv():
            if not righe_report:
                messagebox.showinfo(
                    tr("Nessun dato"),
                    tr("Non ci sono righe da esportare con i filtri attuali.")
                )
                return

            nome_file = (
                "ludox_report_documenti_"
                f"{inizio.strftime('%Y-%m-%d')}_"
                f"{data_fine.strftime('%Y-%m-%d')}.csv"
            )

            percorso = filedialog.asksaveasfilename(
                title=tr("Esporta report persone / documenti"),
                defaultextension=".csv",
                initialfile=nome_file,
                filetypes=[
                    ("CSV", "*.csv"),
                    (tr("common.all_files"), "*.*")
                ]
            )

            if not percorso:
                return

            intestazioni = [
                tr("people_report.csv_document"),
                tr("people_report.csv_token"),
                tr("people_report.csv_entry"),
                tr("people_report.csv_exit"),
                tr("people_report.csv_num_loans"),
                tr("people_report.csv_stay"),
                tr("people_report.csv_stay_minutes"),
                tr("people_report.csv_avg"),
                tr("people_report.csv_avg_minutes"),
                tr("people_report.csv_status")
            ]
            righe_csv = reporting.righe_csv_documenti(
                report,
                tr("common.in_progress"),
                tr("common.closed")
            )

            try:
                reporting.esporta_csv(percorso, intestazioni, righe_csv)

            except OSError as e:
                messagebox.showerror(
                    tr("Errore esportazione"),
                    tr(f"Impossibile salvare il file:\n\n{e}")
                )
                return

            messagebox.showinfo(
                tr("Esportazione completata"),
                tr("Il report CSV è stato salvato correttamente.")
            )

        azioni = ttk.Frame(
            frame
        )
        azioni.pack(
            pady=(10, 0)
        )

        ttk.Button(
            azioni,
            text=tr("ESPORTA CSV"),
            command=esporta_csv,
            bootstyle="success"
        ).pack(
            side=LEFT,
            padx=5,
            ipadx=18,
            ipady=7
        )

        ttk.Button(
            azioni,
            text=tr("TORNA AL BACKOFFICE"),
            command=self.show_backoffice,
            bootstyle="secondary-outline"
        ).pack(
            side=LEFT,
            padx=5,
            ipadx=12,
            ipady=7
        )

    # ========================================================
    # BACKOFFICE - REPORT UTILIZZO LUDOTECA
    # ========================================================

    def show_report_utilizzo_ludoteca(
        self,
        data_inizio=None,
        data_fine=None,
        proprietario_id=None,
        ordina_per="gioco",
        ordine_desc=False,
        escludi_tempo_zero=False
    ):
        """
        Report storico per titolo.

        Il proprietario NON viene attribuito al singolo prestito:
        serve esclusivamente come filtro sui titoli presenti nella ludoteca.

        Un titolo con più proprietari compare una sola volta e la colonna
        PROPRIETARI elenca tutti i proprietari che hanno copie del titolo.
        """
        frame = self.clear()

        self.pulsante_indietro(
            frame,
            self.show_backoffice
        )

        self.titolo_pagina(
            frame,
            "REPORT UTILIZZO LUDOTECA",
            "Prestiti e durata di utilizzo dei titoli presenti in ludoteca"
        )

        oggi = datetime.now().replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )

        if data_inizio is None:
            data_inizio = oggi

        if data_fine is None:
            data_fine = oggi

        # ----------------------------------------------------
        # FILTRI
        # ----------------------------------------------------

        filtri = ttk.Labelframe(
            frame,
            text=tr("Filtri"),
            padding=12,
            bootstyle="secondary"
        )
        filtri.pack(
            fill=X,
            padx=35,
            pady=(0, 10)
        )

        riga_filtri = ttk.Frame(
            filtri
        )
        riga_filtri.pack(
            fill=X
        )

        ttk.Label(
            riga_filtri,
            text=tr("Dal:"),
            font=("Arial", 11, "bold")
        ).pack(
            side=LEFT,
            padx=(0, 6)
        )

        try:
            data_da_picker = DateEntry(
                riga_filtri,
                date_format="%d/%m/%Y",
                first_weekday=0,
                start_date=data_inizio,
                bootstyle="primary",
                width=12
            )
        except TypeError:
            data_da_picker = DateEntry(
                riga_filtri,
                dateformat="%d/%m/%Y",
                firstweekday=0,
                startdate=data_inizio,
                bootstyle="primary",
                width=12
            )

        data_da_picker.pack(
            side=LEFT,
            padx=(0, 12)
        )

        ttk.Label(
            riga_filtri,
            text=tr("Al:"),
            font=("Arial", 11, "bold")
        ).pack(
            side=LEFT,
            padx=(0, 6)
        )

        try:
            data_a_picker = DateEntry(
                riga_filtri,
                date_format="%d/%m/%Y",
                first_weekday=0,
                start_date=data_fine,
                bootstyle="primary",
                width=12
            )
        except TypeError:
            data_a_picker = DateEntry(
                riga_filtri,
                dateformat="%d/%m/%Y",
                firstweekday=0,
                startdate=data_fine,
                bootstyle="primary",
                width=12
            )

        data_a_picker.pack(
            side=LEFT,
            padx=(0, 18)
        )

        proprietari = elenco_proprietari()
        proprietari_by_name = {
            row["nome"]: row["id"]
            for row in proprietari
        }

        proprietario_var = tk.StringVar(
            value=tr("common.all")
        )

        if proprietario_id is not None:
            proprietario = proprietario_per_id(
                proprietario_id
            )
            if proprietario:
                proprietario_var.set(
                    proprietario["nome"]
                )

        ttk.Label(
            riga_filtri,
            text=tr("Proprietario:"),
            font=("Arial", 11, "bold")
        ).pack(
            side=LEFT,
            padx=(0, 6)
        )

        combo_proprietario = ttk.Combobox(
            riga_filtri,
            textvariable=proprietario_var,
            values=[
                tr("common.all"),
                *list(proprietari_by_name.keys())
            ],
            state="readonly",
            width=25
        )
        combo_proprietario.pack(
            side=LEFT,
            padx=(0, 12),
            ipady=2
        )

        def leggi_filtri():
            try:
                da = datetime.strptime(
                    data_da_picker.entry.get().strip(),
                    "%d/%m/%Y"
                ).replace(
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0
                )

                a = datetime.strptime(
                    data_a_picker.entry.get().strip(),
                    "%d/%m/%Y"
                ).replace(
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0
                )

            except (ValueError, AttributeError):
                messagebox.showwarning(
                    tr("Date non valide"),
                    tr("Seleziona due date valide nel formato GG/MM/AAAA.")
                )
                return None

            if a < da:
                messagebox.showwarning(
                    tr("Intervallo non valido"),
                    tr("La data finale non può precedere la data iniziale.")
                )
                return None

            nome_proprietario = proprietario_var.get()

            if (
                nome_proprietario
                and nome_proprietario != tr("common.all")
            ):
                pid = proprietari_by_name.get(
                    nome_proprietario
                )
            else:
                pid = None

            return da, a, pid

        def applica():
            parametri = leggi_filtri()

            if parametri is None:
                return

            da, a, pid = parametri

            self.show_report_utilizzo_ludoteca(
                data_inizio=da,
                data_fine=a,
                proprietario_id=pid
            )

        ttk.Button(
            riga_filtri,
            text=tr("APPLICA"),
            command=applica,
            bootstyle="primary"
        ).pack(
            side=LEFT,
            padx=3
        )

        # ----------------------------------------------------
        # ORDINAMENTO E FILTRI AGGIUNTIVI
        # ----------------------------------------------------

        riga_opzioni = ttk.Frame(
            filtri
        )
        riga_opzioni.pack(
            fill=X,
            pady=(10, 0)
        )

        ttk.Label(
            riga_opzioni,
            text=tr("Ordina per:"),
            font=("Arial", 11, "bold")
        ).pack(
            side=LEFT,
            padx=(0, 6)
        )

        mapping_ordinamento = {
            tr("usage.sort_game"): "gioco",
            tr("usage.sort_loans"): "prestiti",
            tr("usage.sort_total"): "tempo_totale_secondi",
            tr("usage.sort_avg"): "media_secondi"
        }

        mapping_ordinamento_inverso = {
            valore: chiave
            for chiave, valore in mapping_ordinamento.items()
        }

        ordina_var = tk.StringVar(
            value=mapping_ordinamento_inverso.get(
                ordina_per,
                tr("usage.sort_game")
            )
        )

        combo_ordina = ttk.Combobox(
            riga_opzioni,
            textvariable=ordina_var,
            values=list(mapping_ordinamento.keys()),
            state="readonly",
            width=22
        )
        combo_ordina.pack(
            side=LEFT,
            padx=(0, 12),
            ipady=2
        )

        ttk.Label(
            riga_opzioni,
            text=tr("Ordine:"),
            font=("Arial", 11, "bold")
        ).pack(
            side=LEFT,
            padx=(0, 6)
        )

        ordine_var = tk.StringVar(
            value=(
                tr("common.descending")
                if ordine_desc
                else tr("common.ascending")
            )
        )

        combo_ordine = ttk.Combobox(
            riga_opzioni,
            textvariable=ordine_var,
            values=[
                tr("common.ascending"),
                tr("common.descending")
            ],
            state="readonly",
            width=13
        )
        combo_ordine.pack(
            side=LEFT,
            padx=(0, 18),
            ipady=2
        )

        escludi_zero_var = tk.BooleanVar(
            value=escludi_tempo_zero
        )

        ttk.Checkbutton(
            riga_opzioni,
            text=tr("Escludi giochi con tempo totale fuori = 0"),
            variable=escludi_zero_var,
            bootstyle="success-round-toggle"
        ).pack(
            side=LEFT,
            padx=(0, 12)
        )

        # Ridefiniamo applica dopo aver creato anche i controlli
        # di ordinamento, mantenendo gli stessi filtri data/proprietario.
        def applica():
            parametri = leggi_filtri()

            if parametri is None:
                return

            da, a, pid = parametri

            criterio = mapping_ordinamento.get(
                ordina_var.get(),
                "gioco"
            )

            self.show_report_utilizzo_ludoteca(
                data_inizio=da,
                data_fine=a,
                proprietario_id=pid,
                ordina_per=criterio,
                ordine_desc=(
                    ordine_var.get()
                    == "Decrescente"
                ),
                escludi_tempo_zero=escludi_zero_var.get()
            )

        # Ricolleghiamo il pulsante APPLICA alla nuova funzione.
        # Cerchiamo il bottone appena creato nella riga dei filtri.
        for widget in riga_filtri.winfo_children():
            try:
                if widget.cget("text") == tr("common.apply"):
                    widget.configure(
                        command=applica
                    )
                    break
            except tk.TclError:
                pass

        combo_ordina.bind(
            "<<ComboboxSelected>>",
            lambda event: applica()
        )

        combo_ordine.bind(
            "<<ComboboxSelected>>",
            lambda event: applica()
        )

        # ----------------------------------------------------
        # COSTRUZIONE DATI REPORT
        # ----------------------------------------------------

        report = reporting.report_utilizzo(
            data_inizio,
            data_fine,
            proprietario_id=proprietario_id,
            escludi_tempo_zero=escludi_tempo_zero,
            ordina_per=ordina_per,
            ordine_desc=ordine_desc
        )
        inizio = report.inizio
        righe_report = report.righe
        formatta_durata = reporting.formatta_durata

        proprietario_testo = (
            tr("common.all")
            if proprietario_id is None
            else proprietario_per_id(
                proprietario_id
            )["nome"]
        )

        criterio_testo = {
            "gioco": tr("usage.sort_game"),
            "prestiti": tr("usage.sort_loans"),
            "tempo_totale_secondi": tr("usage.sort_total"),
            "media_secondi": tr("usage.sort_avg")
        }.get(
            ordina_per,
            tr("usage.sort_game")
        )

        totale_titoli = report.totale_titoli
        totale_prestiti = report.totale_prestiti
        prestiti_per_titolo = report.prestiti_per_titolo
        media_prestiti_titolo = report.media_prestiti_titolo
        mediana_prestiti_titolo = report.mediana_prestiti_titolo
        dev_std_prestiti_titolo = report.dev_std_prestiti_titolo
        titoli_utilizzati = report.titoli_utilizzati
        percentuale_titoli_utilizzati = report.percentuale_titoli_utilizzati
        durata_mediana_prestito_secondi = report.durata_mediana_prestito_secondi
        tempo_totale_fuori_secondi = report.tempo_totale_fuori_secondi

        ttk.Label(
            frame,
            text=(
                tr(f"Periodo: {inizio.strftime('%d/%m/%Y')} → "
                f"{data_fine.strftime('%d/%m/%Y')}  •  "
                f"Proprietario: {proprietario_testo}  •  "
                f"Titoli visualizzati: {totale_titoli}  •  "
                f"Ordine: {criterio_testo} "
                f"({'↓' if ordine_desc else '↑'})"
                + (
                    "  •  Tempo zero escluso"
                    if escludi_tempo_zero
                    else ""
                ))
            ),
            font=("Arial", 11, "bold"),
            bootstyle="secondary"
        ).pack(
            pady=(0, 6)
        )

        kpi = ttk.Frame(
            frame
        )
        kpi.pack(
            fill=X,
            padx=25,
            pady=(0, 7)
        )

        for col in range(6):
            kpi.columnconfigure(
                col,
                weight=1
            )

        kpi_valori = [
            (
                str(totale_prestiti),
                "PRESTITI TOTALI"
            ),
            (
                f"{media_prestiti_titolo:.2f}",
                "MEDIA PRESTITI / TITOLO"
            ),
            (
                f"{mediana_prestiti_titolo:g}",
                "MEDIANA PRESTITI / TITOLO"
            ),
            (
                f"{dev_std_prestiti_titolo:.2f}",
                "DEV. STD PRESTITI / TITOLO"
            ),
            (
                f"{percentuale_titoli_utilizzati:.1f}%",
                "TITOLI UTILIZZATI"
            ),
            (
                formatta_durata(
                    durata_mediana_prestito_secondi
                ),
                "DURATA MEDIANA PRESTITO"
            )
        ]

        for indice, (
            valore,
            etichetta
        ) in enumerate(kpi_valori):
            box = ttk.Frame(
                kpi,
                padding=5
            )
            box.grid(
                row=0,
                column=indice,
                padx=4,
                sticky=NSEW
            )

            ttk.Label(
                box,
                text=tr(valore),
                font=("Arial", 15, "bold"),
                bootstyle="primary"
            ).pack()

            ttk.Label(
                box,
                text=tr(etichetta),
                font=("Arial", 8, "bold"),
                bootstyle="secondary",
                justify=CENTER,
                wraplength=145
            ).pack()

        ttk.Label(
            frame,
            text=(
                tr(f"Titoli utilizzati: {titoli_utilizzati}/{totale_titoli}.  "
                f"Tempo totale fuori: {formatta_durata(tempo_totale_fuori_secondi)}.  "
                "Il filtro Proprietario seleziona i titoli associati a quel proprietario; "
                "le statistiche dei prestiti restano riferite al titolo nel suo complesso. "
                "Le durate considerano soltanto i prestiti conclusi.")
            ),
            font=("Arial", 9),
            bootstyle="secondary",
            wraplength=1050,
            justify=CENTER
        ).pack(
            pady=(0, 4)
        )

        # ----------------------------------------------------
        # GRAFICO DELLE OCCORRENZE: PRESTITI PER TITOLO
        # ----------------------------------------------------

        distribuzione = {}

        for valore in prestiti_per_titolo:
            distribuzione[valore] = (
                distribuzione.get(
                    valore,
                    0
                )
                + 1
            )

        if distribuzione:
            valori_x = sorted(
                distribuzione
            )

            valori_y = [
                distribuzione[x]
                for x in valori_x
            ]

            fig = Figure(
                figsize=(9, 2.15),
                dpi=100
            )

            ax = fig.add_subplot(111)

            ax.bar(
                valori_x,
                valori_y
            )

            ax.set_title(
                tr("Distribuzione del numero di prestiti per titolo"),
                fontsize=10
            )
            ax.set_xlabel(
                tr("Numero di prestiti")
            )
            ax.set_ylabel(
                tr("Titoli")
            )
            ax.grid(
                True,
                axis="y",
                alpha=0.2
            )

            ax.set_xticks(
                valori_x
            )

            massimo = max(
                valori_y
            )

            spazio_testo = max(
                0.2,
                massimo * 0.02
            )

            for x, y in zip(
                valori_x,
                valori_y
            ):
                ax.text(
                    x,
                    y + spazio_testo,
                    str(y),
                    ha="center",
                    va="bottom",
                    fontsize=8
                )

            ax.set_ylim(
                0,
                massimo * 1.15 + 0.5
            )

            fig.tight_layout()

            canvas = FigureCanvasTkAgg(
                fig,
                master=frame
            )
            canvas.draw()

            canvas.get_tk_widget().pack(
                fill=X,
                padx=45,
                pady=(0, 6)
            )

        # ----------------------------------------------------
        # TABELLA
        # ----------------------------------------------------

        tabella_frame = ttk.Frame(
            frame
        )
        tabella_frame.pack(
            fill=BOTH,
            expand=YES,
            padx=10
        )

        tree = ttk.Treeview(
            tabella_frame,
            columns=(
                "gioco",
                "proprietari",
                "copie",
                "prestiti",
                "tempo_totale",
                "media",
                "deviazione"
            ),
            show="headings",
            height=8,
            bootstyle="primary"
        )

        tree.heading(
            "gioco",
            text=tr("GIOCO")
        )
        tree.heading(
            "proprietari",
            text=tr("PROPRIETARI")
        )
        tree.heading(
            "copie",
            text=tr("COPIE")
        )
        tree.heading(
            "prestiti",
            text=tr("PRESTITI")
        )
        tree.heading(
            "tempo_totale",
            text=tr("TEMPO TOTALE FUORI")
        )
        tree.heading(
            "media",
            text=tr("DURATA MEDIA")
        )
        tree.heading(
            "deviazione",
            text=tr("DEV. STANDARD")
        )

        tree.column(
            "gioco",
            width=260
        )
        tree.column(
            "proprietari",
            width=330
        )
        tree.column(
            "copie",
            width=75,
            anchor=CENTER
        )
        tree.column(
            "prestiti",
            width=85,
            anchor=CENTER
        )
        tree.column(
            "tempo_totale",
            width=145,
            anchor=CENTER
        )
        tree.column(
            "media",
            width=125,
            anchor=CENTER
        )
        tree.column(
            "deviazione",
            width=125,
            anchor=CENTER
        )

        scrollbar_y = ttk.Scrollbar(
            tabella_frame,
            orient=VERTICAL,
            command=tree.yview
        )

        scrollbar_x = ttk.Scrollbar(
            tabella_frame,
            orient=HORIZONTAL,
            command=tree.xview
        )

        tree.configure(
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set
        )

        tree.grid(
            row=0,
            column=0,
            sticky=NSEW
        )
        scrollbar_y.grid(
            row=0,
            column=1,
            sticky=NS
        )
        scrollbar_x.grid(
            row=1,
            column=0,
            sticky=EW
        )

        tabella_frame.rowconfigure(
            0,
            weight=1
        )
        tabella_frame.columnconfigure(
            0,
            weight=1
        )

        for row in righe_report:
            tree.insert(
                "",
                END,
                values=(
                    row["gioco"],
                    row["proprietari"],
                    row["copie_totali"],
                    row["prestiti"],
                    row["tempo_totale"],
                    row["media"],
                    row["deviazione"]
                )
            )

        # ----------------------------------------------------
        # ESPORTAZIONE CSV
        # ----------------------------------------------------

        def esporta_csv():
            if not righe_report:
                messagebox.showinfo(
                    tr("Nessun dato"),
                    tr("Non ci sono righe da esportare con i filtri attuali.")
                )
                return

            nome_file = (
                "ludox_report_utilizzo_"
                f"{inizio.strftime('%Y-%m-%d')}_"
                f"{data_fine.strftime('%Y-%m-%d')}.csv"
            )

            percorso = filedialog.asksaveasfilename(
                title=tr("Esporta report utilizzo ludoteca"),
                defaultextension=".csv",
                initialfile=nome_file,
                filetypes=[
                    ("CSV", "*.csv"),
                    (tr("common.all_files"), "*.*")
                ]
            )

            if not percorso:
                return

            intestazioni = [
                tr("usage.sort_game"),
                tr("usage.csv_owners"),
                tr("usage.csv_total_copies"),
                tr("usage.csv_loans"),
                tr("usage.csv_total_time"),
                tr("usage.csv_total_minutes"),
                tr("usage.csv_avg"),
                tr("usage.csv_avg_minutes"),
                tr("usage.csv_std"),
                tr("usage.csv_std_minutes")
            ]
            righe_csv = reporting.righe_csv_utilizzo(report)

            try:
                reporting.esporta_csv(percorso, intestazioni, righe_csv)

            except OSError as e:
                messagebox.showerror(
                    tr("Errore esportazione"),
                    tr(f"Impossibile salvare il file:\n\n{e}")
                )
                return

            messagebox.showinfo(
                tr("Esportazione completata"),
                tr("Il report CSV è stato salvato correttamente.")
            )

        azioni = ttk.Frame(
            frame
        )
        azioni.pack(
            pady=(10, 0)
        )

        ttk.Button(
            azioni,
            text=tr("ESPORTA CSV"),
            command=esporta_csv,
            bootstyle="success"
        ).pack(
            side=LEFT,
            padx=5,
            ipadx=18,
            ipady=7
        )

        ttk.Button(
            azioni,
            text=tr("TORNA AL BACKOFFICE"),
            command=self.show_backoffice,
            bootstyle="secondary-outline"
        ).pack(
            side=LEFT,
            padx=5,
            ipadx=12,
            ipady=7
        )

        combo_proprietario.bind(
            "<<ComboboxSelected>>",
            lambda event: applica()
        )

        escludi_zero_var.trace_add(
            "write",
            lambda *args: applica()
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

        proprietari = catalog.elenco_proprietari()
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
            text=tr("Proprietario:"),
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
            value=tr("owner_games.select")
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

        tree.heading("gioco", text=tr("GIOCO"))
        tree.heading(
            "copie_proprietario",
            text=tr("COPIE PROPRIETARIO")
        )
        tree.heading(
            "copie_totali",
            text=tr("COPIE TOTALI")
        )
        tree.heading(
            "prestiti_attivi_titolo",
            text=tr("PRESTITI ATTIVI TITOLO")
        )
        tree.heading(
            "gioco_attivo",
            text=tr("ATTIVO")
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
                tr("Nota: i prestiti sono registrati per titolo e non per singola copia; "
                "quindi i prestiti attivi mostrati non sono attribuiti a uno specifico proprietario.")
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
                    tr("owner_games.select")
                )
                return

            proprietario_id = proprietari_by_name[nome]

            inventario = catalog.inventario_proprietario(proprietario_id)
            righe = inventario.righe
            totale_titoli = inventario.totale_titoli
            totale_copie = inventario.totale_copie

            riepilogo_var.set(
                tr(f"{nome}  •  Titoli: {totale_titoli}  •  Copie: {totale_copie}")
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
                        tr("common.yes") if row["gioco_attivo"] else tr("common.no")
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
            text=tr("＋ AGGIUNGI PROPRIETARIO"),
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

        tree.heading("nome", text=tr("PROPRIETARIO"))
        tree.heading("copie", text=tr("COPIE TOTALI"))
        tree.heading("attivo", text=tr("ATTIVO"))

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

        for proprietario in catalog.elenco_proprietari():
            tree.insert(
                "",
                END,
                iid=str(proprietario["id"]),
                values=(
                    proprietario["nome"],
                    catalog.totale_copie_proprietario(
                        proprietario["id"]
                    ),
                    tr("common.yes") if proprietario["attivo"] else tr("common.no")
                )
            )

        def modifica():
            selezione = tree.selection()

            if not selezione:
                messagebox.showwarning(
                    tr("Seleziona un proprietario"),
                    tr("Seleziona prima un proprietario.")
                )
                return

            self.show_modifica_proprietario(
                int(selezione[0])
            )

        ttk.Button(
            frame,
            text=tr("MODIFICA PROPRIETARIO SELEZIONATO"),
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
            text=tr("Nome proprietario"),
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
            try:
                catalog.aggiungi_proprietario(nome_var.get())
            except catalog.NomeMancante:
                messagebox.showwarning(
                    tr("Nome mancante"),
                    tr("Inserisci il nome del proprietario.")
                )
                return

            except catalog.NomeDuplicato:
                messagebox.showerror(
                    tr("Proprietario già presente"),
                    tr("Esiste già un proprietario con questo nome.")
                )
                return

            self.show_gestione_proprietari()

        ttk.Button(
            card,
            text=tr("SALVA PROPRIETARIO"),
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
        proprietario = catalog.proprietario_per_id(
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
            text=tr("Nome proprietario"),
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
                tr(f"Copie associate: "
                f"{catalog.totale_copie_proprietario(proprietario_id)}")
            ),
            font=("Arial", 12),
            bootstyle="secondary"
        ).pack(
            anchor=W,
            pady=(0, 15)
        )

        ttk.Checkbutton(
            card,
            text=tr("Proprietario attivo"),
            variable=attivo_var,
            bootstyle="success-round-toggle"
        ).pack(
            anchor=W,
            pady=10
        )

        def salva():
            nome = nome_var.get()
            attivo = attivo_var.get()
            try:
                try:
                    catalog.modifica_proprietario(proprietario_id, nome, attivo)
                except catalog.ConfermaDisattivazione:
                    conferma = messagebox.askyesno(
                        tr("Proprietario con copie associate"),
                        tr("Questo proprietario ha ancora copie "
                        "associate ai giochi.\n\n"
                        "Vuoi comunque disattivarlo?")
                    )
                    if not conferma:
                        return
                    catalog.modifica_proprietario(
                        proprietario_id, nome, attivo_var.get(),
                        conferma_disattivazione=True,
                    )
            except catalog.NomeMancante:
                messagebox.showwarning(
                    tr("Nome mancante"),
                    tr("Inserisci il nome del proprietario.")
                )
                return
            except catalog.NomeDuplicato:
                messagebox.showerror(
                    tr("Nome duplicato"),
                    tr("Esiste già un proprietario con questo nome.")
                )
                return

            self.show_gestione_proprietari()

        ttk.Button(
            card,
            text=tr("SALVA MODIFICHE"),
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
            text=tr("＋ AGGIUNGI GIOCO"),
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

        tree.heading("nome", text=tr("GIOCO"))
        tree.heading("proprietari", text=tr("PROPRIETARI / COPIE"))
        tree.heading("copie", text=tr("COPIE"))
        tree.heading("fuori", text=tr("FUORI"))
        tree.heading("attivo", text=tr("ATTIVO"))

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

        for gioco in catalog.elenco_giochi_backoffice():
            tree.insert(
                "",
                END,
                iid=str(gioco["id"]),
                values=(
                    gioco["nome"],
                    catalog.riepilogo_proprietari_gioco(
                        gioco["id"]
                    ),
                    gioco["copie_totali"],
                    catalog.copie_in_prestito(
                        gioco["id"]
                    ),
                    tr("common.yes") if gioco["attivo"] else tr("common.no")
                )
            )

        def modifica():
            selezione = tree.selection()

            if not selezione:
                messagebox.showwarning(
                    tr("Seleziona un gioco"),
                    tr("Seleziona prima un gioco.")
                )
                return

            self.show_modifica_gioco(
                int(selezione[0])
            )

        ttk.Button(
            frame,
            text=tr("MODIFICA GIOCO SELEZIONATO"),
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
            text=tr("Nome gioco"),
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
            try:
                gioco_id = catalog.aggiungi_gioco(nome_var.get())
            except catalog.NomeMancante:
                messagebox.showwarning(
                    tr("Nome mancante"),
                    tr("Inserisci il nome del gioco.")
                )
                return

            except catalog.NomeDuplicato:
                messagebox.showerror(
                    tr("Gioco già presente"),
                    tr("Esiste già un gioco con questo nome.")
                )
                return

            self.show_modifica_gioco(
                gioco_id
            )

        ttk.Button(
            card,
            text=tr("SALVA E ASSEGNA COPIE"),
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
        gioco = catalog.gioco_per_id(
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
            text=tr("Nome gioco"),
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
            text=tr("Gioco attivo"),
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
            text=tr("COPIE PER PROPRIETARIO"),
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
            text=tr("PROPRIETARIO")
        )
        tree.heading(
            "quantita",
            text=tr("COPIE")
        )
        tree.heading(
            "stato",
            text=tr("STATO")
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

            righe = catalog.copie_per_proprietario_del_gioco(
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
                        tr("common.active")
                        if row["proprietario_attivo"]
                        else tr("common.inactive")
                    )
                )

        aggiorna_lista()

        # ----------------------------------------------------
        # MODIFICA QUANTITÀ
        # ----------------------------------------------------

        modifica_box = ttk.Labelframe(
            frame,
            text=tr("Modifica quantità"),
            padding=15,
            bootstyle="secondary"
        )
        modifica_box.pack(
            fill=X,
            padx=70,
            pady=15
        )

        selezionato_var = tk.StringVar(
            value=tr("games.no_owner_selected")
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
            try:
                catalog.imposta_quantita(gioco_id, proprietario_id, quantita_var.get())
            except catalog.ProprietarioNonSelezionato:
                messagebox.showwarning(
                    tr("Seleziona un proprietario"),
                    tr("Seleziona prima un proprietario nella tabella.")
                )
                return
            except catalog.QuantitaNonValida:
                messagebox.showwarning(
                    tr("Quantità non valida"),
                    tr("Inserisci un numero intero maggiore o uguale a zero.")
                )
                return
            except catalog.CopieInsufficienti as e:
                messagebox.showwarning(
                    tr("Copie insufficienti"),
                    tr(str(e))
                )
                return

            aggiorna_lista()

        ttk.Button(
            modifica_box,
            text=tr("SALVA QUANTITÀ"),
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
            try:
                catalog.modifica_gioco(gioco_id, nome_var.get(), attivo_var.get())
            except catalog.NomeMancante:
                messagebox.showwarning(
                    tr("Nome mancante"),
                    tr("Inserisci il nome del gioco.")
                )
                return
            except catalog.GiocoInPrestito:
                messagebox.showwarning(
                    tr("Gioco in prestito"),
                    tr("Non puoi disattivare un gioco "
                    "mentre ci sono copie in prestito.")
                )
                return
            except catalog.NomeDuplicato:
                messagebox.showerror(
                    tr("Nome duplicato"),
                    tr("Esiste già un gioco con questo nome.")
                )
                return

            self.show_gestione_giochi()

        fondo = ttk.Frame(frame)
        fondo.pack(
            pady=(5, 0)
        )

        ttk.Button(
            fondo,
            text=tr("SALVA GIOCO"),
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
            text=tr("TORNA ALL'ELENCO"),
            command=self.show_gestione_giochi,
            bootstyle="secondary-outline"
        ).pack(
            side=LEFT,
            padx=5,
            ipadx=20,
            ipady=8
        )

    # ========================================================
    # BACKOFFICE - IMPOSTAZIONI
    # ========================================================

    def show_impostazioni(self):
        frame = self.clear()

        self.pulsante_indietro(
            frame,
            self.show_backoffice
        )

        self.titolo_pagina(
            frame,
            tr("settings.title"),
            tr("settings.subtitle")
        )

        panel = ttk.Labelframe(
            frame,
            text=tr("settings.title"),
            padding=24,
            bootstyle="secondary"
        )
        panel.pack(
            fill=X,
            padx=120,
            pady=(10, 20)
        )

        ttk.Label(
            panel,
            text=tr("settings.language"),
            font=("Arial", 12, "bold")
        ).pack(anchor=W, pady=(0, 5))

        language_names = language_display_names()
        display_to_code = {
            display: code
            for code, display in language_names.items()
        }
        language_var = tk.StringVar(
            value=language_names.get(
                self.config.language,
                language_names["it"]
            )
        )

        ttk.Combobox(
            panel,
            textvariable=language_var,
            values=list(display_to_code.keys()),
            state="readonly",
            width=28
        ).pack(anchor=W, pady=(0, 18), ipady=3)

        ttk.Label(
            panel,
            text=tr("settings.tokens"),
            font=("Arial", 12, "bold")
        ).pack(anchor=W, pady=(0, 5))

        tokens_var = tk.StringVar(
            value=str(self.config.max_tokens)
        )
        tokens_entry = ttk.Entry(
            panel,
            textvariable=tokens_var,
            width=14
        )
        tokens_entry.pack(anchor=W, pady=(0, 4), ipady=3)

        ttk.Label(
            panel,
            text=tr("settings.tokens_help"),
            bootstyle="secondary"
        ).pack(anchor=W, pady=(0, 18))

        ttk.Label(
            panel,
            text=tr("settings.database"),
            font=("Arial", 12, "bold")
        ).pack(anchor=W, pady=(0, 5))

        database_var = tk.StringVar(value=self.config.database)
        database_row = ttk.Frame(panel)
        database_row.pack(fill=X, pady=(0, 8))

        ttk.Entry(
            database_row,
            textvariable=database_var
        ).pack(side=LEFT, fill=X, expand=YES, ipady=3)

        def scegli_nuovo_database():
            selected = filedialog.asksaveasfilename(
                parent=self,
                title=tr("settings.database_new_title"),
                initialdir=str(PROJECT_DIR),
                initialfile=Path(
                    database_var.get().strip() or "ludox.db"
                ).name,
                defaultextension=".db",
                filetypes=[
                    (tr("settings.sqlite_files"), "*.db *.sqlite *.sqlite3"),
                    (tr("settings.all_files"), "*.*"),
                ],
            )
            if selected:
                database_var.set(database_setting_from_path(selected))

        def scegli_database_esistente():
            selected = filedialog.askopenfilename(
                parent=self,
                title=tr("settings.database_open_title"),
                initialdir=str(PROJECT_DIR),
                filetypes=[
                    (tr("settings.sqlite_files"), "*.db *.sqlite *.sqlite3"),
                    (tr("settings.all_files"), "*.*"),
                ],
            )
            if selected:
                database_var.set(database_setting_from_path(selected))

        database_buttons = ttk.Frame(panel)
        database_buttons.pack(fill=X, pady=(0, 4))

        ttk.Button(
            database_buttons,
            text=tr("settings.database_new"),
            command=scegli_nuovo_database,
            bootstyle="secondary-outline"
        ).pack(side=LEFT, padx=(0, 8))

        ttk.Button(
            database_buttons,
            text=tr("settings.database_open"),
            command=scegli_database_esistente,
            bootstyle="secondary-outline"
        ).pack(side=LEFT)

        ttk.Label(
            panel,
            text=tr("settings.database_help"),
            bootstyle="secondary",
            wraplength=720,
            justify=LEFT
        ).pack(anchor=W, pady=(0, 20))

        def salva():
            try:
                max_tokens = int(tokens_var.get().strip())
            except ValueError:
                max_tokens = 0

            if max_tokens <= 0:
                messagebox.showwarning(
                    tr("settings.invalid_tokens"),
                    tr("settings.invalid_tokens_msg")
                )
                return

            try:
                database = normalize_database_setting(database_var.get())
                target_path = resolve_database_path(database)
            except (OSError, ValueError) as exc:
                messagebox.showwarning(
                    tr("settings.invalid_database"),
                    tr("settings.invalid_database_msg_tpl", error=str(exc))
                )
                return

            current_path = get_db_path().resolve(strict=False)
            database_changed = target_path != current_path

            # Avoid abandoning an event database while documents are still
            # physically deposited in it.
            if database_changed and conta_documenti_attivi() > 0:
                messagebox.showwarning(
                    tr("settings.database_busy"),
                    tr("settings.database_busy_msg")
                )
                return

            if not database_changed:
                highest_open = massimo_token_aperto()
                if highest_open > max_tokens:
                    messagebox.showwarning(
                        tr("settings.invalid_tokens"),
                        tr(
                            "settings.active_token_limit_tpl",
                            token=highest_open
                        )
                    )
                    return

            language = display_to_code.get(
                language_var.get(),
                "it"
            )

            old_path = current_path
            switched = False
            if database_changed:
                try:
                    set_db_path(target_path)
                    switched = True
                    init_db(default_owner_name=tr("owner.default"))
                    highest_open = massimo_token_aperto()
                    if highest_open > max_tokens:
                        set_db_path(old_path)
                        switched = False
                        messagebox.showwarning(
                            tr("settings.invalid_tokens"),
                            tr(
                                "settings.target_active_token_limit_tpl",
                                token=highest_open
                            )
                        )
                        return
                except (sqlite3.Error, OSError, ValueError) as exc:
                    set_db_path(old_path)
                    switched = False
                    messagebox.showwarning(
                        tr("settings.invalid_database"),
                        tr("settings.database_switch_failed_tpl", error=str(exc))
                    )
                    return

            candidate = AppConfig(
                language=language,
                max_tokens=max_tokens,
                database=database
            )

            try:
                save_config(candidate)
            except (OSError, ValueError) as exc:
                if switched:
                    set_db_path(old_path)
                messagebox.showwarning(
                    tr("settings.save_failed"),
                    tr("settings.save_failed_tpl", error=str(exc))
                )
                return

            self.config = candidate
            set_language(language)
            self.title(tr("app.title"))

            messagebox.showinfo(
                tr("settings.saved"),
                tr(
                    "settings.saved_database_msg"
                    if database_changed
                    else "settings.saved_msg"
                )
            )
            self.show_backoffice()

        ttk.Button(
            panel,
            text=tr("settings.save"),
            command=salva,
            bootstyle="success"
        ).pack(anchor=E, ipadx=24, ipady=8)

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
                tr("Prestiti ancora aperti"),
                tr(f"Ci sono ancora {attivi} "
                f"documenti depositati.\n\n"
                f"Token: {token_str}\n\n"
                "Vuoi davvero chiudere il programma?")
            )

            if not conferma:
                return

        self.destroy()
