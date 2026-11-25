"""
ui/main_window.py
Top-level application window.
"""

from __future__ import annotations
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QTabWidget,
    QStatusBar, QLabel, QHBoxLayout,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon

from ui.styles import STYLESHEET, BG, SURFACE, BLUE, GREEN, RED, TEXT_SUB
from ui.compose_tab import ComposeTab
from ui.groups_tab import GroupsTab
from ui.schedule_tab import ScheduleTab
from core.scheduler import MessageScheduler
from core.messenger import check_messages_running


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mass Messenger")
        self.setMinimumSize(QSize(860, 600))
        self.resize(QSize(1060, 720))
        self.setStyleSheet(STYLESHEET)

        self._scheduler = MessageScheduler(on_sent=self._on_scheduled_sent)

        self._build_ui()
        self._check_messages_app()

    def _build_ui(self):
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)

        from PyQt6.QtWidgets import QVBoxLayout
        vlay = QVBoxLayout(central)
        vlay.setContentsMargins(0, 0, 0, 0)
        vlay.setSpacing(0)

        # Tab bar
        self._tabs = QTabWidget()
        self._tabs.setTabPosition(QTabWidget.TabPosition.North)
        self._tabs.setDocumentMode(True)

        self._compose_tab = ComposeTab()
        self._groups_tab  = GroupsTab()
        self._schedule_tab = ScheduleTab(scheduler=self._scheduler)

        self._tabs.addTab(self._compose_tab,  "✉  Compose")
        self._tabs.addTab(self._groups_tab,   "👥  Groups")
        self._tabs.addTab(self._schedule_tab, "🕐  Scheduled")

        self._tabs.currentChanged.connect(self._on_tab_changed)
        self._groups_tab.groupsChanged.connect(self._compose_tab.refresh)

        vlay.addWidget(self._tabs)

        # Status bar
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._msg_status = QLabel("Ready")
        self._status.addWidget(self._msg_status)

        right_status = QLabel("Mass Messenger  •  Individual threads only")
        right_status.setStyleSheet(f"color: {TEXT_SUB}; padding-right: 8px;")
        self._status.addPermanentWidget(right_status)

    def _on_tab_changed(self, index: int):
        # Refresh schedule tab when switching to it
        if index == 2:
            self._schedule_tab.refresh()

    def _check_messages_app(self):
        import sys
        if sys.platform == "darwin":
            ok = check_messages_running()
            if not ok:
                self._msg_status.setStyleSheet(f"color: {RED};")
                self._msg_status.setText("⚠  Messages.app not accessible — check Automation permissions")
            else:
                self._msg_status.setStyleSheet(f"color: {GREEN};")
                self._msg_status.setText("✓  Messages.app connected")
        else:
            self._msg_status.setStyleSheet(f"color: {TEXT_SUB};")
            self._msg_status.setText("Dev mode — sends simulated")

    def _on_scheduled_sent(self, scheduled_id: int, success: bool):
        color = GREEN if success else RED
        label = "✓ Scheduled send complete" if success else "⚠ Scheduled send had errors"
        self._msg_status.setStyleSheet(f"color: {color};")
        self._msg_status.setText(label)
        self._schedule_tab.refresh()

    def closeEvent(self, event):
        self._scheduler.shutdown()
        super().closeEvent(event)
