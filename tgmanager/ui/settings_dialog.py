"""Диалог настроек: путь к Telegram, переносной Telegram, proxychains, папка данных."""
from __future__ import annotations

import os

from PyQt6.QtCore import QProcess, Qt
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .. import paths
from ..config import Settings
from ..telegram import is_snap, resolve_proxychains, resolve_telegram
from .download import DownloadTelegramDialog


class SettingsDialog(QDialog):
    def __init__(self, parent, settings: Settings):
        super().__init__(parent)
        self.settings = settings
        self._proc: QProcess | None = None
        self.setWindowTitle("Настройки")
        self.setMinimumWidth(560)
        self._build()
        self._refresh_status()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 22, 22, 18)
        root.setSpacing(14)

        title = QLabel("Настройки")
        title.setObjectName("AppTitle")
        root.addWidget(title)

        # --- Telegram binary ---
        root.addWidget(self._section("Telegram (бинарник для запуска)"))
        tg_row = QHBoxLayout()
        tg_row.setSpacing(8)
        self.tg_edit = QLineEdit(self.settings.telegram_binary)
        self.tg_edit.setPlaceholderText("Автоопределение: переносной Telegram внутри программы")
        self.tg_edit.textChanged.connect(self._refresh_status)
        browse = QPushButton("Обзор…")
        browse.setObjectName("Ghost")
        browse.clicked.connect(self._browse_tg)
        auto = QPushButton("Автоопределить")
        auto.setObjectName("Ghost")
        auto.clicked.connect(self._autodetect_tg)
        tg_row.addWidget(self.tg_edit, 1)
        tg_row.addWidget(browse)
        tg_row.addWidget(auto)
        root.addLayout(tg_row)

        self.tg_status = QLabel()
        self.tg_status.setObjectName("Hint")
        self.tg_status.setWordWrap(True)
        root.addWidget(self.tg_status)

        # Скачать переносной Telegram
        dl_row = QHBoxLayout()
        self.dl_btn = QPushButton("⬇  Скачать переносной Telegram")
        self.dl_btn.setObjectName("Primary")
        self.dl_btn.clicked.connect(self._download_telegram)
        dl_row.addWidget(self.dl_btn)
        dl_row.addStretch(1)
        root.addLayout(dl_row)

        # --- proxychains ---
        root.addWidget(self._section("proxychains (для HTTP/SOCKS5 прокси)"))
        pc_row = QHBoxLayout()
        pc_row.setSpacing(8)
        self.pc_edit = QLineEdit(self.settings.proxychains_binary)
        self.pc_edit.setPlaceholderText("Автоопределение (proxychains4)")
        self.pc_edit.textChanged.connect(self._refresh_status)
        pc_auto = QPushButton("Автоопределить")
        pc_auto.setObjectName("Ghost")
        pc_auto.clicked.connect(self._autodetect_pc)
        pc_row.addWidget(self.pc_edit, 1)
        pc_row.addWidget(pc_auto)
        root.addLayout(pc_row)
        self.pc_status = QLabel()
        self.pc_status.setObjectName("Hint")
        self.pc_status.setWordWrap(True)
        root.addWidget(self.pc_status)

        # --- прочее ---
        self.many_chk = QCheckBox("Разрешать много окон одновременно (флаг -many)")
        self.many_chk.setChecked(self.settings.allow_many)
        root.addWidget(self.many_chk)

        # Папка данных
        data_row = QHBoxLayout()
        data_lbl = QLabel(f"Данные аккаунтов: {paths.ACCOUNTS_DIR}")
        data_lbl.setObjectName("Hint")
        data_lbl.setWordWrap(True)
        open_data = QPushButton("Открыть")
        open_data.setObjectName("Ghost")
        open_data.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(paths.ACCOUNTS_DIR))
        )
        data_row.addWidget(data_lbl, 1)
        data_row.addWidget(open_data)
        root.addLayout(data_row)

        # Кнопки
        btns = QHBoxLayout()
        btns.addStretch(1)
        cancel = QPushButton("Отмена")
        cancel.setObjectName("Ghost")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Сохранить")
        save.setObjectName("Primary")
        save.clicked.connect(self._save)
        btns.addWidget(cancel)
        btns.addWidget(save)
        root.addLayout(btns)

    def _section(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("FieldLabel")
        return lbl

    # ---- actions ----
    def _browse_tg(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Выберите бинарник Telegram", os.path.expanduser("~"))
        if path:
            self.tg_edit.setText(path)

    def _autodetect_tg(self) -> None:
        found = resolve_telegram("")
        if found:
            self.tg_edit.setText(found)
        self._refresh_status()

    def _autodetect_pc(self) -> None:
        found = resolve_proxychains("")
        if found:
            self.pc_edit.setText(found)
        self._refresh_status()

    def _refresh_status(self) -> None:
        tg = resolve_telegram(self.tg_edit.text().strip())
        if not tg:
            self.tg_status.setText("⚠ Переносной Telegram не установлен — нажмите "
                                   "«Скачать переносной Telegram».")
            self.tg_status.setStyleSheet("color:#ffb454;")
        elif is_snap(tg):
            self.tg_status.setText(
                f"⚠ Указан snap: {tg}\n"
                "Через snap прокси (proxychains) НЕ работает. "
                "Уберите путь, чтобы использовать переносной Telegram."
            )
            self.tg_status.setStyleSheet("color:#ffb454;")
        else:
            self.tg_status.setText(f"✓ Будет использован: {tg}")
            self.tg_status.setStyleSheet("color:#3ddc84;")

        pc = resolve_proxychains(self.pc_edit.text().strip())
        if pc:
            self.pc_status.setText(f"✓ proxychains: {pc}")
            self.pc_status.setStyleSheet("color:#3ddc84;")
        else:
            self.pc_status.setText("⚠ proxychains4 не найден. Установите: sudo apt install proxychains4")
            self.pc_status.setStyleSheet("color:#ffb454;")

    def _download_telegram(self) -> None:
        dlg = DownloadTelegramDialog(self)
        dlg.exec()
        if dlg.succeeded:
            # оставляем автоопределение (пустое поле) — bundled подхватится сам
            if self.tg_edit.text().strip() and not os.path.exists(self.tg_edit.text().strip()):
                self.tg_edit.clear()
        self._refresh_status()

    def _save(self) -> None:
        self.settings.telegram_binary = self.tg_edit.text().strip()
        self.settings.proxychains_binary = self.pc_edit.text().strip()
        self.settings.allow_many = self.many_chk.isChecked()
        self.accept()
