from __future__ import annotations

import configparser
from dataclasses import dataclass
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_DIR / "config.ini"
DEFAULT_LANGUAGE = "it"
DEFAULT_MAX_TOKENS = 100
SUPPORTED_LANGUAGES = ("it", "en")


@dataclass
class AppConfig:
    language: str = DEFAULT_LANGUAGE
    max_tokens: int = DEFAULT_MAX_TOKENS


def validate_config(config: AppConfig) -> bool:
    return (
        config.language in SUPPORTED_LANGUAGES
        and isinstance(config.max_tokens, int)
        and config.max_tokens > 0
    )


def load_config(path: Path = CONFIG_PATH) -> AppConfig | None:
    if not path.exists():
        return None

    parser = configparser.ConfigParser()
    try:
        parser.read(path, encoding="utf-8")
        language = parser.get("general", "language", fallback=DEFAULT_LANGUAGE).strip().lower()
        max_tokens = parser.getint("general", "max_tokens", fallback=DEFAULT_MAX_TOKENS)
    except (configparser.Error, ValueError):
        return None

    result = AppConfig(language=language, max_tokens=max_tokens)
    return result if validate_config(result) else None


def save_config(config: AppConfig, path: Path = CONFIG_PATH) -> None:
    if not validate_config(config):
        raise ValueError("Invalid LudoX configuration")

    parser = configparser.ConfigParser()
    parser["general"] = {
        "language": config.language,
        "max_tokens": str(config.max_tokens),
    }
    with path.open("w", encoding="utf-8") as handle:
        parser.write(handle)


def _first_run_dialog(initial: AppConfig | None = None) -> AppConfig | None:
    import tkinter as tk
    from tkinter import messagebox
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import BOTH, RIGHT, X

    initial = initial or AppConfig()
    result: AppConfig | None = None

    root = ttk.Window(
        title="LudoX — Configurazione iniziale / Initial setup",
        themename="flatly",
    )
    root.geometry("520x350")
    root.minsize(480, 320)
    root.resizable(False, False)

    frame = ttk.Frame(root, padding=30)
    frame.pack(fill=BOTH, expand=True)

    ttk.Label(
        frame,
        text="LudoX",
        font=("Arial", 26, "bold"),
        bootstyle="primary",
    ).pack(pady=(0, 4))

    ttk.Label(
        frame,
        text="Configurazione iniziale / Initial setup",
        font=("Arial", 14, "bold"),
    ).pack(pady=(0, 24))

    form = ttk.Frame(frame)
    form.pack(fill=X)

    ttk.Label(form, text="Lingua / Language", font=("Arial", 11, "bold")).pack(anchor="w")
    language_var = tk.StringVar(value="Italiano" if initial.language == "it" else "English")
    language_combo = ttk.Combobox(
        form,
        textvariable=language_var,
        values=["Italiano", "English"],
        state="readonly",
        width=28,
    )
    language_combo.pack(fill=X, pady=(4, 16), ipady=3)

    ttk.Label(
        form,
        text="Numero di token / Number of tokens",
        font=("Arial", 11, "bold"),
    ).pack(anchor="w")

    tokens_var = tk.StringVar(value=str(initial.max_tokens or DEFAULT_MAX_TOKENS))
    tokens_entry = ttk.Entry(form, textvariable=tokens_var, width=12)
    tokens_entry.pack(anchor="w", pady=(4, 2), ipady=3)

    ttk.Label(
        form,
        text="Valore suggerito / Suggested value: 100",
        bootstyle="secondary",
    ).pack(anchor="w", pady=(0, 18))

    def confirm() -> None:
        nonlocal result
        try:
            max_tokens = int(tokens_var.get().strip())
        except ValueError:
            max_tokens = 0

        language = "it" if language_var.get() == "Italiano" else "en"
        candidate = AppConfig(language=language, max_tokens=max_tokens)
        if not validate_config(candidate):
            messagebox.showwarning(
                "Configurazione non valida / Invalid configuration",
                "Inserisci un numero di token maggiore di zero.\n"
                "Enter a number of tokens greater than zero.",
                parent=root,
            )
            return
        result = candidate
        root.destroy()

    ttk.Button(
        frame,
        text="SALVA E AVVIA / SAVE AND START",
        command=confirm,
        bootstyle="success",
    ).pack(side=RIGHT, pady=(8, 0), ipadx=20, ipady=8)

    root.protocol("WM_DELETE_WINDOW", root.destroy)
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
