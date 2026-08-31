@echo off
setlocal EnableExtensions
chcp 65001 >nul
title TG Manager — установка из исходников
cd /d "%~dp0"

echo.
echo === TG Manager :: установка (Windows 10/11) ===
echo     Папка: %~dp0
echo.

where py >nul 2>&1
if not errorlevel 1 (
    set "PY=py -3"
) else (
    where python >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Нужен Python 3.10+. https://www.python.org/downloads/
        echo         Отметьте "Add python.exe to PATH".
        pause
        exit /b 1
    )
    set "PY=python"
)

echo [1/3] Виртуальное окружение .venv
if not exist ".venv\Scripts\python.exe" (
    %PY% -m venv .venv
    if errorlevel 1 goto :fail
)
set "VPY=%~dp0.venv\Scripts\python.exe"
"%VPY%" -m pip install -U pip
"%VPY%" -m pip install -r requirements.txt
if errorlevel 1 goto :fail

echo [2/3] Иконки
"%VPY%" assets\make_icon.py
if errorlevel 1 echo [warn] иконки не пересобрались — используем уже лежащие.

echo [3/3] Ярлык на рабочий стол
"%VPY%" -c "from tgmanager.ui.settings_dialog import create_desktop_shortcut; print(create_desktop_shortcut())"
if errorlevel 1 echo [warn] ярлык не создан — сделайте его позже из Настроек.

echo.
echo === Готово ===
echo   Запуск:  start.bat
echo   или      .venv\Scripts\python.exe main.py
echo.
echo Portable-сборка (exe без Python) собирается build.bat
echo и публикуется GitHub Actions на ветке windows.
echo.
pause
exit /b 0

:fail
echo.
echo === Установка не удалась ===
pause
exit /b 1
