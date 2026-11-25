"""
ui/group_chat_picker.py
Checkable list of existing iMessage group chats read from chat.db.
"""

from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
    QListWidgetItem, QLabel, QPushButton, QLineEdit,
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSlot

from core.chat_db import GroupChat, get_group_chats, has_full_disk_access
from ui.styles import TEXT_SUB, TEXT_MUTED, RED, YELLOW


class _LoadThread(QThread):
    done = pyqtSignal(list, bool)   # chats, has_access

    def run(self):
        access = has_full_disk_access()
        chats = get_group_chats() if access else []
        self.done.emit(chats, access)


class GroupChatItem(QListWidgetItem):
    def __init__(self, chat: GroupChat):
        super().__init__()
        self.chat = chat
        self.setFlags(self.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        self.setCheckState(Qt.CheckState.Unchecked)
        participants_str = f"{len(chat.participants)} people"
        label = chat.label
        self.setText(f"{label}  —  {participants_str}")
        self.setToolTip(", ".join(chat.participants[:10]))


class GroupChatPicker(QWidget):
    """
    Checkable list of iMessage group chats.
    Emits selectionChanged(list[GroupChat]).
    """
    selectionChanged = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_chats: list[GroupChat] = []
        self._build_ui()
        self._load()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        # Header row
        hdr = QHBoxLayout()
        lbl = QLabel("IMESSAGE GROUP CHATS")
        lbl.setObjectName("SectionTitle")
        self._count_lbl = QLabel("Loading…")
        self._count_lbl.setObjectName("SubText")
        hdr.addWidget(lbl)
        hdr.addStretch()
        hdr.addWidget(self._count_lbl)
        lay.addLayout(hdr)

        # Permission warning (hidden by default)
        self._warn = QLabel(
            "⚠  Full Disk Access required to list group chats.\n"
            "Grant it in System Settings → Privacy & Security → Full Disk Access."
        )
        self._warn.setStyleSheet(f"color: {YELLOW}; font-size: 12px;")
        self._warn.setWordWrap(True)
        self._warn.hide()
        lay.addWidget(self._warn)

        # Search
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search group chats…")
        self._search.textChanged.connect(self._filter)
        lay.addWidget(self._search)

        # List
        self._list = QListWidget()
        self._list.setSpacing(2)
        self._list.itemChanged.connect(self._on_item_changed)
        lay.addWidget(self._list)

    def _load(self):
        self._thread = _LoadThread()
        self._thread.done.connect(self._on_loaded)
        self._thread.start()

    @pyqtSlot(list, bool)
    def _on_loaded(self, chats: list[GroupChat], has_access: bool):
        self._all_chats = chats
        if not has_access:
            self._warn.show()
            self._count_lbl.setText("No access")
        else:
            self._warn.hide()
            self._populate(chats)
            self._update_count()

    def _filter(self, query: str):
        q = query.lower()
        filtered = [
            c for c in self._all_chats
            if not q or q in c.label.lower() or any(q in p.lower() for p in c.participants)
        ]
        self._populate(filtered)
        self._update_count()

    def _populate(self, chats: list[GroupChat]):
        checked_ids = {
            self._list.item(i).chat.chat_id
            for i in range(self._list.count())
            if self._list.item(i).checkState() == Qt.CheckState.Checked
        }
        self._list.blockSignals(True)
        self._list.clear()
        for c in chats:
            item = GroupChatItem(c)
            if c.chat_id in checked_ids:
                item.setCheckState(Qt.CheckState.Checked)
            self._list.addItem(item)
        self._list.blockSignals(False)

    def _on_item_changed(self, _item):
        self.selectionChanged.emit(self._get_selected())
        self._update_count()

    def _get_selected(self) -> list[GroupChat]:
        return [
            self._list.item(i).chat
            for i in range(self._list.count())
            if self._list.item(i).checkState() == Qt.CheckState.Checked
        ]

    def _update_count(self):
        selected = len(self._get_selected())
        total = self._list.count()
        if selected:
            self._count_lbl.setText(f"{selected} of {total} selected")
        else:
            self._count_lbl.setText(f"{total} chats")

    # ── Public API ─────────────────────────────────────────────────────────

    def selected_chats(self) -> list[GroupChat]:
        return self._get_selected()

    def set_checked_ids(self, ids: set[str]):
        self._list.blockSignals(True)
        for i in range(self._list.count()):
            item = self._list.item(i)
            state = Qt.CheckState.Checked if item.chat.chat_id in ids else Qt.CheckState.Unchecked
            item.setCheckState(state)
        self._list.blockSignals(False)
        self.selectionChanged.emit(self._get_selected())
        self._update_count()

    def reload(self):
        self._load()
