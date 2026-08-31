@echo off
setlocal EnableExtensions
chcp 65001 >nul
title TG Manager — сборка portable exe
cd /d "%~dp0"

set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
set "DIST=%ROOT%\dist"
set "BUILD=%ROOT%\build"

echo.
echo ============================================================
echo   TG Manager :: Windows portable build
echo ============================================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    where py >nul 2>&1
    if errorlevel 1 (
        echo [error] python не найден
        exit /b 1
    )
    set "PY=py -3"
) else (
    set "PY=python"
)

echo [1/4] Зависимости сборки
%PY% -m pip install -U pip pyinstaller
%PY% -m pip install -r requirements.txt
if errorlevel 1 goto :fail
%PY% -m pip uninstall -y PyQt5 PyQt5-Qt5 PyQt5-sip >nul 2>&1

echo [2/4] Иконки
%PY% assets\make_icon.py
if not exist "%ROOT%\assets\icon.ico" (
    echo [error] нет assets\icon.ico
    goto :fail
)

echo [3/4] PyInstaller
if exist "%BUILD%" rmdir /s /q "%BUILD%"
if exist "%DIST%\TGManager.exe" del /f /q "%DIST%\TGManager.exe"
%PY% -m PyInstaller --clean --noconfirm --distpath "%DIST%" --workpath "%BUILD%\pyi" "%ROOT%\tgmanager.spec"
if errorlevel 1 goto :fail
if not exist "%DIST%\TGManager.exe" goto :fail

echo [4/4] Portable-папка
set "PORT=%DIST%\TG-Manager"
if exist "%PORT%" rmdir /s /q "%PORT%"
mkdir "%PORT%"
copy /Y "%DIST%\TGManager.exe" "%PORT%\TGManager.exe" >nul
copy /Y "%ROOT%\README.md" "%PORT%\README.txt" >nul
if exist "%ROOT%\RELEASE_NOTES.md" copy /Y "%ROOT%\RELEASE_NOTES.md" "%PORT%\RELEASE_NOTES.txt" >nul

echo.
echo ============================================================
echo   BUILD OK
echo   exe:     %DIST%\TGManager.exe
echo   folder:  %PORT%
echo ============================================================
echo   Запуск с автономной папки: TGManager.exe
echo   Telegram скачается кнопкой в программе (~50 МБ).
echo.
exit /b 0

:fail
echo.
echo ============================================================
echo   BUILD FAILED
echo ============================================================
exit /b 1
