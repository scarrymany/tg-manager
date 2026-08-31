"""Строка одного Telegram-аккаунта (формат списка: 1 строка = 1 аккаунт)."""
from __future__ import annotations

import os

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .. import paths
from ..models import Account
from .style import TEXT_SEC, YELLOW


class AccountRow(QFrame):
    launch = pyqtSignal(str)
    stop = pyqtSignal(str)
    edit = pyqtSignal(str)
    delete = pyqtSignal(str)
    open_folder = pyqtSignal(str)
    automate = pyqtSignal(str)

    def __init__(self, account: Account, parent: QWidget | None = None):
        super().__init__(parent)
        self.account = account
        self._running = False
        self._busy = False
        self._state = None  # чтобы первое обновление применилось
        self.setObjectName("Row")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(60)
        self._build()

    # ---------- построение ----------
    def _build(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 8, 12, 8)
        root.setSpacing(10)

        # Цветная метка-идентификатор
        self.bar = QFrame()
        self.bar.setObjectName("AccentBar")
        self.bar.setFixedSize(3, 36)
        self.bar.setStyleSheet(f"background: {self.account.color}; border-radius: 2px;")
        root.addWidget(self.bar)

        # Имя + мета
        info = QVBoxLayout()
        info.setContentsMargins(0, 0, 0, 0)
        info.setSpacing(2)
        self.name_label = QLabel(self.account.name)
        self.name_label.setObjectName("RowName")
        self.meta_label = QLabel()
        self.meta_label.setObjectName("RowMeta")
        info.addWidget(self.name_label)
        info.addWidget(self.meta_label)
        info_w = QWidget()
        info_w.setLayout(info)
        info_w.setMinimumWidth(220)
        root.addWidget(info_w, 1)

        # Статус
        self.pill = QLabel("○ Остановлен")
        self.pill.setObjectName("PillStopped")
        self.pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.pill)

        # Кнопки действий
        self.launch_btn = QPushButton("▶  Запуск")
        self.launch_btn.setObjectName("Launch")
        self.launch_btn.setFixedWidth(104)
        self.launch_btn.clicked.connect(lambda: self.launch.emit(self.account.id))
        self.stop_btn = QPushButton("■  Стоп")
        self.stop_btn.setObjectName("Stop")
        self.stop_btn.setFixedWidth(84)
        self.stop_btn.clicked.connect(lambda: self.stop.emit(self.account.id))

        folder_btn = QPushButton("📁  Папка")
        folder_btn.setObjectName("Ghost")
        folder_btn.setFixedWidth(96)
        folder_btn.setToolTip("Открыть папку аккаунта — сюда положите папку tdata")
        folder_btn.clicked.connect(lambda: self.open_folder.emit(self.account.id))
        self.auto_btn = QPushButton("🧹")
        self.auto_btn.setObjectName("Ghost")
        self.auto_btn.setFixedSize(34, 34)
        self.auto_btn.setToolTip("Автоматизация (чистка аккаунта)")
        self.auto_btn.clicked.connect(lambda: self.automate.emit(self.account.id))
        edit_btn = QPushButton("✏")
        edit_btn.setObjectName("Ghost")
        edit_btn.setFixedSize(34, 34)
        edit_btn.setToolTip("Изменить")
        edit_btn.clicked.connect(lambda: self.edit.emit(self.account.id))
        del_btn = QPushButton("🗑")
        del_btn.setObjectName("Danger")
        del_btn.setFixedSize(34, 34)
        del_btn.setToolTip("Удалить")
        del_btn.clicked.connect(lambda: self.delete.emit(self.account.id))

        for w in (self.launch_btn, self.stop_btn, folder_btn, self.auto_btn, edit_btn, del_btn):
            root.addWidget(w)

        self._apply_state()
        self.refresh()

    # ---------- обновление ----------
    def set_account(self, account: Account) -> None:
        self.account = account
        self.name_label.setText(account.name)
        self.bar.setStyleSheet(f"background: {account.color}; border-radius: 3px;")
        self.refresh()

    def refresh(self) -> None:
        proxy = self.account.proxy.summary()
        if os.path.isdir(paths.account_tdata(self.account.id)):
            tdata = f'<span style="color:{TEXT_SEC}">✓ tdata</span>'
        else:
            tdata = f'<span style="color:{YELLOW}">✗ нет tdata</span>'
        # жёлтый только на сегменте «нет tdata», прокси остаётся серым
        self.meta_label.setText(
            f'<span style="color:{TEXT_SEC}">{proxy}  ·  </span>{tdata}')

    def set_running(self, running: bool) -> None:
        if running != self._running:
            self._running = running
            self._apply_state()

    def set_busy(self, busy: bool) -> None:
        if busy != self._busy:
            self._busy = busy
            self._apply_state()

    def _apply_state(self) -> None:
        # приоритет: busy (автоматизация) > running > stopped
        state = "busy" if self._busy else ("running" if self._running else "stopped")
        if state == self._state:
            return
        self._state = state
        if state == "busy":
            self.pill.setText("🔒 Чистка…")
            self.pill.setObjectName("PillStopped")
            self.launch_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
            self.auto_btn.setEnabled(True)   # открыть окно прогресса
        elif state == "running":
            self.pill.setText("● Запущен")
            self.pill.setObjectName("PillRunning")
            self.launch_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.auto_btn.setEnabled(False)  # нельзя чистить при запущенном TG
        else:
            self.pill.setText("○ Остановлен")
            self.pill.setObjectName("PillStopped")
            self.launch_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.auto_btn.setEnabled(True)
        self.pill.style().unpolish(self.pill)
        self.pill.style().polish(self.pill)


# Обратная совместимость по имени
AccountCard = AccountRow
