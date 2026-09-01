"""Команда воркера: export-session — tdata → SCARP_CC {phone}.session + json + zip.

Запуск:
  TGWorker.exe export-session --workdir <container> --output-dir <dir>
  python -m tgmanager.automation.worker export-session --workdir ... [--tdata ...]

Прогресс — те же JSON-строки, что у чистки.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import shutil
import tempfile
from typing import Any, List, Optional

try:
    from tgmanager.automation.session_pack import (
        assert_real_session,
        build_account_json,
        fingerprint_from,
        is_real_telethon_session,
        normalize_phone,
        write_session_pack,
    )
    from tgmanager.automation.worker import (
        FLOOD_AUTOSLEEP,
        _build_proxy,
        _tdata_error,
        container_busy_error,
        emit,
        load_tdesktop,
        to_telethon_kwargs,
    )
except ImportError:  # запуск из этой же папки / frozen
    from session_pack import (  # type: ignore
        assert_real_session,
        build_account_json,
        fingerprint_from,
        is_real_telethon_session,
        normalize_phone,
        write_session_pack,
    )
    from worker import (  # type: ignore
        FLOOD_AUTOSLEEP,
        _build_proxy,
        _tdata_error,
        container_busy_error,
        emit,
        load_tdesktop,
        to_telethon_kwargs,
    )


def save_telethon_session(client: Any, dest_path: str) -> None:
    """Живая Memory/SQLite-сессия → настоящий Telethon SQLite на диск."""
    from telethon.sessions import SQLiteSession

    dest_path = os.path.abspath(dest_path)
    base = dest_path[:-8] if dest_path.endswith(".session") else dest_path
    dest_path = base + ".session"
    for extra in (dest_path, dest_path + "-journal", dest_path + "-wal"):
        try:
            os.remove(extra)
        except FileNotFoundError:
            pass
    src = client.session
    dc_id = getattr(src, "dc_id", None)
    addr = getattr(src, "server_address", None)
    port = getattr(src, "port", None)
    key = getattr(src, "auth_key", None)
    if dc_id is None or not addr or port is None or key is None:
        raise RuntimeError(
            "В сконвертированной сессии нет DC/auth_key — opentele не отдал ключ."
        )
    sqlite = SQLiteSession(base)
    try:
        sqlite.set_dc(int(dc_id), str(addr), int(port))
        sqlite.auth_key = key
        takeout = getattr(src, "takeout_id", None)
        if takeout is not None:
            try:
                sqlite.takeout_id = takeout
            except Exception:
                pass
        sqlite.save()
    finally:
        try:
            sqlite.close()
        except Exception:
            pass
    assert_real_session(dest_path)


async def _connect_from_tdata(tdesk: Any, proxy: Any, tmp_dir: str) -> Any:
    """ToTelethon: сначала файл (как в доке opentele), иначе in-memory — как чистка."""
    tmp_base = os.path.join(tmp_dir, "export")
    last_err: Optional[BaseException] = None
    for session in (tmp_base, None):
        kwargs = to_telethon_kwargs(proxy, session=session)
        try:
            client = await tdesk.ToTelethon(**kwargs)
            return client
        except BaseException as e:
            last_err = e
            if session is None:
                raise
            emit({"type": "warn", "label": "ToTelethon",
                  "error": f"сессия-файл не вышел ({e.__class__.__name__}), пробую in-memory"})
    if last_err is not None:
        raise last_err
    raise RuntimeError("ToTelethon не вернул клиент")


async def run_export(args) -> int:
    workdir = args.workdir
    tdata = args.tdata or os.path.join(workdir, "tdata")
    output_dir = args.output_dir or workdir
    twofa = (args.twofa or "").strip() or None

    busy = container_busy_error(workdir)
    if busy:
        emit({"type": "error", "error": busy})
        return 2
    if not os.path.isdir(tdata):
        emit({"type": "error", "error": "В контейнере нет папки tdata"})
        return 2

    try:
        os.makedirs(output_dir, exist_ok=True)
    except OSError as e:
        emit({"type": "error", "error": f"Не создать папку экспорта: {e}"})
        return 2

    total = 5
    emit({"type": "stage", "msg": "Загрузка tdata…"})
    emit({"type": "progress", "done": 0, "total": total, "label": "tdata", "cat": "export"})
    try:
        tdesk = load_tdesktop(tdata)
    except BaseException as e:
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

    emit({"type": "progress", "done": 1, "total": total, "label": "tdata", "cat": "export"})
    emit({"type": "stage", "msg": f"Конвертация tdata → Telethon ({proxy_human})…"})

    tmp = tempfile.mkdtemp(prefix="tgman-export-")
    client = None
    try:
        try:
            client = await _connect_from_tdata(tdesk, proxy, tmp)
        except BaseException as e:
            emit({"type": "error", "error": _tdata_error(e)})
            return 2

        client.flood_sleep_threshold = FLOOD_AUTOSLEEP
        try:
            await client.connect()
        except BaseException as e:
            where = "через прокси " + proxy_human if proxy is not None else "напрямую"
            emit({"type": "error",
                  "error": f"Не удалось подключиться к Telegram ({where}): "
                           f"{e.__class__.__name__}: {e}. Проверьте прокси/интернет."})
            return 2

        emit({"type": "progress", "done": 2, "total": total,
              "label": "подключение", "cat": "export"})

        if not await client.is_user_authorized():
            emit({"type": "error", "error": "Сессия не авторизована (нужен вход в аккаунт)"})
            return 2

        emit({"type": "stage", "msg": "Чтение профиля…"})
        me = await client.get_me()
        phone = normalize_phone(getattr(me, "phone", None))
        if not phone:
            uid = getattr(me, "id", None)
            if uid:
                phone = str(int(uid))
                emit({"type": "warn", "label": "phone",
                      "error": "в профиле нет номера — файлы названы по user_id"})
            else:
                emit({"type": "error", "error": "В профиле нет телефона и user_id"})
                return 2

        emit({"type": "progress", "done": 3, "total": total,
              "label": phone, "cat": "export"})
        emit({"type": "stage", "msg": f"Пишу {phone}.session + json…"})

        fp = fingerprint_from(tdesk, client)
        meta = build_account_json(me=me, fingerprint=fp, proxy=proxy, twofa=twofa)

        dest_session = os.path.join(output_dir, f"{phone}.session")
        tmp_session = os.path.join(tmp, "export.session")
        if is_real_telethon_session(tmp_session):
            shutil.copy2(tmp_session, dest_session)
            assert_real_session(dest_session)
        else:
            save_telethon_session(client, dest_session)

        try:
            await client.disconnect()
        except Exception:
            pass
        client = None

        pack = write_session_pack(output_dir, phone, dest_session, meta, twofa=twofa)
        emit({"type": "progress", "done": 4, "total": total,
              "label": os.path.basename(pack["zip"] or ""), "cat": "export"})
        emit({
            "type": "done",
            "done": total,
            "phone": pack["phone"],
            "zip": pack["zip"],
            "session": pack["session"],
            "json": pack["json"],
        })
        emit({"type": "progress", "done": total, "total": total,
              "label": "готово", "cat": "export"})
        return 0
    finally:
        if client is not None:
            try:
                await client.disconnect()
            except Exception:
                pass
        shutil.rmtree(tmp, ignore_errors=True)


def export_main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="export-session")
    p.add_argument("--workdir", default="")
    p.add_argument("--tdata", default="")
    p.add_argument("--output-dir", default="")
    p.add_argument("--twofa", default="")
    p.add_argument("--proxy-type", default="")
    p.add_argument("--proxy-host", default="")
    p.add_argument("--proxy-port", default="")
    p.add_argument("--proxy-user", default="")
    p.add_argument("--proxy-pass", default="")
    args = p.parse_args(argv)
    if not args.workdir and args.tdata:
        args.workdir = os.path.dirname(os.path.abspath(args.tdata.rstrip("\\/")))
    if not args.workdir:
        emit({"type": "error", "error": "Нужен --workdir (папка контейнера) или --tdata"})
        return 2
    if not args.output_dir:
        args.output_dir = args.workdir
    if not args.proxy_pass:
        args.proxy_pass = os.environ.get("TGMANAGER_PROXY_PASS", "")
    try:
        return asyncio.run(run_export(args))
    except KeyboardInterrupt:
        emit({"type": "error", "error": "Прервано"})
        return 1
    except BaseException as e:
        emit({"type": "error", "error": f"{e.__class__.__name__}: {e}"})
        return 1
