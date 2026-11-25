"""
core/scheduler.py
Wraps APScheduler to fire scheduled message sends at the right time.
"""

from __future__ import annotations
from datetime import datetime
from typing import Callable

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.date import DateTrigger
    HAS_APSCHEDULER = True
except ImportError:
    HAS_APSCHEDULER = False

from core import groups as db
from core.messenger import send_bulk


class MessageScheduler:
    def __init__(self, on_sent: Callable[[int, bool], None] | None = None):
        self.on_sent = on_sent
        self._scheduler: "BackgroundScheduler | None" = None

        if HAS_APSCHEDULER:
            self._scheduler = BackgroundScheduler()
            self._scheduler.start()
            self._reload_pending()

    def _reload_pending(self) -> None:
        if not self._scheduler:
            return
        for item in db.get_pending_scheduled():
            self._register(item)

    def _register(self, item: dict) -> None:
        if not self._scheduler:
            return
        try:
            send_at = datetime.fromisoformat(item["send_at"])
        except ValueError:
            return

        if send_at <= datetime.now():
            self._fire(item["id"])
            return

        self._scheduler.add_job(
            func=self._fire,
            trigger=DateTrigger(run_date=send_at),
            args=[item["id"]],
            id=f"sched_{item['id']}",
            replace_existing=True,
        )

    def _fire(self, scheduled_id: int) -> None:
        pending = {s["id"]: s for s in db.get_pending_scheduled()}
        item = pending.get(scheduled_id)
        if not item:
            return

        results = send_bulk(
            item["handles"],
            item["messages"],
            group_chat_ids=item.get("group_chats", []),
        )
        all_ok = all(ok for hr in results.values() for ok, _ in hr)
        db.mark_scheduled_status(scheduled_id, "sent" if all_ok else "failed")

        if self.on_sent:
            self.on_sent(scheduled_id, all_ok)

    def add(self, handles: list[str], messages: list[str], send_at: datetime,
            group_id: int | None = None, group_chat_ids: list[str] | None = None) -> int:
        """Schedule a bulk send. Returns the DB id."""
        sched_id = db.schedule_message(
            handles, messages, send_at.isoformat(), group_id, group_chat_ids
        )
        item = {
            "id": sched_id,
            "handles": handles,
            "messages": messages,
            "send_at": send_at.isoformat(),
            "group_chats": group_chat_ids or [],
        }
        self._register(item)
        return sched_id

    def cancel(self, scheduled_id: int) -> None:
        if self._scheduler:
            job_id = f"sched_{scheduled_id}"
            if self._scheduler.get_job(job_id):
                self._scheduler.remove_job(job_id)
        db.delete_scheduled(scheduled_id)

    def shutdown(self) -> None:
        if self._scheduler:
            self._scheduler.shutdown(wait=False)
