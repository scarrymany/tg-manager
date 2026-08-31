"""Модальный диалог скачивания переносного Telegram (официальный win64 portable)."""
from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from .. import bundle


class _DownloadThread(QThread):
    line = pyqtSignal(str)
    failed = pyqtSignal(str)
    ok = pyqtSignal()

    def run(self) -> None:
        try:
            bundle.download_telegram(log=self.line.emit)
            self.ok.emit()
        except Exception as e:
            self.failed.emit(str(e))


class DownloadTelegramDialog(QDialog):
    """Скачивает официальный переносной Telegram в ./telegram. .succeeded == True при успехе."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.succeeded = False
        self._thr: _DownloadThread | None = None
        self.setWindowTitle("Переносной Telegram")
        self.setMinimumWidth(520)
        self._build()
        self._start()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 22, 22, 18)
        root.setSpacing(12)

        title = QLabel("Скачивание переносного Telegram")
        title.setObjectName("DialogTitle")
        root.addWidget(title)

        sub = QLabel("Официальный Telegram Desktop (Windows 64-bit portable) будет "
                     "установлен в папку программы (./telegram). Используется только он.")
        sub.setObjectName("Hint")
        sub.setWordWrap(True)
        root.addWidget(sub)

        self.bar = QProgressBar()
        self.bar.setRange(0, 0)
        self.bar.setTextVisible(False)
        root.addWidget(self.bar)

        self.log = QPlainTextEdit()
        self.log.setObjectName("Log")
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
        self.log.appendPlainText("Скачивание…")
        self._thr = _DownloadThread(self)
        self._thr.line.connect(self._append)
        self._thr.ok.connect(lambda: self._finished(True, ""))
        self._thr.failed.connect(lambda e: self._finished(False, e))
        self._thr.start()

    def _append(self, text: str) -> None:
        self.log.appendPlainText(text)
        self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())

    def _finished(self, ok: bool, err: str) -> None:
        self._thr = None
        self.bar.setRange(0, 1)
        if ok and bundle.telegram_ready():
            self.succeeded = True
            self.bar.setValue(1)
            self.log.appendPlainText("✓ Готово. Переносной Telegram установлен.")
            self.close_btn.setText("Готово")
        else:
            if err:
                self.log.appendPlainText(f"✗ {err}")
            self.log.appendPlainText("Проверьте интернет и повторите.")
            self.close_btn.setText("Закрыть")

    def _on_close(self) -> None:
        if self._thr is not None:
            self._thr.requestInterruption()
            self._thr = None
        if self.succeeded:
            self.accept()
        else:
            self.reject()
