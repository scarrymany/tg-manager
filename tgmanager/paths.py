"""Портативные пути: всё живёт в папке с программой (как SCARP.CC).

В frozen-сборке (PyInstaller) корень — папка с exe. В исходниках — корень репо.
Иконки при упаковке читаются из sys._MEIPASS, данные всегда рядом с exe.
"""
from __future__ import annotations

import os
import sys

from . import APP_ID


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False) or getattr(sys, "_MEIPASS", None))


def app_root() -> str:
    """Папка, в которой лежит программа (exe или main.py). Данные пишутся сюда."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resources_dir() -> str:
    """Read-only ресурсы (иконки). В onefile — распакованный _MEIPASS."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return meipass
    return app_root()


APP_ROOT = app_root()
ASSETS_DIR = os.path.join(resources_dir(), "assets")

BUNDLED_TELEGRAM_DIR = os.path.join(APP_ROOT, "telegram")
BUNDLED_TELEGRAM_BIN = os.path.join(
    BUNDLED_TELEGRAM_DIR,
    "Telegram.exe" if os.name == "nt" else "Telegram",
)

TOOLS_DIR = os.path.join(APP_ROOT, "tools")
PROXYCHAINS_DIR = os.path.join(TOOLS_DIR, "proxychains")

CONFIG_DIR = APP_ROOT
DATA_DIR = APP_ROOT
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
ACCOUNTS_DIR = os.path.join(DATA_DIR, "accounts")


def refresh() -> None:
    """Пересчитать корни после смены cwd (на всякий случай)."""
    global APP_ROOT, ASSETS_DIR, BUNDLED_TELEGRAM_DIR, BUNDLED_TELEGRAM_BIN
    global TOOLS_DIR, PROXYCHAINS_DIR, CONFIG_DIR, DATA_DIR, CONFIG_FILE, ACCOUNTS_DIR
    APP_ROOT = app_root()
    ASSETS_DIR = os.path.join(resources_dir(), "assets")
    BUNDLED_TELEGRAM_DIR = os.path.join(APP_ROOT, "telegram")
    BUNDLED_TELEGRAM_BIN = os.path.join(
        BUNDLED_TELEGRAM_DIR,
        "Telegram.exe" if os.name == "nt" else "Telegram",
    )
    TOOLS_DIR = os.path.join(APP_ROOT, "tools")
    PROXYCHAINS_DIR = os.path.join(TOOLS_DIR, "proxychains")
    CONFIG_DIR = APP_ROOT
    DATA_DIR = APP_ROOT
    CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
    ACCOUNTS_DIR = os.path.join(DATA_DIR, "accounts")


def ensure_dirs() -> None:
    refresh()
    for d in (CONFIG_DIR, DATA_DIR, ACCOUNTS_DIR):
        os.makedirs(d, exist_ok=True)


def account_workdir(account_id: str) -> str:
    """Рабочая папка контейнера. Telegram ждёт tdata внутри неё."""
    return os.path.join(ACCOUNTS_DIR, account_id)


def account_tdata(account_id: str) -> str:
    return os.path.join(account_workdir(account_id), "tdata")


def icon_path() -> str:
    png = os.path.join(ASSETS_DIR, "icon.png")
    if os.path.exists(png):
        return png
    ico = os.path.join(ASSETS_DIR, "icon.ico")
    if os.path.exists(ico):
        return ico
    # рядом с exe (portable)
    for name in ("icon.ico", "assets/icon.ico", "assets/icon.png"):
        cand = os.path.join(APP_ROOT, name)
        if os.path.exists(cand):
            return cand
    return png


def icon_ico_path() -> str:
    for cand in (
        os.path.join(ASSETS_DIR, "icon.ico"),
        os.path.join(APP_ROOT, "icon.ico"),
        os.path.join(APP_ROOT, "assets", "icon.ico"),
    ):
        if os.path.exists(cand):
            return cand
    return os.path.join(ASSETS_DIR, "icon.ico")


def logo_mark_path() -> str:
    return os.path.join(ASSETS_DIR, "logo_mark.png")


def proxychains_exe() -> str:
    if os.name == "nt":
        return os.path.join(PROXYCHAINS_DIR, "proxychains_win32_x64.exe")
    return ""
