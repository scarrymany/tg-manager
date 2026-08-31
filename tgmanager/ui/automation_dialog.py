"""Панель автоматизации контейнера: чистка аккаунта (каналы/группы/чаты/…)."""
from __future__ import annotations

import json
import os
import sys

from PyQt6.QtCore import QProcess, Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from .. import paths, proc
from ..automation import deps, lock
from ..models import Account
from .style import GREEN, RED, TEXT_SEC, YELLOW

# (ключ, подпись, по умолчанию)
ACTIONS = [
    ("channels", "Каналы — выйти", True),
    ("groups", "Группы — выйти / удалить", True),
    ("private", "Личные переписки — удалить", True),
    ("bots", "Боты — удалить чат", True),
    ("saved", "«Избранное» (Saved) — очистить", True),
    ("contacts", "Контакты — удалить", False),
    ("photos", "Фото профиля — удалить", False),
]


class AutomationDialog(QDialog):
    def __init__(self, parent, account: Account):
        super().__init__(parent)
        self.account = account
        self.workdir = paths.account_workdir(account.id)
        self._proc: QProcess | None = None
        self._buf = ""
        self._running = False
        self._dry = False
        self.requested = None  # (actions, revoke) — выставляется при «Запустить чистку»
        self.setWindowTitle("Автоматизация")
        self.setMinimumWidth(540)
        self.setModal(True)
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 22, 22, 18)
        root.setSpacing(12)

        title = QLabel(f"Автоматизация — «{self.account.name}»")
        title.setObjectName("DialogTitle")
        root.addWidget(title)

        warn = QLabel("⚠ Действия необратимы. Telegram этого контейнера должен быть закрыт "
                      "(во время чистки запуск заблокирован).")
        warn.setObjectName("Hint")
        warn.setWordWrap(True)
        warn.setStyleSheet(f"color:{YELLOW};")
        root.addWidget(warn)

        # Через какой прокси пойдёт подключение
        prx = self.account.proxy
        conn = f"Подключение: через {prx.summary()}" if prx.enabled \
            else "Подключение: напрямую (у контейнера не задан прокси)"
        self.conn_label = QLabel(conn)
        self.conn_label.setObjectName("Hint")
        self.conn_label.setWordWrap(True)
        root.addWidget(self.conn_label)

        # Галочки действий
        card = QFrame()
        card.setObjectName("SettingsCard")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(14, 12, 14, 12)
        cl.setSpacing(8)
        head = QLabel("ЧТО ЧИСТИТЬ")
        head.setObjectName("FieldLabel")
        cl.addWidget(head)
        self.checks: dict[str, QCheckBox] = {}
        for key, label, default in ACTIONS:
            chk = QCheckBox(label)
            chk.setChecked(default)
            self.checks[key] = chk
            cl.addWidget(chk)
        self.revoke_chk = QCheckBox("Удалять личные переписки и у собеседника (revoke)")
        cl.addWidget(self.revoke_chk)
        root.addWidget(card)

        # Прогресс
        self.status = QLabel("Готово к проверке.")
        self.status.setObjectName("Hint")
        self.status.setWordWrap(True)
        root.addWidget(self.status)
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        root.addWidget(self.bar)
        self.log = QPlainTextEdit()
        self.log.setObjectName("Log")
        self.log.setReadOnly(True)
        self.log.setFixedHeight(130)
        root.addWidget(self.log)

        # Подтверждение необратимости
        self.confirm_chk = QCheckBox("Я понимаю, что это необратимо")
        self.confirm_chk.toggled.connect(self._sync_buttons)
        root.addWidget(self.confirm_chk)

        # Кнопки
        btns = QHBoxLayout()
        self.dry_btn = QPushButton("Проверить (dry-run)")
        self.dry_btn.setObjectName("Ghost")
        self.dry_btn.clicked.connect(lambda: self._start(dry=True))
        self.run_btn = QPushButton("Запустить чистку")
        self.run_btn.setObjectName("Danger")
        self.run_btn.clicked.connect(self._request_cleanup)
        btns.addWidget(self.dry_btn)
        btns.addStretch(1)
        self.close_btn = QPushButton("Закрыть")
        self.close_btn.setObjectName("Ghost")
        self.close_btn.clicked.connect(self._on_close)
        btns.addWidget(self.run_btn)
        btns.addWidget(self.close_btn)
        root.addLayout(btns)
        self._sync_buttons()

    # ---------- helpers ----------
    def _selected(self):
        return [k for k, c in self.checks.items() if c.isChecked()]

    def _sync_buttons(self):
        self.run_btn.setEnabled(self.confirm_chk.isChecked() and not self._running)

    def _set_inputs_enabled(self, enabled: bool):
        for c in self.checks.values():
            c.setEnabled(enabled)
        self.revoke_chk.setEnabled(enabled)
        self.confirm_chk.setEnabled(enabled)
        self.dry_btn.setEnabled(enabled)
        self._sync_buttons()

    def _request_cleanup(self):
        """Не запускает здесь, а отдаёт конфиг в TaskManager (фоновая задача)."""
        if self._running:
            return
        if deps.missing():
            QMessageBox.warning(self, "Нет зависимостей",
                                "Не установлены telethon/opentele.\n\n" + deps.INSTALL_HINT)
            return
        actions = self._selected()
        if not actions:
            QMessageBox.information(self, "Ничего не выбрано", "Отметьте, что чистить.")
            return
        if proc.is_running(self.workdir):
            QMessageBox.warning(self, "Telegram запущен",
                                "Сначала остановите Telegram этого контейнера («Стоп»).")
            return
        r = QMessageBox.question(
            self, "Подтверждение",
            "Запустить необратимую чистку выбранных разделов в фоне?\n"
            f"Разделы: {', '.join(actions)}"
            + ("\nЛичные — с revoke (у обеих сторон)." if self.revoke_chk.isChecked() else ""),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if r != QMessageBox.StandardButton.Yes:
            return
        self.requested = (actions, self.revoke_chk.isChecked())
        self.accept()

    # ---------- dry-run (внутри окна) ----------
    def _start(self, dry: bool):
        if self._running:
            return
        if deps.missing():
            QMessageBox.warning(self, "Нет зависимостей",
                                "Не установлены telethon/opentele.\n\n" + deps.INSTALL_HINT)
            return
        actions = self._selected()
        if not actions:
            QMessageBox.information(self, "Ничего не выбрано", "Отметьте, что чистить.")
            return
        # Критично: Telegram этого контейнера не должен быть запущен
        if proc.is_running(self.workdir):
            QMessageBox.warning(self, "Telegram запущен",
                                "Сначала остановите Telegram этого контейнера "
                                "(кнопка «Стоп»), иначе сессию выбросит.")
            return
        if not dry:
            r = QMessageBox.question(
                self, "Подтверждение",
                "Выполнить необратимую чистку выбранных разделов?\n"
                f"Разделы: {', '.join(actions)}"
                + ("\nЛичные — с revoke (у обеих сторон)." if self.revoke_chk.isChecked() else ""),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if r != QMessageBox.StandardButton.Yes:
                return

        self._dry = dry
        self._buf = ""
        self.log.clear()
        self.bar.setRange(0, 0)  # индикатор до summary
        self.status.setText("Проверка…" if dry else "Чистка…")
        self._running = True
        self._set_inputs_enabled(False)
        self.close_btn.setText("Остановить")

        argv = ["-m", "tgmanager.automation.worker", "--workdir", self.workdir,
                "--actions", ",".join(actions)]
        if self.revoke_chk.isChecked():
            argv.append("--revoke")
        if dry:
            argv.append("--dry-run")
        # Прокси контейнера — Telethon пойдёт через него
        prx = self.account.proxy
        if prx.enabled:
            argv += ["--proxy-type", prx.type, "--proxy-host", prx.host,
                     "--proxy-port", str(prx.port)]
            if prx.username:
                argv += ["--proxy-user", prx.username]
            if prx.password:
                argv += ["--proxy-pass", prx.password]

        self._proc = QProcess(self)
        self._proc.setWorkingDirectory(paths.APP_ROOT)
        self._proc.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        self._proc.readyReadStandardOutput.connect(self._read_out)
        self._proc.readyReadStandardError.connect(self._read_err)
        self._proc.finished.connect(self._finished)
        self._proc.start(sys.executable, argv)
        self._proc.waitForStarted(3000)
        # Блокировка: пока идёт — запуск Telegram этого контейнера запрещён
        lock.acquire(self.workdir, self._proc.processId(), "cleanup" if not dry else "dry-run")

    # ---------- поток ----------
    def _read_out(self):
        if not self._proc:
            return
        self._buf += bytes(self._proc.readAllStandardOutput()).decode("utf-8", "replace")
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            line = line.strip()
            if line:
                self._handle(line)

    def _read_err(self):
        if not self._proc:
            return
        data = bytes(self._proc.readAllStandardError()).decode("utf-8", "replace").rstrip()
        if data:
            self.log.appendPlainText(data)

    def _handle(self, line: str):
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            self.log.appendPlainText(line)
            return
        t = obj.get("type")
        if t == "stage":
            self.status.setText(obj.get("msg", ""))
            self.log.appendPlainText("• " + obj.get("msg", ""))
        elif t == "summary":
            c = obj.get("counts", {})
            total = obj.get("total", 0)
            self.bar.setRange(0, max(1, total))
            self.bar.setValue(0)
            parts = [f"каналы {c.get('channels',0)}", f"группы {c.get('groups',0)}",
                     f"личные {c.get('private',0)}", f"боты {c.get('bots',0)}",
                     f"избранное {c.get('saved',0)}"]
            if obj.get("contacts"):
                parts.append("контакты")
            if obj.get("photos"):
                parts.append("фото")
            msg = "Найдено: " + ", ".join(parts) + f" · всего действий: {total}"
            self.status.setText(msg)
            self.log.appendPlainText(msg)
        elif t == "progress":
            self.bar.setValue(obj.get("done", 0))
            self.status.setText(f"{obj.get('done',0)}/{obj.get('total',0)} — {obj.get('label','')}")
            self.log.appendPlainText(f"[{obj.get('cat','')}] {obj.get('label','')}")
        elif t == "flood":
            self.log.appendPlainText(
                f"⏳ FloodWait: Telegram просит подождать {obj.get('seconds',0)} c — ждём…")
            self.status.setText(f"Пауза по требованию Telegram: {obj.get('seconds',0)} c")
        elif t == "warn":
            self.log.appendPlainText(f"! {obj.get('label','')}: {obj.get('error','')}")
        elif t == "done":
            if obj.get("dry_run"):
                self.status.setText("Проверка завершена (ничего не удалено).")
                self.status.setStyleSheet(f"color:{GREEN};")
            else:
                self.status.setText(f"Готово. Выполнено действий: {obj.get('done',0)}.")
                self.status.setStyleSheet(f"color:{GREEN};")
        elif t == "error":
            self.log.appendPlainText("✗ " + obj.get("error", ""))
            self.status.setText("Ошибка: " + obj.get("error", ""))
            self.status.setStyleSheet(f"color:{RED};")

    def _finished(self, code, _status):
        lock.release(self.workdir)
        self._proc = None
        self._running = False
        if self.bar.maximum() == 0:
            self.bar.setRange(0, 1)
        self.bar.setValue(self.bar.maximum())
        self._set_inputs_enabled(True)
        self.close_btn.setText("Закрыть")
        # после реальной чистки снимаем подтверждение
        if not self._dry:
            self.confirm_chk.setChecked(False)

    def _on_close(self):
        if self._running and self._proc is not None:
            r = QMessageBox.question(
                self, "Остановить?",
                "Остановить процесс автоматизации?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if r != QMessageBox.StandardButton.Yes:
                return
            self._proc.kill()
            lock.release(self.workdir)
            self._running = False
            return
        self.accept()

    def closeEvent(self, event):  # noqa: N802
        if self._running and self._proc is not None:
            self._proc.kill()
        lock.release(self.workdir)
        super().closeEvent(event)
