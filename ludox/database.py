# Copyright (C) 2026 Matteo Sassi
# SPDX-License-Identifier: AGPL-3.0-only

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime

from . import migrations

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


def init_db(
    default_owner_name="Organizzazione",
    *,
    migration_authorized=False,
    now=None,
):
    from . import bootstrap

    return bootstrap.prepare_database(
        DB_PATH,
        migration_authorized=migration_authorized,
        initialize_schema=lambda: initialize_current_schema(default_owner_name),
        now=now,
    )


def initialize_current_schema(default_owner_name="Organizzazione"):
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


def token_documenti_aperti():
    with get_db() as db:
        return db.execute("""
            SELECT token
            FROM documenti
            WHERE uscita IS NULL
            ORDER BY token
        """).fetchall()


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


def righe_export_ludoteca_legacy():
    """Return positive legacy game/owner quantities in stable order."""
    with get_db() as db:
        return db.execute("""
            SELECT
                g.nome AS game_name,
                p.nome AS owner_label,
                cg.quantita AS quantity
            FROM copie_gioco cg
            JOIN giochi g ON g.id = cg.gioco_id
            JOIN proprietari p ON p.id = cg.proprietario_id
            WHERE cg.quantita > 0
            ORDER BY
                g.nome COLLATE NOCASE,
                g.nome,
                p.nome COLLATE NOCASE,
                p.nome,
                g.id,
                p.id
        """).fetchall()


# ============================================================
# FUNZIONI DATI - ORGANIZATIONS
# ============================================================

def elenco_organizzazioni(solo_attive=False):
    with get_db() as db:
        if solo_attive:
            return db.execute("""
                SELECT id, name, active
                FROM organizations
                WHERE active = 1
                ORDER BY name COLLATE NOCASE, id
            """).fetchall()

        return db.execute("""
            SELECT id, name, active
            FROM organizations
            ORDER BY name COLLATE NOCASE, id
        """).fetchall()


def organizzazione_per_id(organizzazione_id):
    with get_db() as db:
        return db.execute("""
            SELECT id, name, active
            FROM organizations
            WHERE id = ?
        """, (organizzazione_id,)).fetchone()


def inserisci_organizzazione(nome):
    with get_db() as db:
        return db.execute(
            "INSERT INTO organizations (name, active) VALUES (?, 1)",
            (nome,),
        ).lastrowid


def aggiorna_organizzazione(organizzazione_id, nome, attiva):
    with get_db() as db:
        return db.execute("""
            UPDATE organizations
            SET name = ?, active = ?
            WHERE id = ?
        """, (nome, attiva, organizzazione_id)).rowcount


# ============================================================
# FUNZIONI DATI - EVENTS E MODULI
# ============================================================

def elenco_eventi(organization_id, solo_selezionabili=False):
    with get_db() as db:
        query = """
            SELECT id, organization_id, name, slug, start_datetime,
                   end_datetime, timezone, status
            FROM events
            WHERE organization_id = ?
        """
        parameters = [organization_id]
        if solo_selezionabili:
            query += " AND status IN ('draft', 'active')"
        query += " ORDER BY start_datetime, name COLLATE NOCASE, id"
        return db.execute(query, parameters).fetchall()


def evento_per_id(event_id):
    with get_db() as db:
        return db.execute("""
            SELECT id, organization_id, name, slug, start_datetime,
                   end_datetime, timezone, status
            FROM events
            WHERE id = ?
        """, (event_id,)).fetchone()


def inserisci_evento(
    organization_id,
    nome,
    slug,
    inizio,
    fine,
    timezone,
):
    with get_db() as db:
        return db.execute("""
            INSERT INTO events(
                organization_id, name, slug, start_datetime,
                end_datetime, timezone, status
            ) VALUES (?, ?, ?, ?, ?, ?, 'draft')
        """, (
            organization_id, nome, slug, inizio, fine, timezone,
        )).lastrowid


def aggiorna_evento(event_id, nome, inizio, fine, timezone, stato):
    with get_db() as db:
        return db.execute("""
            UPDATE events
            SET name = ?, start_datetime = ?, end_datetime = ?,
                timezone = ?, status = ?
            WHERE id = ?
        """, (nome, inizio, fine, timezone, stato, event_id)).rowcount


def elimina_evento(event_id):
    with get_db() as db:
        return db.execute(
            "DELETE FROM events WHERE id = ?",
            (event_id,),
        ).rowcount


def moduli_evento(event_id):
    with get_db() as db:
        return db.execute("""
            SELECT module_id, enabled
            FROM event_modules
            WHERE event_id = ?
            ORDER BY module_id
        """, (event_id,)).fetchall()


def imposta_modulo_evento(event_id, module_id, abilitato):
    with get_db() as db:
        db.execute("""
            INSERT INTO event_modules(event_id, module_id, enabled)
            VALUES (?, ?, ?)
            ON CONFLICT(event_id, module_id) DO UPDATE
            SET enabled = excluded.enabled
        """, (event_id, module_id, 1 if abilitato else 0))


