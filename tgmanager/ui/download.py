"""Модальный диалог скачивания переносного Telegram (get_telegram.sh)."""
from __future__ import annotations

import os

from PyQt6.QtCore import QProcess, Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from .. import paths


class DownloadTelegramDialog(QDialog):
    """Скачивает официальный переносной Telegram в ./telegram. .succeeded == True при успехе."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.succeeded = False
        self._proc: QProcess | None = None
        self.setWindowTitle("Переносной Telegram")
        self.setMinimumWidth(520)
        self._build()
        self._start()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 22, 22, 18)
        root.setSpacing(12)

        title = QLabel("Скачивание переносного Telegram")
        title.setObjectName("AppTitle")
        root.addWidget(title)

        sub = QLabel("Официальный Telegram Desktop будет установлен в папку программы "
                     "(./telegram). Используется только он.")
        sub.setObjectName("Hint")
        sub.setWordWrap(True)
        root.addWidget(sub)

        self.bar = QProgressBar()
        self.bar.setRange(0, 0)  # индикатор без процентов
        self.bar.setTextVisible(False)
        root.addWidget(self.bar)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setFixedHeight(150)
        root.addWidget(self.log)

        btns = QHBoxLayout()
        btns.addStretch(1)
        self.close_btn = QPushButton("Отмена")
        self.close_btn.setObjectName("Ghost")
        self.close_btn.clicked.connect(self._on_close)
        btns.addWidget(self.close_btn)
        root.addLayout(btns)

    def _start(self) -> None:
        script = os.path.join(paths.APP_ROOT, "get_telegram.sh")
        if not os.path.exists(script):
            self.log.appendPlainText("Не найден get_telegram.sh рядом с программой.")
            self.bar.setRange(0, 1)
            return
        self.log.appendPlainText("Скачивание…")
        self._proc = QProcess(self)
        self._proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self._proc.readyReadStandardOutput.connect(self._read)
        self._proc.finished.connect(self._finished)
        self._proc.start("bash", [script])

    def _read(self) -> None:
        if not self._proc:
            return
        data = bytes(self._proc.readAllStandardOutput()).decode("utf-8", "replace")
        self.log.appendPlainText(data.rstrip())
        self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())

    def _finished(self, code: int, _status) -> None:
        self._proc = None
        self.bar.setRange(0, 1)
        if code == 0 and os.path.exists(paths.BUNDLED_TELEGRAM_BIN):
            self.succeeded = True
            self.bar.setValue(1)
            self.log.appendPlainText("✓ Готово. Переносной Telegram установлен.")
            self.close_btn.setText("Готово")
        else:
            self.log.appendPlainText(f"✗ Не удалось (код {code}). Проверьте интернет и повторите.")
            self.close_btn.setText("Закрыть")

    def _on_close(self) -> None:
        if self._proc is not None:
            self._proc.kill()
            self._proc = None
        if self.succeeded:
            self.accept()
        else:
            self.reject()
