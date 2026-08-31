"""Совместимость opentele с Python 3.13+/3.14.

В 3.13+ у классов появились дандеры __firstlineno__/__static_attributes__,
из-за которых декоратор @extend_class в opentele падает (BaseException("err")).
Добавляем их в список игнорируемых в установленном файле opentele/utils.py.
Идемпотентно, вызывать ДО import opentele.
"""
from __future__ import annotations

import os
import site
import sysconfig

_OLD = '["__abstractmethods__", "__module__", "_abc_impl", "__doc__"]'
_NEW = ('["__abstractmethods__", "__module__", "_abc_impl", "__doc__", '
        '"__firstlineno__", "__static_attributes__", "__qualname__"]')


def _candidate_dirs():
    dirs = []
    try:
        dirs += site.getsitepackages()
    except Exception:
        pass
    try:
        dirs.append(site.getusersitepackages())
    except Exception:
        pass
    try:
        dirs.append(sysconfig.get_paths()["purelib"])
    except Exception:
        pass
    return dirs


def apply() -> bool:
    """Патчит opentele/utils.py при необходимости. True — если файл в порядке/пропатчен."""
    for base in _candidate_dirs():
        path = os.path.join(base, "opentele", "utils.py")
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except OSError:
            continue
        if "__firstlineno__" in text:
            return True  # уже пропатчено
        if _OLD in text:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text.replace(_OLD, _NEW))
                return True
            except OSError:
                return False
    return False


if __name__ == "__main__":
    print("opentele patched" if apply() else "opentele: нечего патчить/не найден")