def evento_ha_storico(event_id):
    with get_db() as db:
        return bool(db.execute("""
            SELECT EXISTS(
                SELECT 1 FROM game_library_sessions WHERE event_id = ?
                UNION ALL
                SELECT 1 FROM game_library_loans WHERE event_id = ?
            )
        """, (event_id, event_id)).fetchone()[0])


# ============================================================
# GAME LIBRARY EVENT-SPECIFIC (schema v3)
# ============================================================

def inizializza_game_library(event_id):
    with get_db() as db:
        db.execute("""
            INSERT OR IGNORE INTO game_library_settings(event_id)
            VALUES (?)
        """, (event_id,))


def impostazioni_game_library(event_id):
    with get_db() as db:
        return db.execute("""
            SELECT event_id, max_slots, identification_mode
            FROM game_library_settings WHERE event_id = ?
        """, (event_id,)).fetchone()


def aggiorna_impostazioni_game_library(event_id, max_slots, identification_mode):
    with get_db() as db:
        db.execute("""
            UPDATE game_library_settings
            SET max_slots = ?, identification_mode = ?
            WHERE event_id = ?
        """, (max_slots, identification_mode, event_id))


def conta_prestiti_evento(event_id):
    with get_db() as db:
        return db.execute(
            "SELECT COUNT(*) FROM game_library_loans WHERE event_id = ?",
            (event_id,),
        ).fetchone()[0]


def conta_sessioni_evento(event_id):
    with get_db() as db:
        return db.execute(
            "SELECT COUNT(*) FROM game_library_sessions WHERE event_id = ?",
            (event_id,),
        ).fetchone()[0]


def conta_sessioni_attive_evento(event_id):
    with get_db() as db:
        return db.execute("""
            SELECT COUNT(*) FROM game_library_sessions
            WHERE event_id = ? AND closed_at IS NULL
        """, (event_id,)).fetchone()[0]


def slot_sessioni_aperte(event_id):
    with get_db() as db:
        return db.execute("""
            SELECT slot AS token FROM game_library_sessions
            WHERE event_id = ? AND closed_at IS NULL ORDER BY slot
        """, (event_id,)).fetchall()


def slot_libero(event_id, max_slots):
    occupati = {row["token"] for row in slot_sessioni_aperte(event_id)}
    return next((slot for slot in range(1, max_slots + 1) if slot not in occupati), None)


def sessione_aperta_da_slot(event_id, slot):
    with get_db() as db:
        return db.execute("""
            SELECT id, event_id, slot AS token, opened_at AS ingresso,
                   closed_at AS uscita
            FROM game_library_sessions
            WHERE event_id = ? AND slot = ? AND closed_at IS NULL
        """, (event_id, slot)).fetchone()


def prestito_aperto_sessione(event_id, session_id):
    with get_db() as db:
        return db.execute("""
            SELECT l.id, l.event_id, l.session_id AS documento_id,
                   l.game_id AS gioco_id, l.copy_id,
                   l.checked_out_at AS uscita, l.returned_at AS rientro,
                   g.name AS gioco_nome
            FROM game_library_loans l
            JOIN game_library_games g
              ON g.event_id = l.event_id AND g.id = l.game_id
            WHERE l.event_id = ? AND l.session_id = ?
              AND l.returned_at IS NULL
        """, (event_id, session_id)).fetchone()


def copie_totali_gioco_evento(event_id, game_id):
    with get_db() as db:
        return db.execute("""
            SELECT COUNT(*) FROM game_library_game_copies
            WHERE event_id = ? AND game_id = ? AND active = 1
        """, (event_id, game_id)).fetchone()[0]


def copie_in_prestito_evento(event_id, game_id):
    with get_db() as db:
        return db.execute("""
            SELECT COUNT(*) FROM game_library_loans
            WHERE event_id = ? AND game_id = ? AND returned_at IS NULL
        """, (event_id, game_id)).fetchone()[0]


def disponibilita_gioco_evento(event_id, game_id):
    totale = copie_totali_gioco_evento(event_id, game_id)
    fuori = copie_in_prestito_evento(event_id, game_id)
    return max(0, totale - fuori), totale


def cerca_giochi_evento(event_id, testo=""):
    with get_db() as db:
        return db.execute("""
            SELECT g.id, g.name AS nome, COUNT(c.id) AS copie_totali
            FROM game_library_games g
            JOIN game_library_game_copies c
              ON c.event_id = g.event_id AND c.game_id = g.id AND c.active = 1
            WHERE g.event_id = ? AND g.active = 1 AND g.name LIKE ?
            GROUP BY g.id, g.name
            HAVING COUNT(c.id) > 0
            ORDER BY g.name COLLATE NOCASE, g.id
        """, (event_id, f"%{testo.strip()}%")).fetchall()


