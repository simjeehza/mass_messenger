"""
core/groups.py
SQLite-backed storage for named groups of contacts + group chats.
"""

from __future__ import annotations
import sqlite3
import json
from pathlib import Path

DB_PATH = Path.home() / "Library" / "Application Support" / "MassMessenger" / "data.db"


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    _init_schema(conn)
    return conn


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS groups (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS group_members (
            group_id       INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
            contact_id     TEXT NOT NULL,
            contact_name   TEXT NOT NULL,
            handle         TEXT NOT NULL,
            PRIMARY KEY (group_id, contact_id)
        );

        -- iMessage group chats attached to a group
        CREATE TABLE IF NOT EXISTS group_chats (
            group_id     INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
            chat_id      TEXT NOT NULL,
            display_name TEXT NOT NULL DEFAULT '',
            PRIMARY KEY (group_id, chat_id)
        );

        CREATE TABLE IF NOT EXISTS scheduled_messages (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id    INTEGER REFERENCES groups(id) ON DELETE SET NULL,
            handles     TEXT NOT NULL,
            group_chats TEXT NOT NULL DEFAULT '[]',
            messages    TEXT NOT NULL,
            send_at     TEXT NOT NULL,
            status      TEXT NOT NULL DEFAULT 'pending',
            created_at  TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)
    # Migration: add group_chats column to scheduled_messages if missing
    try:
        conn.execute("ALTER TABLE scheduled_messages ADD COLUMN group_chats TEXT NOT NULL DEFAULT '[]'")
        conn.commit()
    except Exception:
        pass  # column already exists
    conn.commit()


# ── Groups ────────────────────────────────────────────────────────────────────

def list_groups() -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute("SELECT id, name FROM groups ORDER BY name").fetchall()
        return [dict(r) for r in rows]


def create_group(name: str) -> int:
    with _get_conn() as conn:
        cur = conn.execute("INSERT INTO groups (name) VALUES (?)", (name,))
        conn.commit()
        return cur.lastrowid


def delete_group(group_id: int) -> None:
    with _get_conn() as conn:
        conn.execute("DELETE FROM groups WHERE id=?", (group_id,))
        conn.commit()


def rename_group(group_id: int, new_name: str) -> None:
    with _get_conn() as conn:
        conn.execute("UPDATE groups SET name=? WHERE id=?", (new_name, group_id))
        conn.commit()


# ── Contact members ───────────────────────────────────────────────────────────

def get_members(group_id: int) -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT contact_id, contact_name, handle FROM group_members WHERE group_id=? ORDER BY contact_name",
            (group_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def set_members(group_id: int, members: list[dict]) -> None:
    """Replace all contact members. Each: {contact_id, contact_name, handle}."""
    with _get_conn() as conn:
        conn.execute("DELETE FROM group_members WHERE group_id=?", (group_id,))
        conn.executemany(
            "INSERT INTO group_members (group_id, contact_id, contact_name, handle) VALUES (?,?,?,?)",
            [(group_id, m["contact_id"], m["contact_name"], m["handle"]) for m in members],
        )
        conn.commit()


# ── Group chat members ────────────────────────────────────────────────────────

def get_group_chats(group_id: int) -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT chat_id, display_name FROM group_chats WHERE group_id=? ORDER BY display_name",
            (group_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def set_group_chats(group_id: int, chats: list[dict]) -> None:
    """Replace all group chat members. Each: {chat_id, display_name}."""
    with _get_conn() as conn:
        conn.execute("DELETE FROM group_chats WHERE group_id=?", (group_id,))
        conn.executemany(
            "INSERT INTO group_chats (group_id, chat_id, display_name) VALUES (?,?,?)",
            [(group_id, c["chat_id"], c.get("display_name", "")) for c in chats],
        )
        conn.commit()


# ── Scheduled messages ────────────────────────────────────────────────────────

def schedule_message(
    handles: list[str],
    messages: list[str],
    send_at: str,
    group_id: int | None = None,
    group_chat_ids: list[str] | None = None,
) -> int:
    with _get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO scheduled_messages (group_id, handles, group_chats, messages, send_at) VALUES (?,?,?,?,?)",
            (group_id, json.dumps(handles), json.dumps(group_chat_ids or []), json.dumps(messages), send_at),
        )
        conn.commit()
        return cur.lastrowid


def get_pending_scheduled() -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM scheduled_messages WHERE status='pending' ORDER BY send_at"
        ).fetchall()
        return _parse_scheduled(rows)


def get_all_scheduled() -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM scheduled_messages ORDER BY send_at DESC LIMIT 200"
        ).fetchall()
        return _parse_scheduled(rows)


def _parse_scheduled(rows) -> list[dict]:
    result = []
    for r in rows:
        d = dict(r)
        d["handles"] = json.loads(d["handles"])
        d["messages"] = json.loads(d["messages"])
        d["group_chats"] = json.loads(d.get("group_chats") or "[]")
        result.append(d)
    return result


def mark_scheduled_status(msg_id: int, status: str) -> None:
    with _get_conn() as conn:
        conn.execute("UPDATE scheduled_messages SET status=? WHERE id=?", (status, msg_id))
        conn.commit()


def delete_scheduled(msg_id: int) -> None:
    with _get_conn() as conn:
        conn.execute("DELETE FROM scheduled_messages WHERE id=?", (msg_id,))
        conn.commit()
