"""Скачивание переносного Telegram и Windows-обёртки прокси (рядом с программой)."""
from __future__ import annotations

import os
import shutil
import tempfile
import zipfile
from typing import Callable
from urllib.request import Request, urlopen

from . import paths

LogFn = Callable[[str], None]

TELEGRAM_URL = "https://telegram.org/dl/desktop/win64_portable"
PROXYCHAINS_URL = (
    "https://github.com/shunf4/proxychains-windows/releases/download/"
    "0.6.8/proxychains_0.6.8_win32_x64.zip"
)

_UA = "TGManager/1.0 (+https://github.com/scarrymany/tg-manager)"


def _log(log: LogFn | None, msg: str) -> None:
    if log:
        log(msg)


def _download(url: str, dest: str, log: LogFn | None = None, label: str = "файл") -> None:
    req = Request(url, headers={"User-Agent": _UA})
    with urlopen(req, timeout=60) as resp:
        total = int(resp.headers.get("Content-Length") or 0)
        read = 0
        chunk = 256 * 1024
        with open(dest, "wb") as out:
            while True:
                buf = resp.read(chunk)
                if not buf:
                    break
                out.write(buf)
                read += len(buf)
                if total:
                    pct = int(read * 100 / total)
                    _log(log, f"↓ {label}: {pct}% ({read // (1024 * 1024)} / {total // (1024 * 1024)} МБ)")
                else:
                    _log(log, f"↓ {label}: {read // 1024} КБ")


def _find_file(root: str, names: tuple[str, ...], max_depth: int = 4) -> str | None:
    want = {n.lower() for n in names}
    root = os.path.abspath(root)
    for dirpath, dirnames, filenames in os.walk(root):
        rel = os.path.relpath(dirpath, root)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        if depth > max_depth:
            dirnames[:] = []
            continue
        for fn in filenames:
            if fn.lower() in want:
                return os.path.join(dirpath, fn)
    return None


def telegram_ready() -> bool:
    paths.refresh()
    return os.path.isfile(paths.BUNDLED_TELEGRAM_BIN)


def download_telegram(log: LogFn | None = None) -> str:
    """Качает официальный portable Telegram x64 в ./telegram. Возвращает путь к exe."""
    paths.ensure_dirs()
    dest_dir = paths.BUNDLED_TELEGRAM_DIR
    os.makedirs(dest_dir, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="tgman-dl-")
    try:
        zip_path = os.path.join(tmp, "telegram.zip")
        _log(log, "Скачиваю официальный Telegram Desktop (win64 portable)…")
        _download(TELEGRAM_URL, zip_path, log, "Telegram")
        _log(log, "Распаковываю…")
        extract = os.path.join(tmp, "extract")
        os.makedirs(extract, exist_ok=True)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(extract)
        exe = _find_file(extract, ("Telegram.exe", "telegram.exe"))
        if not exe:
            raise RuntimeError("В архиве не найден Telegram.exe")
        src_dir = os.path.dirname(exe)
        # копируем всё содержимое папки с exe (Updater.exe и т.д.)
        for name in os.listdir(src_dir):
            s = os.path.join(src_dir, name)
            d = os.path.join(dest_dir, name)
            if os.path.isdir(s):
                if os.path.exists(d):
                    shutil.rmtree(d, ignore_errors=True)
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)
        final = os.path.join(dest_dir, "Telegram.exe")
        if not os.path.isfile(final):
            # на всякий случай — прямое копирование exe
            shutil.copy2(exe, final)
        _log(log, f"✓ Готово: {final}")
        return final
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def proxychains_ready() -> bool:
    paths.refresh()
    return os.path.isfile(paths.proxychains_exe())


def download_proxychains(log: LogFn | None = None) -> str:
    """Качает proxychains-windows x64 в ./tools/proxychains. Возвращает путь к exe."""
    paths.ensure_dirs()
    dest_dir = paths.PROXYCHAINS_DIR
    os.makedirs(dest_dir, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="tgman-pc-")
    try:
        zip_path = os.path.join(tmp, "pc.zip")
        _log(log, "Скачиваю прокси-обёртку для Windows (ProxyChains)…")
        _download(PROXYCHAINS_URL, zip_path, log, "ProxyChains")
        _log(log, "Распаковываю…")
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(dest_dir)
        exe = paths.proxychains_exe()
        if not os.path.isfile(exe):
            found = _find_file(dest_dir, ("proxychains_win32_x64.exe", "proxychains.exe"))
            if not found:
                raise RuntimeError("В архиве не найден proxychains_win32_x64.exe")
            if os.path.abspath(found) != os.path.abspath(exe):
                shutil.copy2(found, exe)
        _log(log, f"✓ Готово: {exe}")
        return exe
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