def elenco_owner_labels(event_id, solo_attivi=False):
    query = """SELECT id, event_id, name AS nome, active AS attivo
               FROM game_library_owner_labels WHERE event_id = ?"""
    if solo_attivi:
        query += " AND active = 1"
    query += " ORDER BY name COLLATE NOCASE, id"
    with get_db() as db:
        return db.execute(query, (event_id,)).fetchall()


def owner_label_per_id(event_id, owner_id):
    with get_db() as db:
        return db.execute("""
            SELECT id, event_id, name AS nome, active AS attivo
            FROM game_library_owner_labels WHERE event_id = ? AND id = ?
        """, (event_id, owner_id)).fetchone()


def inserisci_owner_label(event_id, nome, name_key):
    try:
        with get_db() as db:
            cursor = db.execute("""
                INSERT INTO game_library_owner_labels(event_id, name, name_key)
                VALUES (?, ?, ?)
            """, (event_id, nome, name_key))
            return cursor.lastrowid
    except sqlite3.IntegrityError as exc:
        if "UNIQUE" in str(exc).upper():
            raise NomeDuplicato(nome) from exc
        raise


def aggiorna_owner_label(event_id, owner_id, nome, name_key, attivo):
    try:
        with get_db() as db:
            db.execute("""
                UPDATE game_library_owner_labels
                SET name = ?, name_key = ?, active = ?
                WHERE event_id = ? AND id = ?
            """, (nome, name_key, attivo, event_id, owner_id))
    except sqlite3.IntegrityError as exc:
        if "UNIQUE" in str(exc).upper():
            raise NomeDuplicato(nome) from exc
        raise


def totale_copie_owner_label(event_id, owner_id):
    with get_db() as db:
        return db.execute("""
            SELECT COUNT(*) FROM game_library_game_copies
            WHERE event_id = ? AND owner_label_id = ? AND active = 1
        """, (event_id, owner_id)).fetchone()[0]


def gioco_evento_per_id(event_id, game_id):
    with get_db() as db:
        return db.execute("""
            SELECT id, event_id, name AS nome, active AS attivo,
                   external_id, difficulty, difficulty_source, notes
            FROM game_library_games WHERE event_id = ? AND id = ?
        """, (event_id, game_id)).fetchone()


def inserisci_gioco_evento(event_id, nome, name_key):
    try:
        with get_db() as db:
            cursor = db.execute("""
                INSERT INTO game_library_games(event_id, name, name_key)
                VALUES (?, ?, ?)
            """, (event_id, nome, name_key))
            return cursor.lastrowid
    except sqlite3.IntegrityError as exc:
        if "UNIQUE" in str(exc).upper():
            raise NomeDuplicato(nome) from exc
        raise


def aggiorna_gioco_evento(event_id, game_id, nome, name_key, attivo):
    try:
        with get_db() as db:
            db.execute("""
                UPDATE game_library_games
                SET name = ?, name_key = ?, active = ?
                WHERE event_id = ? AND id = ?
            """, (nome, name_key, attivo, event_id, game_id))
    except sqlite3.IntegrityError as exc:
        if "UNIQUE" in str(exc).upper():
            raise NomeDuplicato(nome) from exc
        raise


def elenco_giochi_evento_backoffice(event_id):
    with get_db() as db:
        return db.execute("""
            SELECT g.id, g.event_id, g.name AS nome, g.active AS attivo,
                   COUNT(c.id) AS copie_totali
            FROM game_library_games g
            LEFT JOIN game_library_game_copies c
              ON c.event_id = g.event_id AND c.game_id = g.id AND c.active = 1
            WHERE g.event_id = ?
            GROUP BY g.id, g.event_id, g.name, g.active
            ORDER BY g.name COLLATE NOCASE, g.id
        """, (event_id,)).fetchall()


def copie_per_owner_del_gioco(event_id, game_id):
    with get_db() as db:
        return db.execute("""
            SELECT o.id AS proprietario_id, o.name AS proprietario_nome,
                   o.active AS proprietario_attivo,
                   COUNT(c.id) AS quantita
            FROM game_library_owner_labels o
            LEFT JOIN game_library_game_copies c
              ON c.event_id = o.event_id AND c.owner_label_id = o.id
             AND c.game_id = ? AND c.active = 1
            WHERE o.event_id = ?
            GROUP BY o.id, o.name, o.active
            ORDER BY o.name COLLATE NOCASE, o.id
        """, (game_id, event_id)).fetchall()


def riepilogo_owner_gioco(event_id, game_id):
    rows = copie_per_owner_del_gioco(event_id, game_id)
    return ", ".join(
        f'{row["proprietario_nome"]}: {row["quantita"]}'
        for row in rows if row["quantita"] > 0
    ) or "—"


def copie_altri_owner(event_id, game_id, owner_id):
    with get_db() as db:
        return db.execute("""
            SELECT COUNT(*) FROM game_library_game_copies
            WHERE event_id = ? AND game_id = ? AND owner_label_id <> ?
              AND active = 1
        """, (event_id, game_id, owner_id)).fetchone()[0]


