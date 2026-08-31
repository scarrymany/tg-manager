#!/usr/bin/env bash
# Быстрый запуск TG Manager
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"
exec python3 "$DIR/main.py" "$@"
