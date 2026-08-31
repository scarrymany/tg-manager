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
        self.tg_edit.setPlaceholderText("Автоопределение (переносной внутри программы → системный)")
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
        self.dl_btn = QPushButton("⬇  Скачать переносной Telegram (рекомендуется для прокси)")
        self.dl_btn.setObjectName("Primary")
        self.dl_btn.clicked.connect(self._download_telegram)
        dl_row.addWidget(self.dl_btn)
        dl_row.addStretch(1)
        root.addLayout(dl_row)

        self.dl_log = QPlainTextEdit()
        self.dl_log.setReadOnly(True)
        self.dl_log.setFixedHeight(120)
        self.dl_log.setVisible(False)
        root.addWidget(self.dl_log)

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
            self.tg_status.setText("⚠ Telegram не найден. Скачайте переносной или укажите путь.")
            self.tg_status.setStyleSheet("color:#ffb454;")
        elif is_snap(tg):
            self.tg_status.setText(
                f"Найден (snap): {tg}\n"
                "⚠ Через snap прокси (proxychains) НЕ работает. "
                "Для прокси скачайте переносной Telegram."
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
        if self._proc is not None:
            return
        script = os.path.join(paths.APP_ROOT, "get_telegram.sh")
        if not os.path.exists(script):
            self.dl_log.setVisible(True)
            self.dl_log.appendPlainText("Не найден get_telegram.sh рядом с программой.")
            return
        self.dl_log.setVisible(True)
        self.dl_log.clear()
        self.dl_log.appendPlainText("Скачивание переносного Telegram…")
        self.dl_btn.setEnabled(False)
        self._proc = QProcess(self)
        self._proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self._proc.readyReadStandardOutput.connect(self._read_dl)
        self._proc.finished.connect(self._dl_finished)
        self._proc.start("bash", [script])

    def _read_dl(self) -> None:
        if not self._proc:
            return
        data = bytes(self._proc.readAllStandardOutput()).decode("utf-8", "replace")
        self.dl_log.appendPlainText(data.rstrip())

    def _dl_finished(self, code: int, _status) -> None:
        self.dl_btn.setEnabled(True)
        self._proc = None
        if code == 0 and os.path.exists(paths.BUNDLED_TELEGRAM_BIN):
            self.dl_log.appendPlainText("✓ Готово. Переносной Telegram установлен в программу.")
            self.tg_edit.setText(paths.BUNDLED_TELEGRAM_BIN)
        else:
            self.dl_log.appendPlainText(f"✗ Не удалось (код {code}). Проверьте интернет.")
        self._refresh_status()

    def _save(self) -> None:
        self.settings.telegram_binary = self.tg_edit.text().strip()
        self.settings.proxychains_binary = self.pc_edit.text().strip()
        self.settings.allow_many = self.many_chk.isChecked()
        self.accept()
