#!/usr/bin/env bash
# Скачивает официальный переносной Telegram Desktop и кладёт его в ./telegram
# (бинарник будет ./telegram/Telegram). Используется программой и кнопкой в настройках.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$DIR/telegram"
URL="https://telegram.org/dl/desktop/linux"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "→ Скачиваю официальный Telegram Desktop…"
if command -v curl >/dev/null 2>&1; then
    curl -L --fail --progress-bar -o "$TMP/tg.tar.xz" "$URL"
elif command -v wget >/dev/null 2>&1; then
    wget -q --show-progress -O "$TMP/tg.tar.xz" "$URL"
else
    echo "✗ Нужен curl или wget." >&2
    exit 1
fi

echo "→ Распаковываю…"
tar -xJf "$TMP/tg.tar.xz" -C "$TMP"

SRC_BIN="$(find "$TMP" -maxdepth 3 -type f -name Telegram | head -n1 || true)"
if [ -z "${SRC_BIN:-}" ]; then
    echo "✗ В архиве не найден бинарник Telegram." >&2
    exit 1
fi

mkdir -p "$DEST"
cp -a "$(dirname "$SRC_BIN")/." "$DEST/"
chmod +x "$DEST/Telegram" 2>/dev/null || true

echo "✓ Готово: $DEST/Telegram"
