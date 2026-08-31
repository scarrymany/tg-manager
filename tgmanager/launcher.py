"""Запуск и остановка аккаунтов Telegram."""
from __future__ import annotations

import os
import subprocess
from typing import Optional

from . import proc
from .telegram import LaunchPlan, build_launch_plan


def launch(plan: LaunchPlan) -> Optional[int]:
    """Запускает Telegram по плану (отвязанный от менеджера процесс). Возвращает PID."""
    if not plan.ok or not plan.argv:
        return None
    log_path = os.path.join(plan.workdir, "launch.log")
    log = open(log_path, "ab", buffering=0)
    proc_ = subprocess.Popen(
        plan.argv,
        cwd=plan.workdir,
        stdout=log,
        stderr=log,
        stdin=subprocess.DEVNULL,
        start_new_session=True,  # отвязать от менеджера — Telegram живёт сам по себе
    )
    return proc_.pid


def stop(workdir: str, force: bool = False) -> int:
    return proc.terminate(workdir, kill=force)


def is_running(workdir: str) -> bool:
    return proc.is_running(workdir)
