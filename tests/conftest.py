"""Isolate all tests from the application's real database and configuration."""

import sqlite3
from pathlib import Path

import pytest

from ludox import config, database


@pytest.fixture(autouse=True)
def isolated_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(database, "PROJECT_DIR", tmp_path)
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(config, "PROJECT_DIR", tmp_path)
    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "config.ini")
    # Default path arguments are bound at import time: config tests must always
    # pass their temporary INI path explicitly.
    original_connect = sqlite3.connect
    connections = []

    def temporary_connect(path, *args, **kwargs):
        resolved = Path(path).resolve()
        if not resolved.is_relative_to(tmp_path.resolve()):
            raise AssertionError("Tests may only connect to temporary databases")
        connection = original_connect(path, *args, **kwargs)
        connections.append(connection)
        return connection

    monkeypatch.setattr(sqlite3, "connect", temporary_connect)
    yield tmp_path
    # SQLite's connection context manager commits/rolls back, but does not close.
    for connection in connections:
        connection.close()


@pytest.fixture
def db():
    database.init_db()
    connection = database.get_db()
    yield connection
    connection.close()


@pytest.fixture
def catalog(db):
    """SQL is test data preparation, not a replacement for UI operations."""
    db.executemany(
        "INSERT INTO giochi(id, nome, attivo) VALUES (?, ?, ?)",
        [(1, "Azul", 1), (2, "Cascadia", 1), (3, "Disattivo", 0), (4, "Vuoto", 1)],
    )
    db.executemany(
        "INSERT INTO proprietari(id, nome, attivo) VALUES (?, ?, ?)",
        [(2, "Biblioteca", 1), (3, "Privato", 0)],
    )
    db.executemany(
        "INSERT INTO copie_gioco(gioco_id, proprietario_id, quantita) VALUES (?, ?, ?)",
        [(1, 2, 2), (1, 3, 1), (2, 2, 1), (3, 2, 2)],
    )
    db.commit()
    return db
