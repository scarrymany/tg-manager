#!/usr/bin/env python3
"""TG Manager — менеджер Telegram-аккаунтов (tdata) для Linux. Точка входа."""
from __future__ import annotations

import os
import sys

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from tgmanager import APP_ID, APP_NAME, paths
from tgmanager.config import Store
from tgmanager.ui.main_window import MainWindow


def main() -> int:
    paths.ensure_dirs()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    # Для корректной иконки/группировки в GNOME/Wayland
    app.setDesktopFileName(APP_ID)

    icon = paths.icon_path()
    if os.path.exists(icon):
        app.setWindowIcon(QIcon(icon))

    store = Store.load()
    window = MainWindow(store)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
