"""
ui/groups_tab.py
Manage named groups of contacts + iMessage group chats.
Features:
  - Selected-contacts panel (right side) so filtering never loses picks
  - Clone group button
  - Group chat picker section
"""

from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
    QListWidgetItem, QPushButton, QLabel, QLineEdit,
    QMessageBox, QSplitter, QFrame, QScrollArea,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from ui.contact_picker import ContactPicker
from ui.group_chat_picker import GroupChatPicker
from ui.styles import BLUE, RED, GREEN, BORDER, TEXT_SUB, SURFACE, SURFACE2, TEXT_MUTED, TEXT
from core.contacts import Contact
from core import groups as db


# ── Selected-contacts panel ───────────────────────────────────────────────────

class SelectedPanel(QWidget):
    """
    Shows currently selected contacts as removable rows.
    Calls remove_cb(contact_id) when user clicks ✕.
    """
    def __init__(self, remove_cb, parent=None):
        super().__init__(parent)
        self._remove_cb = remove_cb
        self._rows: dict[str, QWidget] = {}  # contact_id -> row widget

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Header
        hdr = QHBoxLayout()
        lbl = QLabel("SELECTED")
        lbl.setObjectName("SectionTitle")
        self._count_lbl = QLabel("0")
        self._count_lbl.setObjectName("SubText")
        hdr.addWidget(lbl)
        hdr.addStretch()
        hdr.addWidget(self._count_lbl)
        lay.addLayout(hdr)
        lay.addSpacing(6)

        # Scroll area for rows
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._inner = QWidget()
        self._inner_lay = QVBoxLayout(self._inner)
        self._inner_lay.setContentsMargins(0, 0, 0, 0)
        self._inner_lay.setSpacing(3)
        self._inner_lay.addStretch()

        scroll.setWidget(self._inner)
        lay.addWidget(scroll, 1)

        self._empty_lbl = QLabel("No contacts selected yet.\nCheck names on the left.")
        self._empty_lbl.setObjectName("SubText")
        self._empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_lbl.setWordWrap(True)
        lay.addWidget(self._empty_lbl)

    def update_selection(self, contacts: list[Contact]):
        existing_ids = set(self._rows.keys())
        new_ids = {c.identifier for c in contacts}

        # Remove rows no longer selected
        for cid in existing_ids - new_ids:
            w = self._rows.pop(cid)
            self._inner_lay.removeWidget(w)
            w.deleteLater()

        # Add new rows
        for c in contacts:
            if c.identifier not in self._rows:
                row = self._make_row(c)
                self._rows[c.identifier] = row
                # Insert before the stretch at the end
                self._inner_lay.insertWidget(self._inner_lay.count() - 1, row)

        count = len(self._rows)
        self._count_lbl.setText(str(count))
        self._empty_lbl.setVisible(count == 0)

    def _make_row(self, contact: Contact) -> QWidget:
        row = QWidget()
        row.setStyleSheet(f"""
            QWidget {{ background: {SURFACE2}; border-radius: 5px; }}
        """)
        rl = QHBoxLayout(row)
        rl.setContentsMargins(8, 4, 4, 4)
        rl.setSpacing(6)

        name_lbl = QLabel(contact.full_name)
        name_lbl.setStyleSheet(f"color: {TEXT}; background: transparent; font-size: 12px;")
        handle_lbl = QLabel(contact.display_handle)
        handle_lbl.setStyleSheet(f"color: {TEXT_MUTED}; background: transparent; font-size: 11px;")

        remove_btn = QPushButton("✕")
        remove_btn.setObjectName("GhostBtn")
        remove_btn.setFixedSize(20, 20)
        remove_btn.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; background: transparent;")
        remove_btn.setToolTip(f"Remove {contact.full_name}")
        cid = contact.identifier
        remove_btn.clicked.connect(lambda: self._remove_cb(cid))

        rl.addWidget(name_lbl)
        rl.addWidget(handle_lbl)
        rl.addStretch()
        rl.addWidget(remove_btn)
        return row

    def clear(self):
        for w in list(self._rows.values()):
            self._inner_lay.removeWidget(w)
            w.deleteLater()
        self._rows.clear()
        self._count_lbl.setText("0")
        self._empty_lbl.setVisible(True)


# ── Groups tab ────────────────────────────────────────────────────────────────

