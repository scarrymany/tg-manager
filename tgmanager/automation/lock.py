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
    if os.name == "nt":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
        if not h:
            return False
        try:
            code = ctypes.c_ulong()
            if kernel32.GetExitCodeProcess(h, ctypes.byref(code)):
                return code.value == STILL_ACTIVE
            return True
        finally:
            kernel32.CloseHandle(h)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False


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


def _image_name(pid: int) -> str:
    if pid <= 0:
        return ""
    if os.name != "nt":
        try:
            return os.path.basename(os.readlink(f"/proc/{pid}/exe"))
        except OSError:
            return ""
    import ctypes
    from ctypes import wintypes
    kernel32 = ctypes.windll.kernel32
    h = kernel32.OpenProcess(0x1000, False, int(pid))
    if not h:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(32768)
        size = wintypes.DWORD(len(buf))
        QueryFullProcessImageNameW = kernel32.QueryFullProcessImageNameW
        QueryFullProcessImageNameW.argtypes = [
            wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD),
        ]
        QueryFullProcessImageNameW.restype = wintypes.BOOL
        if QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
            return buf.value
        return ""
    finally:
        kernel32.CloseHandle(h)


def telegram_running(workdir: str) -> bool:
    """True, если telegram.pid указывает на живой telegram/proxychains этого контейнера."""
    path = os.path.join(workdir, "telegram.pid")
    try:
        with open(path, encoding="utf-8") as f:
            pid = int(f.read().strip() or "0")
    except (OSError, ValueError):
        return False
    if not _alive(pid):
        return False
    image = _image_name(pid).lower()
    if not image:
        # имя недоступно — fail-closed, иначе можно словить AUTH_KEY_DUPLICATED
        return True
    base = os.path.basename(image.replace("\\", "/"))
    return "telegram" in base or "proxychains" in base
