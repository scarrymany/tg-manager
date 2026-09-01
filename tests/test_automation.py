"""Юнит-тесты воркера: без Telethon, без сети."""
from __future__ import annotations

import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tgmanager.automation.lock import telegram_running, _alive  # noqa: E402
from tgmanager.automation.worker import (  # noqa: E402
    _build_proxy,
    _tdata_error,
    categorize,
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
