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
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .. import paths
from ..config import Settings
from ..telegram import is_snap, resolve_proxychains, resolve_telegram
from .download import DownloadTelegramDialog
from .style import GREEN, YELLOW


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
        root.setContentsMargins(20, 20, 20, 16)
        root.setSpacing(14)

        title = QLabel("Настройки")
        title.setObjectName("DialogTitle")
        root.addWidget(title)

        # --- Карточка: Telegram ---
        tg_card, tg_body = self._card("TELEGRAM (БИНАРНИК ДЛЯ ЗАПУСКА)")
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
        tg_body.addLayout(tg_row)

        self.tg_status = QLabel()
        self.tg_status.setObjectName("Hint")
        self.tg_status.setWordWrap(True)
        tg_body.addWidget(self.tg_status)

        dl_row = QHBoxLayout()
        self.dl_btn = QPushButton("⬇  Скачать переносной Telegram")
        self.dl_btn.setObjectName("Primary")
        self.dl_btn.clicked.connect(self._download_telegram)
        dl_row.addWidget(self.dl_btn)
        dl_row.addStretch(1)
        tg_body.addLayout(dl_row)
        root.addWidget(tg_card)

        # --- Карточка: proxychains ---
        pc_card, pc_body = self._card("PROXYCHAINS (ДЛЯ HTTP/SOCKS5 ПРОКСИ)")
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
        pc_body.addLayout(pc_row)
        self.pc_status = QLabel()
        self.pc_status.setObjectName("Hint")
        self.pc_status.setWordWrap(True)
        pc_body.addWidget(self.pc_status)
        root.addWidget(pc_card)

        # --- Карточка: прочее ---
        misc_card, misc_body = self._card("ПРОЧЕЕ")
        self.many_chk = QCheckBox("Разрешать много окон одновременно (флаг -many)")
        self.many_chk.setChecked(self.settings.allow_many)
        misc_body.addWidget(self.many_chk)

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
        misc_body.addLayout(data_row)
        root.addWidget(misc_card)

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

    def _card(self, title: str):
        """Карточка-группа настроек (QFrame#SettingsCard). Возвращает (frame, body_vbox)."""
        card = QFrame()
        card.setObjectName("SettingsCard")
        body = QVBoxLayout(card)
        body.setContentsMargins(14, 12, 14, 12)
        body.setSpacing(8)
        head = QLabel(title)
        head.setObjectName("FieldLabel")
        body.addWidget(head)
        return card, body

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
            self.tg_status.setStyleSheet(f"color:{YELLOW};")
        elif is_snap(tg):
            self.tg_status.setText(
                f"⚠ Указан snap: {tg}\n"
                "Через snap прокси (proxychains) НЕ работает. "
                "Уберите путь, чтобы использовать переносной Telegram."
            )
            self.tg_status.setStyleSheet(f"color:{YELLOW};")
        else:
            self.tg_status.setText(f"✓ Будет использован: {tg}")
            self.tg_status.setStyleSheet(f"color:{GREEN};")

        pc = resolve_proxychains(self.pc_edit.text().strip())
        if pc:
            self.pc_status.setText(f"✓ proxychains: {pc}")
            self.pc_status.setStyleSheet(f"color:{GREEN};")
        else:
            self.pc_status.setText("⚠ proxychains4 не найден. Установите: sudo apt install proxychains4")
            self.pc_status.setStyleSheet(f"color:{YELLOW};")

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
