#!/usr/bin/env bash
# Удаление интеграции TG Manager из рабочего окружения (файлы данных не трогаем).
set -euo pipefail

APP_ID="tg-manager"
TG_ICON="tgmanager-telegram-running"
APPS_DIR="$HOME/.local/share/applications"
ICONS_ROOT="$HOME/.local/share/icons/hicolor"

echo "==> Удаляю ярлыки и иконки TG Manager"
rm -f "$APPS_DIR/$APP_ID.desktop"
rm -f "$APPS_DIR/org.telegram.desktop.desktop"
for s in 48 64 128 256 512; do
    rm -f "$ICONS_ROOT/${s}x${s}/apps/$APP_ID.png"
    rm -f "$ICONS_ROOT/${s}x${s}/apps/$TG_ICON.png"
done

gtk-update-icon-cache -f -t "$ICONS_ROOT" 2>/dev/null || true
update-desktop-database "$APPS_DIR" 2>/dev/null || true

echo "==> Готово. Данные аккаунтов и конфиг НЕ удалены:"
echo "    ~/.config/tg-manager  и  ~/.local/share/tg-manager"