class GroupsTab(QWidget):
    groupsChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_group_id: int | None = None
        self._build_ui()
        self._refresh_list()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        outer_splitter = QSplitter(Qt.Orientation.Horizontal)
        outer_splitter.setHandleWidth(1)

        # ── Far left: saved groups list ───────────────────────────────────
        group_list_widget = QWidget()
        group_list_widget.setMinimumWidth(200)
        group_list_widget.setMaximumWidth(280)
        gll = QVBoxLayout(group_list_widget)
        gll.setContentsMargins(16, 16, 16, 16)
        gll.setSpacing(10)

        lbl = QLabel("GROUPS")
        lbl.setObjectName("SectionTitle")
        gll.addWidget(lbl)

        self._group_list = QListWidget()
        self._group_list.currentItemChanged.connect(self._on_group_selected)
        gll.addWidget(self._group_list)

        btn_row = QHBoxLayout()
        new_btn = QPushButton("+ New")
        new_btn.setObjectName("PrimaryBtn")
        new_btn.clicked.connect(self._new_group)

        self._clone_btn = QPushButton("⧉ Clone")
        self._clone_btn.setEnabled(False)
        self._clone_btn.setToolTip("Duplicate selected group")
        self._clone_btn.clicked.connect(self._clone_group)

        btn_row.addWidget(new_btn, 1)
        btn_row.addWidget(self._clone_btn, 1)
        gll.addLayout(btn_row)

        outer_splitter.addWidget(group_list_widget)

        # ── Middle: contact search picker ─────────────────────────────────
        middle = QWidget()
        middle.setMinimumWidth(260)
        ml = QVBoxLayout(middle)
        ml.setContentsMargins(12, 16, 12, 16)
        ml.setSpacing(10)

        # Group name row at top
        name_row = QHBoxLayout()
        name_lbl = QLabel("Name:")
        name_lbl.setObjectName("SubText")
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Group name…")
        self._name_edit.setEnabled(False)
        name_row.addWidget(name_lbl)
        name_row.addWidget(self._name_edit, 1)
        ml.addLayout(name_row)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {BORDER};")
        ml.addWidget(sep)

        contacts_lbl = QLabel("ADD CONTACTS")
        contacts_lbl.setObjectName("SectionTitle")
        ml.addWidget(contacts_lbl)

        self._picker = ContactPicker()
        self._picker.selectionChanged.connect(self._on_contacts_changed)
        ml.addWidget(self._picker, 1)

        gc_sep = QFrame()
        gc_sep.setFrameShape(QFrame.Shape.HLine)
        gc_sep.setStyleSheet(f"color: {BORDER};")
        ml.addWidget(gc_sep)

        self._gc_picker = GroupChatPicker()
        self._gc_picker.selectionChanged.connect(self._on_gc_changed)
        ml.addWidget(self._gc_picker)

        outer_splitter.addWidget(middle)

        # ── Right: selected panel ─────────────────────────────────────────
        right = QWidget()
        right.setMinimumWidth(200)
        right.setMaximumWidth(300)
        rl = QVBoxLayout(right)
        rl.setContentsMargins(12, 16, 16, 16)
        rl.setSpacing(10)

        self._selected_panel = SelectedPanel(remove_cb=self._remove_contact)
        rl.addWidget(self._selected_panel, 1)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet(f"color: {BORDER};")
        rl.addWidget(sep2)

        # Action buttons
        self._delete_btn = QPushButton("Delete Group")
        self._delete_btn.setObjectName("DangerBtn")
        self._delete_btn.setEnabled(False)
        self._delete_btn.clicked.connect(self._delete_group)

        self._save_btn = QPushButton("Save Group")
        self._save_btn.setObjectName("PrimaryBtn")
        self._save_btn.setEnabled(False)
        self._save_btn.clicked.connect(self._save_group)

        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("SubText")
        self._status_lbl.setWordWrap(True)

        rl.addWidget(self._status_lbl)
        rl.addWidget(self._save_btn)
        rl.addWidget(self._delete_btn)

        outer_splitter.addWidget(right)
        outer_splitter.setSizes([220, 360, 240])

        root.addWidget(outer_splitter)

    # ── Group list ─────────────────────────────────────────────────────────

    def _refresh_list(self):
        self._group_list.blockSignals(True)
        self._group_list.clear()
        for g in db.list_groups():
            item = QListWidgetItem(g["name"])
            item.setData(Qt.ItemDataRole.UserRole, g["id"])
            self._group_list.addItem(item)
        self._group_list.blockSignals(False)

    def _on_group_selected(self, item: QListWidgetItem, _prev):
        if item is None:
            self._current_group_id = None
            self._name_edit.setEnabled(False)
            self._save_btn.setEnabled(False)
            self._delete_btn.setEnabled(False)
            self._clone_btn.setEnabled(False)
            self._selected_panel.clear()
            return

        gid = item.data(Qt.ItemDataRole.UserRole)
        self._current_group_id = gid
        self._name_edit.setText(item.text())
        self._name_edit.setEnabled(True)
        self._save_btn.setEnabled(True)
        self._delete_btn.setEnabled(True)
        self._clone_btn.setEnabled(True)
        self._status_lbl.setText("")

        members = db.get_members(gid)
        ids = {m["contact_id"] for m in members}
        self._picker.set_checked_ids(ids)

        gc_members = db.get_group_chats(gid)
        gc_ids = {g["chat_id"] for g in gc_members}
        self._gc_picker.set_checked_ids(gc_ids)

    # ── Contact selection callbacks ────────────────────────────────────────

    def _on_contacts_changed(self, contacts: list[Contact]):
        self._selected_panel.update_selection(contacts)

    def _on_gc_changed(self, _chats):
        pass

    def _remove_contact(self, contact_id: str):
        """Called when user clicks ✕ in the selected panel."""
        self._picker.remove_contact(contact_id)

    # ── CRUD ───────────────────────────────────────────────────────────────

    def _new_group(self):
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "New Group", "Group name:")
        if not ok or not name.strip():
            return
        try:
            gid = db.create_group(name.strip())
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))
            return
        self._refresh_list()
        self.groupsChanged.emit()
        for i in range(self._group_list.count()):
            if self._group_list.item(i).data(Qt.ItemDataRole.UserRole) == gid:
                self._group_list.setCurrentRow(i)
                break

    def _clone_group(self):
        if self._current_group_id is None:
            return
        from PyQt6.QtWidgets import QInputDialog
        current_name = self._name_edit.text().strip()
        new_name, ok = QInputDialog.getText(
            self, "Clone Group", "Name for the cloned group:",
            text=f"{current_name} (copy)"
        )
        if not ok or not new_name.strip():
            return
        try:
            new_gid = db.create_group(new_name.strip())
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))
            return

        # Copy contact members
        members = db.get_members(self._current_group_id)
        db.set_members(new_gid, members)

        # Copy group chat members
        gc_members = db.get_group_chats(self._current_group_id)
        db.set_group_chats(new_gid, gc_members)

        self._refresh_list()
        self.groupsChanged.emit()

        # Select the new cloned group
        for i in range(self._group_list.count()):
            if self._group_list.item(i).data(Qt.ItemDataRole.UserRole) == new_gid:
                self._group_list.setCurrentRow(i)
                break

        self._status_lbl.setStyleSheet(f"color: {GREEN};")
        self._status_lbl.setText(f'✓ Cloned as "{new_name.strip()}"')

    def _save_group(self):
        if self._current_group_id is None:
            return
        new_name = self._name_edit.text().strip()
        if not new_name:
            QMessageBox.warning(self, "Name required", "Group name cannot be empty.")
            return

        db.rename_group(self._current_group_id, new_name)

        members = [
            {"contact_id": c.identifier, "contact_name": c.full_name, "handle": c.display_handle}
            for c in self._picker.selected_contacts()
            if c.display_handle
        ]
        db.set_members(self._current_group_id, members)

        gc_members = [
            {"chat_id": g.chat_id, "display_name": g.display_name}
            for g in self._gc_picker.selected_chats()
        ]
        db.set_group_chats(self._current_group_id, gc_members)

        self._refresh_list()
        self.groupsChanged.emit()
        self._status_lbl.setStyleSheet(f"color: {GREEN};")
        self._status_lbl.setText(f"✓ Saved — {len(members)} contact{'s' if len(members) != 1 else ''}"
                                  f"{', ' + str(len(gc_members)) + ' chat' + ('s' if len(gc_members) != 1 else '') if gc_members else ''}")

    def _delete_group(self):
        if self._current_group_id is None:
            return
        confirm = QMessageBox.question(
            self, "Delete group",
            f'Delete "{self._name_edit.text()}"? This cannot be undone.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        db.delete_group(self._current_group_id)
        self._current_group_id = None
        self._refresh_list()
        self.groupsChanged.emit()
        self._name_edit.setText("")
        self._name_edit.setEnabled(False)
        self._save_btn.setEnabled(False)
        self._delete_btn.setEnabled(False)
        self._clone_btn.setEnabled(False)
        self._picker.set_checked_ids(set())
        self._gc_picker.set_checked_ids(set())
        self._selected_panel.clear()
