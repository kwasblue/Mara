# mara_host/gui/core/theme.py
"""
Modern minimal dark theme for the MARA GUI.

Design principles:
- Generous whitespace and breathing room
- Subtle, muted colors
- Minimal borders - use spacing and subtle shadows
- Clean typography with clear hierarchy
- Reduced visual noise
"""

# Color palette - subtle, muted tones
COLORS = {
    # Backgrounds - subtle gray with slight cool tint
    "bg_base": "#111113",        # Deepest background
    "bg_subtle": "#18181B",      # Main content background
    "bg_muted": "#1F1F23",       # Elevated surfaces
    "bg_elevated": "#27272A",    # Cards, inputs
    "bg_hover": "#2E2E33",       # Hover states

    # Text - high contrast but not pure white
    "text_primary": "#FAFAFA",   # Primary text
    "text_secondary": "#A1A1AA", # Secondary/labels
    "text_tertiary": "#71717A",  # Muted/placeholder
    "text_quaternary": "#52525B", # Very subtle

    # Accent - refined blue, used sparingly
    "accent": "#3B82F6",
    "accent_hover": "#2563EB",
    "accent_subtle": "rgba(59, 130, 246, 0.15)",

    # Semantic colors
    "success": "#22C55E",
    "warning": "#F59E0B",
    "danger": "#EF4444",
    "info": "#06B6D4",

    # Borders - very subtle
    "border": "#27272A",
    "border_subtle": "#1F1F23",
    "border_focus": "#3B82F6",

    # States
    "state_idle": "#52525B",
    "state_armed": "#F59E0B",
    "state_active": "#8B5CF6",
    "state_estop": "#EF4444",
}


