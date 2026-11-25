"""
ui/schedule_tab.py
View, manage, and cancel scheduled messages.
"""

from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QMessageBox,
)
from PyQt6.QtCore import Qt, QTimer

from ui.styles import GREEN, RED, YELLOW, TEXT_SUB, TEXT_MUTED
from core import groups as db


STATUS_COLORS = {
    "pending": YELLOW,
    "sent":    GREEN,
    "failed":  RED,
}


class ScheduleTab(QWidget):
    def __init__(self, scheduler=None, parent=None):
        super().__init__(parent)
        self._scheduler = scheduler
        self._build_ui()
        self._refresh()

        # Auto-refresh every 30 s
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(30_000)

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(10)

        top_row = QHBoxLayout()
        lbl = QLabel("SCHEDULED MESSAGES")
        lbl.setObjectName("SectionTitle")
        refresh_btn = QPushButton("↻  Refresh")
        refresh_btn.setObjectName("GhostBtn")
        refresh_btn.clicked.connect(self._refresh)
        top_row.addWidget(lbl)
        top_row.addStretch()
        top_row.addWidget(refresh_btn)
        lay.addLayout(top_row)

        self._tree = QTreeWidget()
        self._tree.setColumnCount(5)
        self._tree.setHeaderLabels(["Send At", "Status", "Recipients", "Messages", ""])
        self._tree.setColumnWidth(0, 180)
        self._tree.setColumnWidth(1, 80)
        self._tree.setColumnWidth(2, 200)
        self._tree.setColumnWidth(3, 260)
        self._tree.setColumnWidth(4, 80)
        self._tree.setRootIsDecorated(False)
        self._tree.setAlternatingRowColors(False)
        lay.addWidget(self._tree)

        self._empty_lbl = QLabel("No scheduled messages.")
        self._empty_lbl.setObjectName("SubText")
        self._empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._empty_lbl)

    def _refresh(self):
        self._tree.clear()
        items = db.get_all_scheduled()

        self._empty_lbl.setVisible(len(items) == 0)
        self._tree.setVisible(len(items) > 0)

        for s in items:
            from datetime import datetime
            try:
                dt = datetime.fromisoformat(s["send_at"])
                send_at_str = dt.strftime("%b %d, %Y  %I:%M %p")
            except Exception:
                send_at_str = s["send_at"]

            recipients = ", ".join(s["handles"][:3])
            if len(s["handles"]) > 3:
                recipients += f" +{len(s['handles']) - 3} more"

            msg_preview = " → ".join(m[:40] + ("…" if len(m) > 40 else "") for m in s["messages"])

            item = QTreeWidgetItem([
                send_at_str,
                s["status"].upper(),
                recipients,
                msg_preview,
                "",
            ])

            color = STATUS_COLORS.get(s["status"], TEXT_SUB)
            item.setForeground(1, _color(color))
            item.setData(0, Qt.ItemDataRole.UserRole, s["id"])

            self._tree.addTopLevelItem(item)

            # Cancel button only for pending
            if s["status"] == "pending":
                cancel_btn = QPushButton("Cancel")
                cancel_btn.setObjectName("DangerBtn")
                cancel_btn.setFixedSize(70, 26)
                cancel_btn.clicked.connect(lambda _, sid=s["id"]: self._cancel(sid))
                self._tree.setItemWidget(item, 4, cancel_btn)

    def _cancel(self, scheduled_id: int):
        confirm = QMessageBox.question(
            self, "Cancel send",
            "Cancel this scheduled message?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        if self._scheduler:
            self._scheduler.cancel(scheduled_id)
        else:
            db.delete_scheduled(scheduled_id)
        self._refresh()

    def set_scheduler(self, scheduler):
        self._scheduler = scheduler

    def refresh(self):
        self._refresh()


def _color(hex_color: str):
    from PyQt6.QtGui import QColor
    return QColor(hex_color)
