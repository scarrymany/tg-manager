"""Поиск/остановка инстансов Telegram по рабочей папке контейнера."""
from __future__ import annotations

import os
import signal
import time
from typing import List, Set

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


def _norm_path(p: str) -> str:
    return os.path.normcase(os.path.abspath(p or "")).replace("/", "\\").rstrip("\\")


def _contains_workdir(text: str, marker: str) -> bool:
    if not text or not marker:
        return False
    t = text.replace("/", "\\").lower()
    m = marker.replace("/", "\\").lower()
    return m in t


def _is_our_target(name: str, exe: str, cmd: str) -> bool:
    blob = f"{name} {exe} {cmd}".lower()
    if "--tg-worker" in blob or "tgmanager.automation" in blob:
        return False
    if "telegram" in blob:
        return True
    if "proxychains" in blob:
        return True
    if "--tg-http-bridge" in blob:
        return True
    return False


def _psutil_children(pid: int) -> List[int]:
    try:
        import psutil  # type: ignore
        p = psutil.Process(int(pid))
        return [int(c.pid) for c in p.children(recursive=True)]
    except Exception:
        return []


def _win_pids(workdir: str) -> List[int]:
    """PID'ы Telegram / proxychains / HTTP-моста, привязанные к контейнеру."""
    marker = _norm_path(workdir)
    found: List[int] = []
    mypid = os.getpid()
    try:
        import psutil  # type: ignore
    except Exception:
        return found

    for p in psutil.process_iter(["pid", "name", "cmdline", "cwd", "exe"]):
        try:
            info = p.info
            pid = int(info["pid"])
            if pid == mypid:
                continue
            name = info.get("name") or ""
            exe = info.get("exe") or ""
            cmd = " ".join(info.get("cmdline") or [])
            cwd = info.get("cwd") or ""
        except (psutil.Error, TypeError, ValueError, OSError):
            continue
        if not _is_our_target(name, exe, cmd):
            continue
        if (
            _contains_workdir(cmd, marker)
            or _contains_workdir(cwd, marker)
            or _contains_workdir(exe, marker)
        ):
            found.append(pid)
    return found


def _win_cmdlines() -> list[tuple[int, str, str]]:
    """Оставлено для совместимости: (pid, name, cmdline)."""
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
    found: List[int] = []
    seen: Set[int] = set()

    def _add(pid: int) -> None:
        pid = int(pid)
        if not pid or pid in seen:
            return
        if not _pid_alive(pid):
            return
        seen.add(pid)
        found.append(pid)

    pidfile = _read_pidfile(os.path.join(workdir, PID_FILE))
    if pidfile:
        _add(pidfile)
        for child in _psutil_children(pidfile):
            _add(child)

    bridge = _read_pidfile(os.path.join(workdir, BRIDGE_PID_FILE))
    if bridge:
        _add(bridge)
        for child in _psutil_children(bridge):
            _add(child)

    if os.name != "nt":
        for pid in _linux_pids(workdir):
            _add(pid)
        return found

    for pid in _win_pids(workdir):
        _add(pid)
        for child in _psutil_children(pid):
            _add(child)
    return found


def is_running(workdir: str) -> bool:
    return bool(pids_for_workdir(workdir))


def _terminate_nt(pid: int) -> bool:
    """TerminateProcess — иначе Telegram только сворачивается в трей."""
    import ctypes
    kernel32 = ctypes.windll.kernel32
    PROCESS_TERMINATE = 0x0001
    h = kernel32.OpenProcess(PROCESS_TERMINATE, False, int(pid))
    if not h:
        return False
    try:
        return bool(kernel32.TerminateProcess(h, 1))
    finally:
        kernel32.CloseHandle(h)


def _kill_pid(pid: int, force: bool = False) -> bool:
    if os.name == "nt":
        # WM_CLOSE (taskkill без /F) = «в трей», не выход. Всегда TerminateProcess.
        ok = False
        try:
            import psutil  # type: ignore
            try:
                p = psutil.Process(int(pid))
                for c in p.children(recursive=True):
                    try:
                        c.kill()
                        ok = True
                    except psutil.Error:
                        pass
                try:
                    p.kill()
                    ok = True
                except psutil.Error:
                    pass
            except psutil.Error:
                pass
        except Exception:
            pass
        import subprocess
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(int(pid))],
                capture_output=True, timeout=8, creationflags=flags,
            )
            ok = True
        except Exception:
            pass
        if _pid_alive(pid):
            ok = _terminate_nt(pid) or ok
        return ok
    sig = signal.SIGKILL if force else signal.SIGTERM
    try:
        os.kill(pid, sig)
        return True
    except (ProcessLookupError, PermissionError, OSError):
        return False


def terminate(workdir: str, kill: bool = False) -> int:
    """Остановить Telegram (и HTTP-мост, если был). Возвращает число сигналов."""
    if os.name == "nt":
        kill = True  # иначе Telegram Desktop прячется в трей
    count = 0
    rounds = 4 if os.name == "nt" else 1
    for i in range(rounds):
        pids = pids_for_workdir(workdir)
        if not pids and i > 0:
            break
        for pid in pids:
            if _kill_pid(pid, force=kill):
                count += 1
        if os.name == "nt" and i + 1 < rounds:
            time.sleep(0.15)
    bridge = _read_pidfile(os.path.join(workdir, BRIDGE_PID_FILE))
    if bridge and _pid_alive(bridge):
        if _kill_pid(bridge, force=True):
            count += 1
    clear_pid(workdir, PID_FILE)
    clear_pid(workdir, BRIDGE_PID_FILE)
    return count
