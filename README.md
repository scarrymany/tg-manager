<div align="center">

<img src="assets/icon_128.png" width="96" alt="TG Manager">

# TG Manager

**Много Telegram-аккаунтов на одном Windows. Каждый — в своём контейнере, со своим прокси.**

[![Release](https://img.shields.io/github/v/release/scarrymany/tg-manager?filter=*-windows&label=release&color=white&labelColor=0a0a0a)](https://github.com/scarrymany/tg-manager/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/scarrymany/tg-manager/total?color=white&labelColor=0a0a0a)](https://github.com/scarrymany/tg-manager/releases)
[![Windows 10/11](https://img.shields.io/badge/Windows-10%20%7C%2011-white?labelColor=0a0a0a)](#требования)
[![.NET 9 · WPF](https://img.shields.io/badge/.NET%209-WPF-white?labelColor=0a0a0a)](src/TGManager)
[![Portable](https://img.shields.io/badge/portable-без%20установки-white?labelColor=0a0a0a)](#скачать)

<br>

<img src="docs/screens/main.png" width="900" alt="TG Manager — список контейнеров">

</div>

<br>

Один контейнер — одна папка `tdata`, своё имя, свой HTTP/SOCKS5-прокси. Запуск многих
окон Telegram Desktop одновременно, живой статус, честная остановка процесса.
Чистка аккаунта (каналы, группы, личка, боты, контакты, фото) — через Telethon прямо
из `tdata`, без ввода номера и кода.

Портативно: распаковали zip — работает. Ничего не пишется в `%APPDATA%`,
папку можно перенести на другой диск или ПК целиком.

## Скачать

**[⬇ TG-Manager-1.2.0-windows.zip](https://github.com/scarrymany/tg-manager/releases/latest)** · Windows 10 (1809+) / 11, x64

1. Распакуйте в любую папку.
2. Запустите `TGManager.exe` (`TGWorker.exe` должен лежать рядом).
3. **Добавить контейнер** → **Папка** → положите туда `tdata` → **Запуск**.

Официальный портативный Telegram Desktop программа скачает сама при первом запуске (~50 МБ).

## Возможности

- **Контейнеры.** Карточка = аккаунт: имя, цвет, папка, `tdata`. Сколько угодно.
- **Параллельный запуск.** `Telegram.exe -workdir <контейнер> -many -noupdate`, живой статус каждые 2 секунды.
- **Стоп — это стоп.** Процесс завершается (`TerminateProcess` + `taskkill /T`), а не прячется в трей.
- **Прокси на контейнер.** SOCKS5 напрямую, HTTP через встроенный мост. Логин и пароль поддерживаются.
  Строку вида `socks5://user:pass@host:port` или `host:port:user:pass` можно просто вставить.
- **Чистка аккаунта.** Каналы, группы, личные чаты, боты (с блокировкой), «Избранное», контакты, фото профиля.
  Dry-run перед необратимым. FloodWait ждётся автоматически. Журнал в UTF-8.
- **Защита сессии.** Пока идёт чистка, запуск Telegram этого контейнера заблокирован — никаких `AUTH_KEY_DUPLICATED`.
- **Нативный интерфейс.** WPF, тёмная тема, скруглённое окно, плавные анимации, PerMonitorV2 DPI.

## Как это выглядит

<table>
<tr>
<td width="50%"><img src="docs/screens/tasks.png" alt="Активные задачи"><br><sub><b>Активные задачи</b> — чистка идёт в фоне, прогресс и журнал по каждому контейнеру.</sub></td>
<td width="50%"><img src="docs/screens/cleanup.png" alt="Автоматизация"><br><sub><b>Автоматизация</b> — выбираете разделы, проверяете dry-run, подтверждаете.</sub></td>
</tr>
<tr>
<td width="50%"><img src="docs/screens/account.png" alt="Новый контейнер"><br><sub><b>Контейнер</b> — имя, цвет, прокси одной строкой.</sub></td>
<td width="50%"><img src="docs/screens/settings.png" alt="Настройки"><br><sub><b>Настройки</b> — портативный Telegram, прокси-обёртка, ярлык на рабочий стол.</sub></td>
</tr>
</table>

## Как устроено

```
TG-Manager\
  TGManager.exe          запуск (WPF, .NET 9, self-contained)
  TGWorker.exe           чистка tdata (Telethon + opentele-ng), без окна
  config.json            контейнеры и настройки
  accounts\<id>\tdata\   сюда кладёте tdata
  telegram\Telegram.exe  портативный Telegram (скачивается кнопкой)
  tools\proxychains\     прокси-обёртка (скачивается кнопкой, ~200 КБ)
```

| Что | Как |
|---|---|
| Запуск | `Telegram.exe -workdir accounts\<id> -many -noupdate` |
| SOCKS5 | Windows-порт [ProxyChains](https://github.com/shunf4/proxychains-windows) оборачивает процесс Telegram |
| HTTP | локальный SOCKS5-мост внутри `TGManager.exe` → `HTTP CONNECT` → ваш прокси |
| Чистка | `TGWorker.exe` читает `tdata` через opentele, работает с Telegram API через тот же прокси |
| Стоп | дерево процессов контейнера завершается принудительно, pid-файл и мост очищаются |

## Сборка из исходников

Нужны .NET 9 SDK и Python 3.12.

```bat
git clone -b windows https://github.com/scarrymany/tg-manager.git
cd tg-manager
build.bat
```

Результат — `dist\TG-Manager\` с `TGManager.exe` и `TGWorker.exe`.
Для разработки: `dotnet run --project src\TGManager\TGManager.csproj`; воркер подхватится
как `python -m tgmanager.automation.worker`, если рядом нет `TGWorker.exe`
(`pip install -r requirements-worker.txt`).

CI (GitHub Actions, `windows-latest`) собирает zip и публикует релиз
`v<версия>-windows` при каждом пуше в ветку `windows`; версия берётся из `TGManager.csproj`.

## Требования

- Windows 10 x64 (1809+) или Windows 11 x64.
- Ничего ставить не нужно: .NET и Python внутри exe.

## Если что-то не так

| Симптом | Что делать |
|---|---|
| «Не найден Telegram» | Настройки → **Скачать переносной Telegram** |
| Прокси не применился | Настройки → **Скачать прокси-обёртку** |
| Аккаунт не запускается | В папке контейнера должна быть именно `tdata`, а не `tdata\tdata` |
| Чистка не стартует | `TGWorker.exe` должен лежать рядом с `TGManager.exe` из того же zip |
| Telegram не остановился | Закройте его из трея (Quit Telegram) — это редкий случай зависшего процесса |
| Что-то упало | Рядом с программой появится `error.log` — приложите его к issue |

## Автор

Разработчик — [@yeet17](https://t.me/yeet17) в Telegram · [scarrymany](https://github.com/scarrymany) на GitHub.
Кнопки GitHub и Telegram есть прямо в заголовке программы.

История изменений — в [CHANGELOG.md](CHANGELOG.md). Linux-версия (PyQt) осталась на ветке
[`main`](https://github.com/scarrymany/tg-manager/tree/main) и больше не развивается.
