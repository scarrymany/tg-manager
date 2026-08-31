"""Загрузка/сохранение конфигурации и списка аккаунтов."""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from typing import List, Optional

from . import paths
from .models import Account


@dataclass
class Settings:
    # Пустое значение => определять автоматически
    telegram_binary: str = ""
    proxychains_binary: str = ""
    allow_many: bool = True  # флаг -many, чтобы открывать много окон одновременно

    def to_dict(self) -> dict:
        return {
            "telegram_binary": self.telegram_binary,
            "proxychains_binary": self.proxychains_binary,
            "allow_many": self.allow_many,
        }

    @classmethod
    def from_dict(cls, d: dict | None) -> "Settings":
        d = d or {}
        return cls(
            telegram_binary=d.get("telegram_binary", "") or "",
            proxychains_binary=d.get("proxychains_binary", "") or "",
            allow_many=bool(d.get("allow_many", True)),
        )


@dataclass
class Store:
    settings: Settings = field(default_factory=Settings)
    accounts: List[Account] = field(default_factory=list)

    # ---- persistence ----
    @classmethod
    def load(cls) -> "Store":
        paths.ensure_dirs()
        if not os.path.exists(paths.CONFIG_FILE):
            return cls()
        try:
            with open(paths.CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return cls()
        settings = Settings.from_dict(data.get("settings"))
        accounts = [Account.from_dict(a) for a in data.get("accounts", [])]
        return cls(settings=settings, accounts=accounts)

    def save(self) -> None:
        paths.ensure_dirs()
        data = {
            "settings": self.settings.to_dict(),
            "accounts": [a.to_dict() for a in self.accounts],
        }
        # Атомарная запись
        fd, tmp = tempfile.mkstemp(dir=paths.CONFIG_DIR, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, paths.CONFIG_FILE)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

    # ---- accounts CRUD ----
    def add(self, account: Account) -> None:
        os.makedirs(paths.account_workdir(account.id), exist_ok=True)
        self.accounts.append(account)
        self.save()

    def update(self, account: Account) -> None:
        for i, a in enumerate(self.accounts):
            if a.id == account.id:
                self.accounts[i] = account
                break
        self.save()

    def remove(self, account_id: str) -> None:
        self.accounts = [a for a in self.accounts if a.id != account_id]
        self.save()

    def get(self, account_id: str) -> Optional[Account]:
        for a in self.accounts:
            if a.id == account_id:
                return a
        return None
