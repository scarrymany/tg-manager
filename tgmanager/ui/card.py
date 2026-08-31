"""Карточка одного Telegram-аккаунта."""
from __future__ import annotations

import os

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .. import paths
from ..models import Account

CARD_WIDTH = 300


class AccountCard(QFrame):
    launch = pyqtSignal(str)
    stop = pyqtSignal(str)
    edit = pyqtSignal(str)
    delete = pyqtSignal(str)
    open_folder = pyqtSignal(str)

    def __init__(self, account: Account, parent: QWidget | None = None):
        super().__init__(parent)
        self.account = account
        self._running = False
        self.setObjectName("Card")
        self.setFixedWidth(CARD_WIDTH)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._build()

    # ---------- построение ----------
    def _build(self) -> None:
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setXOffset(0)
        shadow.setYOffset(6)
        shadow.setColor(QColor(0, 0, 0, 110))
        self.setGraphicsEffect(shadow)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 14)
        root.setSpacing(12)

        # Верх: акцентная полоса + имя + статус
        top = QHBoxLayout()
        top.setSpacing(10)
        bar = QFrame()
        bar.setObjectName("AccentBar")
        bar.setFixedSize(6, 34)
        bar.setStyleSheet(f"background: {self.account.color}; border-radius: 3px;")
        top.addWidget(bar)

        name_box = QVBoxLayout()
        name_box.setSpacing(2)
        self.name_label = QLabel(self.account.name)
        self.name_label.setObjectName("CardName")
        self.name_label.setWordWrap(True)
        name_box.addWidget(self.name_label)
        top.addLayout(name_box, 1)

        self.pill = QLabel("○ Остановлен")
        self.pill.setObjectName("PillStopped")
        self.pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top.addWidget(self.pill, 0, Qt.AlignmentFlag.AlignTop)
        root.addLayout(top)

        # Мета: прокси + tdata
        self.proxy_label = QLabel(self.account.proxy.summary())
        self.proxy_label.setObjectName("CardMeta")
        root.addWidget(self.proxy_label)

        self.tdata_label = QLabel()
        self.tdata_label.setObjectName("CardMeta")
        root.addWidget(self.tdata_label)

        # Кнопки: запуск/стоп
        run_row = QHBoxLayout()
        run_row.setSpacing(8)
        self.launch_btn = QPushButton("▶  Запуск")
        self.launch_btn.setObjectName("Launch")
        self.launch_btn.clicked.connect(lambda: self.launch.emit(self.account.id))
        self.stop_btn = QPushButton("■  Стоп")
        self.stop_btn.setObjectName("Stop")
        self.stop_btn.clicked.connect(lambda: self.stop.emit(self.account.id))
        run_row.addWidget(self.launch_btn, 1)
        run_row.addWidget(self.stop_btn, 1)
        root.addLayout(run_row)

        # Второй ряд: папка / изменить / удалить
        act_row = QHBoxLayout()
        act_row.setSpacing(8)
        folder_btn = QPushButton("📁  Папка")
        folder_btn.setObjectName("Ghost")
        folder_btn.setToolTip("Открыть папку аккаунта — сюда положите папку tdata")
        folder_btn.clicked.connect(lambda: self.open_folder.emit(self.account.id))
        edit_btn = QPushButton("✏")
        edit_btn.setObjectName("Ghost")
        edit_btn.setToolTip("Изменить")
        edit_btn.setFixedWidth(42)
        edit_btn.clicked.connect(lambda: self.edit.emit(self.account.id))
        del_btn = QPushButton("🗑")
        del_btn.setObjectName("Danger")
        del_btn.setToolTip("Удалить")
        del_btn.setFixedWidth(42)
        del_btn.clicked.connect(lambda: self.delete.emit(self.account.id))
        act_row.addWidget(folder_btn, 1)
        act_row.addWidget(edit_btn)
        act_row.addWidget(del_btn)
        root.addLayout(act_row)

        self.refresh()

    # ---------- обновление ----------
    def set_account(self, account: Account) -> None:
        self.account = account
        self.name_label.setText(account.name)
        self.proxy_label.setText(account.proxy.summary())
        # обновить цвет полосы
        for child in self.findChildren(QFrame, "AccentBar"):
            child.setStyleSheet(f"background: {account.color}; border-radius: 3px;")
        self.refresh()

    def refresh(self) -> None:
        tdata = paths.account_tdata(self.account.id)
        if os.path.isdir(tdata):
            self.tdata_label.setText("✓  tdata на месте")
            self.tdata_label.setStyleSheet("color: #3ddc84;")
        else:
            self.tdata_label.setText("✗  нет tdata — положите папку tdata")
            self.tdata_label.setStyleSheet("color: #ffb454;")

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
        # перечитать стиль после смены objectName
        self.pill.style().unpolish(self.pill)
        self.pill.style().polish(self.pill)
