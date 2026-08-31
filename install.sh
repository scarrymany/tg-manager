#!/usr/bin/env bash
# Установщик TG Manager для Linux (Debian/Ubuntu и производные).
# Ставит зависимости, регистрирует ярлык в меню приложений.
set -euo pipefail

APP_ID="tg-manager"
APP_NAME="TG Manager"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Установка $APP_NAME"
echo "    Папка программы: $DIR"

# --- Системные зависимости ---
if command -v apt >/dev/null 2>&1; then
    echo "==> Устанавливаю зависимости (нужен sudo): python3-pyqt6, proxychains4"
    sudo apt update -y
    sudo apt install -y python3-pyqt6 proxychains4 python3-pil || {
        echo "!! Не удалось установить пакеты через apt."; }
else
    echo "!! apt не найден. Установите вручную: PyQt6 и proxychains4."
fi

# --- Проверка PyQt6 ---
if python3 -c "import PyQt6.QtWidgets" 2>/dev/null; then
    echo "==> PyQt6: OK"
else
    echo "!! PyQt6 не импортируется. Попробуйте: sudo apt install python3-pyqt6"
fi

# --- Иконки (если Pillow есть и PNG отсутствуют) ---
if [ ! -f "$DIR/assets/icon.png" ] && python3 -c "import PIL" 2>/dev/null; then
    echo "==> Генерирую иконку"
    python3 "$DIR/assets/make_icon.py" || true
fi

# --- Права на запуск ---
chmod +x "$DIR/run.sh" "$DIR/main.py" "$DIR/get_telegram.sh" 2>/dev/null || true

# --- .desktop для меню приложений ---
APPS_DIR="$HOME/.local/share/applications"
ICONS_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"
mkdir -p "$APPS_DIR" "$ICONS_DIR"
if [ -f "$DIR/assets/icon.png" ]; then
    cp "$DIR/assets/icon.png" "$ICONS_DIR/$APP_ID.png"
fi

cat > "$APPS_DIR/$APP_ID.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=$APP_NAME
Comment=Менеджер Telegram-аккаунтов (tdata)
Exec=$DIR/run.sh
Icon=$APP_ID
Terminal=false
Categories=Network;Utility;
StartupWMClass=$APP_ID
EOF
chmod +x "$APPS_DIR/$APP_ID.desktop" 2>/dev/null || true
update-desktop-database "$APPS_DIR" 2>/dev/null || true

echo ""
echo "==> Готово!"
echo "    Запуск из меню приложений: «$APP_NAME»"
echo "    Или из терминала:          $DIR/run.sh"
echo ""
echo "    Для прокси рекомендуется переносной Telegram —"
echo "    скачайте его кнопкой в Настройках или командой: $DIR/get_telegram.sh"
