@echo off
setlocal EnableExtensions
chcp 65001 >nul
title TG Manager — сборка portable (WPF + worker)
cd /d "%~dp0"

set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
set "DIST=%ROOT%\dist"
set "BUILD=%ROOT%\build"

echo.
echo ============================================================
echo   TG Manager :: Windows portable build (WPF + TGWorker)
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

where dotnet >nul 2>&1
if errorlevel 1 (
    echo [error] .NET SDK 9 не найден. Поставьте https://dotnet.microsoft.com/download
    exit /b 1
)

echo [1/5] Зависимости воркера
%PY% -m pip install -U pip pyinstaller
%PY% -m pip install "telethon>=1.36,<2" "opentele-ng>=1.4.0" "python-socks>=2.4" "tgcrypto-pyrofork>=1.2.7"
if errorlevel 1 goto :fail
%PY% -m pip uninstall -y PyQt5 PyQt5-Qt5 PyQt5-sip >nul 2>&1

echo [2/5] Иконки
%PY% assets\make_icon.py
if not exist "%ROOT%\assets\icon.ico" (
    echo [error] нет assets\icon.ico
    goto :fail
)
if not exist "%ROOT%\src\TGManager\Assets\icon.ico" copy /Y "%ROOT%\assets\icon.ico" "%ROOT%\src\TGManager\Assets\icon.ico" >nul

echo [3/5] WPF TGManager.exe
dotnet publish "%ROOT%\src\TGManager\TGManager.csproj" -c Release -r win-x64 --self-contained true ^
  -p:PublishSingleFile=true ^
  -p:IncludeNativeLibrariesForSelfExtract=true ^
  -p:EnableCompressionInSingleFile=true ^
  -p:DebugType=embedded ^
  -o "%DIST%\app"
if errorlevel 1 goto :fail
if not exist "%DIST%\app\TGManager.exe" goto :fail

echo [4/5] PyInstaller TGWorker.exe
if exist "%BUILD%\pyi" rmdir /s /q "%BUILD%\pyi"
if exist "%DIST%\TGWorker.exe" del /f /q "%DIST%\TGWorker.exe"
%PY% -m PyInstaller --clean --noconfirm --distpath "%DIST%" --workpath "%BUILD%\pyi" "%ROOT%\worker.spec"
if errorlevel 1 goto :fail
if not exist "%DIST%\TGWorker.exe" goto :fail

echo [5/5] Portable-папка
set "PORT=%DIST%\TG-Manager"
if exist "%PORT%" rmdir /s /q "%PORT%"
mkdir "%PORT%"
copy /Y "%DIST%\app\TGManager.exe" "%PORT%\TGManager.exe" >nul
copy /Y "%DIST%\TGWorker.exe" "%PORT%\TGWorker.exe" >nul
copy /Y "%ROOT%\README.md" "%PORT%\README.txt" >nul
if exist "%ROOT%\RELEASE_NOTES.md" copy /Y "%ROOT%\RELEASE_NOTES.md" "%PORT%\RELEASE_NOTES.txt" >nul

echo.
echo ============================================================
echo   BUILD OK
echo   exe:     %PORT%\TGManager.exe
echo   worker:  %PORT%\TGWorker.exe
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