def aggiorna_quantita_copie_evento(event_id, game_id, owner_id, quantita):
    with get_db() as db:
        rows = db.execute("""
            SELECT id FROM game_library_game_copies
            WHERE event_id = ? AND game_id = ? AND owner_label_id = ?
              AND active = 1 ORDER BY id
        """, (event_id, game_id, owner_id)).fetchall()
        differenza = quantita - len(rows)
        if differenza > 0:
            db.executemany("""
                INSERT INTO game_library_game_copies(
                    event_id, game_id, owner_label_id
                ) VALUES (?, ?, ?)
            """, [(event_id, game_id, owner_id)] * differenza)
        elif differenza < 0:
            ids = [row["id"] for row in rows[differenza:]]
            db.executemany(
                "DELETE FROM game_library_game_copies WHERE id = ?",
                [(copy_id,) for copy_id in ids],
            )


class DuplicateCopyIdentifierValue(Exception):
    pass


def copia_evento_per_id(event_id, copy_id):
    with get_db() as db:
        return db.execute("""
            SELECT c.id AS copy_id, c.event_id, c.game_id,
                   c.owner_label_id, c.active AS copy_active,
                   g.name AS game_name, g.active AS game_active,
                   o.name AS owner_label
            FROM game_library_game_copies c
            JOIN game_library_games g
              ON g.event_id = c.event_id AND g.id = c.game_id
            JOIN game_library_owner_labels o
              ON o.event_id = c.event_id AND o.id = c.owner_label_id
            WHERE c.event_id = ? AND c.id = ?
        """, (event_id, copy_id)).fetchone()


def identificatore_copia(event_id, copy_id):
    with get_db() as db:
        return db.execute("""
            SELECT id, event_id, copy_id, source, value
            FROM game_library_copy_identifiers
            WHERE event_id = ? AND copy_id = ?
        """, (event_id, copy_id)).fetchone()


def identificatore_per_valore(event_id, value):
    with get_db() as db:
        return db.execute("""
            SELECT id, event_id, copy_id, source, value
            FROM game_library_copy_identifiers
            WHERE event_id = ? AND value = ?
        """, (event_id, value)).fetchone()


def copia_da_identificatore(event_id, value):
    with get_db() as db:
        return db.execute("""
            SELECT c.id AS copy_id, c.event_id, c.game_id,
                   c.owner_label_id, c.active AS copy_active,
                   g.name AS game_name, g.active AS game_active,
                   o.name AS owner_label,
                   i.id AS identifier_id, i.value AS copy_identifier,
                   i.source AS identifier_source
            FROM game_library_copy_identifiers i
            JOIN game_library_game_copies c
              ON c.event_id = i.event_id AND c.id = i.copy_id
            JOIN game_library_games g
              ON g.event_id = c.event_id AND g.id = c.game_id
            JOIN game_library_owner_labels o
              ON o.event_id = c.event_id AND o.id = c.owner_label_id
            WHERE i.event_id = ? AND i.value = ?
        """, (event_id, value)).fetchone()


def inserisci_identificatore_copia(event_id, copy_id, source, value):
    try:
        with get_db() as db:
            return db.execute("""
                INSERT INTO game_library_copy_identifiers(
                    event_id, copy_id, source, value
                ) VALUES (?, ?, ?, ?)
            """, (event_id, copy_id, source, value)).lastrowid
    except sqlite3.IntegrityError as exc:
        if "UNIQUE" in str(exc).upper():
            raise DuplicateCopyIdentifierValue(
                "L'identificatore è già in uso nell'Event corrente."
            ) from exc
        raise


def aggiorna_identificatore_copia(event_id, copy_id, source, value):
    try:
        with get_db() as db:
            return db.execute("""
                UPDATE game_library_copy_identifiers
                SET source = ?, value = ?
                WHERE event_id = ? AND copy_id = ?
            """, (source, value, event_id, copy_id)).rowcount
    except sqlite3.IntegrityError as exc:
        if "UNIQUE" in str(exc).upper():
            raise DuplicateCopyIdentifierValue(
                "L'identificatore è già in uso nell'Event corrente."
            ) from exc
        raise


def elimina_identificatore_copia(event_id, copy_id):
    with get_db() as db:
        return db.execute("""
            DELETE FROM game_library_copy_identifiers
            WHERE event_id = ? AND copy_id = ?
        """, (event_id, copy_id)).rowcount


def copia_ha_prestito_aperto(event_id, copy_id):
    with get_db() as db:
        return bool(db.execute("""
            SELECT EXISTS(
                SELECT 1 FROM game_library_loans
                WHERE event_id = ? AND copy_id = ? AND returned_at IS NULL
            )
        """, (event_id, copy_id)).fetchone()[0])


