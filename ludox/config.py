from __future__ import annotations

import configparser
import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_DIR / "config.ini"
DEFAULT_LANGUAGE = "it"
DEFAULT_MAX_TOKENS = 50
DEFAULT_DATABASE = "ludox.db"
SUPPORTED_LANGUAGES = ("it", "en")


@dataclass
class AppConfig:
    language: str = DEFAULT_LANGUAGE
    max_tokens: int = DEFAULT_MAX_TOKENS
    database: str = DEFAULT_DATABASE


def resolve_database_path(database: str) -> Path:
    """Resolve a configured DB filename/path.

    Relative paths are relative to the LudoX project/application directory.
    Absolute paths are kept absolute. Environment variables and ~ are expanded.
    """
    raw = os.path.expandvars(str(database).strip())
    if not raw:
        raise ValueError("Database path cannot be empty")

    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = PROJECT_DIR / path
    return path.resolve(strict=False)


def database_setting_from_path(path: str | Path) -> str:
    """Store project-local DBs as relative paths, external DBs as absolute paths."""
    resolved = resolve_database_path(str(path))
    project = PROJECT_DIR.resolve(strict=False)
    try:
        return str(resolved.relative_to(project))
    except ValueError:
        return str(resolved)


def normalize_database_setting(value: str) -> str:
    """Validate and normalize a DB setting without creating the database."""
    raw = str(value).strip()
    if not raw:
        raise ValueError("Database path cannot be empty")

    path = Path(os.path.expandvars(raw)).expanduser()
    # A simple name such as "AMIGO2026" becomes "AMIGO2026.db".
    if not path.suffix:
        path = path.with_suffix(".db")

    resolved = resolve_database_path(str(path))
    if resolved.exists() and resolved.is_dir():
        raise ValueError("The selected database path is a directory")
    if not resolved.parent.exists():
        raise ValueError("The selected database folder does not exist")

    return database_setting_from_path(resolved)


def validate_config(config: AppConfig) -> bool:
    if not (
        config.language in SUPPORTED_LANGUAGES
        and isinstance(config.max_tokens, int)
        and config.max_tokens > 0
        and isinstance(config.database, str)
        and bool(config.database.strip())
    ):
        return False

    try:
        normalize_database_setting(config.database)
    except (OSError, ValueError):
        return False
    return True


def load_config(path: Path = CONFIG_PATH) -> AppConfig | None:
    if not path.exists():
        return None

    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read(path, encoding="utf-8")
        language = parser.get(
            "general", "language", fallback=DEFAULT_LANGUAGE
        ).strip().lower()
        max_tokens = parser.getint(
            "general", "max_tokens", fallback=DEFAULT_MAX_TOKENS
        )
        database = parser.get(
            "general", "database", fallback=DEFAULT_DATABASE
        ).strip()
        database = normalize_database_setting(database)
    except (configparser.Error, OSError, ValueError):
        return None

    result = AppConfig(
        language=language,
        max_tokens=max_tokens,
        database=database,
    )
    return result if validate_config(result) else None


def save_config(config: AppConfig, path: Path = CONFIG_PATH) -> None:
    database = normalize_database_setting(config.database)
    normalized = AppConfig(
        language=config.language,
        max_tokens=config.max_tokens,
        database=database,
    )
    if not validate_config(normalized):
        raise ValueError("Invalid LudoX configuration")

    parser = configparser.ConfigParser(interpolation=None)
    parser["general"] = {
        "language": normalized.language,
        "max_tokens": str(normalized.max_tokens),
        "database": normalized.database,
    }
    with path.open("w", encoding="utf-8") as handle:
        parser.write(handle)


