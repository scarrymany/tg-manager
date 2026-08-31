@echo off
chcp 65001 >nul
title TG Manager
cd /d "%~dp0"

if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" "%~dp0main.py" %*
    goto :eof
)

where py >nul 2>&1
if not errorlevel 1 (
    py -3 "%~dp0main.py" %*
    goto :eof
)

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3.10+ не найден. Поставьте с https://www.python.org/
    echo         либо распакуйте готовый архив с TGManager.exe из Releases.
    pause
    exit /b 1
)
python "%~dp0main.py" %*
