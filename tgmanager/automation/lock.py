"""Взаимная блокировка контейнера: запуск Telegram vs автоматизация.

Один tdata нельзя одновременно открывать в TDesktop и в Telethon —
сервер выбросит сессию (AUTH_KEY_DUPLICATED). Лок это предотвращает.
"""
from __future__ import annotations

import json
import os
from typing import Optional

LOCK_NAME = "automation.lock"


def _path(workdir: str) -> str:
    return os.path.join(workdir, LOCK_NAME)


def _alive(pid: int) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # существует, но чужой — считаем живым


def acquire(workdir: str, pid: int, action: str = "") -> None:
    with open(_path(workdir), "w", encoding="utf-8") as f:
        json.dump({"pid": int(pid), "action": action}, f)


def release(workdir: str) -> None:
    try:
        os.remove(_path(workdir))
    except FileNotFoundError:
        pass


def info(workdir: str) -> Optional[dict]:
    try:
        with open(_path(workdir), "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def is_locked(workdir: str) -> bool:
    """True, если идёт автоматизация. Устаревший лок (мёртвый pid) снимается."""
    d = info(workdir)
    if not d:
        return False
    pid = int(d.get("pid", 0) or 0)
    if pid and not _alive(pid):
        release(workdir)
        return False
    return True
