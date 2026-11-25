"""
ui/styles.py
App-wide stylesheet and colour tokens.
"""

# Colour tokens
BLUE       = "#0A84FF"   # macOS system blue
BLUE_DARK  = "#0060D0"
GREEN      = "#30D158"
RED        = "#FF453A"
YELLOW     = "#FFD60A"

BG         = "#1C1C1E"   # window background
SURFACE    = "#2C2C2E"   # card/panel surface
SURFACE2   = "#3A3A3C"   # elevated / hovered surface
BORDER     = "#48484A"
TEXT       = "#FFFFFF"
TEXT_SUB   = "#AEAEB2"
TEXT_MUTED = "#636366"


STYLESHEET = f"""
/* ── Global ──────────────────────────────────────────── */
QWidget {{
    background-color: {BG};
    color: {TEXT};
    font-family: ".AppleSystemUIFont";
    font-size: 13px;
}}

/* ── Main window splitter ────────────────────────────── */
QSplitter::handle {{
    background: {BORDER};
}}

/* ── Sidebar panel ───────────────────────────────────── */
#Sidebar {{
    background-color: {SURFACE};
    border-right: 1px solid {BORDER};
}}

/* ── Tab bar (top navigation) ────────────────────────── */
QTabBar::tab {{
    background: transparent;
    color: {TEXT_SUB};
    padding: 10px 22px;
    border: none;
    font-size: 13px;
    font-weight: 500;
}}
QTabBar::tab:selected {{
    color: {TEXT};
    border-bottom: 2px solid {BLUE};
}}
QTabBar::tab:hover:!selected {{
    color: {TEXT};
}}
QTabWidget::pane {{
    border: none;
    border-top: 1px solid {BORDER};
}}

/* ── Buttons ─────────────────────────────────────────── */
QPushButton {{
    background-color: {SURFACE2};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 7px;
    padding: 7px 16px;
    font-size: 13px;
}}
QPushButton:hover {{
    background-color: #48484A;
}}
QPushButton:pressed {{
    background-color: {BORDER};
}}
QPushButton#PrimaryBtn {{
    background-color: {BLUE};
    border: none;
    color: white;
    font-weight: 600;
}}
QPushButton#PrimaryBtn:hover {{
    background-color: {BLUE_DARK};
}}
QPushButton#DangerBtn {{
    background-color: transparent;
    border: 1px solid {RED};
    color: {RED};
}}
QPushButton#DangerBtn:hover {{
    background-color: {RED};
    color: white;
}}
QPushButton#GhostBtn {{
    background-color: transparent;
    border: none;
    color: {BLUE};
}}
QPushButton#GhostBtn:hover {{
    color: {BLUE_DARK};
}}

/* ── List / Tree widgets ─────────────────────────────── */
QListWidget, QTreeWidget {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 8px;
    outline: none;
}}
QListWidget::item, QTreeWidget::item {{
    padding: 6px 8px;
    border-radius: 5px;
}}
QListWidget::item:selected, QTreeWidget::item:selected {{
    background-color: {BLUE};
    color: white;
}}
QListWidget::item:hover:!selected, QTreeWidget::item:hover:!selected {{
    background-color: {SURFACE2};
}}

/* ── Text inputs ─────────────────────────────────────── */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 7px;
    padding: 7px 10px;
    color: {TEXT};
    selection-background-color: {BLUE};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {BLUE};
}}

/* ── ComboBox ────────────────────────────────────────── */
QComboBox {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 7px;
    padding: 6px 10px;
    color: {TEXT};
}}
QComboBox::drop-down {{ border: none; }}
QComboBox QAbstractItemView {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    selection-background-color: {BLUE};
}}

/* ── DateTimeEdit ────────────────────────────────────── */
QDateTimeEdit {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 7px;
    padding: 6px 10px;
    color: {TEXT};
}}
QDateTimeEdit::up-button, QDateTimeEdit::down-button {{
    width: 18px;
    background: {SURFACE2};
    border-left: 1px solid {BORDER};
}}

/* ── ScrollBar ───────────────────────────────────────── */
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 3px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{ height: 6px; background: transparent; }}
QScrollBar::handle:horizontal {{
    background: {BORDER};
    border-radius: 3px;
}}

/* ── CheckBox ────────────────────────────────────────── */
QCheckBox {{
    spacing: 8px;
    color: {TEXT};
}}
QCheckBox::indicator {{
    width: 17px;
    height: 17px;
    border-radius: 4px;
    border: 1.5px solid {BORDER};
    background: {SURFACE};
}}
QCheckBox::indicator:checked {{
    background-color: {BLUE};
    border-color: {BLUE};
}}

/* ── Labels ──────────────────────────────────────────── */
QLabel#SectionTitle {{
    font-size: 11px;
    font-weight: 600;
    color: {TEXT_MUTED};
    letter-spacing: 0.5px;
    text-transform: uppercase;
}}
QLabel#Heading {{
    font-size: 17px;
    font-weight: 700;
    color: {TEXT};
}}
QLabel#SubText {{
    color: {TEXT_SUB};
    font-size: 12px;
}}

/* ── Status bar ──────────────────────────────────────── */
QStatusBar {{
    background: {SURFACE};
    border-top: 1px solid {BORDER};
    color: {TEXT_SUB};
    font-size: 12px;
}}

/* ── Progress bar ────────────────────────────────────── */
QProgressBar {{
    background: {SURFACE2};
    border-radius: 4px;
    border: none;
    height: 6px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background-color: {BLUE};
    border-radius: 4px;
}}

/* ── Tooltips ────────────────────────────────────────── */
QToolTip {{
    background: {SURFACE2};
    color: {TEXT};
    border: 1px solid {BORDER};
    padding: 5px 8px;
    border-radius: 5px;
}}

/* ── Group box ───────────────────────────────────────── */
QGroupBox {{
    border: 1px solid {BORDER};
    border-radius: 8px;
    margin-top: 16px;
    padding-top: 8px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    color: {TEXT_SUB};
    font-size: 12px;
}}
"""