DARK_THEME = f"""
/* ==================== Base ==================== */
QMainWindow {{
    background-color: {COLORS['bg_base']};
}}

QWidget {{
    background-color: transparent;
    color: {COLORS['text_primary']};
    font-family: "Helvetica Neue", "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
}}

/* ==================== Panels ==================== */
QGroupBox {{
    background-color: {COLORS['bg_subtle']};
    border: none;
    border-radius: 8px;
    margin-top: 24px;
    padding: 20px;
    padding-top: 16px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 20px;
    top: 4px;
    padding: 0;
    color: {COLORS['text_secondary']};
    font-size: 12px;
    font-weight: 500;
}}

QFrame#Card {{
    background-color: {COLORS['bg_muted']};
    border: none;
    border-radius: 8px;
}}

/* ==================== Buttons ==================== */
QPushButton {{
    background-color: {COLORS['accent']};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 500;
    font-size: 13px;
}}

QPushButton:hover {{
    background-color: {COLORS['accent_hover']};
}}

QPushButton:pressed {{
    background-color: #1D4ED8;
}}

QPushButton:disabled {{
    background-color: {COLORS['bg_elevated']};
    color: {COLORS['text_tertiary']};
}}

QPushButton#secondary {{
    background-color: {COLORS['bg_elevated']};
    color: {COLORS['text_primary']};
}}

QPushButton#secondary:hover {{
    background-color: {COLORS['bg_hover']};
}}

QPushButton#danger {{
    background-color: {COLORS['danger']};
}}

QPushButton#danger:hover {{
    background-color: #DC2626;
}}

QPushButton#warning {{
    background-color: {COLORS['warning']};
    color: #18181B;
}}

QPushButton#warning:hover {{
    background-color: #D97706;
}}

QPushButton#success {{
    background-color: {COLORS['success']};
}}

QPushButton#flat {{
    background-color: transparent;
    color: {COLORS['text_secondary']};
    padding: 6px 10px;
}}

QPushButton#flat:hover {{
    color: {COLORS['text_primary']};
    background-color: {COLORS['bg_elevated']};
}}

/* ==================== Inputs ==================== */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background-color: {COLORS['bg_elevated']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 8px 12px;
    color: {COLORS['text_primary']};
    selection-background-color: {COLORS['accent']};
}}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border-color: {COLORS['accent']};
}}

QLineEdit::placeholder {{
    color: {COLORS['text_tertiary']};
}}

QComboBox::drop-down {{
    border: none;
    width: 32px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {COLORS['text_tertiary']};
    margin-right: 12px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLORS['bg_elevated']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 4px;
    selection-background-color: {COLORS['bg_hover']};
    outline: none;
}}

QComboBox QAbstractItemView::item {{
    padding: 8px 12px;
    border-radius: 4px;
}}

QComboBox QAbstractItemView::item:selected {{
    background-color: {COLORS['bg_hover']};
}}

/* ==================== Sliders ==================== */
QSlider::groove:horizontal {{
    background-color: {COLORS['bg_elevated']};
    height: 6px;
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    background-color: {COLORS['text_primary']};
    width: 14px;
    height: 14px;
    margin: -4px 0;
    border-radius: 7px;
}}

QSlider::handle:horizontal:hover {{
    background-color: {COLORS['accent']};
}}

QSlider::sub-page:horizontal {{
    background-color: {COLORS['accent']};
    border-radius: 3px;
}}

/* ==================== Labels ==================== */
QLabel {{
    color: {COLORS['text_primary']};
    background: transparent;
}}

QLabel#heading {{
    font-size: 15px;
    font-weight: 600;
}}

QLabel#subheading {{
    color: {COLORS['text_secondary']};
    font-size: 12px;
}}

QLabel#muted {{
    color: {COLORS['text_tertiary']};
    font-size: 12px;
}}

QLabel#mono {{
    font-family: "Menlo", "JetBrains Mono", "Fira Code", monospace;
}}

/* ==================== Tabs ==================== */
QTabWidget::pane {{
    border: none;
    background-color: transparent;
}}

QTabBar::tab {{
    background-color: transparent;
    color: {COLORS['text_tertiary']};
    padding: 10px 16px;
    margin-right: 4px;
    border-bottom: 2px solid transparent;
}}

QTabBar::tab:selected {{
    color: {COLORS['text_primary']};
    border-bottom-color: {COLORS['accent']};
}}

QTabBar::tab:hover:!selected {{
    color: {COLORS['text_secondary']};
}}

/* ==================== Scrollbars ==================== */
QScrollBar:vertical {{
    background-color: transparent;
    width: 10px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background-color: {COLORS['bg_hover']};
    min-height: 40px;
    border-radius: 5px;
    margin: 2px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {COLORS['text_quaternary']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
    height: 0;
}}

QScrollBar:horizontal {{
    background-color: transparent;
    height: 10px;
}}

QScrollBar::handle:horizontal {{
    background-color: {COLORS['bg_hover']};
    min-width: 40px;
    border-radius: 5px;
    margin: 2px;
}}

/* ==================== Text Areas ==================== */
QPlainTextEdit, QTextEdit {{
    background-color: {COLORS['bg_muted']};
    border: none;
    border-radius: 6px;
    padding: 12px;
    color: {COLORS['text_primary']};
    font-family: "Menlo", "JetBrains Mono", "Fira Code", monospace;
    font-size: 12px;
    selection-background-color: {COLORS['accent_subtle']};
}}

/* ==================== Tables & Lists ==================== */
QTreeView, QListView, QTableView {{
    background-color: {COLORS['bg_muted']};
    border: none;
    border-radius: 6px;
    outline: none;
    gridline-color: {COLORS['border_subtle']};
}}

QTreeView::item, QListView::item, QTableView::item {{
    padding: 8px;
    border: none;
}}

QTreeView::item:selected, QListView::item:selected, QTableView::item:selected {{
    background-color: {COLORS['accent_subtle']};
    color: {COLORS['text_primary']};
}}

QTreeView::item:hover:!selected, QListView::item:hover:!selected {{
    background-color: {COLORS['bg_elevated']};
}}

QHeaderView::section {{
    background-color: {COLORS['bg_subtle']};
    border: none;
    border-bottom: 1px solid {COLORS['border_subtle']};
    padding: 10px 12px;
    font-weight: 500;
    font-size: 12px;
    color: {COLORS['text_secondary']};
}}

QTableView QTableCornerButton::section {{
    background-color: {COLORS['bg_subtle']};
    border: none;
}}

/* ==================== Progress Bar ==================== */
QProgressBar {{
    background-color: {COLORS['bg_elevated']};
    border: none;
    border-radius: 2px;
    height: 4px;
    text-align: center;
}}

QProgressBar::chunk {{
    background-color: {COLORS['accent']};
    border-radius: 2px;
}}

/* ==================== Status Bar ==================== */
QStatusBar {{
    background-color: {COLORS['bg_subtle']};
    border-top: 1px solid {COLORS['border_subtle']};
    padding: 8px 16px;
}}

QStatusBar QLabel {{
    color: {COLORS['text_secondary']};
    font-size: 12px;
}}

/* ==================== Tooltips ==================== */
QToolTip {{
    background-color: {COLORS['bg_elevated']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 12px;
}}

/* ==================== Sidebar ==================== */
QListWidget#Sidebar {{
    background-color: transparent;
    border: none;
    outline: none;
}}

QListWidget#Sidebar::item {{
    padding: 10px 16px;
    border-radius: 6px;
    margin: 2px 8px;
    color: {COLORS['text_secondary']};
}}

QListWidget#Sidebar::item:selected {{
    background-color: {COLORS['bg_muted']};
    color: {COLORS['text_primary']};
}}

QListWidget#Sidebar::item:hover:!selected {{
    background-color: {COLORS['bg_elevated']};
    color: {COLORS['text_primary']};
}}

/* ==================== Splitter ==================== */
QSplitter::handle {{
    background-color: transparent;
}}

QSplitter::handle:hover {{
    background-color: {COLORS['border']};
}}

/* ==================== Checkbox & Radio ==================== */
QCheckBox, QRadioButton {{
    spacing: 8px;
    color: {COLORS['text_primary']};
}}

QCheckBox::indicator, QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {COLORS['text_quaternary']};
    background-color: transparent;
}}

QCheckBox::indicator {{
    border-radius: 4px;
}}

QRadioButton::indicator {{
    border-radius: 8px;
}}

QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background-color: {COLORS['accent']};
    border-color: {COLORS['accent']};
}}

QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
    border-color: {COLORS['text_tertiary']};
}}

/* ==================== Menu ==================== */
QMenu {{
    background-color: {COLORS['bg_elevated']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 6px;
}}

QMenu::item {{
    padding: 8px 16px;
    border-radius: 4px;
    color: {COLORS['text_primary']};
}}

QMenu::item:selected {{
    background-color: {COLORS['bg_hover']};
}}

QMenu::separator {{
    height: 1px;
    background-color: {COLORS['border']};
    margin: 6px 8px;
}}

/* ==================== State Pills ==================== */
QLabel#state-idle {{
    background-color: {COLORS['state_idle']};
    color: white;
    border-radius: 4px;
    padding: 4px 12px;
    font-size: 11px;
    font-weight: 600;
}}

QLabel#state-armed {{
    background-color: {COLORS['state_armed']};
    color: #18181B;
    border-radius: 4px;
    padding: 4px 12px;
    font-size: 11px;
    font-weight: 600;
}}

QLabel#state-active {{
    background-color: {COLORS['state_active']};
    color: white;
    border-radius: 4px;
    padding: 4px 12px;
    font-size: 11px;
    font-weight: 600;
}}

QLabel#state-estop {{
    background-color: {COLORS['state_estop']};
    color: white;
    border-radius: 4px;
    padding: 4px 12px;
    font-size: 11px;
    font-weight: 600;
}}
"""


def apply_theme(app) -> None:
    """Apply the dark theme to a QApplication."""
    app.setStyleSheet(DARK_THEME)
