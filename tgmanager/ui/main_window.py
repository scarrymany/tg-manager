"""Главное окно TG Manager."""
from __future__ import annotations

import os

from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QDesktopServices, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .. import APP_NAME, __version__, launcher, paths
from ..automation import deps, lock
from ..config import Store
from ..models import Account
from ..telegram import build_launch_plan, resolve_proxychains, resolve_telegram
from .account_dialog import AccountDialog
from .automation_dialog import AutomationDialog
from .card import AccountRow
from .download import DownloadTelegramDialog
from .prepare import PrepareContainerDialog
from .settings_dialog import DownloadProxychainsDialog, SettingsDialog
from .style import QSS
from .task_manager import TaskManager
from .task_row import TaskLogDialog, TaskRow


def _widen_messagebox(msg: QMessageBox, width: int) -> None:
    """QMessageBox не слушает setMinimumWidth — расширяем через распорку в grid."""
    layout = msg.layout()
    if isinstance(layout, QGridLayout):
        spacer = QSpacerItem(width, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        layout.addItem(spacer, layout.rowCount(), 0, 1, layout.columnCount())


class MainWindow(QMainWindow):
    def __init__(self, store: Store):
        super().__init__()
        self.store = store
        self.cards: dict[str, AccountCard] = {}
        self.task_rows: dict[str, TaskRow] = {}
        self.task_manager = TaskManager(self)
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(920, 600)
        self.resize(1060, 720)
        icon = paths.icon_path()
        if os.path.exists(icon):
            self.setWindowIcon(QIcon(icon))
        self.setStyleSheet(QSS)

        self._build()
        self.reload_cards()

        self.task_manager.added.connect(self._task_added)
        self.task_manager.changed.connect(self._task_changed)
        self.task_manager.removed.connect(self._task_removed)
        self._refresh_tasks_nav()

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
        outer.addWidget(self._nav_strip())

        self.stack = QStackedWidget()
        self.stack.addWidget(self._containers_page())
        self.stack.addWidget(self._tasks_page())
        outer.addWidget(self.stack, 1)

        self.statusBar().showMessage(f"{APP_NAME} {__version__}")

    def _containers_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.board = QWidget()
        self.board.setObjectName("Board")
        self.rows_layout = QVBoxLayout(self.board)
        self.rows_layout.setContentsMargins(16, 16, 16, 16)
        self.rows_layout.setSpacing(10)
        self.rows_layout.addStretch(1)
        self.scroll.setWidget(self.board)
        lay.addWidget(self.scroll, 1)

        self.empty = self._empty_state()
        lay.addWidget(self.empty, 1)
        return page

    def _nav_strip(self) -> QWidget:
        strip = QFrame()
        strip.setObjectName("Header")
        strip.setFixedHeight(46)
        lay = QHBoxLayout(strip)
        lay.setContentsMargins(16, 6, 16, 6)
        lay.setSpacing(8)

        self.nav_containers = QPushButton("Контейнеры")
        self.nav_containers.setObjectName("Ghost")
        self.nav_containers.setCheckable(True)
        self.nav_containers.setChecked(True)
        self.nav_containers.clicked.connect(lambda: self._switch_page(0))
        self.nav_tasks = QPushButton("Активные задачи")
        self.nav_tasks.setObjectName("Ghost")
        self.nav_tasks.setCheckable(True)
        self.nav_tasks.clicked.connect(lambda: self._switch_page(1))
        lay.addWidget(self.nav_containers)
        lay.addWidget(self.nav_tasks)
        lay.addStretch(1)
        return strip

    def _tasks_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(10)

        bar = QHBoxLayout()
        head = QLabel("Активные задачи")
        head.setObjectName("EmptyTitle")
        bar.addWidget(head)
        bar.addStretch(1)
        clear_btn = QPushButton("Очистить завершённые")
        clear_btn.setObjectName("Ghost")
        clear_btn.clicked.connect(self.task_manager.clear_finished)
        stop_all_btn = QPushButton("Остановить все")
        stop_all_btn.setObjectName("Danger")
        stop_all_btn.clicked.connect(self.task_manager.stop_all)
        bar.addWidget(clear_btn)
        bar.addWidget(stop_all_btn)
        lay.addLayout(bar)

        self.tasks_scroll = QScrollArea()
        self.tasks_scroll.setWidgetResizable(True)
        tboard = QWidget()
        tboard.setObjectName("Board")
        self.tasks_layout = QVBoxLayout(tboard)
        self.tasks_layout.setContentsMargins(0, 0, 0, 0)
        self.tasks_layout.setSpacing(10)
        self.tasks_layout.addStretch(1)
        self.tasks_scroll.setWidget(tboard)
        lay.addWidget(self.tasks_scroll, 1)

        self.tasks_empty = QLabel("Нет активных задач.\nЗапустите чистку контейнера — задача появится здесь.")
        self.tasks_empty.setObjectName("EmptyText")
        self.tasks_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.tasks_empty)
        return page

    def _switch_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        self.nav_containers.setChecked(index == 0)
        self.nav_tasks.setChecked(index == 1)

    def _header(self) -> QWidget:
        header = QWidget()
        header.setObjectName("Header")
        header.setFixedHeight(58)
        lay = QHBoxLayout(header)
        lay.setContentsMargins(20, 10, 20, 10)
        lay.setSpacing(12)

        logo = QLabel()
        mark = paths.logo_mark_path()
        if os.path.exists(mark):
            logo.setPixmap(QPixmap(mark).scaled(
                36, 36, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))
        lay.addWidget(logo)

        titles = QVBoxLayout()
        titles.setSpacing(0)
        t = QLabel(APP_NAME)
        t.setObjectName("AppTitle")
        tf = t.font()
        tf.setLetterSpacing(tf.SpacingType.AbsoluteSpacing, 1.2)
        t.setFont(tf)
        s = QLabel("Менеджер Telegram-контейнеров")
        s.setObjectName("AppSubtitle")
        titles.addWidget(t)
        titles.addWidget(s)
        lay.addLayout(titles)
        lay.addStretch(1)

        add_btn = QPushButton("＋  Добавить контейнер")
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
        lay.setSpacing(12)

        # Знак в графитовой рамке (не голубая плитка)
        mark_frame = QFrame()
        mark_frame.setObjectName("EmptyMark")
        mark_frame.setFixedSize(88, 88)
        mf = QVBoxLayout(mark_frame)
        mf.setContentsMargins(0, 0, 0, 0)
        mf.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mark = paths.logo_mark_path()
        if os.path.exists(mark):
            img = QLabel()
            img.setPixmap(QPixmap(mark).scaled(
                44, 44, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))
            img.setAlignment(Qt.AlignmentFlag.AlignCenter)
            mf.addWidget(img)
        mwrap = QHBoxLayout()
        mwrap.addStretch(1)
        mwrap.addWidget(mark_frame)
        mwrap.addStretch(1)
        lay.addLayout(mwrap)

        title = QLabel("Пока нет контейнеров")
        title.setObjectName("EmptyTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text = QLabel("Создайте первый контейнер, дайте имя,\n"
                      "а затем положите папку tdata в его папку.")
        text.setObjectName("EmptyText")
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn = QPushButton("＋  Создать контейнер")
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
        # очистить всё, включая распорку
        while self.rows_layout.count():
            item = self.rows_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        self.cards.clear()

        for account in self.store.accounts:
            row = AccountRow(account)
            row.launch.connect(self.launch_account)
            row.stop.connect(self.stop_account)
            row.edit.connect(self.edit_account)
            row.delete.connect(self.delete_account)
            row.open_folder.connect(self.open_folder)
            row.automate.connect(self.automate_account)
            self.rows_layout.addWidget(row)
            self.cards[account.id] = row
        self.rows_layout.addStretch(1)

        has = bool(self.store.accounts)
        self.scroll.setVisible(has)
        self.empty.setVisible(not has)
        self._poll_status()

    def _poll_status(self) -> None:
        for aid, card in self.cards.items():
            workdir = paths.account_workdir(aid)
            busy = lock.is_locked(workdir)
            card.set_busy(busy)
            card.set_running(False if busy else launcher.is_running(workdir))
            card.refresh()

    # ---------- действия ----------
    def add_account(self) -> None:
        dlg = AccountDialog(self)
        if not dlg.exec():
            return
        account = dlg.result_account()
        # Подготовка контейнера: папка + докачка переносного Telegram
        prep = PrepareContainerDialog(self, account)
        prep.exec()
        self.store.add(account)
        self.reload_cards()
        if prep.succeeded:
            self.statusBar().showMessage("Контейнер создан и подготовлен", 4000)
        else:
            self.statusBar().showMessage(
                "Контейнер создан (переносной Telegram можно докачать позже)", 6000)
        # Сразу открываем папку — чтобы положить tdata
        self.open_folder(account.id)

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
            self.statusBar().showMessage("Контейнер обновлён", 4000)

    def delete_account(self, account_id: str) -> None:
        account = self.store.get(account_id)
        if not account:
            return
        workdir = paths.account_workdir(account_id)
        running = launcher.is_running(workdir)
        msg = QMessageBox(self)
        msg.setWindowTitle("Удалить контейнер")
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setText(f"Удалить «{account.name}»?")
        info = "Контейнер будет остановлен.\n" if running else ""
        info += ("Также удалить папку с данными (tdata)?\n"
                 "«Нет» — оставить папку на диске.")
        msg.setInformativeText(info)
        del_data = msg.addButton("Удалить с данными", QMessageBox.ButtonRole.DestructiveRole)
        keep_data = msg.addButton("Удалить, папку оставить", QMessageBox.ButtonRole.AcceptRole)
        cancel = msg.addButton("Отмена", QMessageBox.ButtonRole.RejectRole)
        _widen_messagebox(msg, 540)
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
        self.statusBar().showMessage("Контейнер удалён", 4000)

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
        if lock.is_locked(workdir):
            QMessageBox.warning(self, "Идёт автоматизация",
                                "Сейчас выполняется чистка этого контейнера. "
                                "Запуск заблокирован до завершения.")
            return
        if launcher.is_running(workdir):
            self.statusBar().showMessage("Контейнер уже запущен", 4000)
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

        # Прокси без обёртки — предлагаем скачать (Windows ProxyChains)
        if account.proxy.enabled and not resolve_proxychains(self.store.settings.proxychains_binary):
            r = QMessageBox.question(
                self, "Нужна прокси-обёртка",
                "У контейнера задан прокси, но обёртка ещё не установлена.\n"
                "Скачать прокси-обёртку сейчас (~200 КБ)?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if r == QMessageBox.StandardButton.Yes:
                pcd = DownloadProxychainsDialog(self)
                pcd.exec()

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

    def automate_account(self, account_id: str) -> None:
        account = self.store.get(account_id)
        if not account:
            return
        if self.task_manager.is_active(account_id):
            self._switch_page(1)
            return
        workdir = paths.account_workdir(account_id)
        if launcher.is_running(workdir):
            QMessageBox.warning(self, "Telegram запущен",
                                "Сначала остановите Telegram этого контейнера («Стоп») — "
                                "иначе сессию выбросит при подключении.")
            return
        if deps.missing():
            QMessageBox.warning(
                self, "Нужны зависимости",
                "Для автоматизации нужны telethon и opentele. Установите:\n\n"
                + deps.INSTALL_HINT)
            return
        if not os.path.isdir(paths.account_tdata(account_id)):
            QMessageBox.warning(self, "Нет tdata",
                                "В контейнере нет папки tdata — нечего чистить.")
            return
        dlg = AutomationDialog(self, account)
        if dlg.exec() and getattr(dlg, "requested", None):
            actions, revoke = dlg.requested
            self.task_manager.start(account, actions, revoke)
        self._poll_status()

    # ---------- задачи ----------
    def _task_added(self, tid: str) -> None:
        task = self.task_manager.tasks.get(tid)
        if not task:
            return
        old = self.task_rows.pop(tid, None)
        if old:
            old.deleteLater()
        row = TaskRow(task)
        row.stop.connect(self.task_manager.stop)
        row.remove.connect(self.task_manager.remove)
        row.show_log.connect(self._show_task_log)
        self.task_rows[tid] = row
        self.tasks_layout.insertWidget(self.tasks_layout.count() - 1, row)
        self._refresh_tasks_nav()
        self._switch_page(1)  # задача «перелетает» в активные

    def _task_changed(self, tid: str) -> None:
        row = self.task_rows.get(tid)
        if row:
            row.task = self.task_manager.tasks.get(tid, row.task)
            row.update_view()
        self._refresh_tasks_nav()
        self._poll_status()

    def _task_removed(self, tid: str) -> None:
        row = self.task_rows.pop(tid, None)
        if row:
            row.deleteLater()
        self._refresh_tasks_nav()
        self._poll_status()

    def _show_task_log(self, tid: str) -> None:
        task = self.task_manager.tasks.get(tid)
        if task:
            TaskLogDialog(self, task).exec()

    def _refresh_tasks_nav(self) -> None:
        active = self.task_manager.active_count()
        total = len(self.task_manager.tasks)
        self.nav_tasks.setText(
            f"Активные задачи ({active})" if active else "Активные задачи")
        if hasattr(self, "tasks_empty"):
            self.tasks_empty.setVisible(total == 0)
            self.tasks_scroll.setVisible(total > 0)

    def open_settings(self) -> None:
        dlg = SettingsDialog(self, self.store.settings)
        if dlg.exec():
            self.store.save()
            self.statusBar().showMessage("Настройки сохранены", 4000)

    def closeEvent(self, event):  # noqa: N802
        if self.task_manager.active_count() > 0:
            r = QMessageBox.question(
                self, "Идут задачи",
                f"Выполняется задач: {self.task_manager.active_count()}. "
                "Закрыть программу и прервать их?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if r != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.task_manager.stop_all()
        super().closeEvent(event)
