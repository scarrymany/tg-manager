"""Тёмная тема TG Manager. Палитра и размеры — язык SCARP.CC.

Токены сняты с SCARP.CC (SCARPCC-NEW/web/css/style.css :root).
Все цвета/радиусы объявлены здесь; другие модули импортируют эти токены,
а не хардкодят HEX.
"""

# ---- Поверхности (нейтральный графит, без navy) ----
BG = "#0A0A0A"           # окно, поля ввода
BG_SIDE = "#0F0F0F"      # шапка, статусбар
BG_CARD = "#141414"      # строка, панель, модалка
BG_CARD2 = "#181818"     # карточка группы настроек (чуть выше)
BG_HOVER = "#1A1A1A"     # hover строки/кнопки

# ---- Контуры ----
BORDER = "#1E1E1E"
BORDER_LIGHT = "#2A2A2A"

# ---- Текст ----
TEXT = "#D4D4D4"
TEXT_SEC = "#A3A3A3"
TEXT_MUTED = "#737373"
TEXT_WHITE = "#FFFFFF"

# ---- Акцент (единственный — белый) ----
ACCENT = "#FFFFFF"
ACCENT_HOVER = "#E0E0E0"
ACCENT_PRESSED = "#D0D0D0"
ACCENT_INK = "#000000"
ACCENT_DISABLED = "#3A3A3A"

# ---- Семантика ----
GREEN = "#4ADE80"
GREEN_BG = "#141C16"
RED = "#F87171"
RED_BG = "#1C1414"
YELLOW = "#FBBF24"
YELLOW_BG = "#1C1810"

# ---- Радиусы ----
RADIUS = "6px"      # карточка/диалог/панель
RADIUS_SM = "4px"   # кнопка/инпут/пилюля
RADIUS_PILL = "4px"

