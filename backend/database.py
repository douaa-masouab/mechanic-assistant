import os
import sqlite3
import hashlib
from datetime import datetime

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOCAL_DB_PATH = os.path.join(BASE_DIR, "data", "app.db")

if os.environ.get("VERCEL"):
    tmp_dir = os.environ.get("TMPDIR", "/tmp")
    DB_PATH = os.path.join(tmp_dir, "app.db")
else:
    DB_PATH = LOCAL_DB_PATH

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA journal_mode=WAL")

# ─── Schéma des tables ─────────────────────────────────────────────────────────

CREATE_APP_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS app_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
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
    FOREIGN KEY (user_id) REFERENCES app_users (id) ON DELETE CASCADE
);
"""

# Tables de compatibilité ascendante (gardées pour ne pas casser le chatbot existant)
CREATE_LEGACY_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    role TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

CREATE_REGISTERED_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS registered_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    code TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""

conn.execute(CREATE_APP_USERS_TABLE)
conn.execute(CREATE_HISTORY_TABLE)
conn.execute(CREATE_LEGACY_USERS_TABLE)
conn.execute(CREATE_REGISTERED_USERS_TABLE)
conn.commit()


def init_db():
    conn.execute(CREATE_APP_USERS_TABLE)
    conn.execute(CREATE_HISTORY_TABLE)
    conn.execute(CREATE_LEGACY_USERS_TABLE)
    conn.execute(CREATE_REGISTERED_USERS_TABLE)
    conn.commit()


# ─── Utilitaires ───────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Hache un mot de passe avec SHA-256."""
    return hashlib.sha256(password.strip().encode("utf-8")).hexdigest()


# ─── Authentification (app_users) ──────────────────────────────────────────────

def get_app_user_by_email(email: str):
    cursor = conn.execute(
        "SELECT * FROM app_users WHERE email = ?", (email.strip().lower(),)
    )
    return cursor.fetchone()


def get_app_user_by_id(user_id: int):
    cursor = conn.execute("SELECT * FROM app_users WHERE id = ?", (user_id,))
    return cursor.fetchone()


def register_user(name: str, email: str, password: str) -> dict:
    """Inscrit un nouvel utilisateur. Lève ValueError si l'email existe déjà."""
    email_clean = email.strip().lower()
    existing = get_app_user_by_email(email_clean)
    if existing:
        raise ValueError("Cet email est déjà utilisé. Veuillez vous connecter.")

    now = datetime.utcnow().isoformat()
    password_hash = hash_password(password)

    cursor = conn.execute(
        "INSERT INTO app_users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
        (name.strip(), email_clean, password_hash, now)
    )
    conn.commit()
    return {"id": cursor.lastrowid, "name": name.strip(), "email": email_clean, "created_at": now}


def login_user(email: str, password: str) -> dict:
    """Vérifie les identifiants. Lève ValueError si incorrect."""
    email_clean = email.strip().lower()
    user = get_app_user_by_email(email_clean)

    if not user:
        raise ValueError("Aucun compte trouvé avec cet email.")

    user_dict = dict(user)
    if user_dict["password_hash"] != hash_password(password):
        raise ValueError("Mot de passe incorrect.")

    return user_dict


# ─── Historique (user_history) ─────────────────────────────────────────────────

def save_user_history(user_id: int, session_id: str = "", user_message: str = "", bot_reply: str = "", vehicle: str | None = None, message: str = "", response: str = ""):
    """Enregistre un échange dans l'historique de l'utilisateur."""
    final_message = user_message or message
    final_reply = bot_reply or response
    now = datetime.utcnow().isoformat()
    conn.execute(
        "INSERT INTO user_history (user_id, session_id, user_message, bot_reply, vehicle, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, session_id, final_message, final_reply, vehicle, now)
    )
    conn.commit()


def get_user_history(user_id: int, limit: int = 50):
    """Retourne l'historique d'un utilisateur, du plus récent au plus ancien."""
    cursor = conn.execute(
        "SELECT h.id, h.session_id, h.user_message, h.bot_reply, h.vehicle, h.created_at, u.name as user_name, u.email as user_email "
        "FROM user_history h "
        "JOIN app_users u ON h.user_id = u.id "
        "WHERE h.user_id = ? ORDER BY h.id DESC LIMIT ?",
        (user_id, limit)
    )
    return [dict(row) for row in cursor.fetchall()]


def delete_history_entry(entry_id: int, user_id: int) -> bool:
    """Supprime une entrée d'historique. Vérifie que l'entrée appartient à l'utilisateur."""
    cursor = conn.execute(
        "DELETE FROM user_history WHERE id = ? AND user_id = ?",
        (entry_id, user_id)
    )
    conn.commit()
    return cursor.rowcount > 0


def delete_all_user_history(user_id: int):
    """Supprime tout l'historique d'un utilisateur."""
    conn.execute("DELETE FROM user_history WHERE user_id = ?", (user_id,))
    conn.commit()


# ─── Compatibilité ascendante (anciens systèmes) ───────────────────────────────

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


def get_registered_user_by_name(name: str):
    cursor = conn.execute("SELECT * FROM registered_users WHERE name = ?", (name.strip(),))
    return cursor.fetchone()


def verify_registered_user(name: str, code: str) -> dict:
    name_clean = name.strip()
    code_clean = code.strip()
    existing = get_registered_user_by_name(name_clean)
    if existing:
        user_dict = dict(existing)
        if user_dict["code"] != code_clean:
            raise ValueError("Code d'accès incorrect pour cet utilisateur.")
        return user_dict
    now = datetime.utcnow().isoformat()
    cursor = conn.execute(
        "INSERT INTO registered_users (name, code, created_at) VALUES (?, ?, ?)",
        (name_clean, code_clean, now)
    )
    conn.commit()
    return {"id": cursor.lastrowid, "name": name_clean, "code": code_clean, "created_at": now}
