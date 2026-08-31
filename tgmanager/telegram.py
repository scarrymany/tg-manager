"""Определение Telegram.exe / ProxyChains и сборка команды запуска (Windows)."""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from typing import List, Optional

from . import paths
from .models import Account, PROXY_HTTP, PROXY_SOCKS5


def is_snap(path: str) -> bool:
    """На Windows snap нет — оставлено для совместимости сигнатуры."""
    if os.name == "nt" or not path:
        return False
    rp = os.path.realpath(path)
    return (
        path.startswith("/snap/")
        or rp.startswith("/snap/")
        or os.path.basename(rp) == "snap"
    )


def detect_telegram() -> Optional[str]:
    paths.refresh()
    bundled = paths.BUNDLED_TELEGRAM_BIN
    if bundled and os.path.isfile(bundled):
        return bundled
    if os.name == "nt":
        for cand in (
            os.path.expandvars(r"%LOCALAPPDATA%\Telegram Desktop\Telegram.exe"),
            os.path.expandvars(r"%PROGRAMFILES%\Telegram Desktop\Telegram.exe"),
            os.path.expandvars(r"%PROGRAMFILES(X86)%\Telegram Desktop\Telegram.exe"),
        ):
            if cand and os.path.isfile(cand):
                return cand
        found = shutil.which("Telegram.exe") or shutil.which("telegram")
        return found
    for name in ("telegram-desktop", "telegram", "Telegram"):
        found = shutil.which(name)
        if found:
            return found
    return None


def detect_proxychains() -> Optional[str]:
    paths.refresh()
    if os.name == "nt":
        exe = paths.proxychains_exe()
        if os.path.isfile(exe):
            return exe
        return None
    for name in ("proxychains4", "proxychains"):
        found = shutil.which(name)
        if found:
            return found
    return None


def resolve_telegram(configured: str = "") -> Optional[str]:
    """Явно указанный путь → только переносной Telegram рядом с программой."""
    paths.refresh()
    if configured and os.path.isfile(configured):
        return configured
    bundled = paths.BUNDLED_TELEGRAM_BIN
    if bundled and os.path.isfile(bundled):
        return bundled
    return None


def bundled_exists() -> bool:
    paths.refresh()
    return bool(paths.BUNDLED_TELEGRAM_BIN) and os.path.isfile(paths.BUNDLED_TELEGRAM_BIN)


def resolve_proxychains(configured: str = "") -> Optional[str]:
    if configured and os.path.isfile(configured):
        return configured
    return detect_proxychains()


def write_proxychains_conf(account: Account, workdir: str,
                           socks_host: str | None = None,
                           socks_port: int | None = None) -> str:
    """proxychains.conf в папке контейнера. На Windows HTTP идёт через локальный SOCKS-мост."""
    conf_path = os.path.join(workdir, "proxychains.conf")
    if socks_host and socks_port:
        line = f"socks5 {socks_host} {socks_port}"
    else:
        line = account.proxy.proxychains_line()
        # Windows-порт понимает в первую очередь socks5
        if os.name == "nt" and line.startswith("http "):
            line = "socks5 " + line[5:]
    body = (
        "# Автогенерация TG Manager — не редактируйте вручную\n"
        "strict_chain\n"
        "proxy_dns\n"
        "quiet_mode\n"
        "remote_dns_subnet 224\n"
        "tcp_read_time_out 15000\n"
        "tcp_connect_time_out 8000\n"
        "\n"
        "[ProxyList]\n"
        f"{line}\n"
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
    # HTTP-мост (только Windows, тип HTTP)
    bridge_args: List[str] | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


def build_launch_plan(settings, account: Account) -> LaunchPlan:
    workdir = paths.account_workdir(account.id)
    os.makedirs(workdir, exist_ok=True)

    tg = resolve_telegram(settings.telegram_binary)
    if not tg:
        return LaunchPlan(
            argv=[], workdir=workdir, tg_binary="",
            error="Переносной Telegram не установлен. Нажмите «Скачать "
                  "переносной Telegram» (в настройках или при запуске).",
        )

    base_args = [tg, "-workdir", workdir, "-noupdate"]
    if settings.allow_many:
        base_args.append("-many")

    plan = LaunchPlan(argv=base_args, workdir=workdir, tg_binary=tg,
                      proxy_requested=account.proxy.enabled)

    if not account.proxy.enabled:
        return plan

    if is_snap(tg):
        plan.warnings.append(
            "Telegram запущен из snap — proxychains внутрь песочницы не проникает, "
            "прокси НЕ будет применён. Используйте переносной Telegram."
        )
        return plan

    pc = resolve_proxychains(settings.proxychains_binary)
    if not pc:
        if os.name == "nt":
            plan.warnings.append(
                "Прокси-обёртка не установлена — прокси не применён. "
                "Нажмите «Скачать прокси-обёртку» в настройках "
                "(или подтвердите скачивание при запуске)."
            )
        else:
            plan.warnings.append(
                "proxychains4 не установлен — прокси не применён. "
                "Установите: sudo apt install proxychains4"
            )
        return plan

    proxy = account.proxy
    bridge_args = None
    socks_host = socks_port = None
    if os.name == "nt" and proxy.type == PROXY_HTTP:
        # локальный SOCKS5 → HTTP CONNECT, порт выберет ОС; подставим после старта моста
        bridge_args = [
            "--tg-http-bridge",
            "--bind-host", "127.0.0.1",
            "--bind-port", "0",
            "--proxy-host", proxy.host,
            "--proxy-port", str(proxy.port),
        ]
        if proxy.username:
            bridge_args += ["--proxy-user", proxy.username]
        if proxy.password:
            bridge_args += ["--proxy-pass", proxy.password]
        plan.bridge_args = bridge_args
        # conf перепишет launcher после READY, а пока — заглушка
        socks_host, socks_port = "127.0.0.1", 0

    if socks_host and socks_port == 0:
        # conf с 127.0.0.1:0 бесполезен — launcher перезапишет после старта моста
        conf = write_proxychains_conf(account, workdir)
    else:
        conf = write_proxychains_conf(account, workdir, socks_host, socks_port)

    plan.argv = [pc, "-f", conf] + base_args
    plan.proxy_applied = True
    if os.name == "nt" and proxy.type not in (PROXY_HTTP, PROXY_SOCKS5):
        plan.proxy_applied = False
        plan.warnings.append("Неизвестный тип прокси.")
    return plan