QSS = f"""
* {{
    font-family: "Inter", "Segoe UI", "Ubuntu", "Cantarell", sans-serif;
    font-size: 13px;
    color: {TEXT};
    outline: none;
}}

QMainWindow, QWidget#Board {{ background: {BG}; }}
QDialog {{ background: {BG_CARD}; }}

/* ---- Шапка ---- */
#Header {{
    background: {BG_SIDE};
    border-bottom: 1px solid {BORDER};
}}
#AppTitle {{
    font-size: 17px;
    font-weight: 700;
    color: {TEXT_WHITE};
}}
#AppSubtitle {{
    font-size: 12px;
    color: {TEXT_MUTED};
}}
#DialogTitle {{
    font-size: 14px;
    font-weight: 600;
    color: {TEXT_WHITE};
}}

/* ---- Прокрутка ---- */
QScrollArea {{ border: none; background: {BG}; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 4px; }}
QScrollBar::handle:vertical {{ background: {BORDER_LIGHT}; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #333333; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}

/* ---- Кнопки ---- */
QPushButton {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_SM};
    padding: 8px 12px;
    font-size: 12px;
    font-weight: 500;
    color: {TEXT_SEC};
}}
QPushButton:hover {{ background: {BG_HOVER}; border-color: {BORDER_LIGHT}; color: {TEXT}; }}
QPushButton:pressed {{ background: {BG_CARD}; }}
QPushButton:disabled {{ color: {TEXT_MUTED}; background: {BG_CARD}; border-color: {BORDER}; }}

/* Primary / Launch — единственная белая заливка */
QPushButton#Primary, QPushButton#Launch {{
    background: {ACCENT}; border: none; color: {ACCENT_INK}; font-weight: 600;
}}
QPushButton#Primary:hover, QPushButton#Launch:hover {{ background: {ACCENT_HOVER}; }}
QPushButton#Primary:pressed, QPushButton#Launch:pressed {{ background: {ACCENT_PRESSED}; }}
QPushButton#Primary:disabled, QPushButton#Launch:disabled {{
    background: {ACCENT_DISABLED}; color: {TEXT_MUTED};
}}

/* Ghost / secondary */
QPushButton#Ghost {{
    background: {BG_CARD}; border: 1px solid {BORDER}; color: {TEXT_SEC};
}}
QPushButton#Ghost:hover {{ background: {BG_HOVER}; border-color: {BORDER_LIGHT}; color: {TEXT}; }}
QPushButton#Ghost:checked {{ background: {BG_HOVER}; border-color: {ACCENT}; color: {TEXT_WHITE}; }}

/* Stop — контурная красная, тише primary */
QPushButton#Stop {{
    background: transparent; border: 1px solid {RED}; color: {RED}; font-weight: 600;
}}
QPushButton#Stop:hover {{ background: {RED_BG}; }}
QPushButton#Stop:disabled {{ background: {BG_CARD}; border: 1px solid {BORDER}; color: {TEXT_MUTED}; }}

/* Danger (корзина) — масса как Ghost, не аварийная */
QPushButton#Danger {{
    background: {BG_CARD}; border: 1px solid {BORDER}; color: {RED};
}}
QPushButton#Danger:hover {{ background: {RED_BG}; border-color: {BORDER_LIGHT}; color: {RED}; }}

/* ---- Строка контейнера ---- */
#Row {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: {RADIUS};
}}
#Row:hover {{ background: {BG_HOVER}; border-color: {BORDER_LIGHT}; }}
#RowName {{ font-size: 13px; font-weight: 700; color: {TEXT}; }}
#RowMeta {{ font-size: 12px; color: {TEXT_SEC}; }}
#AccentBar {{ border-radius: 2px; }}

/* ---- Пилюли статуса ---- */
#PillRunning {{
    background: {GREEN_BG}; color: {GREEN};
    border-radius: {RADIUS_PILL}; padding: 3px 8px; font-size: 11px; font-weight: 600;
}}
#PillStopped {{
    background: {BG_HOVER}; color: {TEXT_SEC};
    border-radius: {RADIUS_PILL}; padding: 3px 8px; font-size: 11px; font-weight: 600;
}}

/* ---- Поля ввода ---- */
QLineEdit, QComboBox, QSpinBox, QPlainTextEdit {{
    background: {BG};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_SM};
    padding: 8px 12px;
    min-height: 18px;
    color: {TEXT};
    selection-background-color: {BORDER_LIGHT};
    selection-color: {TEXT_WHITE};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QPlainTextEdit:focus {{
    border-color: {BORDER_LIGHT};
}}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {BG_CARD}; border: 1px solid {BORDER};
    selection-background-color: {BG_HOVER}; selection-color: {TEXT_WHITE}; padding: 4px;
}}

/* ---- Лейблы/хинты ---- */
QLabel#FieldLabel {{
    color: {TEXT_MUTED}; font-size: 11px; font-weight: 600;
}}
QLabel#Hint {{ color: {TEXT_MUTED}; font-size: 12px; }}
QLabel#WarnLabel {{ color: {YELLOW}; font-size: 12px; }}

/* ---- Настройки: карточка группы ---- */
#SettingsCard {{
    background: {BG_CARD2};
    border: 1px solid {BORDER};
    border-radius: {RADIUS};
}}

/* ---- Пустое состояние ---- */
#EmptyMark {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 8px;
}}
#EmptyTitle {{ font-size: 17px; font-weight: 700; color: {TEXT_WHITE}; }}
#EmptyText {{ font-size: 13px; color: {TEXT_MUTED}; }}

/* ---- Прогресс ---- */
QProgressBar {{
    background: {BORDER};
    border: none;
    border-radius: 3px;
    min-height: 6px;
    max-height: 6px;
    text-align: center;
}}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 3px; }}

QPlainTextEdit#Log {{
    background: {BG}; border: 1px solid {BORDER}; border-radius: {RADIUS_SM};
    font-size: 12px; color: {TEXT_SEC};
}}

/* ---- Чекбокс ---- */
QCheckBox {{ spacing: 8px; color: {TEXT}; }}
QCheckBox::indicator {{
    width: 16px; height: 16px; border: 1px solid {BORDER_LIGHT};
    border-radius: 3px; background: {BG};
}}
QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}

/* ---- Тултипы ---- */
QToolTip {{
    background: {BG_CARD}; color: {TEXT};
    border: 1px solid {BORDER}; border-radius: 4px; padding: 6px;
}}

/* ---- Статусбар ---- */
QStatusBar {{ background: {BG_SIDE}; color: {TEXT_MUTED}; border-top: 1px solid {BORDER}; }}

/* ---- Модальные окна QMessageBox ---- */
QMessageBox {{ background: {BG_CARD}; }}
QMessageBox QLabel {{ color: {TEXT}; }}
QMessageBox QPushButton {{ min-width: 84px; }}
"""
