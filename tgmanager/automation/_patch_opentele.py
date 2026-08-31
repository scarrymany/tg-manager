"""Патчи совместимости opentele. Идемпотентно, вызывать ДО import opentele.

1) Python 3.13+: у классов появились дандеры __firstlineno__/__static_attributes__,
   из-за которых @extend_class в opentele падает. Добавляем их в игнор-лист.
2) Новые версии Telegram Desktop добавляют типы записей в map (напр. 23 =
   lskMediaLastPlaybackPositions), которых нет в opentele → падает чтение tdata.
   Эти ключи не нужны для MTP-авторизации: на неизвестном ключе прекращаем разбор
   map (break), и аккаунт всё равно загружается.
"""
from __future__ import annotations

import os
import site
import sys
import sysconfig

# (относительный путь, что_ищем, на_что_меняем, маркер_уже_пропатчено)
_PATCHES = [
    (
        os.path.join("opentele", "utils.py"),
        '["__abstractmethods__", "__module__", "_abc_impl", "__doc__"]',
        '["__abstractmethods__", "__module__", "_abc_impl", "__doc__", '
        '"__firstlineno__", "__static_attributes__", "__qualname__"]',
        "__firstlineno__",
    ),
    (
        os.path.join("opentele", "td", "account.py"),
        'raise TDataReadMapDataFailed(\n'
        '                    f"Unknown key type in encrypted map: {keyType}"\n'
        '                )',
        "break  # opentele-patch: пропускаем неизвестные (новые) ключи map",
        "opentele-patch",
    ),
]


def _candidate_dirs():
    dirs = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        dirs.append(meipass)
    for fn in (lambda: site.getsitepackages(),
               lambda: [site.getusersitepackages()],
               lambda: [sysconfig.get_paths()["purelib"]]):
        try:
            dirs += fn()
        except Exception:
            pass
    return dirs


def apply() -> bool:
    """Применяет все патчи там, где найдёт opentele. True — если всё на месте."""
    ok_any = False
    for base in _candidate_dirs():
        for rel, old, new, marker in _PATCHES:
            path = os.path.join(base, rel)
            if not os.path.exists(path):
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    text = f.read()
            except OSError:
                continue
            if marker in text:
                ok_any = True
                continue
            if old in text:
                try:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(text.replace(old, new))
                    ok_any = True
                except OSError:
                    pass
    return ok_any


if __name__ == "__main__":
    print("opentele patched" if apply() else "opentele: нечего патчить/не найден")