def giochi_per_owner_evento(event_id, owner_id):
    with get_db() as db:
        return db.execute("""
            SELECT g.id AS gioco_id, g.name AS gioco, g.active AS gioco_attivo,
                   SUM(CASE WHEN c.owner_label_id = ? AND c.active = 1 THEN 1 ELSE 0 END)
                       AS copie_proprietario,
                   SUM(CASE WHEN c.active = 1 THEN 1 ELSE 0 END) AS copie_totali,
                   (SELECT COUNT(*) FROM game_library_loans l
                    WHERE l.event_id = g.event_id AND l.game_id = g.id
                      AND l.returned_at IS NULL) AS prestiti_attivi_titolo
            FROM game_library_games g
            JOIN game_library_game_copies c
              ON c.event_id = g.event_id AND c.game_id = g.id
            WHERE g.event_id = ?
            GROUP BY g.id, g.name, g.active
            HAVING copie_proprietario > 0
            ORDER BY g.name COLLATE NOCASE, g.id
        """, (owner_id, event_id)).fetchall()


def inserisci_sessione(db, event_id, slot, timestamp):
    cursor = db.execute("""
        INSERT INTO game_library_sessions(event_id, slot, opened_at)
        VALUES (?, ?, ?)
    """, (event_id, slot, timestamp))
    return cursor.lastrowid


def inserisci_prestito_evento(db, event_id, session_id, game_id, timestamp):
    cursor = db.execute("""
        INSERT INTO game_library_loans(
            event_id, session_id, game_id, checked_out_at
        ) VALUES (?, ?, ?, ?)
    """, (event_id, session_id, game_id, timestamp))
    return cursor.lastrowid


def nome_gioco_evento_in_transazione(db, event_id, game_id):
    return db.execute("""
        SELECT name AS nome FROM game_library_games
        WHERE event_id = ? AND id = ?
    """, (event_id, game_id)).fetchone()


def sessione_per_cambio(db, event_id, session_id, slot):
    return db.execute("""
        SELECT 1 FROM game_library_sessions
        WHERE event_id = ? AND id = ? AND slot = ? AND closed_at IS NULL
    """, (event_id, session_id, slot)).fetchone()


def prestito_evento_per_cambio(db, event_id, loan_id, session_id):
    return db.execute("""
        SELECT game_id AS gioco_id FROM game_library_loans
        WHERE event_id = ? AND id = ? AND session_id = ?
          AND returned_at IS NULL
    """, (event_id, loan_id, session_id)).fetchone()


def gioco_evento_per_cambio(db, event_id, game_id):
    return db.execute("""
        SELECT id, name AS nome, active AS attivo
        FROM game_library_games WHERE event_id = ? AND id = ?
    """, (event_id, game_id)).fetchone()


def conteggi_copie_evento_in_transazione(db, event_id, game_id):
    totale = db.execute("""
        SELECT COUNT(*) FROM game_library_game_copies
        WHERE event_id = ? AND game_id = ? AND active = 1
    """, (event_id, game_id)).fetchone()[0]
    fuori = db.execute("""
        SELECT COUNT(*) FROM game_library_loans
        WHERE event_id = ? AND game_id = ? AND returned_at IS NULL
    """, (event_id, game_id)).fetchone()[0]
    return totale, fuori


def chiudi_prestito_evento_per_cambio(db, event_id, loan_id, session_id, timestamp):
    return db.execute("""
        UPDATE game_library_loans SET returned_at = ?
        WHERE event_id = ? AND id = ? AND session_id = ?
          AND returned_at IS NULL
    """, (timestamp, event_id, loan_id, session_id)).rowcount


def chiudi_prestito_evento(db, event_id, loan_id, timestamp):
    return db.execute("""
        UPDATE game_library_loans SET returned_at = ?
        WHERE event_id = ? AND id = ? AND returned_at IS NULL
    """, (timestamp, event_id, loan_id)).rowcount


def chiudi_sessione_evento(db, event_id, session_id, timestamp):
    return db.execute("""
        UPDATE game_library_sessions SET closed_at = ?
        WHERE event_id = ? AND id = ? AND closed_at IS NULL
    """, (timestamp, event_id, session_id)).rowcount


def game_library_ha_aperti(event_id):
    return conta_sessioni_attive_evento(event_id) > 0


def righe_export_ludoteca_evento(event_id):
    with get_db() as db:
        return db.execute("""
            SELECT g.name AS game_name, o.name AS owner_label,
                   COUNT(c.id) AS quantity
            FROM game_library_game_copies c
            JOIN game_library_games g
              ON g.event_id = c.event_id AND g.id = c.game_id
            JOIN game_library_owner_labels o
              ON o.event_id = c.event_id AND o.id = c.owner_label_id
            WHERE c.event_id = ? AND c.active = 1
            GROUP BY g.id, g.name, o.id, o.name
            HAVING COUNT(c.id) > 0
            ORDER BY g.name COLLATE NOCASE, g.id,
                     o.name COLLATE NOCASE, o.id
        """, (event_id,)).fetchall()


