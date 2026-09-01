"""SCARP_CC-совместимый пак: {phone}.session + {phone}.json + zip.

Писатели без сети и без Telethon — их можно тестировать на Linux.
Формат JSON сверен с реальным session-shop паком (ключи как у SCARP_CC_CHATS).
"""
from __future__ import annotations

import json
import os
import shutil
import time
import zipfile
from datetime import datetime
from typing import Any, Mapping, Optional

# Официальный Telegram Desktop (то, что берёт opentele / TDesktop API).
TDESKTOP_APP_ID = 2040
TDESKTOP_APP_HASH = "b18441a1ff607e10a989891a5462e627"

# Если из tdata/opentele ничего не вытащили — Windows Desktop, как в эталонном паке.
DEFAULT_SDK = "Windows 11"
DEFAULT_APP_VERSION = "5.14.3 x64"
DEFAULT_DEVICE = "Desktop"
DEFAULT_LANG_CODE = "en"
DEFAULT_SYSTEM_LANG_CODE = "en-US"
DEFAULT_LANG_PACK = "tdesktop"
DEFAULT_AVATAR = "img/default.png"
DEFAULT_PERF_CAT = 2

# PySocks / типичные session-shops: 1=SOCKS4, 2=SOCKS5, 3=HTTP.
PROXY_TYPE_SOCKS4 = 1
PROXY_TYPE_SOCKS5 = 2
PROXY_TYPE_HTTP = 3

# Telethon SQLite — килобайты. 13-байтовая заглушка (просто номер) — запрещена.
MIN_SESSION_BYTES = 100
SQLITE_MAGIC = b"SQLite format 3"

JSON_KEYS = (
    "session_file",
    "phone",
    "user_id",
    "app_id",
    "app_hash",
    "sdk",
    "app_version",
    "device",
    "device_token",
    "device_token_secret",
    "device_secret",
    "signature",
    "certificate",
    "safetynet",
    "perf_cat",
    "tz_offset",
    "register_time",
    "last_check_time",
    "avatar",
    "first_name",
    "last_name",
    "username",
    "sex",
    "lang_code",
    "system_lang_code",
    "lang_pack",
    "twoFA",
    "proxy",
    "ipv6",
)

# Классовые дефолты старого opentele — не считаем «отпечатком из tdata».
_STALE_APP_VERSIONS = frozenset({"3.4.3 x64", "3.4.3"})


def normalize_phone(phone: Any) -> str:
    """Только цифры, без '+' и мусора. Пустая строка, если номера нет."""
    if phone is None:
        return ""
    return "".join(c for c in str(phone) if c.isdigit())


def local_tz_offset() -> int:
    off = datetime.now().astimezone().utcoffset()
    return int(off.total_seconds()) if off is not None else 0


def encode_scarp_proxy(proxy: Any) -> Optional[str]:
    """Прокси в JSON: строка PySocks-кортежа или null.

    Формат session-shop / Telegradd (тот же набор ключей, что у SCARP-пака):
      "[2, \\"host\\", 1080, true, \\"user\\", \\"pass\\"]"
    type: 1 SOCKS4, 2 SOCKS5, 3 HTTP.
    4-й элемент — rdns=true (как в Telegradd-примере).

    Неизвестная схема / нет host:port → None (не выдумываем форму).
    """
    if proxy is None:
        return None
    if isinstance(proxy, str):
        s = proxy.strip()
        return s or None
    if not isinstance(proxy, Mapping):
        return None
    raw_type = str(proxy.get("proxy_type") or proxy.get("type") or "").strip().lower()
    if raw_type in ("socks5", "2"):
        code = PROXY_TYPE_SOCKS5
    elif raw_type in ("socks4", "1"):
        code = PROXY_TYPE_SOCKS4
    elif raw_type in ("http", "https", "3"):
        code = PROXY_TYPE_HTTP
    else:
        return None
    host = proxy.get("addr") or proxy.get("host")
    port = proxy.get("port")
    if not host or not port:
        return None
    try:
        port_i = int(port)
    except (TypeError, ValueError):
        return None
    if port_i <= 0 or port_i > 65535:
        return None
    user = proxy.get("username") or None
    if isinstance(user, str) and not user:
        user = None
    password = proxy.get("password") or None
    if isinstance(password, str) and not password:
        password = None
    return json.dumps([code, str(host), port_i, True, user, password], ensure_ascii=False)


