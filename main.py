#!/usr/bin/env python3
"""TG Manager — менеджер Telegram-контейнеров (tdata) для Windows 10/11. Точка входа."""
from __future__ import annotations

import os
import sys


def _windows_app_id() -> None:
    if os.name != "nt":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Scarry.TGManager")
    except Exception:
        pass


def _single_instance() -> bool:
    """True, если можно продолжать (мы первые). False — уже запущено, фокус передан."""
    if os.name != "nt":
        return True
    import ctypes
    from ctypes import wintypes
    kernel32 = ctypes.windll.kernel32
    user32 = ctypes.windll.user32
    kernel32.SetLastError(0)
    kernel32.CreateMutexW(None, True, "Local\\Scarry.TGManager.single")
    if kernel32.GetLastError() != 183:  # ERROR_ALREADY_EXISTS
        return True
    hwnd = user32.FindWindowW(None, "TG Manager")
    if hwnd:
        SW_RESTORE = 9
        user32.ShowWindow(hwnd, SW_RESTORE)
        user32.SetForegroundWindow(hwnd)
    return False


def _dispatch_worker() -> int | None:
    """Подпроцессы frozen-сборки: воркер чистки и HTTP-мост."""
    if "--tg-worker" in sys.argv:
        idx = sys.argv.index("--tg-worker")
        sys.argv = [sys.argv[0], *sys.argv[idx + 1:]]
        from tgmanager.automation.worker import main as worker_main
        return worker_main()
    if "--tg-http-bridge" in sys.argv:
        # http_bridge.main сам парсит argv — убираем только наш флаг
        sys.argv = [a for a in sys.argv if a != "--tg-http-bridge"]
        from tgmanager.http_bridge import main as bridge_main
        return bridge_main()
    return None


def main() -> int:
    dispatched = _dispatch_worker()
    if dispatched is not None:
        return dispatched

    _windows_app_id()
    if not _single_instance():
        return 0

    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QIcon
    from PyQt6.QtWidgets import QApplication

    from tgmanager import APP_NAME, paths
    from tgmanager.config import Store
    from tgmanager.ui.main_window import MainWindow

    try:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    except Exception:
        pass

    os.chdir(paths.app_root())
    paths.ensure_dirs()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setOrganizationName("Scarry")
    app.setQuitOnLastWindowClosed(True)

    icon = paths.icon_path()
    if os.path.exists(icon):
        app.setWindowIcon(QIcon(icon))

    store = Store.load()
    window = MainWindow(store)
    window.show()
    return app.exec()


if __name__ == "__main__":
    if os.name == "nt":
        try:
            import multiprocessing
            multiprocessing.freeze_support()
        except Exception:
            pass
    sys.exit(main())
