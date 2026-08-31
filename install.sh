#!/usr/bin/env bash
# Установщик TG Manager для Linux (Debian/Ubuntu и производные).
# Ставит зависимости, регистрирует программу в меню приложений с иконкой,
# и настраивает иконку «наша + зелёная точка» для запускаемых Telegram.
set -euo pipefail

APP_ID="tg-manager"
APP_NAME="TG Manager"
TG_ICON="tgmanager-telegram-running"   # имя иконки для запущенных Telegram
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

APPS_DIR="$HOME/.local/share/applications"
ICONS_ROOT="$HOME/.local/share/icons/hicolor"

echo "==> Установка $APP_NAME"
echo "    Папка программы: $DIR"

# --- Системные зависимости ---
if command -v apt >/dev/null 2>&1; then
    echo "==> Зависимости (нужен sudo): PyQt6, proxychains4, Pillow, Telethon, pip"
    sudo apt update -y || true
    sudo apt install -y python3-pyqt6 proxychains4 python3-pil python3-telethon python3-pip || \
        echo "!! Не удалось поставить пакеты через apt — проверьте вручную."
else
    echo "!! apt не найден. Установите вручную: PyQt6 и proxychains4."
fi

# --- opentele (чтение tdata) — через pip; + патч совместимости с Python 3.13+ ---
if python3 -m pip --version >/dev/null 2>&1; then
    echo "==> Ставлю opentele (pip --user)"
    python3 -m pip install --user --break-system-packages opentele >/dev/null 2>&1 || \
        echo "!! opentele не установился — автоматизация будет недоступна."
    python3 "$DIR/tgmanager/automation/_patch_opentele.py" >/dev/null 2>&1 || true
else
    echo "!! pip недоступен — opentele не поставлен (автоматизация опциональна)."
fi

python3 -c "import PyQt6.QtWidgets" 2>/dev/null && echo "==> PyQt6: OK" \
    || echo "!! PyQt6 не импортируется: sudo apt install python3-pyqt6"

# --- Иконки: сгенерировать при необходимости ---
if [ ! -f "$DIR/assets/icon_running_256.png" ] && python3 -c "import PIL" 2>/dev/null; then
    echo "==> Генерирую иконки"
    python3 "$DIR/assets/make_icon.py" || true
fi

# --- Установка иконок в hicolor (все размеры) ---
install_icon() {  # $1=исходник $2=имя-иконки $3=размер
    local src="$1" name="$2" size="$3"
    local dst="$ICONS_ROOT/${size}x${size}/apps"
    [ -f "$src" ] || return 0
    mkdir -p "$dst"
    cp "$src" "$dst/$name.png"
}
for s in 48 64 128 256; do
    install_icon "$DIR/assets/icon_${s}.png" "$APP_ID" "$s"
    install_icon "$DIR/assets/icon_running_${s}.png" "$TG_ICON" "$s"
done
install_icon "$DIR/assets/icon.png" "$APP_ID" 512
install_icon "$DIR/assets/icon_running_512.png" "$TG_ICON" 512

# --- Права на запуск ---
chmod +x "$DIR/run.sh" "$DIR/main.py" "$DIR/get_telegram.sh" 2>/dev/null || true

mkdir -p "$APPS_DIR"

# --- .desktop самой программы ---
cat > "$APPS_DIR/$APP_ID.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=$APP_NAME
Comment=Менеджер Telegram-контейнеров (tdata)
Exec="$DIR/run.sh"
Icon=$APP_ID
Terminal=false
Categories=Network;
StartupWMClass=$APP_ID
EOF

# --- .desktop-подмена иконки для запускаемых Telegram (app_id = org.telegram.desktop) ---
# GNOME сопоставляет окно с desktop-файлом по app_id и берёт из него Icon.
TG_BIN="$DIR/telegram/Telegram"
[ -x "$TG_BIN" ] || TG_BIN="$(command -v telegram-desktop || echo telegram-desktop)"
cat > "$APPS_DIR/org.telegram.desktop.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Telegram (TG Manager)
Comment=Аккаунт, запущенный из TG Manager
Exec="$TG_BIN" -workdir %f -many
Icon=$TG_ICON
Terminal=false
NoDisplay=true
Categories=Network;
StartupWMClass=org.telegram.desktop
EOF

# --- Ярлык на рабочем столе (мгновенный доступ, без ожидания меню) ---
DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")"
if [ -d "$DESKTOP_DIR" ]; then
    cp "$APPS_DIR/$APP_ID.desktop" "$DESKTOP_DIR/$APP_NAME.desktop"
    chmod +x "$DESKTOP_DIR/$APP_NAME.desktop"
    gio set "$DESKTOP_DIR/$APP_NAME.desktop" metadata::trusted true 2>/dev/null || true
    echo "==> Ярлык на рабочем столе: $DESKTOP_DIR/$APP_NAME.desktop"
fi

# Убрать устаревшие авто-заглушки GNOME для Telegram (мешают сопоставлению иконки)
rm -f "$APPS_DIR"/userapp-Telegram\ Desktop-*.desktop 2>/dev/null || true

# --- Обновить кэши ---
gtk-update-icon-cache -f -t "$ICONS_ROOT" 2>/dev/null || true
update-desktop-database "$APPS_DIR" 2>/dev/null || true

echo ""
echo "==> Готово!"
echo "    Программа в меню: «$APP_NAME» (со своей иконкой)"
echo "    Запуск из терминала: $DIR/run.sh"
echo ""
echo "    Иконка запущенных Telegram = наша + зелёная точка."
echo "    Если старый значок закешировался — перезапустите Telegram-контейнер"
echo "    (а иногда нужно перелогиниться в сессию GNOME)."
