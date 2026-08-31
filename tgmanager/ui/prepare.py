"""Диалог подготовки контейнера: создаёт папку и докачивает переносной Telegram."""
from __future__ import annotations

import os

from PyQt6.QtCore import QThread, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from .. import bundle, paths
from ..models import Account
from ..telegram import bundled_exists
from .style import GREEN, YELLOW


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


class PrepareContainerDialog(QDialog):
    """Готовит контейнер аккаунта. .succeeded == True, если переносной Telegram на месте."""

    def __init__(self, parent, account: Account):
        super().__init__(parent)
        self.account = account
        self.succeeded = False
        self._thr: _DownloadThread | None = None
        self.setWindowTitle("Подготовка контейнера")
        self.setMinimumWidth(520)
        self.setModal(True)
        self._build()
        QTimer.singleShot(60, self._run)

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 22, 22, 18)
        root.setSpacing(12)

        title = QLabel("Подготовка контейнера")
        title.setObjectName("DialogTitle")
        root.addWidget(title)

        self.sub = QLabel(f"«{self.account.name}»")
        self.sub.setObjectName("Hint")
        root.addWidget(self.sub)

        self.status = QLabel("Инициализация…")
        root.addWidget(self.status)

        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        root.addWidget(self.bar)

        self.log = QPlainTextEdit()
        self.log.setObjectName("Log")
        self.log.setReadOnly(True)
        self.log.setFixedHeight(130)
        self.log.setVisible(False)
        root.addWidget(self.log)

        row = QHBoxLayout()
        self.toggle_log = QPushButton("Показать журнал")
        self.toggle_log.setObjectName("Ghost")
        self.toggle_log.clicked.connect(self._toggle_log)
        row.addWidget(self.toggle_log)
        row.addStretch(1)
        self.btn = QPushButton("Отмена")
        self.btn.setObjectName("Ghost")
        self.btn.clicked.connect(self._on_button)
        row.addWidget(self.btn)
        root.addLayout(row)

    def _toggle_log(self) -> None:
        vis = not self.log.isVisible()
        self.log.setVisible(vis)
        self.toggle_log.setText("Скрыть журнал" if vis else "Показать журнал")

    def _run(self) -> None:
        self._set(10, "Создание папки контейнера…")
        os.makedirs(paths.account_workdir(self.account.id), exist_ok=True)
        self.log.appendPlainText(f"Папка: {paths.account_workdir(self.account.id)}")

        if bundled_exists():
            self._set(100, "✓ Переносной Telegram уже установлен")
            self.log.appendPlainText("Переносной Telegram уже на месте.")
            self._finish(True)
            return

        self._set(30, "Скачивание переносного Telegram…")
        self.bar.setRange(0, 0)
        self._thr = _DownloadThread(self)
        self._thr.line.connect(self._read)
        self._thr.ok.connect(lambda: self._dl_finished(True, ""))
        self._thr.failed.connect(lambda e: self._dl_finished(False, e))
        self._thr.start()

    def _read(self, data: str) -> None:
        self.log.appendPlainText(data.rstrip())
        self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())

    def _dl_finished(self, ok: bool, err: str) -> None:
        self._thr = None
        self.bar.setRange(0, 100)
        ok = ok and bundled_exists()
        if ok:
            self._set(100, "✓ Переносной Telegram установлен")
        else:
            if err:
                self.log.appendPlainText(f"✗ {err}")
            self._set(100, "✗ Не удалось скачать")
        self._finish(ok)

    def _finish(self, ok: bool) -> None:
        self.succeeded = ok
        self.bar.setRange(0, 100)
        self.bar.setValue(100)
        if ok:
            self.status.setText("✓ Контейнер готов. Положите папку tdata и запускайте.")
            self.status.setStyleSheet(f"color:{GREEN};")
            self.btn.setText("Готово")
            self.btn.setObjectName("Primary")
            self.btn.style().unpolish(self.btn)
            self.btn.style().polish(self.btn)
        else:
            self.status.setText("Контейнер создан, но Telegram не скачан. "
                                "Можно повторить позже (при запуске или в настройках).")
            self.status.setStyleSheet(f"color:{YELLOW};")
            self.btn.setText("Закрыть")

    def _on_button(self) -> None:
        if self._thr is not None:
            self._thr.requestInterruption()
            self._thr = None
            self.log.appendPlainText("Загрузка отменена.")
        if self.succeeded:
            self.accept()
        else:
            self.reject()

    def _set(self, value: int, text: str) -> None:
        if self.bar.maximum() != 0:
            self.bar.setValue(value)
        self.status.setText(text)
