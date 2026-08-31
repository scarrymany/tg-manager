"""Модели данных: аккаунт и настройки прокси."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

PROXY_NONE = "none"
PROXY_HTTP = "http"
PROXY_SOCKS5 = "socks5"

PROXY_LABELS = {
    PROXY_NONE: "Без прокси",
    PROXY_HTTP: "HTTP",
    PROXY_SOCKS5: "SOCKS5",
}

# Приятные акцентные цвета для карточек
CARD_COLORS = [
    "#2AABEE", "#7E57C2", "#26A69A", "#EF6C57",
    "#FFA726", "#66BB6A", "#EC407A", "#42A5F5",
]


def parse_proxy_line(line: str):
    """Разбирает строку прокси в кортеж (host, port, user, password) или None.

    Поддерживаются форматы:
      host:port
      host:port:user:pass
      user:pass@host:port
      scheme://user:pass@host:port  (scheme игнорируется)
    """
    if not line:
        return None
    s = line.strip()
    if "://" in s:
        s = s.split("://", 1)[1]

    user = password = ""
    host = ""
    port = 0

    if "@" in s:
        creds, hostpart = s.rsplit("@", 1)
        cparts = creds.split(":")
        user = cparts[0] if cparts else ""
        password = cparts[1] if len(cparts) > 1 else ""
        hp = hostpart.split(":")
        if len(hp) < 2:
            return None
        host = hp[0]
        port_str = hp[1]
    else:
        parts = s.split(":")
        if len(parts) == 2:
            host, port_str = parts
        elif len(parts) == 3:
            host, port_str, user = parts
        elif len(parts) >= 4:
            host, port_str, user = parts[0], parts[1], parts[2]
            password = ":".join(parts[3:])  # пароль может содержать ':'
        else:
            return None

    host = host.strip()
    try:
        port = int(port_str.strip())
    except (ValueError, AttributeError):
        return None
    if not host or not (1 <= port <= 65535):
        return None
    return host, port, user.strip(), password


@dataclass
class Proxy:
    type: str = PROXY_NONE
    host: str = ""
    port: int = 0
    username: str = ""
    password: str = ""

    @property
    def enabled(self) -> bool:
        return self.type in (PROXY_HTTP, PROXY_SOCKS5) and bool(self.host) and self.port > 0

    def summary(self) -> str:
        if not self.enabled:
            return "Без прокси"
        label = PROXY_LABELS.get(self.type, self.type.upper())
        auth = " 🔑" if self.username else ""
        return f"{label} {self.host}:{self.port}{auth}"

    def proxychains_line(self) -> str:
        """Строка для секции [ProxyList] в proxychains.conf."""
        kind = "socks5" if self.type == PROXY_SOCKS5 else "http"
        line = f"{kind} {self.host} {self.port}"
        if self.username:
            line += f" {self.username}"
            if self.password:
                line += f" {self.password}"
        return line

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict | None) -> "Proxy":
        d = d or {}
        return cls(
            type=d.get("type", PROXY_NONE),
            host=d.get("host", ""),
            port=int(d.get("port", 0) or 0),
            username=d.get("username", ""),
            password=d.get("password", ""),
        )


@dataclass
class Account:
    name: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    proxy: Proxy = field(default_factory=Proxy)
    color: str = CARD_COLORS[0]
    notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "proxy": self.proxy.to_dict(),
            "color": self.color,
            "notes": self.notes,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Account":
        return cls(
            id=d.get("id") or uuid.uuid4().hex[:12],
            name=d.get("name", "Аккаунт"),
            proxy=Proxy.from_dict(d.get("proxy")),
            color=d.get("color", CARD_COLORS[0]),
            notes=d.get("notes", ""),
            created_at=d.get("created_at", datetime.now(timezone.utc).isoformat()),
        )
