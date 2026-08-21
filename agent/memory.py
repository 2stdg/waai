import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.environ.get("DB_PATH", str(Path(__file__).parent.parent / "bot.db")))


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone_number TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_phone ON messages(phone_number, id)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS estado_conversacion (
            phone_number TEXT PRIMARY KEY,
            escalada INTEGER NOT NULL DEFAULT 0,
            motivo TEXT,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    return conn


def save_message(phone_number: str, role: str, content: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO messages (phone_number, role, content) VALUES (?, ?, ?)",
            (phone_number, role, content),
        )


def get_history(phone_number: str, limit: int = 20) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE phone_number = ? "
            "ORDER BY id DESC LIMIT ?",
            (phone_number, limit),
        ).fetchall()
    return [{"role": r, "content": c} for r, c in reversed(rows)]


def is_escalated(phone_number: str) -> bool:
    with _connect() as conn:
        row = conn.execute(
            "SELECT escalada FROM estado_conversacion WHERE phone_number = ?",
            (phone_number,),
        ).fetchone()
    return bool(row and row[0])


def set_escalated(phone_number: str, motivo: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO estado_conversacion (phone_number, escalada, motivo, updated_at) "
            "VALUES (?, 1, ?, datetime('now')) "
            "ON CONFLICT(phone_number) DO UPDATE SET escalada=1, motivo=excluded.motivo, "
            "updated_at=datetime('now')",
            (phone_number, motivo),
        )


def clear_escalated(phone_number: str) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE estado_conversacion SET escalada = 0 WHERE phone_number = ?",
            (phone_number,),
        )
