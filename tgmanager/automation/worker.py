#!/usr/bin/env python3
"""Воркер автоматизации: чистка tdata и экспорт session-пака через Telethon (opentele).

Запуск отдельным процессом. Пишет прогресс построчным JSON в stdout:
  {"type":"stage","msg":...}
  {"type":"summary","counts":{...},"total":N}
  {"type":"progress","done":d,"total":t,"label":...,"cat":...}
  {"type":"flood","seconds":S,"label":...}
  {"type":"warn","label":...,"error":...}
  {"type":"done","done":d}
  {"type":"error","error":...}

Команды:
  (по умолчанию) чистка — --workdir --actions …
  export-session — tdata → {phone}.session + .json + .zip

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


def _force_utf8_stdio() -> None:
    """Windows + frozen exe: stdout иначе cp1251/cp1252 → кракозябры и UnicodeEncodeError."""
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["PYTHONUTF8"] = "1"
    for fd, name in ((1, "stdout"), (2, "stderr")):
        stream = getattr(sys, name, None)
        enc = (getattr(stream, "encoding", None) or "").lower().replace("-", "")
        ok = stream is not None and enc in ("utf8", "cp65001")
        if ok:
            try:
                stream.reconfigure(encoding="utf-8", errors="replace", newline="\n")
                continue
            except Exception:
                ok = False
        try:
            wrapped = open(
                fd, "w", encoding="utf-8", errors="replace",
                closefd=False, newline="\n", buffering=1,
            )
            setattr(sys, name, wrapped)
        except Exception:
            if stream is not None:
                try:
                    stream.reconfigure(encoding="utf-8", errors="replace")
                except Exception:
                    pass


_force_utf8_stdio()


def emit(obj: dict) -> None:
    """JSON в stdout строго UTF-8, без зависимости от кодовой страницы консоли."""
    line = json.dumps(obj, ensure_ascii=False, default=str) + "\n"
    data = line.encode("utf-8", "replace")
    try:
        buf = getattr(sys.stdout, "buffer", None)
        if buf is not None:
            buf.write(data)
            buf.flush()
            return
    except Exception:
        pass
    try:
        sys.stdout.write(line)
        sys.stdout.flush()
        return
    except Exception:
        pass
    try:
        sys.stdout.write(json.dumps(obj, ensure_ascii=True, default=str) + "\n")
        sys.stdout.flush()
    except Exception:
        pass


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


def container_busy_error(workdir: str):
    """Текст ошибки, если Telegram контейнера ещё жив; иначе None."""
    try:
        from tgmanager.automation.lock import telegram_running
    except Exception:
        try:
            from lock import telegram_running  # запуск из этой же папки
        except Exception:
            telegram_running = None
    if telegram_running is not None and telegram_running(workdir):
        return ("Telegram этого контейнера ещё запущен. Сначала «Стоп» — "
                "иначе сервер выбросит сессию (AUTH_KEY_DUPLICATED).")
    return None


def load_tdesktop(tdata: str):
    from opentele.td import TDesktop
    tdesk = TDesktop(tdata)
    if not tdesk.isLoaded():
        raise RuntimeError("Не удалось прочитать tdata (пусто/повреждено)")
    return tdesk


def to_telethon_kwargs(proxy, session=None):
    """Аргументы TDesktop.ToTelethon. session=None — in-memory (баг StringSession в opentele)."""
    from opentele.api import UseCurrentSession
    kwargs = {
        "session": session,
        "flag": UseCurrentSession,
        # устойчивость (особенно через прокси): не терять диалоги на обрывах
        "connection_retries": 8,
        "request_retries": 8,
        "retry_delay": 2,
        "timeout": 30,
        "auto_reconnect": True,
    }
    if proxy is not None:
        kwargs["proxy"] = proxy
    return kwargs


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


async def _collect(client, me_id, cats):
    """Собрать цели из ВСЕХ папок (основная + архив), дедуп по id.

    Обход устойчив к обрывам (особенно через прокси): при ошибке повторяем
    обход папки, дедуп по id накапливает уже полученное.
    """
    from telethon import errors
    seen = set()
    targets = []
    counts = {"channels": 0, "groups": 0, "private": 0, "bots": 0}
    all_dialogs = 0
    incomplete = [False]
    for folder in (0, 1):  # 0 = основная, 1 = архив
        for attempt in range(6):
            try:
                async for d in client.iter_dialogs(folder=folder):
                    if d.id in seen:
                        continue
                    seen.add(d.id)
                    all_dialogs += 1
                    cat = categorize(d, me_id)
                    if cat and cat in cats:
                        targets.append((cat, d))
                        counts[cat] = counts.get(cat, 0) + 1
                break  # папка обойдена целиком
            except errors.FloodWaitError as e:
                emit({"type": "flood", "seconds": int(e.seconds), "label": "Сканирование"})
                await asyncio.sleep(int(e.seconds) + 2)
            except (errors.RPCError, ConnectionError, OSError, asyncio.TimeoutError):
                emit({"type": "warn", "label": "Сканирование",
                      "error": f"обрыв, повтор обхода (папка {folder})"})
                await asyncio.sleep(2)
        else:
            incomplete[0] = True
            emit({"type": "warn", "label": "Сканирование",
                  "error": f"папка {folder} не обойдена полностью после 6 попыток"})
    return targets, counts, incomplete[0]


async def _delete_dialog(client, cat, d, revoke) -> bool:
    """Удалить/покинуть один диалог. True — успех, False — ошибка (не повторять).

    Ботов дополнительно БЛОКИРУЕМ: иначе бот пришлёт новое сообщение и диалог
    снова всплывёт в списке (боты-кликеры так и делают).
    """
    from telethon import errors
    from telethon.tl.functions.contacts import BlockRequest
    label = getattr(d, "name", None) or str(getattr(d, "id", ""))
    while True:
        try:
            if cat == "bots":
                try:
                    await client(BlockRequest(id=d.entity))
                except errors.FloodWaitError:
                    raise
                except errors.RPCError:
                    pass  # блок не критичен, продолжаем удаление
            await client.delete_dialog(d.entity, revoke=(revoke and cat == "private"))
            return True
        except errors.FloodWaitError as e:
            emit({"type": "flood", "seconds": int(e.seconds), "label": label})
            await asyncio.sleep(int(e.seconds) + 2)
        except errors.RPCError as e:
            emit({"type": "warn", "label": label, "error": str(e)})
            return False


async def run(args) -> int:
    from telethon.tl.functions.contacts import GetContactsRequest, DeleteContactsRequest
    from telethon.tl.functions.photos import DeletePhotosRequest
    from telethon.tl import types

    selected = set(a.strip() for a in args.actions.split(",") if a.strip())
    tdata = os.path.join(args.workdir, "tdata")
    if not os.path.isdir(tdata):
        emit({"type": "error", "error": "В контейнере нет папки tdata"})
        return 2

    busy = container_busy_error(args.workdir)
    if busy:
        emit({"type": "error", "error": busy})
        return 2

    emit({"type": "stage", "msg": "Загрузка tdata…"})
    try:
        tdesk = load_tdesktop(tdata)
    except BaseException as e:  # opentele бросает подклассы BaseException
        emit({"type": "error", "error": _tdata_error(e)})
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
    try:
        client = await tdesk.ToTelethon(**to_telethon_kwargs(proxy, session=None))
    except BaseException as e:
        emit({"type": "error", "error": _tdata_error(e)})
        return 2
    client.flood_sleep_threshold = FLOOD_AUTOSLEEP
    try:
        await client.connect()
    except BaseException as e:
        where = "через прокси " + proxy_human if proxy is not None else "напрямую"
        emit({"type": "error",
              "error": f"Не удалось подключиться к Telegram ({where}): {e.__class__.__name__}: {e}. "
                       "Проверьте прокси/интернет."})
        try:
            await client.disconnect()
        except Exception:
            pass
        return 2
    try:
        if not await client.is_user_authorized():
            emit({"type": "error", "error": "Сессия не авторизована (нужен вход в аккаунт)"})
            return 2
        me = await client.get_me()

        loop_cats = {c for c in ("channels", "groups", "private", "bots") if c in selected}
        saved_sel = "saved" in selected
        contacts_sel = "contacts" in selected
        photos_sel = "photos" in selected

        emit({"type": "stage", "msg": "Сканирование диалогов (включая архив)…"})
        targets, counts, scan_incomplete = await _collect(client, me.id, loop_cats)
        if scan_incomplete:
            emit({"type": "warn", "label": "Сканирование",
                  "error": "список диалогов может быть неполным — чистка продолжится с тем, что удалось получить"})
        counts["saved"] = 1 if saved_sel else 0
        extra = (1 if contacts_sel else 0) + (1 if photos_sel else 0) + (1 if saved_sel else 0)
        total = len(targets) + extra
        emit({"type": "summary", "counts": counts,
              "contacts": contacts_sel, "photos": photos_sel, "total": total})

        if args.dry_run:
            emit({"type": "done", "done": 0, "dry_run": True})
            return 0

        done = 0
        failed = set()

        # «Избранное» — один раз (self-диалог из списка не удаляется, поэтому вне цикла)
        if saved_sel:
            await _safe(lambda: client.delete_dialog("me"), "Избранное")
            done += 1
            emit({"type": "progress", "done": done, "total": total,
                  "label": "Избранное", "cat": "saved"})
            await asyncio.sleep(THROTTLE)

        # Диалоги — повторяем проходы (архив + повторы), пока не станет пусто.
        # Нужны ДВА пустых обхода подряд: одиночный «пусто» может быть неполным
        # обходом (обрыв через прокси), и останавливаться на нём нельзя.
        passes = 0
        empty_streak = 0
        while loop_cats:
            passes += 1
            if passes > 60:
                emit({"type": "warn", "label": "Проходы",
                      "error": "Достигнут лимит проходов — часть могла остаться"})
                break
            targets, _, scan_incomplete = await _collect(client, me.id, loop_cats)
            targets = [(c, d) for c, d in targets if d.id not in failed]
            if not targets:
                if scan_incomplete:
                    emit({"type": "warn", "label": "Проходы",
                          "error": "обход оборвался — не считаем список пустым"})
                    empty_streak = 0
                    await asyncio.sleep(2)
                    continue
                empty_streak += 1
                if empty_streak >= 2:
                    break
                await asyncio.sleep(1.5)  # перепроверка полноты
                continue
            empty_streak = 0
            emit({"type": "stage", "msg": f"Проход {passes}: к удалению {len(targets)}"})
            total = max(total, done + len(targets))
            for cat, d in targets:
                if await _delete_dialog(client, cat, d, args.revoke):
                    done += 1
                else:
                    failed.add(d.id)
                emit({"type": "progress", "done": done, "total": total,
                      "label": d.name or str(d.id), "cat": cat})
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

        emit({"type": "done", "done": done, "skipped": len(failed)})
        return 0
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass


def main() -> int:
    _force_utf8_stdio()
    if len(sys.argv) > 1 and sys.argv[1] in ("export-session", "export_session"):
        try:
            from tgmanager.automation.export_session import export_main
        except ImportError:
            from export_session import export_main  # запуск из этой же папки
        return export_main(sys.argv[2:])
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
    if not args.proxy_pass:
        args.proxy_pass = os.environ.get("TGMANAGER_PROXY_PASS", "")
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
