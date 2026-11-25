"""
core/chat_db.py
Reads ~/Library/Messages/chat.db to get:
  - recently-texted handle order (for contact sort toggle)
  - list of existing iMessage group chats
Requires Full Disk Access permission on macOS 12+.
"""

from __future__ import annotations
import sqlite3
import sys
from pathlib import Path
from dataclasses import dataclass, field

CHAT_DB = Path.home() / "Library" / "Messages" / "chat.db"


@dataclass
class GroupChat:
    chat_id: str          # internal chat identifier used by AppleScript
    display_name: str     # group chat name (e.g. "Weekend Crew")
    participants: list[str] = field(default_factory=list)  # handles

    @property
    def label(self) -> str:
        if self.display_name:
            return self.display_name
        if self.participants:
            return ", ".join(self.participants[:3]) + (" …" if len(self.participants) > 3 else "")
        return self.chat_id


def _open_db() -> sqlite3.Connection | None:
    if sys.platform != "darwin":
        return None
    if not CHAT_DB.exists():
        return None
    try:
        conn = sqlite3.connect(f"file:{CHAT_DB}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as exc:
        print(f"[chat_db] Cannot open chat.db: {exc}")
        return None


def has_full_disk_access() -> bool:
    """Quick check — if we can open chat.db we have access."""
    conn = _open_db()
    if conn:
        conn.close()
        return True
    return False


# ── Recently texted order ─────────────────────────────────────────────────────

def get_recent_handle_order() -> dict[str, int]:
    """
    Returns {normalized_handle: rank} where rank=0 is most recently texted.
    Handles are phone numbers or emails as stored in the handle table.
    """
    conn = _open_db()
    if not conn:
        return {}

    try:
        rows = conn.execute("""
            SELECT h.id AS handle, MAX(m.date) AS last_date
            FROM message m
            JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
            JOIN chat_handle_join chj ON cmj.chat_id = chj.chat_id
            JOIN handle h ON chj.handle_id = h.ROWID
            WHERE m.date IS NOT NULL
            GROUP BY h.id
            ORDER BY last_date DESC
        """).fetchall()
        return {row["handle"]: i for i, row in enumerate(rows)}
    except Exception as exc:
        print(f"[chat_db] recent handle query failed: {exc}")
        return {}
    finally:
        conn.close()


# ── Group chats ───────────────────────────────────────────────────────────────

def get_group_chats() -> list[GroupChat]:
    """
    Returns all iMessage group chats (2+ participants with a chat_identifier).
    Sorted by most recently active first.
    """
    conn = _open_db()
    if not conn:
        return _stub_group_chats()

    try:
        # Get chats that have > 1 participant (group chats)
        chat_rows = conn.execute("""
            SELECT
                c.ROWID        AS rowid,
                c.chat_identifier,
                c.display_name,
                MAX(m.date)    AS last_date
            FROM chat c
            LEFT JOIN chat_message_join cmj ON c.ROWID = cmj.chat_id
            LEFT JOIN message m ON cmj.message_id = m.ROWID
            WHERE c.style = 43   -- group chat style
            GROUP BY c.ROWID
            ORDER BY last_date DESC NULLS LAST
        """).fetchall()

        chats: list[GroupChat] = []
        for row in chat_rows:
            # Get participants
            handle_rows = conn.execute("""
                SELECT h.id FROM handle h
                JOIN chat_handle_join chj ON h.ROWID = chj.handle_id
                WHERE chj.chat_id = ?
            """, (row["rowid"],)).fetchall()

            participants = [r["id"] for r in handle_rows]
            if len(participants) < 2:
                continue  # skip 1-on-1s that slipped through

            chats.append(GroupChat(
                chat_id=row["chat_identifier"],
                display_name=row["display_name"] or "",
                participants=participants,
            ))

        return chats

    except Exception as exc:
        print(f"[chat_db] group chat query failed: {exc}")
        return []
    finally:
        conn.close()


def _stub_group_chats() -> list[GroupChat]:
    """Dev stubs when not on macOS or no DB access."""
    return [
        GroupChat("chat001", "Weekend Crew", ["+15550001111", "+15550002222", "+15550003333"]),
        GroupChat("chat002", "Family", ["+15550004444", "+15550005555"]),
        GroupChat("chat003", "", ["+15550006666", "+15550007777", "+15550008888"]),
    ]
