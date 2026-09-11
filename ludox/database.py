# Copyright (C) 2026 Matteo Sassi
# SPDX-License-Identifier: AGPL-3.0-only

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime

PROJECT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_DIR / "ludox.db"


def set_db_path(path):
    """Select the SQLite database used by all data functions."""
    global DB_PATH
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = PROJECT_DIR / candidate
    candidate = candidate.resolve(strict=False)
    if not candidate.parent.exists():
        raise ValueError(f"Database folder does not exist: {candidate.parent}")
    if candidate.exists() and candidate.is_dir():
        raise ValueError(f"Database path is a directory: {candidate}")
    DB_PATH = candidate
    return DB_PATH


def get_db_path():
    return DB_PATH


def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def init_db(default_owner_name="Organizzazione"):
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

        # Proprietario iniziale utile per partire subito. Viene creato
        # soltanto se il database non contiene ancora proprietari, così un
        # successivo cambio di lingua non genera un secondo proprietario.
        if db.execute("SELECT COUNT(*) FROM proprietari").fetchone()[0] == 0:
            db.execute(
                "INSERT INTO proprietari (nome, attivo) VALUES (?, 1)",
                (default_owner_name,),
            )


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


def token_libero(max_tokens):
    with get_db() as db:
        occupati = {
            row["token"]
            for row in db.execute("""
                SELECT token
                FROM documenti
                WHERE uscita IS NULL
            """)
        }

    for token in range(1, max_tokens + 1):
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


def massimo_token_aperto():
    """Return the highest token currently associated with an open document."""
    with get_db() as db:
        value = db.execute(
            "SELECT COALESCE(MAX(token), 0) FROM documenti WHERE uscita IS NULL"
        ).fetchone()[0]
    return int(value or 0)


class ErrorePersistenza(Exception):
    """Database failure exposed by the extracted lending operations."""


@contextmanager
def transazione_prestiti(immediata=False):
    """Keep the existing commit/rollback boundary, optionally locking first."""
    try:
        with get_db() as db:
            if immediata:
                db.execute("BEGIN IMMEDIATE")
            yield db
    except sqlite3.Error as exc:
        raise ErrorePersistenza(str(exc)) from exc


def inserisci_documento(db, token, timestamp):
    return db.execute(
        "INSERT INTO documenti (token, ingresso) VALUES (?, ?)",
        (token, timestamp),
    ).lastrowid


def inserisci_prestito(db, documento_id, gioco_id, timestamp):
    return db.execute(
        "INSERT INTO prestiti (documento_id, gioco_id, uscita) VALUES (?, ?, ?)",
        (documento_id, gioco_id, timestamp),
    ).lastrowid


def nome_gioco_in_transazione(db, gioco_id):
    return db.execute("SELECT nome FROM giochi WHERE id = ?", (gioco_id,)).fetchone()


def documento_per_cambio(db, documento_id, token):
    return db.execute(
        "SELECT id, token FROM documenti WHERE id = ? AND token = ? AND uscita IS NULL",
        (documento_id, token),
    ).fetchone()


def prestito_per_cambio(db, prestito_id, documento_id):
    return db.execute("""
        SELECT p.id, p.gioco_id, g.nome AS gioco_nome
        FROM prestiti p JOIN giochi g ON g.id = p.gioco_id
        WHERE p.id = ? AND p.documento_id = ? AND p.rientro IS NULL
    """, (prestito_id, documento_id)).fetchone()


def gioco_per_cambio(db, gioco_id):
    return db.execute(
        "SELECT id, nome, attivo FROM giochi WHERE id = ?", (gioco_id,)
    ).fetchone()


def conteggi_copie_in_transazione(db, gioco_id):
    totali = db.execute(
        "SELECT COALESCE(SUM(quantita), 0) FROM copie_gioco WHERE gioco_id = ?",
        (gioco_id,),
    ).fetchone()[0]
    fuori = db.execute(
        "SELECT COUNT(*) FROM prestiti WHERE gioco_id = ? AND rientro IS NULL",
        (gioco_id,),
    ).fetchone()[0]
    return totali, fuori


def chiudi_prestito_per_cambio(db, prestito_id, documento_id, timestamp):
    return db.execute("""
        UPDATE prestiti SET rientro = ?
        WHERE id = ? AND documento_id = ? AND rientro IS NULL
    """, (timestamp, prestito_id, documento_id)).rowcount


def chiudi_prestito_per_restituzione(db, prestito_id, timestamp):
    return db.execute(
        "UPDATE prestiti SET rientro = ? WHERE id = ? AND rientro IS NULL",
        (timestamp, prestito_id),
    ).rowcount


def chiudi_documento_per_restituzione(db, documento_id, timestamp):
    return db.execute(
        "UPDATE documenti SET uscita = ? WHERE id = ? AND uscita IS NULL",
        (timestamp, documento_id),
    ).rowcount
