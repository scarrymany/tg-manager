"""Поиск/остановка инстансов Telegram по рабочей папке контейнера."""
from __future__ import annotations

import os
import signal
from typing import List

PID_FILE = "telegram.pid"
BRIDGE_PID_FILE = "http_bridge.pid"


def _pid_alive(pid: int) -> bool:
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


def _read_pidfile(path: str) -> int:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return int((f.read() or "0").strip() or "0")
    except (OSError, ValueError):
        return 0


def write_pid(workdir: str, pid: int, name: str = PID_FILE) -> None:
    try:
        with open(os.path.join(workdir, name), "w", encoding="utf-8") as f:
            f.write(str(int(pid)))
    except OSError:
        pass


def clear_pid(workdir: str, name: str = PID_FILE) -> None:
    try:
        os.remove(os.path.join(workdir, name))
    except FileNotFoundError:
        pass
    except OSError:
        pass


def _linux_pids(workdir: str) -> List[int]:
    marker = os.path.abspath(workdir)
    found: List[int] = []
    mypid = os.getpid()
    try:
        entries = os.listdir("/proc")
    except OSError:
        return found
    for entry in entries:
        if not entry.isdigit():
            continue
        pid = int(entry)
        if pid == mypid:
            continue
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as f:
                raw = f.read()
        except (OSError, ProcessLookupError):
            continue
        cl = raw.replace(b"\x00", b" ").decode("utf-8", "replace")
        if not cl:
            continue
        if (marker in cl and "telegram" in cl.lower()
                and "tgmanager.automation" not in cl):
            found.append(pid)
    return found


def _win_cmdlines() -> list[tuple[int, str, str]]:
    """(pid, name, cmdline) через psutil, если есть; иначе Toolhelp + pid-файлы."""
    out: list[tuple[int, str, str]] = []
    try:
        import psutil  # type: ignore
        for p in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                info = p.info
                name = (info.get("name") or "")
                cmd = " ".join(info.get("cmdline") or [])
                out.append((int(info["pid"]), name, cmd))
            except (psutil.Error, TypeError, ValueError):
                continue
        return out
    except Exception:
        pass
    # fallback: имена процессов через Toolhelp (без командной строки)
    try:
        import ctypes
        from ctypes import wintypes

        TH32CS_SNAPPROCESS = 0x00000002

        class PROCESSENTRY32(ctypes.Structure):
            _fields_ = [
                ("dwSize", wintypes.DWORD),
                ("cntUsage", wintypes.DWORD),
                ("th32ProcessID", wintypes.DWORD),
                ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                ("th32ModuleID", wintypes.DWORD),
                ("cntThreads", wintypes.DWORD),
                ("th32ParentProcessID", wintypes.DWORD),
                ("pcPriClassBase", ctypes.c_long),
                ("dwFlags", wintypes.DWORD),
                ("szExeFile", wintypes.WCHAR * 260),
            ]

        kernel32 = ctypes.windll.kernel32
        snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        if snap == wintypes.HANDLE(-1).value:
            return out
        try:
            pe = PROCESSENTRY32()
            pe.dwSize = ctypes.sizeof(PROCESSENTRY32)
            if not kernel32.Process32FirstW(snap, ctypes.byref(pe)):
                return out
            while True:
                out.append((int(pe.th32ProcessID), pe.szExeFile, pe.szExeFile))
                if not kernel32.Process32NextW(snap, ctypes.byref(pe)):
                    break
        finally:
            kernel32.CloseHandle(snap)
    except Exception:
        pass
    return out


def pids_for_workdir(workdir: str) -> List[int]:
    """PID процессов Telegram, привязанных к этой рабочей папке."""
    marker = os.path.abspath(workdir)
    found: List[int] = []
    pidfile = _read_pidfile(os.path.join(workdir, PID_FILE))
    if pidfile and _pid_alive(pidfile):
        found.append(pidfile)

    if os.name != "nt":
        for pid in _linux_pids(workdir):
            if pid not in found:
                found.append(pid)
        return found

    mypid = os.getpid()
    marker_l = marker.lower()
    for pid, name, cmd in _win_cmdlines():
        if pid == mypid or pid in found:
            continue
        blob = f"{name} {cmd}".lower()
        if "telegram" not in blob:
            continue
        if "tgmanager.automation" in blob or "--tg-worker" in blob:
            continue
        if marker_l in blob.lower() or marker_l.replace("\\", "/") in blob.replace("\\", "/"):
            found.append(pid)
    return found


def is_running(workdir: str) -> bool:
    return bool(pids_for_workdir(workdir))


def _kill_pid(pid: int, force: bool = False) -> bool:
    if os.name == "nt":
        import subprocess
        args = ["taskkill", "/PID", str(int(pid)), "/T"]
        if force:
            args.append("/F")
        try:
            subprocess.run(args, capture_output=True, timeout=8)
            return True
        except Exception:
            pass
        try:
            os.kill(pid, signal.SIGTERM)
            return True
        except OSError:
            return False
    sig = signal.SIGKILL if force else signal.SIGTERM
    try:
        os.kill(pid, sig)
        return True
    except (ProcessLookupError, PermissionError, OSError):
        return False


def terminate(workdir: str, kill: bool = False) -> int:
    """Остановить Telegram (и HTTP-мост, если был). Возвращает число сигналов."""
    count = 0
    for pid in pids_for_workdir(workdir):
        if _kill_pid(pid, force=kill):
            count += 1
    bridge = _read_pidfile(os.path.join(workdir, BRIDGE_PID_FILE))
    if bridge and _pid_alive(bridge):
        if _kill_pid(bridge, force=True):
            count += 1
    clear_pid(workdir, PID_FILE)
    clear_pid(workdir, BRIDGE_PID_FILE)
    return count
