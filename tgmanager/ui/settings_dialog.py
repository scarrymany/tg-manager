"""Диалог настроек: путь к Telegram, переносной Telegram, прокси-обёртка, ярлык."""
from __future__ import annotations

import os
import sys

from PyQt6.QtCore import QThread, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from .. import bundle, paths
from ..config import Settings
from ..telegram import is_snap, resolve_proxychains, resolve_telegram
from .download import DownloadTelegramDialog
from .style import GREEN, YELLOW


class _PcThread(QThread):
    line = pyqtSignal(str)
    failed = pyqtSignal(str)
    ok = pyqtSignal()

    def run(self) -> None:
        try:
            bundle.download_proxychains(log=self.line.emit)
            self.ok.emit()
        except Exception as e:
            self.failed.emit(str(e))


class DownloadProxychainsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.succeeded = False
        self._thr: _PcThread | None = None
        self.setWindowTitle("Прокси-обёртка")
        self.setMinimumWidth(500)
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 22, 22, 18)
        title = QLabel("Скачивание прокси-обёртки")
        title.setObjectName("DialogTitle")
        root.addWidget(title)
        hint = QLabel("Windows-порт ProxyChains (x64). Нужен, чтобы HTTP/SOCKS5 "
                      "прокси контейнера применялся к Telegram Desktop.")
        hint.setObjectName("Hint")
        hint.setWordWrap(True)
        root.addWidget(hint)
        self.bar = QProgressBar()
        self.bar.setRange(0, 0)
        self.bar.setTextVisible(False)
        root.addWidget(self.bar)
        self.log = QPlainTextEdit()
        self.log.setObjectName("Log")
        self.log.setReadOnly(True)
        self.log.setFixedHeight(120)
        root.addWidget(self.log)
        row = QHBoxLayout()
        row.addStretch(1)
        self.btn = QPushButton("Отмена")
        self.btn.setObjectName("Ghost")
        self.btn.clicked.connect(self._close)
        row.addWidget(self.btn)
        root.addLayout(row)
        self.log.appendPlainText("Скачивание…")
        self._thr = _PcThread(self)
        self._thr.line.connect(self.log.appendPlainText)
        self._thr.ok.connect(lambda: self._done(True, ""))
        self._thr.failed.connect(lambda e: self._done(False, e))
        self._thr.start()

    def _done(self, ok: bool, err: str) -> None:
        self._thr = None
        self.bar.setRange(0, 1)
        if ok and bundle.proxychains_ready():
            self.succeeded = True
            self.bar.setValue(1)
            self.log.appendPlainText("✓ Прокси-обёртка установлена.")
            self.btn.setText("Готово")
        else:
            if err:
                self.log.appendPlainText(f"✗ {err}")
            self.btn.setText("Закрыть")

    def _close(self) -> None:
        if self.succeeded:
            self.accept()
        else:
            self.reject()


def create_desktop_shortcut() -> str:
    """Создаёт ярлык TG Manager.lnk на рабочем столе. Возвращает путь."""
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    if not os.path.isdir(desktop):
        desktop = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")
    lnk = os.path.join(desktop, "TG Manager.lnk")
    if getattr(sys, "frozen", False):
        target = sys.executable
        workdir = os.path.dirname(os.path.abspath(sys.executable))
    else:
        target = sys.executable
        workdir = paths.app_root()
    ico = paths.icon_ico_path()
    # PowerShell COM shortcut — без pywin32
    ps = (
        "$ws = New-Object -ComObject WScript.Shell; "
        f"$s = $ws.CreateShortcut('{lnk.replace(chr(39), chr(39)+chr(39))}'); "
        f"$s.TargetPath = '{target.replace(chr(39), chr(39)+chr(39))}'; "
        f"$s.WorkingDirectory = '{workdir.replace(chr(39), chr(39)+chr(39))}'; "
    )
    if os.path.isfile(ico):
        ps += f"$s.IconLocation = '{ico.replace(chr(39), chr(39)+chr(39))}'; "
    if not getattr(sys, "frozen", False):
        main_py = os.path.join(workdir, "main.py")
        ps += f"$s.Arguments = '\"{main_py}\"'; "
    ps += "$s.Description = 'TG Manager'; $s.Save()"
    import subprocess
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        check=True, capture_output=True, timeout=20,
    )
    return lnk


