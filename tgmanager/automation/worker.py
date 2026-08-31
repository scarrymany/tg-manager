#!/usr/bin/env python3
"""Воркер автоматизации: чистит аккаунт из tdata через Telethon (opentele).

Запуск отдельным процессом. Пишет прогресс построчным JSON в stdout:
  {"type":"stage","msg":...}
  {"type":"summary","counts":{...},"total":N}
  {"type":"progress","done":d,"total":t,"label":...,"cat":...}
  {"type":"flood","seconds":S,"label":...}
  {"type":"warn","label":...,"error":...}
  {"type":"done","done":d}
  {"type":"error","error":...}

БЕЗОПАСНОСТЬ: этот процесс держит Telethon-сессию того же tdata, что и TDesktop.
Нельзя запускать одновременно с открытым Telegram этого контейнера (иначе выброс
сессии). За взаимную блокировку отвечает GUI (automation.lock).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

# Патч совместимости opentele с Python 3.13+ ДО импорта opentele
try:
    from tgmanager.automation import _patch_opentele
    _patch_opentele.apply()
except Exception:
    try:
        import _patch_opentele  # запуск из этой же папки
        _patch_opentele.apply()
    except Exception:
        pass

THROTTLE = 0.8  # пауза между действиями, сек (щадящий режим)
FLOOD_AUTOSLEEP = 24 * 3600  # Telethon сам ждёт FloodWait до суток


def emit(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _build_proxy(args):
    """(proxy_dict|None, человекочитаемо). proxy_dict — формат python-socks для Telethon."""
    if not args.proxy_host or not args.proxy_port:
        return None, "напрямую (без прокси)"
    ptype = "socks5" if args.proxy_type == "socks5" else "http"
    proxy = {
        "proxy_type": ptype,
        "addr": args.proxy_host,
        "port": int(args.proxy_port),
        "rdns": True,
    }
    if args.proxy_user:
        proxy["username"] = args.proxy_user
    if args.proxy_pass:
        proxy["password"] = args.proxy_pass
    human = f"{ptype.upper()} {args.proxy_host}:{args.proxy_port}"
    return proxy, human


def _tdata_error(e: BaseException) -> str:
    s = str(e)
    low = s.lower()
    if "no account" in low:
        return ("В tdata не найдено залогиненного аккаунта. Возможные причины: "
                "в контейнер положен tdata без входа в аккаунт; стоит локальный "
                "пароль на tdata; либо формат tdata новее, чем поддерживает opentele.")
    if "passcode" in low or "decrypt" in low or "badkey" in low:
        return ("tdata защищён локальным паролем — opentele не откроет его без пароля. "
                "Снимите локальный пароль в Telegram и переэкспортируйте tdata.")
    return f"Не удалось прочитать tdata: {e.__class__.__name__}: {s}"


def categorize(dialog, me_id: int):
    ent = dialog.entity
    if dialog.is_user:
        if ent.id == me_id:
            return "saved"
        if getattr(ent, "bot", False):
            return "bots"
        return "private"
    if dialog.is_channel and not dialog.is_group:
        return "channels"
    if dialog.is_group:
        return "groups"
    return None


async def _safe(coro_factory, label: str):
    """Выполнить действие с обработкой FloodWait и RPC-ошибок."""
    from telethon import errors
    while True:
        try:
            return await coro_factory()
        except errors.FloodWaitError as e:
            emit({"type": "flood", "seconds": int(e.seconds), "label": label})
            await asyncio.sleep(int(e.seconds) + 2)
        except errors.RPCError as e:
            emit({"type": "warn", "label": label, "error": str(e)})
            return None


async def run(args) -> int:
    from opentele.td import TDesktop
    from opentele.api import UseCurrentSession
    from telethon.tl.functions.contacts import GetContactsRequest, DeleteContactsRequest
    from telethon.tl.functions.photos import DeletePhotosRequest
    from telethon.tl import types

    selected = set(a.strip() for a in args.actions.split(",") if a.strip())
    tdata = os.path.join(args.workdir, "tdata")
    if not os.path.isdir(tdata):
        emit({"type": "error", "error": "В контейнере нет папки tdata"})
        return 2

    emit({"type": "stage", "msg": "Загрузка tdata…"})
    try:
        tdesk = TDesktop(tdata)
        loaded = tdesk.isLoaded()
    except BaseException as e:  # opentele бросает подклассы BaseException
        emit({"type": "error", "error": _tdata_error(e)})
        return 2
    if not loaded:
        emit({"type": "error", "error": "Не удалось прочитать tdata (пусто/повреждено)"})
        return 2

    proxy, proxy_human = _build_proxy(args)
    if proxy is not None:
        try:
            import python_socks  # noqa: F401
        except Exception:
            emit({"type": "error", "error": "Для прокси нужен python-socks: "
                  "pip install --user --break-system-packages python-socks"})
            return 2

    emit({"type": "stage", "msg": f"Подключение к Telegram ({proxy_human})…"})
    # session=None → Telethon делает in-memory сессию (без файла). Передавать
    # StringSession-объект нельзя: в opentele баг (UnboundLocalError auth_session).
    to_telethon_kwargs = {"session": None, "flag": UseCurrentSession}
    if proxy is not None:
        to_telethon_kwargs["proxy"] = proxy
    client = await tdesk.ToTelethon(**to_telethon_kwargs)
    client.flood_sleep_threshold = FLOOD_AUTOSLEEP
    await client.connect()
    try:
        if not await client.is_user_authorized():
            emit({"type": "error", "error": "Сессия не авторизована (нужен вход в аккаунт)"})
            return 2
        me = await client.get_me()

        emit({"type": "stage", "msg": "Сканирование диалогов…"})
        targets = []
        counts = {"channels": 0, "groups": 0, "private": 0, "bots": 0, "saved": 0}
        async for dialog in client.iter_dialogs():
            cat = categorize(dialog, me.id)
            if cat and cat in selected:
                targets.append((cat, dialog))
                counts[cat] = counts.get(cat, 0) + 1

        extra = (1 if "contacts" in selected else 0) + (1 if "photos" in selected else 0)
        total = len(targets) + extra
        emit({"type": "summary", "counts": counts,
              "contacts": "contacts" in selected, "photos": "photos" in selected,
              "total": total})

        if args.dry_run:
            emit({"type": "done", "done": 0, "dry_run": True})
            return 0

        done = 0
        for cat, dialog in targets:
            label = dialog.name or str(dialog.id)
            revoke = args.revoke and cat in ("private",)
            await _safe(lambda: client.delete_dialog(dialog.entity, revoke=revoke)
                        if cat != "saved" else client.delete_dialog("me"), label)
            done += 1
            emit({"type": "progress", "done": done, "total": total, "label": label, "cat": cat})
            await asyncio.sleep(THROTTLE)

        # Контакты
        if "contacts" in selected:
            async def _del_contacts():
                res = await client(GetContactsRequest(hash=0))
                users = getattr(res, "users", [])
                if users:
                    await client(DeleteContactsRequest(id=users))
                return len(users)
            n = await _safe(_del_contacts, "Контакты")
            done += 1
            emit({"type": "progress", "done": done, "total": total,
                  "label": f"Контакты ({n or 0})", "cat": "contacts"})
            await asyncio.sleep(THROTTLE)

        # Фото профиля
        if "photos" in selected:
            async def _del_photos():
                photos = await client.get_profile_photos("me")
                ids = [types.InputPhoto(id=p.id, access_hash=p.access_hash,
                                        file_reference=p.file_reference) for p in photos]
                if ids:
                    await client(DeletePhotosRequest(id=ids))
                return len(ids)
            n = await _safe(_del_photos, "Фото профиля")
            done += 1
            emit({"type": "progress", "done": done, "total": total,
                  "label": f"Фото профиля ({n or 0})", "cat": "photos"})

        emit({"type": "done", "done": done})
        return 0
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--workdir", required=True)
    p.add_argument("--actions", default="")
    p.add_argument("--revoke", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--proxy-type", default="")
    p.add_argument("--proxy-host", default="")
    p.add_argument("--proxy-port", default="")
    p.add_argument("--proxy-user", default="")
    p.add_argument("--proxy-pass", default="")
    args = p.parse_args()
    try:
        return asyncio.run(run(args))
    except KeyboardInterrupt:
        emit({"type": "error", "error": "Прервано"})
        return 1
    except BaseException as e:  # opentele исключения наследуют BaseException
        emit({"type": "error", "error": f"{e.__class__.__name__}: {e}"})
        return 1


if __name__ == "__main__":
    sys.exit(main())
