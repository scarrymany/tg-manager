"""Проверка наличия зависимостей автоматизации (telethon + opentele)."""
from __future__ import annotations

import importlib.util
from typing import List


def missing() -> List[str]:
    """Список отсутствующих зависимостей (пусто — всё ок).

    Только проверка наличия модулей (без исполнения opentele — его патч и импорт
    делает воркер в отдельном процессе).
    """
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


INSTALL_HINT = (
    "sudo apt install -y python3-pip python3-telethon && "
    "pip install --user --break-system-packages opentele"
)