def _first_run_dialog(initial: AppConfig | None = None) -> AppConfig | None:
    import tkinter as tk
    from tkinter import filedialog, messagebox
    import ttkbootstrap as ttk

    initial = initial or AppConfig()
    result: AppConfig | None = None

    root = ttk.Window(
        title="LudoX — Configurazione iniziale / Initial setup",
        themename="flatly",
    )
    root.geometry("760x610")
    root.minsize(720, 580)
    root.resizable(True, False)
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    frame = ttk.Frame(root, padding=28)
    frame.grid(row=0, column=0, sticky="nsew")
    frame.columnconfigure(0, weight=1)

    ttk.Label(
        frame,
        text="LudoX",
        font=("Arial", 26, "bold"),
        bootstyle="primary",
    ).grid(row=0, column=0, sticky="w")

    ttk.Label(
        frame,
        text="Configurazione iniziale / Initial setup",
        font=("Arial", 14, "bold"),
    ).grid(row=1, column=0, sticky="w", pady=(2, 24))

    form = ttk.Frame(frame)
    form.grid(row=2, column=0, sticky="ew")
    form.columnconfigure(0, weight=1)

    ttk.Label(
        form,
        text="Lingua / Language",
        font=("Arial", 11, "bold"),
    ).grid(row=0, column=0, sticky="w")

    language_var = tk.StringVar(
        value="Italiano" if initial.language == "it" else "English"
    )
    language_combo = ttk.Combobox(
        form,
        textvariable=language_var,
        values=["Italiano", "English"],
        state="readonly",
        width=28,
    )
    language_combo.grid(row=1, column=0, sticky="ew", pady=(4, 18), ipady=3)

    ttk.Label(
        form,
        text="Numero di token / Number of tokens",
        font=("Arial", 11, "bold"),
    ).grid(row=2, column=0, sticky="w")

    tokens_var = tk.StringVar(
        value=str(initial.max_tokens or DEFAULT_MAX_TOKENS)
    )
    tokens_entry = ttk.Entry(form, textvariable=tokens_var, width=12)
    tokens_entry.grid(row=3, column=0, sticky="w", pady=(4, 2), ipady=3)

    ttk.Label(
        form,
        text=f"Valore suggerito / Suggested value: {DEFAULT_MAX_TOKENS}",
        bootstyle="secondary",
    ).grid(row=4, column=0, sticky="w", pady=(0, 18))

    ttk.Label(
        form,
        text="Database",
        font=("Arial", 11, "bold"),
    ).grid(row=5, column=0, sticky="w")

    database_var = tk.StringVar(value=initial.database or DEFAULT_DATABASE)
    database_entry = ttk.Entry(form, textvariable=database_var)
    database_entry.grid(row=6, column=0, sticky="ew", pady=(4, 8), ipady=3)

    db_buttons = ttk.Frame(form)
    db_buttons.grid(row=7, column=0, sticky="w")

    def choose_new_database() -> None:
        selected = filedialog.asksaveasfilename(
            parent=root,
            title="Nuovo database LudoX / New LudoX database",
            initialdir=str(PROJECT_DIR),
            initialfile=Path(database_var.get().strip() or DEFAULT_DATABASE).name,
            defaultextension=".db",
            filetypes=[
                ("SQLite database", "*.db *.sqlite *.sqlite3"),
                ("All files", "*.*"),
            ],
        )
        if selected:
            database_var.set(database_setting_from_path(selected))

    def choose_existing_database() -> None:
        selected = filedialog.askopenfilename(
            parent=root,
            title="Apri database LudoX / Open LudoX database",
            initialdir=str(PROJECT_DIR),
            filetypes=[
                ("SQLite database", "*.db *.sqlite *.sqlite3"),
                ("All files", "*.*"),
            ],
        )
        if selected:
            database_var.set(database_setting_from_path(selected))

    ttk.Button(
        db_buttons,
        text="NUOVO… / NEW…",
        command=choose_new_database,
        bootstyle="secondary-outline",
    ).pack(side="left", padx=(0, 8))

    ttk.Button(
        db_buttons,
        text="APRI ESISTENTE… / OPEN EXISTING…",
        command=choose_existing_database,
        bootstyle="secondary-outline",
    ).pack(side="left")

    ttk.Label(
        form,
        text=(
            "Scrivi un nome (es. AMIGO2026.db), scegli dove creare un nuovo "
            "database oppure aprine uno esistente.\n"
            "Type a name, choose where to create a new database, or open an "
            "existing one."
        ),
        bootstyle="secondary",
        justify="left",
        wraplength=680,
    ).grid(row=8, column=0, sticky="w", pady=(8, 0))

    separator = ttk.Separator(frame)
    separator.grid(row=3, column=0, sticky="ew", pady=(26, 18))

    footer = ttk.Frame(frame)
    footer.grid(row=4, column=0, sticky="ew")
    footer.columnconfigure(1, weight=1)

    def confirm() -> None:
        nonlocal result
        try:
            max_tokens = int(tokens_var.get().strip())
        except ValueError:
            max_tokens = 0

        if max_tokens <= 0:
            messagebox.showwarning(
                "Configurazione non valida / Invalid configuration",
                "Inserisci un numero di token maggiore di zero.\n"
                "Enter a number of tokens greater than zero.",
                parent=root,
            )
            return

        try:
            database = normalize_database_setting(database_var.get())
        except (OSError, ValueError) as exc:
            messagebox.showwarning(
                "Database non valido / Invalid database",
                "Seleziona un nome o un percorso database valido.\n"
                "Select a valid database name or path.\n\n"
                f"Dettaglio / Detail: {exc}",
                parent=root,
            )
            return

        language = "it" if language_var.get() == "Italiano" else "en"
        candidate = AppConfig(
            language=language,
            max_tokens=max_tokens,
            database=database,
        )
        if not validate_config(candidate):
            messagebox.showwarning(
                "Configurazione non valida / Invalid configuration",
                "Controlla i parametri inseriti.\nCheck the entered parameters.",
                parent=root,
            )
            return

        result = candidate
        root.destroy()

    def cancel() -> None:
        root.destroy()

    ttk.Button(
        footer,
        text="ANNULLA / CANCEL",
        command=cancel,
        bootstyle="secondary-outline",
    ).grid(row=0, column=0, sticky="w", padx=(0, 12), ipady=6)

    # Kept wide and at the bottom of the window so it cannot disappear below
    # the form on common Windows display/scaling settings.
    confirm_button = ttk.Button(
        footer,
        text="SALVA CONFIGURAZIONE E AVVIA / SAVE CONFIGURATION AND START",
        command=confirm,
        bootstyle="success",
    )
    confirm_button.grid(row=0, column=1, sticky="ew", ipadx=18, ipady=10)

    root.bind("<Return>", lambda _event: confirm())
    root.protocol("WM_DELETE_WINDOW", cancel)
    tokens_entry.focus_set()
    root.mainloop()
    return result


def ensure_config(path: Path = CONFIG_PATH) -> AppConfig:
    loaded = load_config(path)
    if loaded is not None:
        return loaded

    candidate = _first_run_dialog(AppConfig())
    if candidate is None:
        raise SystemExit(0)
    save_config(candidate, path)
    return candidate
