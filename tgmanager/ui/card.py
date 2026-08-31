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


class AccountRow(QFrame):
    launch = pyqtSignal(str)
    stop = pyqtSignal(str)
    edit = pyqtSignal(str)
    delete = pyqtSignal(str)
    open_folder = pyqtSignal(str)

    def __init__(self, account: Account, parent: QWidget | None = None):
        super().__init__(parent)
        self.account = account
        self._running = None
        self.setObjectName("Row")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(70)
        self._build()

    # ---------- построение ----------
    def _build(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(14, 10, 14, 10)
        root.setSpacing(14)

        # Акцентная полоса
        self.bar = QFrame()
        self.bar.setObjectName("AccentBar")
        self.bar.setFixedSize(5, 46)
        self.bar.setStyleSheet(f"background: {self.account.color}; border-radius: 3px;")
        root.addWidget(self.bar)

        # Имя + мета
        info = QVBoxLayout()
        info.setSpacing(3)
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
        self.pill.setFixedWidth(120)
        root.addWidget(self.pill)

        # Кнопки действий
        self.launch_btn = QPushButton("▶  Запуск")
        self.launch_btn.setObjectName("Launch")
        self.launch_btn.setFixedWidth(112)
        self.launch_btn.clicked.connect(lambda: self.launch.emit(self.account.id))
        self.stop_btn = QPushButton("■  Стоп")
        self.stop_btn.setObjectName("Stop")
        self.stop_btn.setFixedWidth(92)
        self.stop_btn.clicked.connect(lambda: self.stop.emit(self.account.id))

        folder_btn = QPushButton("📁  Папка")
        folder_btn.setObjectName("Ghost")
        folder_btn.setFixedWidth(104)
        folder_btn.setToolTip("Открыть папку аккаунта — сюда положите папку tdata")
        folder_btn.clicked.connect(lambda: self.open_folder.emit(self.account.id))
        edit_btn = QPushButton("✏")
        edit_btn.setObjectName("Ghost")
        edit_btn.setFixedWidth(42)
        edit_btn.setToolTip("Изменить")
        edit_btn.clicked.connect(lambda: self.edit.emit(self.account.id))
        del_btn = QPushButton("🗑")
        del_btn.setObjectName("Danger")
        del_btn.setFixedWidth(42)
        del_btn.setToolTip("Удалить")
        del_btn.clicked.connect(lambda: self.delete.emit(self.account.id))

        for w in (self.launch_btn, self.stop_btn, folder_btn, edit_btn, del_btn):
            root.addWidget(w)

        self.set_running(False)
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
            tdata = "✓ tdata"
            color = "#8a99ad"
        else:
            tdata = "✗ нет tdata"
            color = "#ffb454"
        self.meta_label.setText(f"{proxy}  ·  {tdata}")
        self.meta_label.setStyleSheet(f"color: {color};")

    def set_running(self, running: bool) -> None:
        if running == self._running:
            return
        self._running = running
        if running:
            self.pill.setText("● Запущен")
            self.pill.setObjectName("PillRunning")
            self.launch_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
        else:
            self.pill.setText("○ Остановлен")
            self.pill.setObjectName("PillStopped")
            self.launch_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
        self.pill.style().unpolish(self.pill)
        self.pill.style().polish(self.pill)


# Обратная совместимость по имени
AccountCard = AccountRow