class SettingsDialog(QDialog):
    def __init__(self, parent, settings: Settings):
        super().__init__(parent)
        self.settings = settings
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

        pc_card, pc_body = self._card("ПРОКСИ-ОБЁРТКА (HTTP / SOCKS5 НА КОНТЕЙНЕР)")
        pc_row = QHBoxLayout()
        pc_row.setSpacing(8)
        self.pc_edit = QLineEdit(self.settings.proxychains_binary)
        self.pc_edit.setPlaceholderText("Автоопределение (tools/proxychains)")
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
        pc_dl = QHBoxLayout()
        self.pc_dl_btn = QPushButton("⬇  Скачать прокси-обёртку")
        self.pc_dl_btn.setObjectName("Ghost")
        self.pc_dl_btn.clicked.connect(self._download_pc)
        pc_dl.addWidget(self.pc_dl_btn)
        pc_dl.addStretch(1)
        pc_body.addLayout(pc_dl)
        root.addWidget(pc_card)

        misc_card, misc_body = self._card("ПРОЧЕЕ")
        self.many_chk = QCheckBox("Разрешать много окон одновременно (флаг -many)")
        self.many_chk.setChecked(self.settings.allow_many)
        misc_body.addWidget(self.many_chk)

        data_row = QHBoxLayout()
        data_lbl = QLabel(f"Данные контейнеров: {paths.ACCOUNTS_DIR}")
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

        sc_row = QHBoxLayout()
        sc_btn = QPushButton("📌  Ярлык на рабочий стол")
        sc_btn.setObjectName("Ghost")
        sc_btn.clicked.connect(self._shortcut)
        sc_row.addWidget(sc_btn)
        sc_row.addStretch(1)
        misc_body.addLayout(sc_row)
        root.addWidget(misc_card)

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
        card = QFrame()
        card.setObjectName("SettingsCard")
        body = QVBoxLayout(card)
        body.setContentsMargins(14, 12, 14, 12)
        body.setSpacing(8)
        head = QLabel(title)
        head.setObjectName("FieldLabel")
        body.addWidget(head)
        return card, body

    def _browse_tg(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите Telegram.exe",
            os.path.expanduser("~"),
            "Telegram (Telegram.exe);;Все файлы (*.*)",
        )
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
            self.tg_status.setText(f"⚠ Указан snap: {tg}")
            self.tg_status.setStyleSheet(f"color:{YELLOW};")
        else:
            self.tg_status.setText(f"✓ Будет использован: {tg}")
            self.tg_status.setStyleSheet(f"color:{GREEN};")

        pc = resolve_proxychains(self.pc_edit.text().strip())
        if pc:
            self.pc_status.setText(f"✓ Прокси-обёртка: {pc}")
            self.pc_status.setStyleSheet(f"color:{GREEN};")
        else:
            self.pc_status.setText(
                "⚠ Прокси-обёртка не найдена. Нажмите «Скачать прокси-обёртку», "
                "если будете запускать контейнеры через HTTP/SOCKS5."
            )
            self.pc_status.setStyleSheet(f"color:{YELLOW};")

    def _download_telegram(self) -> None:
        dlg = DownloadTelegramDialog(self)
        dlg.exec()
        if dlg.succeeded:
            if self.tg_edit.text().strip() and not os.path.exists(self.tg_edit.text().strip()):
                self.tg_edit.clear()
        self._refresh_status()

    def _download_pc(self) -> None:
        dlg = DownloadProxychainsDialog(self)
        dlg.exec()
        if dlg.succeeded:
            self.pc_edit.clear()
        self._refresh_status()

    def _shortcut(self) -> None:
        try:
            lnk = create_desktop_shortcut()
            QMessageBox.information(self, "Ярлык", f"Создан:\n{lnk}")
        except Exception as e:
            QMessageBox.warning(self, "Ярлык", f"Не удалось создать ярлык:\n{e}")

    def _save(self) -> None:
        self.settings.telegram_binary = self.tg_edit.text().strip()
        self.settings.proxychains_binary = self.pc_edit.text().strip()
        self.settings.allow_many = self.many_chk.isChecked()
        self.accept()
