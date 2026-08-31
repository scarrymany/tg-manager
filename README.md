# TG Manager — Windows 10/11

Портативный менеджер Telegram-контейнеров. Семья **SCARP.CC**: графит/белый,
одна карточка = один аккаунт (`tdata`), запуск многих окон сразу, HTTP/SOCKS5
на контейнер, чистка аккаунта через Telethon.

Linux-версия живёт на ветке [`main`](https://github.com/scarrymany/tg-manager/tree/main).
Эта ветка (`windows`) — полноценный порт под Windows 10/11.

Интерфейс — **WPF / .NET 9** (тот же стек, что [Клип](https://github.com/scarrymany/klip)):
нативное окно, PerMonitorV2, без Qt. Чистка tdata — отдельный `TGWorker.exe`.

![icon](assets/icon_256.png)

## Скачать и запустить (без Python / SDK)

Релиз: [Releases](https://github.com/scarrymany/tg-manager/releases/tag/v1.1.0-windows)

1. Скачайте `TG-Manager-1.1.0-windows.zip`.
2. Распакуйте в любую папку (программа **не пишет в AppData** — всё рядом с exe).
3. Запустите `TGManager.exe`. `TGWorker.exe` должен лежать рядом.

```
TG-Manager\
  TGManager.exe          ← запуск (WPF)
  TGWorker.exe           ← чистка tdata (без окна)
  README.txt
  telegram\              ← появится после «Скачать переносной Telegram»
  accounts\<id>\tdata\   ← сюда кладёте tdata
  config.json
  tools\proxychains\     ← появится, если пользуетесь прокси
```

Переносить папку целиком на другой диск / ПК можно в любой момент.

## Возможности

- **1 карточка = 1 контейнер.** Имя, цвет, папка, `tdata`.
- **Запуск / стоп**, живой статус. Много окон сразу (`-many`, `-workdir`).
  Стоп на Windows убивает процесс, а не прячет Telegram в трей.
- **Прокси HTTP / SOCKS5** на каждый контейнер (логин/пароль).
- **Официальный portable Telegram** качается кнопкой в `.\telegram\`.
- **Чистка аккаунта** из tdata (Telethon + opentele): каналы, группы,
  личка, боты, избранное, контакты, фото. Dry-run и блокировка сессии,
  чтобы не словить `AUTH_KEY_DUPLICATED`. Журнал в UTF-8 (эмодзи в
  названиях чатов больше не роняют чистку).
- Ярлык на рабочий стол из настроек.

## Как пользоваться

1. **Добавить контейнер** → имя (и прокси, если нужен).
2. На карточке **Папка** — откроется `accounts\<id>\`.
3. Положите туда папку **`tdata`**. Появится «✓ tdata».
4. **Запуск**.

Telegram запускается так:

```
Telegram.exe -workdir <папка_контейнера> -many -noupdate
```

## Прокси

Прокси задаётся на карточке и применяется **только к этому** Telegram.

- **SOCKS5** — напрямую через Windows-порт ProxyChains.
- **HTTP** — локальный SOCKS5-мост (внутри `TGManager.exe`) → HTTP CONNECT.

Если обёртки нет, программа предложит скачать её (~200 КБ) в `.\tools\proxychains\`.
Это аналог `proxychains4` с Linux.

Автоматизация (чистка) ходит в Telegram API через тот же прокси контейнера
(`python-socks`), без обёртки процесса.

## Запуск из исходников

GUI — Visual Studio / `dotnet`, воркер — Python 3.10+.

```bat
git clone -b windows https://github.com/scarrymany/tg-manager.git
cd tg-manager
dotnet run --project src\TGManager\TGManager.csproj
```

Воркер подхватится как `python -m tgmanager.automation.worker`, если рядом нет
`TGWorker.exe`. Для этого:

```bat
python -m pip install -r requirements-worker.txt
```

Старый PyQt-вход `python main.py` / `start.bat` на этой ветке ещё собирается,
но релизный exe — WPF.

## Сборка exe

На машине с Windows, .NET 9 SDK и Python 3.12:

```bat
build.bat
```

Готово: `dist\TG-Manager\TGManager.exe` + `TGWorker.exe`.

CI на этой ветке (GitHub Actions, `windows-latest`) собирает zip и публикует
релиз `v1.1.0-windows` при каждом пуше в `windows`.

## Где что лежит (portable)

| Что | Путь |
|---|---|
| Конфиг | `.\config.json` |
| Контейнеры / tdata | `.\accounts\<id>\tdata\` |
| Переносной Telegram | `.\telegram\Telegram.exe` |
| Прокси-обёртка | `.\tools\proxychains\` |
| Воркер чистки | `.\TGWorker.exe` |

Ничего не пишется в `%APPDATA%`. Удалить программу = удалить папку.

## Требования

- Windows 10 x64 (1809+) или Windows 11 x64
- Для исходников GUI: .NET 9 SDK
- Для исходников воркера: Python 3.10+, Telethon, opentele-ng, python-socks

## Возможные проблемы

- **«Не найден Telegram»** — скачайте переносной в настройках.
- **Прокси не применился** — скачайте прокси-обёртку.
- **Аккаунт не запускается** — в папке должна быть именно `tdata`, не `tdata\tdata`.
- **Чистка не стартует** — рядом должен лежать `TGWorker.exe` из того же zip.