def applica_import_ludoteca(event_id, rows):
    """Apply validated normalized rows atomically and return created counts."""
    created_games = created_owners = created_copies = 0
    with get_db() as db:
        for row in rows:
            game = db.execute("""
                SELECT id FROM game_library_games
                WHERE event_id = ? AND name_key = ?
            """, (event_id, row["game_key"])).fetchone()
            if game is None:
                game_id = db.execute("""
                    INSERT INTO game_library_games(event_id, name, name_key)
                    VALUES (?, ?, ?)
                """, (event_id, row["game_name"], row["game_key"])).lastrowid
                created_games += 1
            else:
                game_id = game["id"]

            owner = db.execute("""
                SELECT id FROM game_library_owner_labels
                WHERE event_id = ? AND name_key = ?
            """, (event_id, row["owner_key"])).fetchone()
            if owner is None:
                owner_id = db.execute("""
                    INSERT INTO game_library_owner_labels(event_id, name, name_key)
                    VALUES (?, ?, ?)
                """, (event_id, row["owner_label"], row["owner_key"])).lastrowid
                created_owners += 1
            else:
                owner_id = owner["id"]

            db.executemany("""
                INSERT INTO game_library_game_copies(
                    event_id, game_id, owner_label_id
                ) VALUES (?, ?, ?)
            """, [(event_id, game_id, owner_id)] * row["quantity"])
            created_copies += row["quantity"]
    return created_games, created_owners, created_copies


def reset_ludoteca_evento(event_id):
    with get_db() as db:
        if db.execute("""
            SELECT EXISTS(SELECT 1 FROM game_library_loans WHERE event_id = ?)
        """, (event_id,)).fetchone()[0]:
            return False
        db.execute(
            "DELETE FROM game_library_game_copies WHERE event_id = ?",
            (event_id,),
        )
        db.execute(
            "DELETE FROM game_library_games WHERE event_id = ?", (event_id,)
        )
        db.execute(
            "DELETE FROM game_library_owner_labels WHERE event_id = ?",
            (event_id,),
        )
    return True


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


class NomeDuplicato(Exception):
    """Integrity failure historically reported as a duplicate catalog name."""


@contextmanager
def _scrittura_nome_catalogo():
    try:
        with get_db() as db:
            yield db
    except sqlite3.IntegrityError as exc:
        raise NomeDuplicato(str(exc)) from exc


def inserisci_proprietario(nome):
    with _scrittura_nome_catalogo() as db:
        return db.execute(
            "INSERT INTO proprietari (nome, attivo) VALUES (?, 1)", (nome,)
        ).lastrowid


def aggiorna_proprietario(proprietario_id, nome, attivo):
    with _scrittura_nome_catalogo() as db:
        db.execute("UPDATE proprietari SET nome = ?, attivo = ? WHERE id = ?",
                   (nome, attivo, proprietario_id))


def inserisci_gioco(nome):
    with _scrittura_nome_catalogo() as db:
        return db.execute(
            "INSERT INTO giochi (nome, attivo) VALUES (?, 1)", (nome,)
        ).lastrowid


def aggiorna_gioco(gioco_id, nome, attivo):
    with _scrittura_nome_catalogo() as db:
        db.execute("UPDATE giochi SET nome = ?, attivo = ? WHERE id = ?",
                   (nome, attivo, gioco_id))


def copie_altri_proprietari(gioco_id, proprietario_id):
    with get_db() as db:
        return db.execute("""
            SELECT COALESCE(SUM(quantita), 0) FROM copie_gioco
            WHERE gioco_id = ? AND proprietario_id <> ?
        """, (gioco_id, proprietario_id)).fetchone()[0]


def aggiorna_quantita_copie(gioco_id, proprietario_id, quantita):
    with get_db() as db:
        if quantita == 0:
            db.execute("DELETE FROM copie_gioco WHERE gioco_id = ? AND proprietario_id = ?",
                       (gioco_id, proprietario_id))
        else:
            db.execute("""
                INSERT INTO copie_gioco (gioco_id, proprietario_id, quantita)
                VALUES (?, ?, ?)
                ON CONFLICT(gioco_id, proprietario_id)
                DO UPDATE SET quantita = excluded.quantita
            """, (gioco_id, proprietario_id, quantita))


def giochi_per_proprietario(proprietario_id):
    with get_db() as db:
        return db.execute("""
            SELECT g.id AS gioco_id, g.nome AS gioco, g.attivo AS gioco_attivo,
                cg.quantita AS copie_proprietario,
                (SELECT COALESCE(SUM(cg2.quantita), 0) FROM copie_gioco cg2
                 WHERE cg2.gioco_id = g.id) AS copie_totali,
                (SELECT COUNT(*) FROM prestiti pr
                 WHERE pr.gioco_id = g.id AND pr.rientro IS NULL) AS prestiti_attivi_titolo
            FROM copie_gioco cg JOIN giochi g ON g.id = cg.gioco_id
            WHERE cg.proprietario_id = ? AND cg.quantita > 0
            ORDER BY g.nome
        """, (proprietario_id,)).fetchall()


# ============================================================
# FUNZIONI DATI - STATISTICHE E REPORT
# ============================================================

