"""Определение бинарника Telegram / proxychains и сборка команды запуска."""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from typing import List, Optional

from . import paths
from .models import Account

# Кандидаты для поиска Telegram (переносной внутри программы — в приоритете)
_TELEGRAM_CANDIDATES = [
    paths.BUNDLED_TELEGRAM_BIN,
    os.path.expanduser("~/Telegram/Telegram"),
    os.path.expanduser("~/.local/share/TelegramDesktop/Telegram"),
    "/opt/Telegram/Telegram",
    "/opt/telegram/Telegram",
    "/usr/bin/telegram-desktop",
    "/snap/bin/telegram-desktop",
]


def is_snap(path: str) -> bool:
    """True, если путь ведёт к snap-версии Telegram.

    /snap/bin/telegram-desktop — это симлинк на /usr/bin/snap (лаунчер snap),
    поэтому проверяем и сам путь, и его realpath.
    """
    if not path:
        return False
    rp = os.path.realpath(path)
    return (
        path.startswith("/snap/")
        or rp.startswith("/snap/")
        or os.path.basename(rp) == "snap"  # /usr/bin/snap — лаунчер snap
    )


def detect_telegram() -> Optional[str]:
    for cand in _TELEGRAM_CANDIDATES:
        if cand and os.path.exists(cand) and os.access(cand, os.X_OK):
            return cand
    for name in ("telegram-desktop", "telegram", "Telegram"):
        found = shutil.which(name)
        if found:
            return found
    return None


def detect_proxychains() -> Optional[str]:
    for name in ("proxychains4", "proxychains"):
        found = shutil.which(name)
        if found:
            return found
    return None


def resolve_telegram(configured: str = "") -> Optional[str]:
    if configured and os.path.exists(configured):
        return configured
    return detect_telegram()


def resolve_proxychains(configured: str = "") -> Optional[str]:
    if configured and os.path.exists(configured):
        return configured
    return detect_proxychains()


def write_proxychains_conf(account: Account, workdir: str) -> str:
    """Создаёт proxychains.conf в папке аккаунта и возвращает путь."""
    conf_path = os.path.join(workdir, "proxychains.conf")
    body = (
        "# Автогенерация TG Multitool — не редактируйте вручную\n"
        "strict_chain\n"
        "proxy_dns\n"
        "remote_dns_subnet 224\n"
        "tcp_read_time_out 15000\n"
        "tcp_connect_time_out 8000\n"
        "\n"
        "[ProxyList]\n"
        f"{account.proxy.proxychains_line()}\n"
    )
    with open(conf_path, "w", encoding="utf-8") as f:
        f.write(body)
    return conf_path


@dataclass
class LaunchPlan:
    argv: List[str]
    workdir: str
    tg_binary: str
    proxy_requested: bool = False
    proxy_applied: bool = False
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None


def build_launch_plan(settings, account: Account) -> LaunchPlan:
    """Собирает план запуска аккаунта с учётом прокси и переносного Telegram."""
    workdir = paths.account_workdir(account.id)
    os.makedirs(workdir, exist_ok=True)

    tg = resolve_telegram(settings.telegram_binary)
    if not tg:
        return LaunchPlan(argv=[], workdir=workdir, tg_binary="",
                          error="Не найден Telegram. Укажите путь в настройках "
                                "или скачайте переносной Telegram.")

    base_args = [tg, "-workdir", workdir]
    if settings.allow_many:
        base_args.append("-many")

    plan = LaunchPlan(argv=base_args, workdir=workdir, tg_binary=tg,
                      proxy_requested=account.proxy.enabled)

    if not account.proxy.enabled:
        return plan

    # Нужен прокси
    pc = resolve_proxychains(settings.proxychains_binary)
    if is_snap(tg):
        plan.warnings.append(
            "Telegram запущен из snap — proxychains внутрь песочницы не проникает, "
            "прокси НЕ будет применён. Используйте переносной Telegram "
            "(кнопка «Скачать переносной Telegram» в настройках)."
        )
        return plan
    if not pc:
        plan.warnings.append(
            "proxychains4 не установлен — прокси не применён. "
            "Установите: sudo apt install proxychains4"
        )
        return plan

    conf = write_proxychains_conf(account, workdir)
    plan.argv = [pc, "-f", conf] + base_args
    plan.proxy_applied = True
    return plan
