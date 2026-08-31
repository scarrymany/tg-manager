# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller recipe: один TGManager.exe, данные — рядом с ним (portable).

PyQt5 нельзя класть рядом с PyQt6 (PyInstaller 6.x abort). GUI — только PyQt6.
Чистка tdata идёт через opentele-ng (чистый Python QDataStream, без Qt).
"""
import os

from PyInstaller.utils.hooks import collect_all

ROOT = os.path.abspath(SPECPATH)

_QT5_PREFIXES = ("PyQt5", "PySide2", "PySide6", "shiboken2", "shiboken6")


def _is_qt5(name: str) -> bool:
    n = str(name).replace("\\", "/")
    return n.startswith(_QT5_PREFIXES) or "/PyQt5/" in n or "\\PyQt5\\" in n


datas = [(os.path.join(ROOT, "assets"), "assets")]
binaries = []
hiddenimports = [
    "PyQt6",
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
    "tgmanager",
    "tgmanager.ui",
    "tgmanager.ui.main_window",
    "tgmanager.ui.settings_dialog",
    "tgmanager.ui.download",
    "tgmanager.ui.prepare",
    "tgmanager.ui.account_dialog",
    "tgmanager.ui.automation_dialog",
    "tgmanager.ui.card",
    "tgmanager.ui.task_manager",
    "tgmanager.ui.task_row",
    "tgmanager.ui.style",
    "tgmanager.automation",
    "tgmanager.automation.worker",
    "tgmanager.automation.lock",
    "tgmanager.automation.deps",
    "tgmanager.automation._patch_opentele",
    "tgmanager.http_bridge",
    "tgmanager.bundle",
    "python_socks",
    "python_socks.sync",
    "python_socks.async_",
    "python_socks.async_.asyncio",
    "psutil",
    "tgcrypto",
    "opentele",
    "opentele.td",
    "opentele.api",
    "opentele.tl",
]

_SKIP = (
    "telethon.tl.test",
    "opentele.tests",
    "python_socks.async_.trio",
)

for pkg in ("telethon", "opentele", "python_socks", "tgcrypto"):
    try:
        d, b, h = collect_all(pkg, include_py_files=False)
        datas += [x for x in d if not _is_qt5(x[0] if isinstance(x, (list, tuple)) else x)]
        binaries += [x for x in b if not _is_qt5(x[0] if isinstance(x, (list, tuple)) else x)]
        hiddenimports += [
            n for n in h
            if n and not n.startswith(_SKIP) and not _is_qt5(n)
        ]
    except Exception:
        pass

datas.sort(key=lambda item: tuple(map(str, item)))
binaries.sort(key=lambda item: tuple(map(str, item)))
hiddenimports = sorted({n for n in hiddenimports if n and not _is_qt5(n)})

a = Analysis(
    [os.path.join(ROOT, "main.py")],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "numpy",
        "test",
        "unittest",
        "trio",
        "PyQt5",
        "PyQt5.QtCore",
        "PyQt5.QtGui",
        "PyQt5.QtWidgets",
        "PyQt5.sip",
        "PySide2",
        "PySide6",
        "shiboken2",
        "shiboken6",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="TGManager",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(ROOT, "assets", "icon.ico"),
    version=os.path.join(ROOT, "file_version_info.txt") if os.path.isfile(os.path.join(ROOT, "file_version_info.txt")) else None,
)
