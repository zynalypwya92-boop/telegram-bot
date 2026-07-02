"""
database.py
مدیریت ذخیره‌سازی تریگرهای شخصی‌سازی‌شده در دیتابیس SQLite.
هر چت (خصوصی یا گروه) تریگرهای مخصوص به خودش رو داره.
"""

import sqlite3
from contextlib import contextmanager

DB_PATH = "bot_data.db"


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS triggers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                keyword TEXT NOT NULL,
                response TEXT NOT NULL,
                match_type TEXT NOT NULL DEFAULT 'contains',
                UNIQUE(chat_id, keyword)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reply_triggers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                keyword TEXT NOT NULL,
                response TEXT NOT NULL,
                UNIQUE(chat_id, keyword)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS joke_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS seen_users (
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                username TEXT,
                first_name TEXT,
                last_seen_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (chat_id, user_id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS nicknames (
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                nickname TEXT NOT NULL,
                PRIMARY KEY (chat_id, user_id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS recent_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                username TEXT,
                text TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def add_trigger(chat_id: int, keyword: str, response: str, match_type: str = "contains"):
    keyword = keyword.strip().lower()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO triggers (chat_id, keyword, response, match_type)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(chat_id, keyword)
            DO UPDATE SET response = excluded.response, match_type = excluded.match_type
            """,
            (chat_id, keyword, response, match_type),
        )


def remove_trigger(chat_id: int, keyword: str) -> bool:
    keyword = keyword.strip().lower()
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM triggers WHERE chat_id = ? AND keyword = ?",
            (chat_id, keyword),
        )
        return cur.rowcount > 0


def list_triggers(chat_id: int):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT keyword, response, match_type FROM triggers WHERE chat_id = ? ORDER BY keyword",
            (chat_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def find_matching_trigger(chat_id: int, text: str):
    """
    متن ورودی رو با تریگرهای ثبت‌شده مقایسه می‌کنه.
    match_type == 'exact' یعنی باید دقیقاً برابر باشه.
    match_type == 'contains' یعنی کافیه کلمه داخل متن باشه.
    """
    text_lower = text.lower().strip()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT keyword, response, match_type FROM triggers WHERE chat_id = ?",
            (chat_id,),
        ).fetchall()

    for row in rows:
        kw = row["keyword"]
        if row["match_type"] == "exact":
            if text_lower == kw:
                return row["response"]
        else:
            if kw in text_lower:
                return row["response"]
    return None


# ---------- تریگرهای ریپلای (نوع دوم: فقط وقتی روی پیام مالک ریپلای بشه) ----------

def add_reply_trigger(chat_id: int, keyword: str, response: str):
    keyword = keyword.strip().lower()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO reply_triggers (chat_id, keyword, response)
            VALUES (?, ?, ?)
            ON CONFLICT(chat_id, keyword)
            DO UPDATE SET response = excluded.response
            """,
            (chat_id, keyword, response),
        )


def remove_reply_trigger(chat_id: int, keyword: str) -> bool:
    keyword = keyword.strip().lower()
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM reply_triggers WHERE chat_id = ? AND keyword = ?",
            (chat_id, keyword),
        )
        return cur.rowcount > 0


def list_reply_triggers(chat_id: int):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT keyword, response FROM reply_triggers WHERE chat_id = ? ORDER BY keyword",
            (chat_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def find_matching_reply_trigger(chat_id: int, text: str):
    text_lower = text.lower().strip()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT keyword, response FROM reply_triggers WHERE chat_id = ?",
            (chat_id,),
        ).fetchall()
    for row in rows:
        if row["keyword"] in text_lower:
            return row["response"]
    return None


# ---------- تاریخچه‌ی جوک‌ها (برای جلوگیری از تکرار) ----------

def save_joke(chat_id: int, text: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO joke_history (chat_id, text) VALUES (?, ?)",
            (chat_id, text),
        )
        # فقط ۱۵ تای آخر رو نگه دار
        conn.execute(
            """
            DELETE FROM joke_history WHERE chat_id = ? AND id NOT IN (
                SELECT id FROM joke_history WHERE chat_id = ? ORDER BY id DESC LIMIT 15
            )
            """,
            (chat_id, chat_id),
        )


def get_recent_jokes(chat_id: int, limit: int = 15):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT text FROM joke_history WHERE chat_id = ? ORDER BY id DESC LIMIT ?",
            (chat_id, limit),
        ).fetchall()
        return [r["text"] for r in rows]


# ---------- کاربران دیده‌شده (برای قابلیت تگ) ----------

def upsert_seen_user(chat_id: int, user_id: int, username: str, first_name: str):
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO seen_users (chat_id, user_id, username, first_name, last_seen_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(chat_id, user_id)
            DO UPDATE SET username = excluded.username, first_name = excluded.first_name,
                          last_seen_at = CURRENT_TIMESTAMP
            """,
            (chat_id, user_id, username, first_name),
        )


def get_all_seen_users(chat_id: int):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT user_id, username, first_name FROM seen_users WHERE chat_id = ?",
            (chat_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_active_users(chat_id: int, hours: int = 24):
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT user_id, username, first_name FROM seen_users
            WHERE chat_id = ? AND last_seen_at >= datetime('now', ?)
            """,
            (chat_id, f"-{hours} hours"),
        ).fetchall()
        return [dict(r) for r in rows]


# ---------- لقب‌ها ----------

def set_nickname(chat_id: int, user_id: int, nickname: str):
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO nicknames (chat_id, user_id, nickname) VALUES (?, ?, ?)
            ON CONFLICT(chat_id, user_id) DO UPDATE SET nickname = excluded.nickname
            """,
            (chat_id, user_id, nickname),
        )


def get_nickname(chat_id: int, user_id: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT nickname FROM nicknames WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id),
        ).fetchone()
        return row["nickname"] if row else None


# ---------- پیام‌های اخیر (برای خلاصه‌ی هوش مصنوعی) ----------

def save_recent_message(chat_id: int, username: str, text: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO recent_messages (chat_id, username, text) VALUES (?, ?, ?)",
            (chat_id, username, text),
        )


def get_and_clear_recent_messages(chat_id: int):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT username, text FROM recent_messages WHERE chat_id = ? ORDER BY id",
            (chat_id,),
        ).fetchall()
        conn.execute("DELETE FROM recent_messages WHERE chat_id = ?", (chat_id,))
        return [dict(r) for r in rows]


def get_all_chats_with_recent_messages():
    with get_conn() as conn:
        rows = conn.execute("SELECT DISTINCT chat_id FROM recent_messages").fetchall()
        return [r["chat_id"] for r in rows]


def delete_all_triggers(chat_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM triggers WHERE chat_id = ?", (chat_id,))


def delete_all_reply_triggers(chat_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM reply_triggers WHERE chat_id = ?", (chat_id,))