def conta_attivita_periodo(inizio, fine):
    with get_db() as db:
        prestiti = db.execute("""
            SELECT COUNT(*) FROM prestiti
            WHERE uscita >= ? AND uscita < ?
        """, (inizio, fine)).fetchone()[0]
        documenti = db.execute("""
            SELECT COUNT(*) FROM documenti
            WHERE ingresso >= ? AND ingresso < ?
        """, (inizio, fine)).fetchone()[0]
    return prestiti, documenti


def timestamp_attivita_periodo(inizio, fine):
    with get_db() as db:
        prestiti = db.execute("""
            SELECT uscita FROM prestiti
            WHERE uscita >= ? AND uscita < ?
        """, (inizio, fine)).fetchall()
        documenti = db.execute("""
            SELECT ingresso FROM documenti
            WHERE ingresso >= ? AND ingresso < ?
        """, (inizio, fine)).fetchall()
    return prestiti, documenti


def storico_prestiti():
    with get_db() as db:
        totale = db.execute("SELECT COUNT(*) FROM prestiti").fetchone()[0]
        attivi = db.execute(
            "SELECT COUNT(*) FROM prestiti WHERE rientro IS NULL"
        ).fetchone()[0]
        righe = db.execute("""
            SELECT p.id AS prestito_id, d.id AS documento_id, d.token,
                   g.nome AS gioco, p.uscita, p.rientro
            FROM prestiti p
            JOIN documenti d ON d.id = p.documento_id
            JOIN giochi g ON g.id = p.gioco_id
            ORDER BY p.uscita DESC, p.id DESC
        """).fetchall()
    return totale, attivi, righe


def storico_documenti():
    with get_db() as db:
        totale = db.execute("SELECT COUNT(*) FROM documenti").fetchone()[0]
        attivi = db.execute(
            "SELECT COUNT(*) FROM documenti WHERE uscita IS NULL"
        ).fetchone()[0]
        righe = db.execute("""
            SELECT d.id, d.token, d.ingresso, d.uscita,
                   COUNT(p.id) AS numero_prestiti
            FROM documenti d
            LEFT JOIN prestiti p ON p.documento_id = d.id
            GROUP BY d.id, d.token, d.ingresso, d.uscita
            ORDER BY d.ingresso DESC, d.id DESC
        """).fetchall()
    return totale, attivi, righe


def documenti_ingressi_periodo(inizio, fine):
    with get_db() as db:
        return db.execute("""
            SELECT id, token, ingresso, uscita
            FROM documenti
            WHERE ingresso >= ? AND ingresso < ?
            ORDER BY ingresso
        """, (inizio, fine)).fetchall()


def prestiti_per_documenti(documenti_ids):
    if not documenti_ids:
        return []
    placeholders = ",".join("?" for _ in documenti_ids)
    with get_db() as db:
        return db.execute(f"""
            SELECT documento_id, uscita, rientro
            FROM prestiti
            WHERE documento_id IN ({placeholders})
            ORDER BY documento_id, uscita
        """, documenti_ids).fetchall()


def giochi_con_copie():
    with get_db() as db:
        return db.execute("""
            SELECT g.id, g.nome, g.attivo,
                   COALESCE(SUM(cg.quantita), 0) AS copie_totali
            FROM giochi g
            LEFT JOIN copie_gioco cg ON cg.gioco_id = g.id
            GROUP BY g.id, g.nome, g.attivo
            HAVING COALESCE(SUM(cg.quantita), 0) > 0
            ORDER BY g.nome
        """).fetchall()


def proprietari_dei_giochi():
    with get_db() as db:
        return db.execute("""
            SELECT cg.gioco_id, p.id AS proprietario_id,
                   p.nome AS proprietario_nome, cg.quantita
            FROM copie_gioco cg
            JOIN proprietari p ON p.id = cg.proprietario_id
            WHERE cg.quantita > 0
            ORDER BY cg.gioco_id, p.nome
        """).fetchall()


def prestiti_usciti_periodo(inizio, fine):
    with get_db() as db:
        return db.execute("""
            SELECT gioco_id, uscita, rientro
            FROM prestiti
            WHERE uscita >= ? AND uscita < ?
            ORDER BY uscita
        """, (inizio, fine)).fetchall()


def conta_attivita_periodo_evento(event_id, inizio, fine):
    with get_db() as db:
        prestiti = db.execute("""
            SELECT COUNT(*) FROM game_library_loans
            WHERE event_id = ? AND checked_out_at >= ? AND checked_out_at < ?
        """, (event_id, inizio, fine)).fetchone()[0]
        sessioni = db.execute("""
            SELECT COUNT(*) FROM game_library_sessions
            WHERE event_id = ? AND opened_at >= ? AND opened_at < ?
        """, (event_id, inizio, fine)).fetchone()[0]
    return prestiti, sessioni


