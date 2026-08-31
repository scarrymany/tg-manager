"""Тёмная тема оформления (QSS) для TG Manager."""

# Палитра
BG = "#0f141a"
BG_ELEV = "#171e27"
CARD = "#1b2531"
CARD_HOVER = "#202c3a"
BORDER = "#273241"
TEXT = "#e8eef5"
TEXT_DIM = "#8a99ad"
ACCENT = "#2AABEE"
ACCENT_HOVER = "#39b6f5"
ACCENT_PRESSED = "#1f97d6"
GREEN = "#3ddc84"
RED = "#ff5c5c"
DANGER = "#e5484d"

QSS = f"""
* {{
    font-family: "Inter", "Segoe UI", "Ubuntu", "Cantarell", sans-serif;
    font-size: 14px;
    color: {TEXT};
    outline: none;
}}

QMainWindow, QDialog {{
    background: {BG};
}}

/* ---- Шапка ---- */
#Header {{
    background: {BG_ELEV};
    border-bottom: 1px solid {BORDER};
}}
#AppTitle {{
    font-size: 20px;
    font-weight: 700;
    color: {TEXT};
}}
#AppSubtitle {{
    font-size: 12px;
    color: {TEXT_DIM};
}}

/* ---- Область прокрутки ---- */
QScrollArea {{ border: none; background: {BG}; }}
#Board {{ background: {BG}; }}

QScrollBar:vertical {{
    background: transparent; width: 10px; margin: 4px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER}; border-radius: 5px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: #33445a; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}

/* ---- Кнопки ---- */
QPushButton {{
    background: {BG_ELEV};
    border: 1px solid {BORDER};
    border-radius: 9px;
    padding: 8px 14px;
    color: {TEXT};
}}
QPushButton:hover {{ background: {CARD_HOVER}; border-color: #33445a; }}
QPushButton:pressed {{ background: {CARD}; }}
QPushButton:disabled {{ color: {TEXT_DIM}; background: {BG_ELEV}; }}

QPushButton#Primary {{
    background: {ACCENT}; border: none; color: #ffffff; font-weight: 600;
}}
QPushButton#Primary:hover {{ background: {ACCENT_HOVER}; }}
QPushButton#Primary:pressed {{ background: {ACCENT_PRESSED}; }}

QPushButton#Launch {{
    background: {ACCENT}; border: none; color: #ffffff; font-weight: 600;
}}
QPushButton#Launch:hover {{ background: {ACCENT_HOVER}; }}
QPushButton#Stop {{
    background: transparent; border: 1px solid {RED}; color: {RED}; font-weight: 600;
}}
QPushButton#Stop:hover {{ background: rgba(255,92,92,0.12); }}

QPushButton#Ghost {{
    background: transparent; border: 1px solid {BORDER}; padding: 7px 10px;
}}
QPushButton#Ghost:hover {{ background: {CARD_HOVER}; }}
QPushButton#Danger {{
    background: transparent; border: 1px solid {DANGER}; color: {DANGER};
}}
QPushButton#Danger:hover {{ background: rgba(229,72,77,0.12); }}

/* ---- Карточка аккаунта ---- */
#Card {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 16px;
}}
#Card:hover {{ background: {CARD_HOVER}; border-color: #31435a; }}
#CardName {{ font-size: 16px; font-weight: 700; color: {TEXT}; }}
#CardMeta {{ font-size: 12px; color: {TEXT_DIM}; }}
#AccentBar {{ border-radius: 3px; }}

#PillRunning {{
    background: rgba(61,220,132,0.15); color: {GREEN};
    border-radius: 10px; padding: 2px 10px; font-size: 12px; font-weight: 600;
}}
#PillStopped {{
    background: rgba(138,153,173,0.12); color: {TEXT_DIM};
    border-radius: 10px; padding: 2px 10px; font-size: 12px; font-weight: 600;
}}

/* ---- Поля ввода ---- */
QLineEdit, QComboBox, QSpinBox, QPlainTextEdit {{
    background: {BG};
    border: 1px solid {BORDER};
    border-radius: 9px;
    padding: 8px 10px;
    selection-background-color: {ACCENT};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QPlainTextEdit:focus {{
    border-color: {ACCENT};
}}
QComboBox::drop-down {{ border: none; width: 26px; }}
QComboBox QAbstractItemView {{
    background: {BG_ELEV}; border: 1px solid {BORDER};
    selection-background-color: {ACCENT}; padding: 4px;
}}
QLabel#FieldLabel {{ color: {TEXT_DIM}; font-size: 12px; }}
QLabel#Hint {{ color: {TEXT_DIM}; font-size: 12px; }}
QLabel#WarnLabel {{ color: #ffb454; font-size: 12px; }}

/* ---- Разное ---- */
QToolTip {{
    background: {BG_ELEV}; color: {TEXT};
    border: 1px solid {BORDER}; border-radius: 6px; padding: 6px;
}}
QCheckBox {{ spacing: 8px; }}
#EmptyTitle {{ font-size: 18px; font-weight: 700; color: {TEXT}; }}
#EmptyText {{ font-size: 13px; color: {TEXT_DIM}; }}
QStatusBar {{ background: {BG_ELEV}; color: {TEXT_DIM}; border-top: 1px solid {BORDER}; }}
"""
