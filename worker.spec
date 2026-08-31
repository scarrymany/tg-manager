# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller: TGWorker.exe — чистка tdata (Telethon + opentele-ng), без Qt."""
import os

from PyInstaller.utils.hooks import collect_all

ROOT = os.path.abspath(SPECPATH)

_SKIP_PREFIXES = ("PyQt5", "PyQt6", "PySide2", "PySide6", "shiboken2", "shiboken6")
_SKIP = (
    "telethon.tl.test",
    "opentele.tests",
    "python_socks.async_.trio",
)


def _is_qt(name: str) -> bool:
    n = str(name).replace("\\", "/")
    return any(n.startswith(p) or f"/{p}/" in n or f"\\{p}\\" in n for p in _SKIP_PREFIXES)


datas = []
binaries = []
hiddenimports = [
    "tgmanager",
    "tgmanager.automation",
    "tgmanager.automation.worker",
    "tgmanager.automation.lock",
    "tgmanager.automation.deps",
    "tgmanager.automation._patch_opentele",
    "python_socks",
    "python_socks.sync",
    "python_socks.async_",
    "python_socks.async_.asyncio",
    "tgcrypto",
    "opentele",
    "opentele.td",
    "opentele.api",
    "opentele.tl",
]

for pkg in ("telethon", "opentele", "python_socks", "tgcrypto"):
    try:
        d, b, h = collect_all(pkg, include_py_files=False)
        datas += [x for x in d if not _is_qt(x[0] if isinstance(x, (list, tuple)) else x)]
        binaries += [x for x in b if not _is_qt(x[0] if isinstance(x, (list, tuple)) else x)]
        hiddenimports += [
            n for n in h
            if n and not n.startswith(_SKIP) and not _is_qt(n)
        ]
    except Exception:
        pass

datas.sort(key=lambda item: tuple(map(str, item)))
binaries.sort(key=lambda item: tuple(map(str, item)))
hiddenimports = sorted({n for n in hiddenimports if n and not _is_qt(n)})

a = Analysis(
    [os.path.join(ROOT, "worker_entry.py")],
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
        "PyQt6",
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
    name="TGWorker",
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
    version=os.path.join(ROOT, "file_version_info_worker.txt")
    if os.path.isfile(os.path.join(ROOT, "file_version_info_worker.txt"))
    else None,
)