def timestamp_attivita_periodo_evento(event_id, inizio, fine):
    with get_db() as db:
        prestiti = db.execute("""
            SELECT checked_out_at AS uscita FROM game_library_loans
            WHERE event_id = ? AND checked_out_at >= ? AND checked_out_at < ?
        """, (event_id, inizio, fine)).fetchall()
        sessioni = db.execute("""
            SELECT opened_at AS ingresso FROM game_library_sessions
            WHERE event_id = ? AND opened_at >= ? AND opened_at < ?
        """, (event_id, inizio, fine)).fetchall()
    return prestiti, sessioni


def storico_prestiti_evento(event_id):
    with get_db() as db:
        totale = db.execute(
            "SELECT COUNT(*) FROM game_library_loans WHERE event_id = ?",
            (event_id,),
        ).fetchone()[0]
        attivi = db.execute("""
            SELECT COUNT(*) FROM game_library_loans
            WHERE event_id = ? AND returned_at IS NULL
        """, (event_id,)).fetchone()[0]
        righe = db.execute("""
            SELECT l.id AS prestito_id, s.id AS documento_id,
                   s.slot AS token, g.name AS gioco,
                   l.checked_out_at AS uscita, l.returned_at AS rientro
            FROM game_library_loans l
            JOIN game_library_sessions s
              ON s.event_id = l.event_id AND s.id = l.session_id
            JOIN game_library_games g
              ON g.event_id = l.event_id AND g.id = l.game_id
            WHERE l.event_id = ?
            ORDER BY l.checked_out_at DESC, l.id DESC
        """, (event_id,)).fetchall()
    return totale, attivi, righe


def storico_sessioni_evento(event_id):
    with get_db() as db:
        totale = db.execute(
            "SELECT COUNT(*) FROM game_library_sessions WHERE event_id = ?",
            (event_id,),
        ).fetchone()[0]
        attivi = db.execute("""
            SELECT COUNT(*) FROM game_library_sessions
            WHERE event_id = ? AND closed_at IS NULL
        """, (event_id,)).fetchone()[0]
        righe = db.execute("""
            SELECT s.id, s.slot AS token, s.opened_at AS ingresso,
                   s.closed_at AS uscita, COUNT(l.id) AS numero_prestiti
            FROM game_library_sessions s
            LEFT JOIN game_library_loans l
              ON l.event_id = s.event_id AND l.session_id = s.id
            WHERE s.event_id = ?
            GROUP BY s.id, s.slot, s.opened_at, s.closed_at
            ORDER BY s.opened_at DESC, s.id DESC
        """, (event_id,)).fetchall()
    return totale, attivi, righe


def sessioni_ingressi_periodo(event_id, inizio, fine):
    with get_db() as db:
        return db.execute("""
            SELECT id, slot AS token, opened_at AS ingresso,
                   closed_at AS uscita
            FROM game_library_sessions
            WHERE event_id = ? AND opened_at >= ? AND opened_at < ?
            ORDER BY opened_at
        """, (event_id, inizio, fine)).fetchall()


def prestiti_per_sessioni(event_id, session_ids):
    if not session_ids:
        return []
    placeholders = ",".join("?" for _ in session_ids)
    with get_db() as db:
        return db.execute(f"""
            SELECT session_id AS documento_id, checked_out_at AS uscita,
                   returned_at AS rientro
            FROM game_library_loans
            WHERE event_id = ? AND session_id IN ({placeholders})
            ORDER BY session_id, checked_out_at
        """, [event_id, *session_ids]).fetchall()


def giochi_con_copie_evento(event_id):
    with get_db() as db:
        return db.execute("""
            SELECT g.id, g.name AS nome, g.active AS attivo,
                   COUNT(c.id) AS copie_totali
            FROM game_library_games g
            JOIN game_library_game_copies c
              ON c.event_id = g.event_id AND c.game_id = g.id AND c.active = 1
            WHERE g.event_id = ?
            GROUP BY g.id, g.name, g.active
            HAVING COUNT(c.id) > 0
            ORDER BY g.name COLLATE NOCASE, g.id
        """, (event_id,)).fetchall()


def owner_dei_giochi_evento(event_id):
    with get_db() as db:
        return db.execute("""
            SELECT c.game_id AS gioco_id, o.id AS proprietario_id,
                   o.name AS proprietario_nome, COUNT(c.id) AS quantita
            FROM game_library_game_copies c
            JOIN game_library_owner_labels o
              ON o.event_id = c.event_id AND o.id = c.owner_label_id
            WHERE c.event_id = ? AND c.active = 1
            GROUP BY c.game_id, o.id, o.name
            ORDER BY c.game_id, o.name COLLATE NOCASE, o.id
        """, (event_id,)).fetchall()


def prestiti_usciti_periodo_evento(event_id, inizio, fine):
    with get_db() as db:
        return db.execute("""
            SELECT game_id AS gioco_id, checked_out_at AS uscita,
                   returned_at AS rientro
            FROM game_library_loans
            WHERE event_id = ? AND checked_out_at >= ? AND checked_out_at < ?
            ORDER BY checked_out_at
        """, (event_id, inizio, fine)).fetchall()