def is_real_telethon_session(path: str) -> bool:
    try:
        if not os.path.isfile(path):
            return False
        if os.path.getsize(path) < MIN_SESSION_BYTES:
            return False
        with open(path, "rb") as f:
            return f.read(len(SQLITE_MAGIC)) == SQLITE_MAGIC
    except OSError:
        return False


def assert_real_session(path: str) -> None:
    if not os.path.isfile(path):
        raise RuntimeError(f"Файл сессии не создан: {path}")
    size = os.path.getsize(path)
    if size < MIN_SESSION_BYTES:
        raise RuntimeError(
            f"Файл сессии слишком маленький ({size} байт) — отказ писать заглушку. "
            "Нужен настоящий Telethon SQLite."
        )
    with open(path, "rb") as f:
        head = f.read(len(SQLITE_MAGIC))
    if head != SQLITE_MAGIC:
        raise RuntimeError(
            "Файл сессии не SQLite (не Telethon .session). "
            "Заглушку из номера телефона не пишем."
        )


def fingerprint_from(tdesk: Any = None, client: Any = None) -> dict[str, Any]:
    """device/sdk/app_version/api из живого opentele-клиента, иначе Desktop-дефолты."""
    fp: dict[str, Any] = {
        "app_id": TDESKTOP_APP_ID,
        "app_hash": TDESKTOP_APP_HASH,
        "device": DEFAULT_DEVICE,
        "sdk": DEFAULT_SDK,
        "app_version": DEFAULT_APP_VERSION,
        "lang_code": DEFAULT_LANG_CODE,
        "system_lang_code": DEFAULT_SYSTEM_LANG_CODE,
        "lang_pack": DEFAULT_LANG_PACK,
        "tz_offset": local_tz_offset(),
        "register_time": 0,
        "last_check_time": int(time.time()),
    }
    api = None
    if client is not None:
        api = getattr(client, "api", None) or getattr(client, "_api", None)
    if api is None and tdesk is not None:
        api = getattr(tdesk, "api", None) or getattr(tdesk, "API", None)
    if api is None:
        try:
            from opentele.api import API  # type: ignore
            api = API.TelegramDesktop
        except Exception:
            api = None
    if api is not None:
        is_class = isinstance(api, type)
        aid = getattr(api, "api_id", None)
        if aid:
            try:
                fp["app_id"] = int(aid)
            except (TypeError, ValueError):
                pass
        ah = getattr(api, "api_hash", None)
        if ah:
            fp["app_hash"] = str(ah)
        # Классовые Windows 10 / 3.4.3 — мусор, оставляем наши дефолты.
        if not is_class:
            dm = getattr(api, "device_model", None)
            if dm:
                fp["device"] = str(dm)
            sv = getattr(api, "system_version", None)
            if sv:
                fp["sdk"] = str(sv)
            av = getattr(api, "app_version", None)
            if av and str(av) not in _STALE_APP_VERSIONS:
                fp["app_version"] = str(av)
            lc = getattr(api, "lang_code", None)
            if lc:
                fp["lang_code"] = str(lc)
            slc = getattr(api, "system_lang_code", None)
            if slc:
                fp["system_lang_code"] = str(slc)
            lp = getattr(api, "lang_pack", None)
            if lp:
                fp["lang_pack"] = str(lp)
    if tdesk is not None:
        av = getattr(tdesk, "AppVersion", None) or getattr(tdesk, "appVersion", None)
        if isinstance(av, str) and av.strip() and av.strip() not in _STALE_APP_VERSIONS:
            fp["app_version"] = av.strip()
    return fp


