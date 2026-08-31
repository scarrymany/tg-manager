"""Определение запущенных инстансов Telegram по рабочей папке (через /proc)."""
from __future__ import annotations

import os
import signal
from typing import List


def _iter_pids():
    for entry in os.listdir("/proc"):
        if entry.isdigit():
            yield int(entry)


def _cmdline(pid: int) -> str:
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            raw = f.read()
    except (OSError, ProcessLookupError):
        return ""
    # аргументы разделены нулевым байтом
    return raw.replace(b"\x00", b" ").decode("utf-8", "replace")


def pids_for_workdir(workdir: str) -> List[int]:
    """PID процессов, чья командная строка ссылается на данную рабочую папку."""
    marker = os.path.abspath(workdir)
    found = []
    mypid = os.getpid()
    for pid in _iter_pids():
        if pid == mypid:
            continue
        cl = _cmdline(pid)
        if not cl:
            continue
        # Именно инстанс Telegram с этой рабочей папкой.
        # Важно: НЕ ловить наш воркер автоматизации (в его cmdline тоже есть workdir).
        if (marker in cl and "telegram" in cl.lower()
                and "tgmanager.automation" not in cl):
            found.append(pid)
    return found


def is_running(workdir: str) -> bool:
    return bool(pids_for_workdir(workdir))


def terminate(workdir: str, kill: bool = False) -> int:
    """Послать SIGTERM (или SIGKILL) всем процессам аккаунта. Возвращает число сигналов."""
    sig = signal.SIGKILL if kill else signal.SIGTERM
    count = 0
    for pid in pids_for_workdir(workdir):
        try:
            os.kill(pid, sig)
            count += 1
        except (ProcessLookupError, PermissionError):
            pass
    return count
