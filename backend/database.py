import os
import sqlite3
from datetime import datetime

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOCAL_DB_PATH = os.path.join(BASE_DIR, "data", "app.db")

# Vercel serverless ne permet pas d'écrire dans le dépôt racine.
# Utiliser un emplacement temporaire en production Vercel.
if os.environ.get("VERCEL"):
    tmp_dir = os.environ.get("TMPDIR", "/tmp")
    DB_PATH = os.path.join(tmp_dir, "app.db")
else:
    DB_PATH = LOCAL_DB_PATH

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row

CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    role TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

CREATE_HISTORY_TABLE = """
CREATE TABLE IF NOT EXISTS user_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    session_id TEXT,
    user_message TEXT NOT NULL,
    bot_reply TEXT NOT NULL,
    vehicle TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (id)
);
"""

conn.execute(CREATE_USERS_TABLE)
conn.execute(CREATE_HISTORY_TABLE)
conn.commit()


def init_db():
    conn.execute(CREATE_USERS_TABLE)
    conn.execute(CREATE_HISTORY_TABLE)
    conn.commit()


def get_user_by_email(email: str):
    cursor = conn.execute("SELECT * FROM users WHERE email = ?", (email,))
    return cursor.fetchone()


def get_user_by_id(user_id: int):
    cursor = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return cursor.fetchone()


def create_or_update_user(email: str, name: str, role: str):
    now = datetime.utcnow().isoformat()
    existing = get_user_by_email(email)
    if existing:
        conn.execute(
            "UPDATE users SET name = ?, role = ?, updated_at = ? WHERE email = ?",
            (name, role, now, email)
        )
        conn.commit()
        return get_user_by_email(email)

    cursor = conn.execute(
        "INSERT INTO users (email, name, role, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (email, name, role, now, now)
    )
    conn.commit()
    return get_user_by_id(cursor.lastrowid)


def save_user_history(user_id: int, session_id: str, user_message: str, bot_reply: str, vehicle: str | None = None):
    now = datetime.utcnow().isoformat()
    conn.execute(
        "INSERT INTO user_history (user_id, session_id, user_message, bot_reply, vehicle, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, session_id, user_message, bot_reply, vehicle, now)
    )
    conn.commit()


def get_user_history(user_id: int, limit: int = 40):
    cursor = conn.execute(
        "SELECT id, session_id, user_message, bot_reply, vehicle, created_at FROM user_history WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, limit)
    )
    return [dict(row) for row in cursor.fetchall()]
