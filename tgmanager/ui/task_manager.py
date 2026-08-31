"""Менеджер фоновых задач автоматизации (параллельно на нескольких контейнерах)."""
from __future__ import annotations

import json
import sys

from PyQt6.QtCore import QObject, QProcess, pyqtSignal

from .. import paths
from ..automation import lock
from ..models import Account


class Task:
    def __init__(self, account: Account, actions: list[str], revoke: bool):
        self.account = account
        self.actions = actions
        self.revoke = revoke
        self.state = "running"        # running | done | error | stopped
        self.done = 0
        self.total = 0
        self.current = ""
        self.error = ""
        self.log: list[str] = []
        self.proxy_human = ""
        self.proc: QProcess | None = None
        self._buf = ""

    @property
    def id(self) -> str:
        return self.account.id

    @property
    def workdir(self) -> str:
        return paths.account_workdir(self.account.id)

    @property
    def finished(self) -> bool:
        return self.state in ("done", "error", "stopped")


class TaskManager(QObject):
    added = pyqtSignal(str)     # task id
    changed = pyqtSignal(str)
    removed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tasks: dict[str, Task] = {}

    # ---- запросы состояния ----
    def is_active(self, account_id: str) -> bool:
        t = self.tasks.get(account_id)
        return bool(t and t.state == "running")

    def active_count(self) -> int:
        return sum(1 for t in self.tasks.values() if t.state == "running")

    # ---- запуск ----
    def start(self, account: Account, actions: list[str], revoke: bool) -> Task:
        # один активный таск на контейнер
        old = self.tasks.get(account.id)
        if old and old.finished:
            self.tasks.pop(account.id, None)
            self.removed.emit(account.id)

        t = Task(account, actions, revoke)
        worker_argv = ["--workdir", t.workdir, "--actions", ",".join(actions)]
        if revoke:
            worker_argv.append("--revoke")
        prx = account.proxy
        if prx.enabled:
            worker_argv += ["--proxy-type", prx.type, "--proxy-host", prx.host,
                            "--proxy-port", str(prx.port)]
            if prx.username:
                worker_argv += ["--proxy-user", prx.username]
            if prx.password:
                worker_argv += ["--proxy-pass", prx.password]

        if getattr(sys, "frozen", False):
            argv = ["--tg-worker", *worker_argv]
        else:
            argv = ["-m", "tgmanager.automation.worker", *worker_argv]

        proc = QProcess(self)
        from PyQt6.QtCore import QProcessEnvironment
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONIOENCODING", "utf-8")
        env.insert("PYTHONUTF8", "1")
        proc.setProcessEnvironment(env)
        proc.setWorkingDirectory(paths.app_root())
        proc.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        proc.readyReadStandardOutput.connect(lambda tid=t.id: self._read(tid))
        proc.readyReadStandardError.connect(lambda tid=t.id: self._read_err(tid))
        proc.finished.connect(lambda code, st, tid=t.id: self._finished(tid, code))
        t.proc = proc
        self.tasks[t.id] = t

        proc.start(sys.executable, argv)
        proc.waitForStarted(3000)
        lock.acquire(t.workdir, proc.processId(), "cleanup")
        self.added.emit(t.id)
        self.changed.emit(t.id)
        return t

    # ---- поток ----
    def _read(self, tid: str) -> None:
        t = self.tasks.get(tid)
        if not t or not t.proc:
            return
        t._buf += bytes(t.proc.readAllStandardOutput()).decode("utf-8", "replace")
        while "\n" in t._buf:
            line, t._buf = t._buf.split("\n", 1)
            line = line.strip()
            if line:
                self._handle(t, line)
        self.changed.emit(tid)

    def _read_err(self, tid: str) -> None:
        t = self.tasks.get(tid)
        if not t or not t.proc:
            return
        data = bytes(t.proc.readAllStandardError()).decode("utf-8", "replace").rstrip()
        if data:
            t.log.append(data)
            self.changed.emit(tid)

    def _handle(self, t: Task, line: str) -> None:
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            t.log.append(line)
            return
        typ = obj.get("type")
        if typ == "stage":
            t.current = obj.get("msg", "")
            t.log.append("• " + obj.get("msg", ""))
        elif typ == "summary":
            t.total = obj.get("total", 0)
            c = obj.get("counts", {})
            t.log.append(
                f"Найдено: каналы {c.get('channels',0)}, группы {c.get('groups',0)}, "
                f"личные {c.get('private',0)}, боты {c.get('bots',0)}, "
                f"избранное {c.get('saved',0)} · всего {t.total}")
        elif typ == "progress":
            t.done = obj.get("done", 0)
            t.total = obj.get("total", t.total)
            t.current = obj.get("label", "")
            t.log.append(f"[{obj.get('cat','')}] {obj.get('label','')}")
        elif typ == "flood":
            t.current = f"Пауза Telegram: {obj.get('seconds',0)} c"
            t.log.append(f"⏳ FloodWait {obj.get('seconds',0)} c — ждём…")
        elif typ == "warn":
            t.log.append(f"! {obj.get('label','')}: {obj.get('error','')}")
        elif typ == "done":
            if obj.get("dry_run"):
                t.current = "Проверка завершена"
            else:
                sk = obj.get("skipped", 0)
                t.current = "Готово" + (f" · пропущено {sk}" if sk else "")
        elif typ == "error":
            t.error = obj.get("error", "")
            t.log.append("✗ " + t.error)

    def _finished(self, tid: str, code: int) -> None:
        t = self.tasks.get(tid)
        if not t:
            return
        lock.release(t.workdir)
        if t.state == "stopped":
            pass
        elif t.error:
            t.state = "error"
        else:
            t.state = "done"
        t.proc = None
        self.changed.emit(tid)

    # ---- управление ----
    def stop(self, tid: str) -> None:
        t = self.tasks.get(tid)
        if not t:
            return
        t.state = "stopped"
        t.current = "Остановлено"
        if t.proc is not None:
            t.proc.kill()
        lock.release(t.workdir)
        self.changed.emit(tid)

    def remove(self, tid: str) -> None:
        t = self.tasks.get(tid)
        if not t or not t.finished:
            return
        self.tasks.pop(tid, None)
        self.removed.emit(tid)

    def clear_finished(self) -> None:
        for tid in [k for k, v in self.tasks.items() if v.finished]:
            self.tasks.pop(tid, None)
            self.removed.emit(tid)

    def stop_all(self) -> None:
        for tid in list(self.tasks.keys()):
            if self.tasks[tid].state == "running":
                self.stop(tid)
