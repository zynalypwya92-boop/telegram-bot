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
