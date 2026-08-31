"""Главное окно TG Manager."""
from __future__ import annotations

import os

from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QDesktopServices, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .. import APP_NAME, __version__, launcher, paths
from ..config import Store
from ..models import Account
from ..telegram import build_launch_plan, resolve_telegram
from .account_dialog import AccountDialog
from .card import AccountCard
from .download import DownloadTelegramDialog
from .flow_layout import FlowLayout
from .settings_dialog import SettingsDialog
from .style import QSS


class MainWindow(QMainWindow):
    def __init__(self, store: Store):
        super().__init__()
        self.store = store
        self.cards: dict[str, AccountCard] = {}
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(880, 600)
        self.resize(1040, 720)
        icon = paths.icon_path()
        if os.path.exists(icon):
            self.setWindowIcon(QIcon(icon))
        self.setStyleSheet(QSS)

        self._build()
        self.reload_cards()

        self.timer = QTimer(self)
        self.timer.setInterval(2000)
        self.timer.timeout.connect(self._poll_status)
        self.timer.start()

    # ---------- построение ----------
    def _build(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(self._header())

        # Область прокрутки с карточками
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.board = QWidget()
        self.board.setObjectName("Board")
        self.flow = FlowLayout(self.board, margin=22, spacing=18)
        self.scroll.setWidget(self.board)
        outer.addWidget(self.scroll, 1)

        # Пустое состояние
        self.empty = self._empty_state()
        outer.addWidget(self.empty, 1)

        self.statusBar().showMessage(f"{APP_NAME} {__version__}")

    def _header(self) -> QWidget:
        header = QWidget()
        header.setObjectName("Header")
        header.setFixedHeight(74)
        lay = QHBoxLayout(header)
        lay.setContentsMargins(22, 12, 22, 12)
        lay.setSpacing(14)

        logo = QLabel()
        icon = paths.icon_path()
        if os.path.exists(icon):
            logo.setPixmap(QPixmap(icon).scaled(
                44, 44, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))
        lay.addWidget(logo)

        titles = QVBoxLayout()
        titles.setSpacing(0)
        t = QLabel(APP_NAME)
        t.setObjectName("AppTitle")
        s = QLabel("Менеджер Telegram-аккаунтов")
        s.setObjectName("AppSubtitle")
        titles.addWidget(t)
        titles.addWidget(s)
        lay.addLayout(titles)
        lay.addStretch(1)

        add_btn = QPushButton("＋  Добавить аккаунт")
        add_btn.setObjectName("Primary")
        add_btn.clicked.connect(self.add_account)
        settings_btn = QPushButton("⚙  Настройки")
        settings_btn.setObjectName("Ghost")
        settings_btn.clicked.connect(self.open_settings)
        lay.addWidget(add_btn)
        lay.addWidget(settings_btn)
        return header

    def _empty_state(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(10)

        icon = paths.icon_path()
        if os.path.exists(icon):
            img = QLabel()
            img.setPixmap(QPixmap(icon).scaled(
                96, 96, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))
            img.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(img)

        title = QLabel("Пока нет аккаунтов")
        title.setObjectName("EmptyTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text = QLabel("Создайте первое окно-аккаунт, дайте имя,\n"
                      "а затем положите папку tdata в его папку.")
        text.setObjectName("EmptyText")
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn = QPushButton("＋  Создать аккаунт")
        btn.setObjectName("Primary")
        btn.clicked.connect(self.add_account)
        lay.addWidget(title)
        lay.addWidget(text)
        wrap = QHBoxLayout()
        wrap.addStretch(1)
        wrap.addWidget(btn)
        wrap.addStretch(1)
        lay.addLayout(wrap)
        return w

    # ---------- данные ----------
    def reload_cards(self) -> None:
        # очистить
        while self.flow.count():
            item = self.flow.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        self.cards.clear()

        for account in self.store.accounts:
            card = AccountCard(account)
            card.launch.connect(self.launch_account)
            card.stop.connect(self.stop_account)
            card.edit.connect(self.edit_account)
            card.delete.connect(self.delete_account)
            card.open_folder.connect(self.open_folder)
            self.flow.addWidget(card)
            self.cards[account.id] = card

        has = bool(self.store.accounts)
        self.scroll.setVisible(has)
        self.empty.setVisible(not has)
        self._poll_status()

    def _poll_status(self) -> None:
        for aid, card in self.cards.items():
            workdir = paths.account_workdir(aid)
            card.set_running(launcher.is_running(workdir))
            card.refresh()

    # ---------- действия ----------
    def add_account(self) -> None:
        dlg = AccountDialog(self)
        if dlg.exec():
            self.store.add(dlg.result_account())
            self.reload_cards()
            self.statusBar().showMessage("Аккаунт создан", 4000)

    def edit_account(self, account_id: str) -> None:
        account = self.store.get(account_id)
        if not account:
            return
        dlg = AccountDialog(self, account)
        if dlg.exec():
            self.store.update(dlg.result_account())
            card = self.cards.get(account_id)
            if card:
                card.set_account(dlg.result_account())
            self.statusBar().showMessage("Аккаунт обновлён", 4000)

    def delete_account(self, account_id: str) -> None:
        account = self.store.get(account_id)
        if not account:
            return
        workdir = paths.account_workdir(account_id)
        running = launcher.is_running(workdir)
        msg = QMessageBox(self)
        msg.setWindowTitle("Удалить аккаунт")
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setText(f"Удалить «{account.name}»?")
        info = "Аккаунт будет остановлен.\n" if running else ""
        info += ("Также удалить папку с данными (tdata)?\n"
                 "«Нет» — оставить папку на диске.")
        msg.setInformativeText(info)
        del_data = msg.addButton("Удалить с данными", QMessageBox.ButtonRole.DestructiveRole)
        keep_data = msg.addButton("Удалить, папку оставить", QMessageBox.ButtonRole.AcceptRole)
        cancel = msg.addButton("Отмена", QMessageBox.ButtonRole.RejectRole)
        msg.exec()
        clicked = msg.clickedButton()
        if clicked is cancel:
            return
        if running:
            launcher.stop(workdir)
        if clicked is del_data:
            import shutil
            shutil.rmtree(workdir, ignore_errors=True)
        self.store.remove(account_id)
        self.reload_cards()
        self.statusBar().showMessage("Аккаунт удалён", 4000)

    def open_folder(self, account_id: str) -> None:
        workdir = paths.account_workdir(account_id)
        os.makedirs(workdir, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(workdir))
        self.statusBar().showMessage("Положите сюда папку tdata", 5000)

    def launch_account(self, account_id: str) -> None:
        account = self.store.get(account_id)
        if not account:
            return
        workdir = paths.account_workdir(account_id)
        if launcher.is_running(workdir):
            self.statusBar().showMessage("Аккаунт уже запущен", 4000)
            return

        # Переносной Telegram обязателен — если его нет, предлагаем скачать
        if not resolve_telegram(self.store.settings.telegram_binary):
            r = QMessageBox.question(
                self, "Нужен переносной Telegram",
                "Для запуска используется переносной Telegram, и он ещё не установлен.\n"
                "Скачать официальный Telegram Desktop сейчас (~50 МБ)?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if r != QMessageBox.StandardButton.Yes:
                return
            dlg = DownloadTelegramDialog(self)
            dlg.exec()
            if not dlg.succeeded:
                self.statusBar().showMessage("Переносной Telegram не установлен", 5000)
                return

        # Предупреждение об отсутствии tdata
        if not os.path.isdir(paths.account_tdata(account_id)):
            r = QMessageBox.question(
                self, "Нет tdata",
                "В папке аккаунта нет tdata. Запустить всё равно "
                "(откроется чистый Telegram для новой авторизации)?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if r != QMessageBox.StandardButton.Yes:
                return

        plan = build_launch_plan(self.store.settings, account)
        if not plan.ok:
            QMessageBox.critical(self, "Не удалось запустить", plan.error or "Ошибка")
            return

        # Прокси запрошен, но не применён
        if plan.proxy_requested and not plan.proxy_applied:
            warn = "\n".join(plan.warnings) or "Прокси не удалось применить."
            r = QMessageBox.warning(
                self, "Прокси не применён",
                warn + "\n\nЗапустить БЕЗ прокси?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if r != QMessageBox.StandardButton.Yes:
                return

        pid = launcher.launch(plan)
        if pid:
            card = self.cards.get(account_id)
            if card:
                card.set_running(True)
            note = " (с прокси)" if plan.proxy_applied else ""
            self.statusBar().showMessage(f"Запущен: {account.name}{note}", 5000)
        else:
            QMessageBox.critical(self, "Ошибка", "Не удалось запустить процесс.")

    def stop_account(self, account_id: str) -> None:
        account = self.store.get(account_id)
        workdir = paths.account_workdir(account_id)
        n = launcher.stop(workdir)
        if n:
            self.statusBar().showMessage(
                f"Остановлен: {account.name if account else account_id}", 4000)
        card = self.cards.get(account_id)
        if card:
            QTimer.singleShot(800, lambda: card.set_running(launcher.is_running(workdir)))

    def open_settings(self) -> None:
        dlg = SettingsDialog(self, self.store.settings)
        if dlg.exec():
            self.store.save()
            self.statusBar().showMessage("Настройки сохранены", 4000)
