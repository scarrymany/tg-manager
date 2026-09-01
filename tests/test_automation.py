"""Юнит-тесты воркера: без Telethon, без сети."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import types
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tgmanager.automation.lock import telegram_running, _alive  # noqa: E402
from tgmanager.automation.session_pack import (  # noqa: E402
    JSON_KEYS,
    TDESKTOP_APP_HASH,
    TDESKTOP_APP_ID,
    assert_real_session,
    build_account_json,
    encode_scarp_proxy,
    fingerprint_from,
    is_real_telethon_session,
    normalize_phone,
    write_session_pack,
)
from tgmanager.automation.worker import (  # noqa: E402
    _build_proxy,
    _tdata_error,
    categorize,
    container_busy_error,
    main as worker_main,
)


def _args(**kwargs):
    ns = types.SimpleNamespace(
        proxy_host="",
        proxy_port="",
        proxy_type="",
        proxy_user="",
        proxy_pass="",
    )
    for k, v in kwargs.items():
        setattr(ns, k, v)
    return ns


class _Ent:
    def __init__(self, id, bot=False):
        self.id = id
        self.bot = bot


class _Dlg:
    def __init__(self, *, entity, is_user=False, is_channel=False, is_group=False):
        self.entity = entity
        self.is_user = is_user
        self.is_channel = is_channel
        self.is_group = is_group


class ProxyBuildTests(unittest.TestCase):
    def test_none_without_host(self):
        proxy, human = _build_proxy(_args())
        self.assertIsNone(proxy)
        self.assertIn("без прокси", human)

    def test_socks5_auth(self):
        proxy, human = _build_proxy(_args(
            proxy_host="127.0.0.1", proxy_port="9050", proxy_type="socks5",
            proxy_user="u", proxy_pass="p",
        ))
        self.assertEqual(proxy["proxy_type"], "socks5")
        self.assertEqual(proxy["addr"], "127.0.0.1")
        self.assertEqual(proxy["port"], 9050)
        self.assertTrue(proxy["rdns"])
        self.assertEqual(proxy["username"], "u")
        self.assertEqual(proxy["password"], "p")
        self.assertIn("SOCKS5", human)

    def test_http_default_when_not_socks5(self):
        proxy, _ = _build_proxy(_args(proxy_host="10.0.0.1", proxy_port="8080", proxy_type="http"))
        self.assertEqual(proxy["proxy_type"], "http")
        self.assertNotIn("username", proxy)


class CategorizeTests(unittest.TestCase):
    def test_saved_private_bot(self):
        me = 42
        self.assertEqual(categorize(_Dlg(entity=_Ent(42), is_user=True), me), "saved")
        self.assertEqual(categorize(_Dlg(entity=_Ent(7), is_user=True), me), "private")
        self.assertEqual(categorize(_Dlg(entity=_Ent(9, bot=True), is_user=True), me), "bots")

    def test_channels_and_groups(self):
        self.assertEqual(categorize(_Dlg(entity=_Ent(1), is_channel=True, is_group=False), 1), "channels")
        self.assertEqual(categorize(_Dlg(entity=_Ent(2), is_group=True), 1), "groups")
        self.assertEqual(categorize(_Dlg(entity=_Ent(3), is_channel=True, is_group=True), 1), "groups")

    def test_unknown(self):
        self.assertIsNone(categorize(_Dlg(entity=_Ent(1)), 1))


class TdataErrorTests(unittest.TestCase):
    def test_no_account(self):
        msg = _tdata_error(RuntimeError("No account found in tdata"))
        self.assertIn("залогиненного", msg)

    def test_passcode(self):
        msg = _tdata_error(RuntimeError("passcode decrypt failed"))
        self.assertIn("локальным паролем", msg)

    def test_generic(self):
        msg = _tdata_error(ValueError("boom"))
        self.assertIn("ValueError", msg)
        self.assertIn("boom", msg)


def _sqlite_session(path: str, auth_key: bytes | None = None) -> None:
    import sqlite3
    con = sqlite3.connect(path)
    try:
        con.execute(
            "CREATE TABLE sessions (dc_id INTEGER, server_address TEXT, "
            "port INTEGER, auth_key BLOB)"
        )
        con.execute(
            "INSERT INTO sessions VALUES (2, '149.154.167.51', 443, ?)",
            (auth_key if auth_key is not None else b"\x01" * 256,),
        )
        con.commit()
    finally:
        con.close()


class PhoneNormTests(unittest.TestCase):
    def test_strips_plus_and_spaces(self):
        self.assertEqual(normalize_phone("+380 67 123-45-67"), "380671234567")

    def test_empty(self):
        self.assertEqual(normalize_phone(None), "")
        self.assertEqual(normalize_phone(""), "")
        self.assertEqual(normalize_phone("abc"), "")


class ScarpProxyTests(unittest.TestCase):
    def test_none(self):
        self.assertIsNone(encode_scarp_proxy(None))
        self.assertIsNone(encode_scarp_proxy(""))
        self.assertIsNone(encode_scarp_proxy({"proxy_type": "socks5"}))

    def test_unknown_type_is_null(self):
        self.assertIsNone(encode_scarp_proxy({
            "proxy_type": "mtproto", "addr": "1.1.1.1", "port": 443,
        }))

    def test_socks5_string_tuple(self):
        raw = encode_scarp_proxy({
            "proxy_type": "socks5", "addr": "127.0.0.1", "port": 9050,
            "username": "u", "password": "p",
        })
        self.assertIsInstance(raw, str)
        parsed = json.loads(raw)
        self.assertEqual(parsed, [2, "127.0.0.1", 9050, True, "u", "p"])

    def test_http_from_worker_dict(self):
        raw = encode_scarp_proxy({
            "proxy_type": "http", "addr": "10.0.0.1", "port": 8080, "rdns": True,
        })
        self.assertEqual(json.loads(raw), [3, "10.0.0.1", 8080, True, None, None])

    def test_passthrough_string(self):
        self.assertEqual(encode_scarp_proxy("[2, \"h\", 1, true, null, null]"),
                         "[2, \"h\", 1, true, null, null]")


class ScarpJsonTests(unittest.TestCase):
    def test_keys_and_get_me(self):
        me = types.SimpleNamespace(
            id=777, phone="+380501112233",
            first_name="Ann", last_name="B", username="annb",
        )
        obj = build_account_json(me=me)
        self.assertEqual(list(obj), list(JSON_KEYS))
        self.assertEqual(obj["phone"], "380501112233")
        self.assertEqual(obj["session_file"], "380501112233")
        self.assertEqual(obj["user_id"], 777)
        self.assertEqual(obj["first_name"], "Ann")
        self.assertEqual(obj["last_name"], "B")
        self.assertEqual(obj["username"], "annb")
        self.assertEqual(obj["app_id"], TDESKTOP_APP_ID)
        self.assertEqual(obj["app_hash"], TDESKTOP_APP_HASH)
        self.assertEqual(obj["sdk"], "Windows 11")
        self.assertEqual(obj["app_version"], "5.14.3 x64")
        self.assertEqual(obj["device"], "Desktop")
        self.assertEqual(obj["lang_pack"], "tdesktop")
        self.assertIsNone(obj["twoFA"])
        self.assertIsNone(obj["proxy"])
        self.assertFalse(obj["ipv6"])
        self.assertEqual(obj["avatar"], "img/default.png")
        self.assertIsNone(obj["device_token"])
        dumped = json.dumps(obj)
        parsed = json.loads(dumped)
        self.assertEqual(parsed["user_id"], 777)

    def test_proxy_and_twofa(self):
        obj = build_account_json(
            phone="123", user_id=1,
            proxy={"proxy_type": "socks5", "addr": "1.2.3.4", "port": 1080},
            twofa="secret",
        )
        self.assertEqual(obj["twoFA"], "secret")
        self.assertEqual(json.loads(obj["proxy"])[0], 2)
        self.assertEqual(json.loads(obj["proxy"])[1], "1.2.3.4")

    def test_fingerprint_instance_wins_class_stale_ignored(self):
        class _Api:
            api_id = 2040
            api_hash = TDESKTOP_APP_HASH
            device_model = "ASUS All Series"
            system_version = "Windows 11"
            app_version = "5.16.4 x64"
            lang_code = "uk"
            system_lang_code = "uk-UA"
            lang_pack = "tdesktop"

        client = types.SimpleNamespace(api=_Api())
        fp = fingerprint_from(client=client)
        self.assertEqual(fp["device"], "ASUS All Series")
        self.assertEqual(fp["app_version"], "5.16.4 x64")
        self.assertEqual(fp["lang_code"], "uk")

        class _Cls:
            api_id = 2040
            api_hash = TDESKTOP_APP_HASH
            device_model = "Desktop"
            system_version = "Windows 10"
            app_version = "3.4.3 x64"

        fp2 = fingerprint_from(client=types.SimpleNamespace(api=_Cls))
        self.assertEqual(fp2["sdk"], "Windows 11")
        self.assertEqual(fp2["app_version"], "5.14.3 x64")


class SessionPackWriteTests(unittest.TestCase):
    def test_zip_contents_and_reject_stub(self):
        with tempfile.TemporaryDirectory() as td:
            stub = os.path.join(td, "stub.session")
            Path(stub).write_bytes(b"380501112233")  # 12-13 byte phone stub
            self.assertFalse(is_real_telethon_session(stub))
            with self.assertRaises(RuntimeError):
                assert_real_session(stub)

            real = os.path.join(td, "real.session")
            _sqlite_session(real)
            self.assertTrue(is_real_telethon_session(real))

            meta = build_account_json(phone="+380501112233", user_id=9,
                                     first_name="A")
            out = os.path.join(td, "out")
            pack = write_session_pack(out, "+380501112233", real, meta)
            self.assertTrue(os.path.isfile(pack["session"]))
            self.assertTrue(os.path.isfile(pack["json"]))
            self.assertTrue(os.path.isfile(pack["zip"]))
            self.assertIsNone(pack["twofa"])
            self.assertFalse(os.path.isfile(os.path.join(out, "2FA.txt")))

            with zipfile.ZipFile(pack["zip"]) as zf:
                names = set(zf.namelist())
            self.assertEqual(names, {"380501112233.session", "380501112233.json"})
            with open(pack["json"], encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(set(data), set(JSON_KEYS))
            self.assertEqual(data["phone"], "380501112233")
            self.assertTrue(is_real_telethon_session(pack["session"]))

    def test_twofa_file_only_when_set(self):
        with tempfile.TemporaryDirectory() as td:
            real = os.path.join(td, "r.session")
            _sqlite_session(real)
            meta = build_account_json(phone="1", user_id=1, twofa="pw")
            pack = write_session_pack(td, "1", real, meta, twofa="pw")
            self.assertTrue(os.path.isfile(pack["twofa"]))
            self.assertEqual(Path(pack["twofa"]).read_text(encoding="utf-8").strip(), "pw")
            with zipfile.ZipFile(pack["zip"]) as zf:
                self.assertIn("2FA.txt", zf.namelist())
                self.assertEqual(zf.read("2FA.txt").decode().strip(), "pw")


class ExportCliTests(unittest.TestCase):
    def test_export_session_requires_workdir(self):
        argv = sys.argv
        sys.argv = ["worker", "export-session"]
        try:
            self.assertEqual(worker_main(), 2)
        finally:
            sys.argv = argv

    def test_export_missing_tdata(self):
        from tgmanager.automation.export_session import export_main
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(export_main(["--workdir", td, "--output-dir", td]), 2)

    def test_busy_when_live_telegram_pid(self):
        # текущий python — не telegram, telegram_running=False
        with tempfile.TemporaryDirectory() as td:
            Path(td, "telegram.pid").write_text(str(os.getpid()), encoding="utf-8")
            self.assertIsNone(container_busy_error(td))


class TelegramRunningTests(unittest.TestCase):
    def test_missing_pidfile(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertFalse(telegram_running(td))

    def test_garbage_pidfile(self):
        with tempfile.TemporaryDirectory() as td:
            Path(td, "telegram.pid").write_text("not-a-pid", encoding="utf-8")
            self.assertFalse(telegram_running(td))

    def test_dead_pid(self):
        with tempfile.TemporaryDirectory() as td:
            Path(td, "telegram.pid").write_text("99999991", encoding="utf-8")
            self.assertFalse(_alive(99999991))
            self.assertFalse(telegram_running(td))

    def test_live_pid_not_telegram(self):
        with tempfile.TemporaryDirectory() as td:
            Path(td, "telegram.pid").write_text(str(os.getpid()), encoding="utf-8")
            # текущий python — не telegram/proxychains
            self.assertFalse(telegram_running(td))


if __name__ == "__main__":
    unittest.main()
