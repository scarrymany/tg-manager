"""Проверка наличия зависимостей автоматизации (telethon + opentele)."""
from __future__ import annotations

import importlib.util
import os
from typing import List


def missing() -> List[str]:
    """Список отсутствующих зависимостей (пусто — всё ок)."""
    out: List[str] = []
    for mod in ("telethon", "opentele"):
        try:
            if importlib.util.find_spec(mod) is None:
                out.append(mod)
        except Exception:
            out.append(mod)
    return out


def available() -> bool:
    return not missing()


if os.name == "nt":
    INSTALL_HINT = (
        "pip install telethon opentele python-socks\n"
        "(в portable-сборке зависимости уже внутри TGManager.exe)"
    )
else:
    INSTALL_HINT = (
        "sudo apt install -y python3-pip python3-telethon && "
        "pip install --user --break-system-packages opentele python-socks"
    )
