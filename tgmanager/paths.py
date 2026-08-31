"""Пути приложения (XDG) и расположение переносного Telegram."""
from __future__ import annotations

import os

from . import APP_ID

# Корень установки приложения (папка, где лежит main.py)
APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(APP_ROOT, "assets")

# Переносной Telegram, вложенный в программу
BUNDLED_TELEGRAM_DIR = os.path.join(APP_ROOT, "telegram")
BUNDLED_TELEGRAM_BIN = os.path.join(BUNDLED_TELEGRAM_DIR, "Telegram")


def _xdg(env: str, default_rel: str) -> str:
    base = os.environ.get(env)
    if not base:
        base = os.path.join(os.path.expanduser("~"), default_rel)
    return os.path.join(base, APP_ID)


CONFIG_DIR = _xdg("XDG_CONFIG_HOME", ".config")
DATA_DIR = _xdg("XDG_DATA_HOME", ".local/share")

CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
ACCOUNTS_DIR = os.path.join(DATA_DIR, "accounts")


def ensure_dirs() -> None:
    for d in (CONFIG_DIR, DATA_DIR, ACCOUNTS_DIR):
        os.makedirs(d, exist_ok=True)


def account_workdir(account_id: str) -> str:
    """Рабочая папка аккаунта. Telegram ждёт tdata внутри неё."""
    return os.path.join(ACCOUNTS_DIR, account_id)


def account_tdata(account_id: str) -> str:
    return os.path.join(account_workdir(account_id), "tdata")


def icon_path() -> str:
    return os.path.join(ASSETS_DIR, "icon.png")


def logo_mark_path() -> str:
    """Белая плашка со знаком — для шапки/пустого состояния (стиль SCARP .logo-icon)."""
    return os.path.join(ASSETS_DIR, "logo_mark.png")
