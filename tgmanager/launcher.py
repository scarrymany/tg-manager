"""Запуск и остановка контейнеров Telegram."""
from __future__ import annotations

import os
import subprocess
import sys
import time
from typing import Optional

from . import paths, proc
from .telegram import LaunchPlan


def _creationflags() -> int:
    if os.name != "nt":
        return 0
    flags = subprocess.CREATE_NEW_PROCESS_GROUP
    flags |= getattr(subprocess, "DETACHED_PROCESS", 0)
    flags |= 0x01000000  # CREATE_BREAKAWAY_FROM_JOB
    return flags


def _popen(argv: list[str], cwd: str, log):
    kwargs = dict(
        cwd=cwd,
        stdout=log,
        stderr=log,
        stdin=subprocess.DEVNULL,
        close_fds=True,
    )
    if os.name == "nt":
        kwargs["creationflags"] = _creationflags()
    else:
        kwargs["start_new_session"] = True
    return subprocess.Popen(argv, **kwargs)


def _start_http_bridge(plan: LaunchPlan) -> Optional[int]:
    """Поднимает локальный SOCKS5→HTTP мост, переписывает proxychains.conf, возвращает pid."""
    if not plan.bridge_args:
        return None
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    argv = [sys.executable, *plan.bridge_args]
    if not getattr(sys, "frozen", False):
        argv = [sys.executable, "-m", "tgmanager.http_bridge", *plan.bridge_args[1:]]

    kwargs = dict(
        cwd=paths.app_root(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        close_fds=True,
    )
    if os.name == "nt":
        kwargs["creationflags"] = (
            subprocess.CREATE_NEW_PROCESS_GROUP
            | getattr(subprocess, "CREATE_NO_WINDOW", 0)
        )
    else:
        kwargs["start_new_session"] = True
    p = subprocess.Popen(argv, **kwargs)
    port = None
    deadline = time.time() + 8
    while time.time() < deadline:
        if p.poll() is not None:
            break
        try:
            line = p.stdout.readline() if p.stdout else b""
        except Exception:
            break
        if not line:
            time.sleep(0.05)
            continue
        text = line.decode("utf-8", "replace").strip()
        if text.startswith("READY "):
            try:
                port = int(text.split(":")[-1])
            except ValueError:
                port = None
            break
    if not port:
        try:
            p.kill()
        except OSError:
            pass
        return None
    conf_path = os.path.join(plan.workdir, "proxychains.conf")
    body = (
        "# Автогенерация TG Manager — не редактируйте вручную\n"
        "strict_chain\n"
        "proxy_dns\n"
        "quiet_mode\n"
        "remote_dns_subnet 224\n"
        "tcp_read_time_out 15000\n"
        "tcp_connect_time_out 8000\n"
        "\n"
        "[ProxyList]\n"
        f"socks5 127.0.0.1 {port}\n"
    )
    with open(conf_path, "w", encoding="utf-8") as f:
        f.write(body)
    proc.write_pid(plan.workdir, p.pid, proc.BRIDGE_PID_FILE)
    return p.pid


def launch(plan: LaunchPlan) -> Optional[int]:
    """Запускает Telegram по плану (отвязанный процесс). Возвращает PID обёртки/Telegram."""
    if not plan.ok or not plan.argv:
        return None
    if plan.bridge_args:
        if _start_http_bridge(plan) is None:
            return None
    log_path = os.path.join(plan.workdir, "launch.log")
    log = open(log_path, "ab", buffering=0)
    proc_ = _popen(plan.argv, plan.workdir, log)
    if proc_.pid:
        proc.write_pid(plan.workdir, proc_.pid)
    return proc_.pid


def stop(workdir: str, force: bool = False) -> int:
    return proc.terminate(workdir, kill=force)


def is_running(workdir: str) -> bool:
    return proc.is_running(workdir)