def build_account_json(
    *,
    me: Any = None,
    phone: Any = None,
    user_id: Any = 0,
    first_name: str = "",
    last_name: str = "",
    username: str = "",
    fingerprint: Optional[Mapping[str, Any]] = None,
    proxy: Any = None,
    twofa: Optional[str] = None,
    **overrides: Any,
) -> dict[str, Any]:
    fp = fingerprint_from()
    if fingerprint:
        for k, v in fingerprint.items():
            if v is None or v == "":
                continue
            fp[k] = v
    if me is not None:
        if phone is None:
            phone = getattr(me, "phone", None)
        user_id = getattr(me, "id", user_id) or 0
        first_name = getattr(me, "first_name", None) or first_name or ""
        last_name = getattr(me, "last_name", None) or last_name or ""
        username = getattr(me, "username", None) or username or ""
    phone_n = normalize_phone(phone)
    twofa_val: Optional[str]
    if isinstance(twofa, str) and twofa.strip():
        twofa_val = twofa.strip()
    else:
        twofa_val = None
    try:
        uid = int(user_id or 0)
    except (TypeError, ValueError):
        uid = 0
    obj: dict[str, Any] = {
        "session_file": phone_n,
        "phone": phone_n,
        "user_id": uid,
        "app_id": int(fp.get("app_id") or TDESKTOP_APP_ID),
        "app_hash": str(fp.get("app_hash") or TDESKTOP_APP_HASH),
        "sdk": str(fp.get("sdk") or DEFAULT_SDK),
        "app_version": str(fp.get("app_version") or DEFAULT_APP_VERSION),
        "device": str(fp.get("device") or DEFAULT_DEVICE),
        "device_token": None,
        "device_token_secret": None,
        "device_secret": None,
        "signature": None,
        "certificate": None,
        "safetynet": None,
        "perf_cat": int(fp.get("perf_cat") or DEFAULT_PERF_CAT),
        "tz_offset": int(fp.get("tz_offset") if fp.get("tz_offset") is not None else local_tz_offset()),
        "register_time": int(fp.get("register_time") or 0),
        "last_check_time": int(fp.get("last_check_time") or int(time.time())),
        "avatar": str(fp.get("avatar") or DEFAULT_AVATAR),
        "first_name": first_name or "",
        "last_name": last_name or "",
        "username": username or "",
        "sex": 0,
        "lang_code": str(fp.get("lang_code") or DEFAULT_LANG_CODE),
        "system_lang_code": str(fp.get("system_lang_code") or DEFAULT_SYSTEM_LANG_CODE),
        "lang_pack": str(fp.get("lang_pack") or DEFAULT_LANG_PACK),
        "twoFA": twofa_val,
        "proxy": encode_scarp_proxy(proxy),
        "ipv6": False,
    }
    for k, v in overrides.items():
        if k in JSON_KEYS:
            obj[k] = v
    return obj


def write_session_pack(
    output_dir: str,
    phone: str,
    session_src: str,
    meta: Mapping[str, Any],
    twofa: Optional[str] = None,
) -> dict[str, Optional[str]]:
    """Пишет {phone}.session / .json / .zip (+ 2FA.txt только если пароль есть)."""
    phone_n = normalize_phone(phone)
    if not phone_n:
        raise ValueError("пустой phone — нечем назвать файлы пака")
    os.makedirs(output_dir, exist_ok=True)
    session_dst = os.path.join(output_dir, f"{phone_n}.session")
    json_dst = os.path.join(output_dir, f"{phone_n}.json")
    zip_dst = os.path.join(output_dir, f"{phone_n}.zip")
    twofa_dst = os.path.join(output_dir, "2FA.txt")

    assert_real_session(session_src)
    src_abs = os.path.abspath(session_src)
    dst_abs = os.path.abspath(session_dst)
    if src_abs != dst_abs:
        shutil.copy2(session_src, session_dst)
    assert_real_session(session_dst)

    payload = dict(meta)
    payload["session_file"] = phone_n
    payload["phone"] = phone_n
    if twofa and str(twofa).strip():
        payload["twoFA"] = str(twofa).strip()
    with open(json_dst, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")

    twofa_written = None
    if twofa and str(twofa).strip():
        with open(twofa_dst, "w", encoding="utf-8") as f:
            f.write(str(twofa).strip() + "\n")
        twofa_written = twofa_dst

    with zipfile.ZipFile(zip_dst, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(session_dst, os.path.basename(session_dst))
        zf.write(json_dst, os.path.basename(json_dst))
        if twofa_written:
            zf.write(twofa_written, "2FA.txt")

    return {
        "phone": phone_n,
        "session": session_dst,
        "json": json_dst,
        "zip": zip_dst,
        "twofa": twofa_written,
    }
