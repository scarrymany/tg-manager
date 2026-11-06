<div align="center">

<img src="assets/icon_128.png" width="88" alt="TG Manager">

# TG Manager

**Десятки Telegram-аккаунтов на одном Windows.<br>Каждый - в своём контейнере, со своим прокси, в один клик.**

[![Release](https://img.shields.io/github/v/release/scarrymany/tg-manager?label=release&color=white&labelColor=0a0a0a)](https://github.com/scarrymany/tg-manager/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/scarrymany/tg-manager/total?color=white&labelColor=0a0a0a)](https://github.com/scarrymany/tg-manager/releases)
[![License](https://img.shields.io/github/license/scarrymany/tg-manager?color=white&labelColor=0a0a0a)](LICENSE)
[![Windows 10/11](https://img.shields.io/badge/Windows-10%20%7C%2011-white?labelColor=0a0a0a)](#требования)
[![.NET 9 · WPF](https://img.shields.io/badge/.NET%209-WPF-white?labelColor=0a0a0a)](src/TGManager)
[![Portable](https://img.shields.io/badge/portable-без%20установки-white?labelColor=0a0a0a)](#скачать)

[**Скачать**](https://github.com/scarrymany/tg-manager/releases/latest) · [Установка одной командой](#установка-одной-командой) · [Возможности](#возможности) · [Скриншоты](#как-это-выглядит) · [Изменения](CHANGELOG.md)

<br>

<img src="docs/media/showcase.gif" alt="TG Manager: запуск контейнеров, поиск, папки и задачи">

</div>

<br>

TG Manager держит каждый Telegram-аккаунт в отдельном контейнере: своя папка `tdata`, своё имя, цвет,
папка-группа и свой HTTP/SOCKS5-прокси. Окна Telegram Desktop запускаются параллельно, статус каждого
виден в списке, а «Стоп» действительно завершает процесс. Чистка аккаунта и экспорт `.session` работают
прямо из `tdata`, без ввода номера и кода.

Программа портативная: распаковали zip - работает. В `%APPDATA%` ничего не пишется, папку целиком
можно перенести на другой диск или ПК.

## Почему TG Manager

<table>
<tr>
<td width="50%" valign="top">

**Полная изоляция аккаунтов**<br>
Каждый контейнер - отдельный `-workdir` Telegram Desktop. Сессии, кэш и настройки
одного аккаунта никак не пересекаются с другими.

</td>
<td width="50%" valign="top">

**Свой прокси на каждый аккаунт**<br>
SOCKS5 и HTTP с логином и паролем. Строку `socks5://user:pass@host:port` или `host:port:user:pass`
достаточно вставить - поля заполнятся сами.

</td>
</tr>
<tr>
<td valign="top">

**Десятки окон без хаоса**<br>
Компактный список помещает 10+ контейнеров на экран, есть поиск, фильтры, сортировка и папки.
Список виртуализирован, 50+ аккаунтов листаются без задержек.

</td>
<td valign="top">

**Честный запуск и остановка**<br>
Живой статус каждые 2 секунды. «Стоп» завершает дерево процессов контейнера, а не прячет Telegram
в трей, и никогда не трогает чужие процессы.

</td>
</tr>
<tr>
<td valign="top">

**Чистка и экспорт из tdata**<br>
Каналы, группы, личка, боты, «Избранное», контакты, фото - через Telethon, без номера и кода.
Dry-run перед необратимым, FloodWait ждётся сам. Экспорт в `.session` + JSON + zip.

</td>
<td valign="top">

**Портативно и безопасно**<br>
Ничего не устанавливается в систему, .NET и Python уже внутри exe. Пока идёт чистка или экспорт,
запуск этого Telegram заблокирован - никаких `AUTH_KEY_DUPLICATED`.

</td>
</tr>
</table>

## Скачать

### Установка одной командой

В PowerShell (Windows 10/11, права администратора не нужны):

```powershell
irm https://raw.githubusercontent.com/scarrymany/tg-manager/main/install.ps1 | iex
```

Скрипт берёт последний GitHub Release (`TG-Manager-x.y.z.zip`, без prerelease) и ставит программу в
`Desktop\TG-Manager\` (OneDrive Desktop подхватывается сам), рядом создаёт ярлык **TG Manager**.
Повторный запуск обновляет программу на месте: **`config.json`, `accounts\`, `telegram\` и `tools\` не трогаются.**

<details>
<summary>Параметры установщика</summary>

<br>

```powershell
powershell -ExecutionPolicy Bypass -File install.ps1
powershell -ExecutionPolicy Bypass -File install.ps1 -InstallDir "D:\Apps\TG-Manager" -Force -NoShortcut
```

| Ключ | Что делает |
|---|---|
| `-InstallDir` | Папка установки (по умолчанию `<Desktop>\TG-Manager`) |
| `-Force` | Закрыть занятые `TGManager.exe`/`TGWorker.exe` из этой папки и перезаписать exe. Данные не трогаются |
| `-NoShortcut` | Не создавать ярлык `TG Manager.lnk` |
| `-LocalZip` | Готовый `TG-Manager-*.zip`, без GitHub (офлайн) |

Для one-liner те же опции задаются через переменные окружения: `TGMANAGER_INSTALL_DIR`, `TGMANAGER_FORCE=1`,
`TGMANAGER_NO_SHORTCUT=1`, `TGMANAGER_LOCAL_ZIP`. Вместо `irm` подойдёт и `iwr ... | iex`.

</details>

### Вручную

**[TG-Manager-1.5.0.zip](https://github.com/scarrymany/tg-manager/releases/latest)** · Windows 10 (1809+) / 11, x64

1. Распакуйте архив в любую папку.
2. Запустите `TGManager.exe` (`TGWorker.exe` должен лежать рядом).
3. **Добавить контейнер** → **Папка** → положите туда `tdata` → **Запуск**.

Официальный портативный Telegram Desktop (~50 МБ) программа скачает сама при первом запуске.
Целостность архива проверяется по `SHA256SUMS.txt` из релиза:
`Get-FileHash .\TG-Manager-1.5.0.zip -Algorithm SHA256`.

## Как это выглядит

<table>
<tr>
<td colspan="2"><img src="docs/screens/main.png" width="100%" alt="Компактный список контейнеров"><br><sub><b>Компактный список</b> - одна строка на аккаунт: статус, прокси, tdata, заметка и все действия значками.</sub></td>
</tr>
<tr>
<td width="50%"><img src="docs/screens/main-comfortable.png" width="100%" alt="Обычная плотность списка"><br><sub><b>Обычная плотность</b> - кнопки с подписями. Плотность, высота карточки и набор кнопок настраиваются.</sub></td>
<td width="50%"><img src="docs/screens/tasks.png" width="100%" alt="Активные задачи"><br><sub><b>Активные задачи</b> - чистка и экспорт идут в фоне, у каждой свой прогресс и журнал.</sub></td>
</tr>
<tr>
<td><img src="docs/screens/account.png" width="100%" alt="Настройки контейнера"><br><sub><b>Контейнер</b> - имя, цвет, папка и прокси. Строка прокси разбирается автоматически.</sub></td>
<td><img src="docs/screens/cleanup.png" width="100%" alt="Чистка аккаунта"><br><sub><b>Чистка</b> - выбираете разделы, проверяете dry-run и только потом подтверждаете.</sub></td>
</tr>
<tr>
<td><img src="docs/screens/settings.png" width="100%" alt="Настройки списка"><br><sub><b>Настройки</b> - переносной Telegram, прокси-обёртка, вид списка контейнеров.</sub></td>
<td><img src="docs/screens/task-log.png" width="100%" alt="Журнал задачи"><br><sub><b>Журнал</b> - каждый шаг чистки в UTF-8, паузы FloodWait видны сразу.</sub></td>
</tr>
</table>

<sub>Скриншоты и GIF сняты с настоящих окон приложения на демо-данных; адреса прокси - документационные (RFC 5737).</sub>

## Возможности

- **Контейнеры.** Карточка = аккаунт: имя, цвет, папка-группа, заметка, `tdata`. Количество не ограничено.
- **Параллельный запуск.** `Telegram.exe -workdir <контейнер> -many -noupdate`, статус обновляется каждые 2 секунды.
- **Стоп - это стоп.** Процесс завершается (`TerminateProcess` + `taskkill /T`), а не прячется в трей.
  Дерево процессов проверяется по пути и командной строке, чужие окна не задеваются.
- **Прокси на контейнер.** SOCKS5 напрямую, HTTP через встроенный локальный мост. Логин и пароль поддерживаются,
  IPv6 в виде `[::1]:port` тоже. Пароль не попадает в командную строку воркера.
- **Чистка аккаунта.** Каналы, группы, личные чаты (по желанию и у собеседника), боты с блокировкой,
  «Избранное», контакты, фото профиля. Dry-run, автоматическое ожидание FloodWait, журнал в UTF-8.
- **Экспорт session.** `{phone}.session` (настоящий Telethon SQLite из tdata), `{phone}.json` (формат SCARP_CC)
  и `{phone}.zip`. Telegram контейнера при этом должен быть закрыт.
- **Папки контейнеров.** Группы для разных задач в боковой панели: создание, переименование, удаление
  без потери аккаунтов. Поиск и фильтр состояния работают внутри выбранной папки.
- **Поиск и фильтры.** По имени, ID, заметке и прокси (без учёта логина и пароля). **Ctrl+F** - к поиску,
  **Escape** - сбросить запрос и фильтры.
- **Вид списка.** Плотность «Обычная» / «Компактная», высота карточки, размер и вид кнопок, набор кнопок.
  Скрытые действия остаются в меню карточки (правая кнопка мыши).
- **Нативный интерфейс.** WPF, тёмная тема, шрифт Inter внутри сборки, скруглённое окно, плавные анимации,
  PerMonitorV2 DPI (проверено на 100-200%).

## Как устроено

```
TG-Manager\
  TGManager.exe          интерфейс (WPF, .NET 9, self-contained)
  TGWorker.exe           чистка и экспорт tdata (Telethon + opentele-ng), без окна
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
| Чистка / экспорт | `TGWorker.exe` читает `tdata` через opentele; экспорт пишет Telethon `{phone}.session` + JSON + zip |
| Защита сессии | `automation.lock` в контейнере: пока он есть, Telegram этого контейнера не запускается |
| Стоп | дерево процессов контейнера завершается принудительно, pid-файл и мост очищаются |

## Сборка из исходников

Нужны .NET 9 SDK и Python 3.12.

```bat
git clone https://github.com/scarrymany/tg-manager.git
cd tg-manager
build.bat
```

Результат - `dist\TG-Manager\` с `TGManager.exe` и `TGWorker.exe`.
Для разработки: `dotnet run --project src\TGManager\TGManager.csproj`; воркер подхватится
как `python -m tgmanager.automation.worker`, если рядом нет `TGWorker.exe`
(`pip install -r requirements-worker.txt`).

| Папка | Что внутри |
|---|---|
| `src/TGManager` | WPF-приложение |
| `tgmanager/automation` | Python-воркер чистки и экспорта |
| `tests/` | проверки `Store`, офскрин-рендер WPF, тесты воркера |
| `docs/showcase` | генератор скриншотов и GIF для README |
| `worker.spec`, `worker_entry.py` | сборка `TGWorker.exe` |

CI (GitHub Actions, `windows-latest`) прогоняет проверки, собирает zip и публикует релиз `v<версия>`
при каждом пуше в `main`; версия берётся из `TGManager.csproj`.

Скриншоты и GIF для README пересобираются одной командой (нужен `ffmpeg` в PATH, окна на экран не выводятся):

```bat
dotnet run --project docs\showcase -c Release
```

## Требования

- Windows 10 x64 (1809+) или Windows 11 x64.
- Больше ничего: .NET и Python уже внутри exe.

## Если что-то не так

| Симптом | Что делать |
|---|---|
| «Не найден Telegram» | Настройки → **Скачать переносной Telegram** |
| Прокси не применился | Настройки → **Скачать прокси-обёртку** |
| Аккаунт не запускается | В папке контейнера должна быть именно `tdata`, а не `tdata\tdata` |
| Чистка не стартует | `TGWorker.exe` должен лежать рядом с `TGManager.exe` из того же zip |
| Telegram не остановился | Закройте его из трея (Quit Telegram) - это редкий случай зависшего процесса |
| Что-то упало | Рядом с программой появится `error.log` - приложите его к [issue](https://github.com/scarrymany/tg-manager/issues) |

## Автор

Разработчик - [@yeet17](https://t.me/yeet17) в Telegram · [scarrymany](https://github.com/scarrymany) на GitHub.
Кнопки GitHub и Telegram есть прямо в боковой панели программы.

История изменений - в [CHANGELOG.md](CHANGELOG.md). Лицензия - [MIT](LICENSE).

Старая Linux-версия (PyQt) сохранена в релизе
[`linux-legacy`](https://github.com/scarrymany/tg-manager/releases/tag/linux-legacy) и не поддерживается.
