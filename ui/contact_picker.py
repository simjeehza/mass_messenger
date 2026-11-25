"""
ui/contact_picker.py
Searchable, checkable contact list with A->Z / Recently Texted sort toggle.

KEY FIX: selected contacts are tracked in a persistent dict (_selected: dict[id, Contact])
that is INDEPENDENT of the visible list. Filtering never loses selections.
"""

from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QListWidget, QListWidgetItem, QLabel, QPushButton,
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSlot

from core.contacts import Contact, load_contacts, sort_by_recent
from ui.styles import TEXT_SUB, BLUE, BORDER


class _LoadThread(QThread):
    done = pyqtSignal(list, dict)

    def run(self):
        contacts = load_contacts()
        try:
            from core.chat_db import get_recent_handle_order
            recent_order = get_recent_handle_order()
        except Exception:
            recent_order = {}
        self.done.emit(contacts, recent_order)


class ContactItem(QListWidgetItem):
    def __init__(self, contact: Contact):
        super().__init__()
        self.contact = contact
        self.setFlags(self.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        self.setCheckState(Qt.CheckState.Unchecked)
        self.setText(f"{contact.full_name}  —  {contact.display_handle}")


class ContactPicker(QWidget):
    """
    Emits selectionChanged(list[Contact]) whenever the selection changes.
    Selection is stored independently of the visible list so filtering
    never loses already-checked contacts.
    """
    selectionChanged = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_contacts: list[Contact] = []
        self._recent_order: dict[str, int] = {}
        self._sort_recent: bool = False
        # SOURCE OF TRUTH for selection — keyed by contact.identifier
        self._selected: dict[str, Contact] = {}
        self._build_ui()
        self._load()

    # ── Build ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search contacts…")
        self._search.textChanged.connect(self._filter)
        lay.addWidget(self._search)

        ctrl_row = QHBoxLayout()
        ctrl_row.setContentsMargins(0, 0, 0, 0)

        self._select_all_btn = QPushButton("Select all")
        self._select_all_btn.setObjectName("GhostBtn")
        self._select_all_btn.clicked.connect(self._select_all)

        self._select_none_btn = QPushButton("Clear")
        self._select_none_btn.setObjectName("GhostBtn")
        self._select_none_btn.clicked.connect(self._select_none)

        self._sort_btn = QPushButton("🕐  Recent first")
        self._sort_btn.setObjectName("GhostBtn")
        self._sort_btn.setToolTip("Toggle between A→Z and recently texted order")
        self._sort_btn.clicked.connect(self._toggle_sort)

        self._count_label = QLabel("Loading…")
        self._count_label.setObjectName("SubText")

        ctrl_row.addWidget(self._select_all_btn)
        ctrl_row.addWidget(self._select_none_btn)
        ctrl_row.addWidget(self._sort_btn)
        ctrl_row.addStretch()
        ctrl_row.addWidget(self._count_label)
        lay.addLayout(ctrl_row)

        self._list = QListWidget()
        self._list.setSpacing(2)
        self._list.itemChanged.connect(self._on_item_changed)
        lay.addWidget(self._list)

    # ── Load ───────────────────────────────────────────────────────────────

    def _load(self):
        self._thread = _LoadThread()
        self._thread.done.connect(self._on_contacts_loaded)
        self._thread.start()

    @pyqtSlot(list, dict)
    def _on_contacts_loaded(self, contacts: list[Contact], recent_order: dict):
        self._all_contacts = contacts
        self._recent_order = recent_order
        self._repopulate()
        self._update_count()

    # ── Sort ───────────────────────────────────────────────────────────────

    def _toggle_sort(self):
        self._sort_recent = not self._sort_recent
        if self._sort_recent:
            self._sort_btn.setText("🔤  A → Z")
            self._sort_btn.setToolTip("Switch back to alphabetical order")
        else:
            self._sort_btn.setText("🕐  Recent first")
            self._sort_btn.setToolTip("Sort by most recently texted")
        self._repopulate()

    def _sorted_contacts(self, contacts: list[Contact]) -> list[Contact]:
        if self._sort_recent and self._recent_order:
            return sort_by_recent(contacts, self._recent_order)
        return contacts

    # ── Filter + populate ──────────────────────────────────────────────────

    def _filter(self, query: str):
        self._repopulate()

    def _repopulate(self):
        q = self._search.text().lower()
        visible = [
            c for c in self._all_contacts
            if not q or q in c.full_name.lower() or q in c.display_handle.lower()
        ]
        self._populate(self._sorted_contacts(visible))

    def _populate(self, contacts: list[Contact]):
        """Render the list; check state is driven by self._selected."""
        self._list.blockSignals(True)
        self._list.clear()
        for c in contacts:
            item = ContactItem(c)
            if c.identifier in self._selected:
                item.setCheckState(Qt.CheckState.Checked)
            self._list.addItem(item)
        self._list.blockSignals(False)
        self._update_count()

    # ── Item interaction ───────────────────────────────────────────────────

    def _on_item_changed(self, item: ContactItem):
        """Sync the persistent _selected dict from a checkbox click."""
        if item.checkState() == Qt.CheckState.Checked:
            self._selected[item.contact.identifier] = item.contact
        else:
            self._selected.pop(item.contact.identifier, None)
        self._emit_selection()
        self._update_count()

    # ── Select all / clear (only affects visible items) ───────────────────

    def _select_all(self):
        self._list.blockSignals(True)
        for i in range(self._list.count()):
            item = self._list.item(i)
            item.setCheckState(Qt.CheckState.Checked)
            self._selected[item.contact.identifier] = item.contact
        self._list.blockSignals(False)
        self._emit_selection()
        self._update_count()

    def _select_none(self):
        """Clear ALL selections (not just visible)."""
        self._selected.clear()
        self._list.blockSignals(True)
        for i in range(self._list.count()):
            self._list.item(i).setCheckState(Qt.CheckState.Unchecked)
        self._list.blockSignals(False)
        self._emit_selection()
        self._update_count()

    # ── Emit + count ───────────────────────────────────────────────────────

    def _emit_selection(self):
        self.selectionChanged.emit(list(self._selected.values()))

    def _update_count(self):
        n_selected = len(self._selected)
        n_visible  = self._list.count()
        n_total    = len(self._all_contacts)
        q = self._search.text()
        if q:
            # Searching: show "X of Y results" + how many selected overall
            base = f"{n_visible} results"
            if n_selected:
                base += f"  •  {n_selected} selected"
        else:
            if n_selected:
                base = f"{n_selected} of {n_total} selected"
            else:
                base = f"{n_total} contacts"
        self._count_label.setText(base)

    # ── Public API ─────────────────────────────────────────────────────────

    def selected_contacts(self) -> list[Contact]:
        return list(self._selected.values())

    def set_checked_ids(self, ids: set[str]):
        """Pre-select contacts by identifier (e.g. loading a saved group)."""
        # Build a lookup from all contacts
        lookup = {c.identifier: c for c in self._all_contacts}
        self._selected = {cid: lookup[cid] for cid in ids if cid in lookup}
        self._repopulate()
        self._emit_selection()

    def remove_contact(self, contact_id: str):
        """Remove a single contact from the selection (called by selected panel)."""
        self._selected.pop(contact_id, None)
        self._repopulate()
        self._emit_selection()

    def reload(self):
        self._load()
