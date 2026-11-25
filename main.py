#!/usr/bin/env python3
"""
Mass Messenger for Mac
Entry point — launches the PyQt6 application.
"""

import sys
import os

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(__file__))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Mass Messenger")
    app.setOrganizationName("MassMessenger")

    # Use system font with slight size bump
    font = QFont(".AppleSystemUIFont", 13)
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
