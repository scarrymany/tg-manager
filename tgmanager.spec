# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller recipe: один TGManager.exe, данные — рядом с ним (portable)."""
import os

from PyInstaller.utils.hooks import collect_all

ROOT = os.path.abspath(SPECPATH)

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
]

_SKIP = (
    "telethon.tl.test",
    "opentele.tests",
)

for pkg in ("telethon", "opentele", "python_socks", "cryptg", "PIL"):
    try:
        d, b, h = collect_all(pkg, include_py_files=False)
        datas += d
        binaries += b
        hiddenimports += [n for n in h if not n.startswith(_SKIP)]
    except Exception:
        pass

datas.sort(key=lambda item: tuple(map(str, item)))
binaries.sort(key=lambda item: tuple(map(str, item)))
hiddenimports = sorted(set(hiddenimports))

a = Analysis(
    [os.path.join(ROOT, "main.py")],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "test", "unittest"],
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
)
