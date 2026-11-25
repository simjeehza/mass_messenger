"""
ui/compose_tab.py
Main compose view: contact picker + group chat picker, message editor, send/schedule.
"""

from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLabel, QTextEdit, QListWidget,
    QListWidgetItem, QGroupBox, QDateTimeEdit,
    QMessageBox, QComboBox, QFrame, QTabWidget,
)
from PyQt6.QtCore import Qt, QDateTime, QThread, pyqtSignal, pyqtSlot

from ui.contact_picker import ContactPicker
from ui.group_chat_picker import GroupChatPicker
from ui.styles import GREEN, RED, BLUE, TEXT_SUB, BORDER
from core.contacts import Contact
from core.chat_db import GroupChat
from core import groups as db


# ── Background send thread ────────────────────────────────────────────────────

class SendThread(QThread):
    progress = pyqtSignal(str, int, int, bool, str)
    finished = pyqtSignal(dict)

    def __init__(self, handles, group_chat_ids, messages):
        super().__init__()
        self.handles = handles
        self.group_chat_ids = group_chat_ids
        self.messages = messages

    def run(self):
        from core.messenger import send_bulk
        results = send_bulk(
            self.handles,
            self.messages,
            group_chat_ids=self.group_chat_ids,
            progress_cb=lambda h, mi, t, ok, err: self.progress.emit(h, mi, t, ok, err),
        )
        self.finished.emit(results)


# ── Message sequence editor ───────────────────────────────────────────────────

class MessageEditor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        title_row = QHBoxLayout()
        lbl = QLabel("MESSAGES")
        lbl.setObjectName("SectionTitle")
        add_btn = QPushButton("+ Add message")
        add_btn.setObjectName("GhostBtn")
        add_btn.clicked.connect(self._add_box)
        reset_btn = QPushButton("↺ Reset")
        reset_btn.setObjectName("GhostBtn")
        reset_btn.setToolTip("Clear all messages and start fresh")
        reset_btn.clicked.connect(self.clear)
        title_row.addWidget(lbl)
        title_row.addStretch()
        title_row.addWidget(reset_btn)
        title_row.addWidget(add_btn)
        lay.addLayout(title_row)

        self._boxes_layout = QVBoxLayout()
        self._boxes_layout.setSpacing(6)
        lay.addLayout(self._boxes_layout)

        self._boxes: list[QWidget] = []
        self._add_box()

    def _add_box(self):
        idx = len(self._boxes) + 1
        wrapper = QWidget()
        wl = QVBoxLayout(wrapper)
        wl.setContentsMargins(0, 0, 0, 0)
        wl.setSpacing(3)

        header = QHBoxLayout()
        num_lbl = QLabel(f"Message {idx}")
        num_lbl.setObjectName("SubText")
        remove_btn = QPushButton("✕")
        remove_btn.setObjectName("GhostBtn")
        remove_btn.setFixedSize(24, 24)
        remove_btn.setToolTip("Remove this message" if idx > 1 else "Clear this message")
        remove_btn.clicked.connect(lambda: self._remove_box(wrapper))

        header.addWidget(num_lbl)
        header.addStretch()
        header.addWidget(remove_btn)   # always visible

        box = QTextEdit()
        box.setPlaceholderText("Type your message here…")
        box.setFixedHeight(90)
        wl.addLayout(header)
        wl.addWidget(box)

        wrapper._text_box = box
        self._boxes.append(wrapper)
        self._boxes_layout.addWidget(wrapper)

    def _remove_box(self, wrapper):
        if len(self._boxes) <= 1:
            # Only one box — just clear its text instead of removing
            wrapper._text_box.clear()
            return
        self._boxes.remove(wrapper)
        wrapper.deleteLater()
        self._renumber()

    def _renumber(self):
        for i, w in enumerate(self._boxes):
            for child in w.findChildren(QLabel):
                child.setText(f"Message {i + 1}")

    def get_messages(self) -> list[str]:
        return [w._text_box.toPlainText().strip() for w in self._boxes
                if w._text_box.toPlainText().strip()]

    def clear(self):
        for w in list(self._boxes):
            self._boxes_layout.removeWidget(w)
            w.deleteLater()
        self._boxes.clear()
        self._add_box()


# ── Compose tab ───────────────────────────────────────────────────────────────

class ComposeTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected_contacts: list[Contact] = []
        self._selected_group_chats: list[GroupChat] = []
        self._send_thread: SendThread | None = None
        self._build_ui()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)

        # ── Left: recipient pickers in sub-tabs ───────────────────────────
        left = QWidget()
        left.setMinimumWidth(300)
        left.setMaximumWidth(440)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(0)

        self._picker_tabs = QTabWidget()
        self._picker_tabs.setDocumentMode(True)

        # Tab 1: individual contacts
        contacts_widget = QWidget()
        cl = QVBoxLayout(contacts_widget)
        cl.setContentsMargins(12, 12, 12, 12)
        cl.setSpacing(8)

        self._picker = ContactPicker()
        self._picker.selectionChanged.connect(self._on_contacts_changed)
        cl.addWidget(self._picker)

        # Group load shortcut
        grp_row = QHBoxLayout()
        grp_lbl = QLabel("Load group:")
        grp_lbl.setObjectName("SubText")
        self._group_combo = QComboBox()
        self._group_combo.setMinimumWidth(120)
        self._group_combo.addItem("— select —", None)
        self._refresh_group_combo()
        load_grp_btn = QPushButton("Load")
        load_grp_btn.clicked.connect(self._load_group)
        grp_row.addWidget(grp_lbl)
        grp_row.addWidget(self._group_combo, 1)
        grp_row.addWidget(load_grp_btn)
        cl.addLayout(grp_row)

        self._picker_tabs.addTab(contacts_widget, "👤  Contacts")

        # Tab 2: group chats
        gc_widget = QWidget()
        gcl = QVBoxLayout(gc_widget)
        gcl.setContentsMargins(12, 12, 12, 12)
        self._gc_picker = GroupChatPicker()
        self._gc_picker.selectionChanged.connect(self._on_gc_changed)
        gcl.addWidget(self._gc_picker)
        self._picker_tabs.addTab(gc_widget, "💬  Group Chats")

        ll.addWidget(self._picker_tabs)
        splitter.addWidget(left)

        # ── Right: compose area ───────────────────────────────────────────
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(20, 16, 20, 16)
        rl.setSpacing(14)

        self._recip_label = QLabel("No recipients selected")
        self._recip_label.setObjectName("SubText")
        self._recip_label.setWordWrap(True)
        rl.addWidget(self._recip_label)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {BORDER};")
        rl.addWidget(sep)

        self._msg_editor = MessageEditor()
        rl.addWidget(self._msg_editor, 1)

        # Schedule box
        sched_box = QGroupBox("Schedule (optional)")
        sb_lay = QHBoxLayout(sched_box)
        sb_lay.setContentsMargins(12, 8, 12, 12)
        self._schedule_dt = QDateTimeEdit()
        self._schedule_dt.setDisplayFormat("MMM d, yyyy  h:mm AP")
        self._schedule_dt.setDateTime(QDateTime.currentDateTime().addSecs(3600))
        self._schedule_dt.setCalendarPopup(True)
        self._use_schedule = QPushButton("Schedule send")
        self._use_schedule.setObjectName("PrimaryBtn")
        self._use_schedule.clicked.connect(self._schedule_send)
        sb_lay.addWidget(QLabel("Send at:"))
        sb_lay.addWidget(self._schedule_dt, 1)
        sb_lay.addWidget(self._use_schedule)
        rl.addWidget(sched_box)

        # Send row
        action_row = QHBoxLayout()
        self._send_btn = QPushButton("Send Now")
        self._send_btn.setObjectName("PrimaryBtn")
        self._send_btn.setFixedHeight(36)
        self._send_btn.clicked.connect(self._send_now)
        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("SubText")
        action_row.addStretch()
        action_row.addWidget(self._status_lbl)
        action_row.addWidget(self._send_btn)
        rl.addLayout(action_row)

        splitter.addWidget(right)
        splitter.setSizes([340, 600])
        root.addWidget(splitter)

    # ── Helpers ────────────────────────────────────────────────────────────

    def _refresh_group_combo(self):
        self._group_combo.blockSignals(True)
        while self._group_combo.count() > 1:
            self._group_combo.removeItem(1)
        for g in db.list_groups():
            self._group_combo.addItem(g["name"], g["id"])
        self._group_combo.blockSignals(False)

    def refresh(self):
        self._refresh_group_combo()

    def _on_contacts_changed(self, contacts: list[Contact]):
        self._selected_contacts = contacts
        self._update_recip_label()

    def _on_gc_changed(self, chats: list[GroupChat]):
        self._selected_group_chats = chats
        self._update_recip_label()

    def _update_recip_label(self):
        parts = []
        if self._selected_contacts:
            parts.append(f"{len(self._selected_contacts)} contact{'s' if len(self._selected_contacts) != 1 else ''}")
        if self._selected_group_chats:
            parts.append(f"{len(self._selected_group_chats)} group chat{'s' if len(self._selected_group_chats) != 1 else ''}")
        if parts:
            self._recip_label.setText("Recipients: " + " + ".join(parts))
        else:
            self._recip_label.setText("No recipients selected")

    def _load_group(self):
        gid = self._group_combo.currentData()
        if gid is None:
            return
        members = db.get_members(gid)
        ids = {m["contact_id"] for m in members}
        self._picker.set_checked_ids(ids)

        gc_members = db.get_group_chats(gid)
        gc_ids = {g["chat_id"] for g in gc_members}
        self._gc_picker.set_checked_ids(gc_ids)

    def _validate(self) -> bool:
        total = len(self._selected_contacts) + len(self._selected_group_chats)
        if total == 0:
            QMessageBox.warning(self, "No recipients", "Please select at least one contact or group chat.")
            return False
        if not self._msg_editor.get_messages():
            QMessageBox.warning(self, "No message", "Please enter at least one message.")
            return False
        missing = [c.full_name for c in self._selected_contacts if not c.display_handle]
        if missing:
            QMessageBox.warning(
                self, "Missing handles",
                f"These contacts have no phone or email:\n{', '.join(missing)}"
            )
            return False
        return True

    # ── Send now ───────────────────────────────────────────────────────────

    def _send_now(self):
        if not self._validate():
            return

        handles = [c.display_handle for c in self._selected_contacts]
        gc_ids  = [g.chat_id for g in self._selected_group_chats]
        messages = self._msg_editor.get_messages()
        total_recipients = len(handles) + len(gc_ids)

        confirm = QMessageBox.question(
            self, "Confirm send",
            f"Send {len(messages)} message{'s' if len(messages) > 1 else ''} to "
            f"{total_recipients} recipient{'s' if total_recipients != 1 else ''}?\n\n"
            f"({len(handles)} individual{'s' if len(handles) != 1 else ''}"
            f"{', ' + str(len(gc_ids)) + ' group chat' + ('s' if len(gc_ids) != 1 else '') if gc_ids else ''})",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self._send_btn.setEnabled(False)
        self._status_lbl.setText("Sending…")

        self._send_thread = SendThread(handles, gc_ids, messages)
        self._send_thread.progress.connect(self._on_progress)
        self._send_thread.finished.connect(self._on_send_done)
        self._send_thread.start()

    @pyqtSlot(str, int, int, bool, str)
    def _on_progress(self, handle, msg_i, total, ok, err):
        self._status_lbl.setText(f"Sending to {handle}… ({msg_i}/{total})")

    @pyqtSlot(dict)
    def _on_send_done(self, results: dict):
        self._send_btn.setEnabled(True)
        failed = sum(1 for v in results.values() for ok, _ in v if not ok)
        if failed:
            self._status_lbl.setStyleSheet(f"color: {RED};")
            self._status_lbl.setText(f"Done — {failed} failed")
        else:
            self._status_lbl.setStyleSheet(f"color: {GREEN};")
            self._status_lbl.setText(f"✓ Sent to {len(results)} recipients")

    # ── Schedule ───────────────────────────────────────────────────────────

    def _schedule_send(self):
        if not self._validate():
            return

        handles  = [c.display_handle for c in self._selected_contacts]
        gc_ids   = [g.chat_id for g in self._selected_group_chats]
        messages = self._msg_editor.get_messages()
        dt       = self._schedule_dt.dateTime().toPyDateTime()

        from datetime import datetime
        if dt <= datetime.now():
            QMessageBox.warning(self, "Invalid time", "Scheduled time must be in the future.")
            return

        if not hasattr(self, "_scheduler"):
            from core.scheduler import MessageScheduler
            self._scheduler = MessageScheduler()

        self._scheduler.add(handles, messages, dt, group_chat_ids=gc_ids)
        self._status_lbl.setStyleSheet(f"color: {GREEN};")
        self._status_lbl.setText(f"✓ Scheduled for {dt.strftime('%b %d at %I:%M %p')}")
        QMessageBox.information(
            self, "Scheduled",
            f"Message scheduled for {dt.strftime('%A, %B %d at %I:%M %p')}.\nView it in the Schedule tab.",
        )
