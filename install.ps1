<#
.SYNOPSIS
    TG Manager — установка / обновление с последнего GitHub Release.

.DESCRIPTION
    Скачивает latest non-prerelease asset TG-Manager-*.zip (предпочтительно
    TG-Manager-x.y.z.zip) из scarrymany/tg-manager и кладёт готовую папку
    на рабочий стол:  <Desktop>\TG-Manager\TGManager.exe (+ TGWorker.exe).

    Desktop резолвится через Known Folder (OneDrive Desktop тоже).
    Админские права не нужны. Только встроенные PowerShell 5.1+ / .NET.

    Обновление: exe и прочие файлы из zip заменяются; существующие
    config.json, accounts\, telegram\, tools\ не трогаются.

.PARAMETER InstallDir
    Папка установки. По умолчанию <Desktop>\TG-Manager.
    Либо env TGMANAGER_INSTALL_DIR.

.PARAMETER Force
    Если TGManager.exe / TGWorker.exe заняты — закрыть процессы из
    папки установки и перезаписать. Данные пользователя всё равно
    сохраняются. Либо env TGMANAGER_FORCE=1.

.PARAMETER NoShortcut
    Не создавать ярлык «TG Manager» на рабочем столе.
    Либо env TGMANAGER_NO_SHORTCUT=1.

.PARAMETER Repo
    owner/name для GitHub Releases API. По умолчанию scarrymany/tg-manager.

.PARAMETER LocalZip
    Готовый TG-Manager-*.zip (без GitHub). Для офлайна / повтора.

.EXAMPLE
    irm https://raw.githubusercontent.com/scarrymany/tg-manager/main/install.ps1 | iex

.EXAMPLE
    iwr https://raw.githubusercontent.com/scarrymany/tg-manager/main/install.ps1 | iex

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File install.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File install.ps1 -InstallDir "D:\Apps\TG-Manager" -Force -NoShortcut

.EXAMPLE
    $env:TGMANAGER_INSTALL_DIR = "D:\Apps\TG-Manager"
    irm https://raw.githubusercontent.com/scarrymany/tg-manager/main/install.ps1 | iex

.NOTES
    irm|iex не прокидывает ключи — для -Force/-InstallDir либо -File,
    либо env: TGMANAGER_INSTALL_DIR / TGMANAGER_FORCE=1 / TGMANAGER_NO_SHORTCUT=1.
#>

# PS 5.1 + irm|iex: param() на верхнем уровне ломает Invoke-Expression,
# поэтому всё в scriptblock, ключи приходят через @args / -File.

& {
    [CmdletBinding()]
    param(
        [string]$InstallDir = '',
        [switch]$Force,
        [switch]$NoShortcut,
        [string]$Repo = 'scarrymany/tg-manager',
        [string]$LocalZip = '',
        [switch]$Help
    )

    Set-StrictMode -Version 1
    $ErrorActionPreference = 'Stop'
    $script:IsFileInvocation = -not [string]::IsNullOrWhiteSpace($PSCommandPath)

    function Write-Info([string]$Message) {
        Write-Host $Message -ForegroundColor Cyan
    }
    function Write-Ok([string]$Message) {
        Write-Host $Message -ForegroundColor Green
    }
    function Write-WarnLine([string]$Message) {
        Write-Host $Message -ForegroundColor Yellow
    }
    function Fail {
        param([string]$Message, [object]$Exception)
        $detail = $Message
        if ($Exception) {
            $inner = $Exception
            if ($Exception.Exception) { $inner = $Exception.Exception }
            if ($inner.Message -and $inner.Message -ne $Message) {
                $detail = "$Message`n  $($inner.Message)"
            }
            if ($inner.Response -and $inner.Response.StatusCode) {
                $code = [int]$inner.Response.StatusCode
                $detail = "$detail`n  HTTP $code"
            }
        }
        Write-Host ""
        Write-Host "ОШИБКА: $detail" -ForegroundColor Red
        Write-Host "Установка прервана." -ForegroundColor Red
        if ($script:IsFileInvocation) { exit 1 }
        throw $Message
    }

    function Test-EnvFlag([string]$Value) {
        return $Value -match '^(1|true|yes|on)$'
    }

    function Enable-Tls12 {
        try {
            $tls = [Net.ServicePointManager]::SecurityProtocol
            $tls = $tls -bor [Net.SecurityProtocolType]::Tls12
            try { $tls = $tls -bor [Net.SecurityProtocolType]::Tls13 } catch { }
            [Net.ServicePointManager]::SecurityProtocol = $tls
        } catch {
            Write-WarnLine "Не удалось явно включить TLS 1.2: $($_.Exception.Message)"
        }
    }

    function Get-DesktopPath {
        $candidates = New-Object System.Collections.Generic.List[string]

        foreach ($folder in @(
                [Environment+SpecialFolder]::DesktopDirectory,
                [Environment+SpecialFolder]::Desktop
            )) {
            try {
                $p = [Environment]::GetFolderPath($folder)
                if ($p) { [void]$candidates.Add($p) }
            } catch { }
        }

        try {
            $reg = Get-ItemProperty -LiteralPath 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders' -ErrorAction Stop
            if ($reg.Desktop) {
                [void]$candidates.Add([Environment]::ExpandEnvironmentVariables([string]$reg.Desktop))
            }
        } catch { }

        try {
            $reg2 = Get-ItemProperty -LiteralPath 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders' -ErrorAction Stop
            if ($reg2.Desktop) { [void]$candidates.Add([string]$reg2.Desktop) }
        } catch { }

        foreach ($root in @($env:OneDrive, $env:OneDriveCommercial, $env:OneDriveConsumer)) {
            if ($root) { [void]$candidates.Add((Join-Path $root 'Desktop')) }
        }

        if ($env:USERPROFILE) {
            [void]$candidates.Add((Join-Path $env:USERPROFILE 'Desktop'))
        }
        if ($env:HOME) {
            [void]$candidates.Add((Join-Path $env:HOME 'Desktop'))
        }

        $seen = @{}
        foreach ($raw in $candidates) {
            if ([string]::IsNullOrWhiteSpace($raw)) { continue }
            try { $full = [IO.Path]::GetFullPath($raw) } catch { continue }
            $key = $full.ToLowerInvariant()
            if ($seen.ContainsKey($key)) { continue }
            $seen[$key] = $true
            if (Test-Path -LiteralPath $full -PathType Container) { return $full }
        }

        throw "Не удалось определить папку рабочего стола (в т.ч. OneDrive Desktop). Укажите -InstallDir."
    }

    function Resolve-InstallDir([string]$Requested) {
        if ([string]::IsNullOrWhiteSpace($Requested)) {
            return Join-Path (Get-DesktopPath) 'TG-Manager'
        }
        $path = $Requested.Trim().Trim('"')
        if (-not [IO.Path]::IsPathRooted($path)) {
            $path = Join-Path (Get-Location).Path $path
        }
        return [IO.Path]::GetFullPath($path)
    }

    function ConvertTo-SizeText([long]$Bytes) {
        if ($Bytes -ge 1MB) { return ('{0:N1} МБ' -f ($Bytes / 1MB)) }
        if ($Bytes -ge 1KB) { return ('{0:N0} КБ' -f ($Bytes / 1KB)) }
        return "$Bytes байт"
    }

    function Select-PortableZip {
        param($Assets)
        if (-not $Assets) {
            throw "У релиза нет assets."
        }
        $list = @($Assets)
        $zips = @($list | Where-Object { $_.name -match '^TG-Manager-.*\.zip$' })
        if ($zips.Count -eq 0) {
            $names = ($list | ForEach-Object { $_.name }) -join ', '
            throw "Нет asset TG-Manager-*.zip в последнем релизе. Есть: $names"
        }
        $semver = @($zips | Where-Object { $_.name -match '^TG-Manager-\d+\.\d+\.\d+\.zip$' })
        $pool = $zips
        if ($semver.Count -gt 0) { $pool = $semver }
        $sorted = @($pool | Sort-Object {
                if ($_.name -match 'TG-Manager-(\d+\.\d+\.\d+)') { [version]$Matches[1] } else { [version]'0.0.0' }
            } -Descending)
        return $sorted[0]
    }

    function Get-LatestReleaseZip {
        param([string]$RepoName)

        if ($RepoName -notmatch '^[^/\s]+/[^/\s]+$') {
            throw "Некорректный -Repo '$RepoName'. Ожидается owner/name."
        }

        $api = "https://api.github.com/repos/$RepoName/releases/latest"
        $headers = @{
            'User-Agent' = 'TG-Manager-Installer'
            'Accept'     = 'application/vnd.github+json'
        }
        if ($env:GITHUB_TOKEN) { $headers['Authorization'] = "Bearer $($env:GITHUB_TOKEN)" }
        elseif ($env:GH_TOKEN) { $headers['Authorization'] = "Bearer $($env:GH_TOKEN)" }

        Write-Host "  GET $api"
        try {
            $release = Invoke-RestMethod -Uri $api -Headers $headers -TimeoutSec 60
        } catch {
            $resp = $_.Exception.Response
            $code = $null
            if ($resp) { try { $code = [int]$resp.StatusCode } catch { } }
            if ($code -eq 404) {
                throw "Релиз не найден (HTTP 404). Проверьте https://github.com/$RepoName/releases"
            }
            if ($code -eq 403) {
                throw "GitHub API отказал (HTTP 403, лимит?). Повторите позже или задайте GITHUB_TOKEN."
            }
            if ($code) {
                throw "GitHub API: HTTP $code ($api)"
            }
            throw "Сеть / GitHub API: $($_.Exception.Message)`n  $api"
        }

        if (-not $release -or -not $release.tag_name) {
            throw "Пустой ответ GitHub Releases API."
        }
        if ($release.prerelease) {
            throw "releases/latest вернул prerelease '$($release.tag_name)' — такого быть не должно."
        }

        $asset = Select-PortableZip -Assets $release.assets
        if (-not $asset.browser_download_url) {
            throw "У $($asset.name) нет browser_download_url."
        }

        return [pscustomobject]@{
            Tag      = [string]$release.tag_name
            Name     = [string]$release.name
            Asset    = [string]$asset.name
            Url      = [string]$asset.browser_download_url
            Size     = [long]$(if ($asset.size) { $asset.size } else { 0 })
        }
    }

    function Get-RemoteFile {
        param(
            [string]$Url,
            [string]$OutFile,
            [long]$ExpectedSize
        )

        $headers = @{ 'User-Agent' = 'TG-Manager-Installer' }
        if ($env:GITHUB_TOKEN) { $headers['Authorization'] = "Bearer $($env:GITHUB_TOKEN)" }
        elseif ($env:GH_TOKEN) { $headers['Authorization'] = "Bearer $($env:GH_TOKEN)" }

        try {
            # WebClient: без лимита 100 с как у IWR, редиректы GitHub, системный прокси.
            $wc = New-Object System.Net.WebClient
            foreach ($k in $headers.Keys) { $wc.Headers[$k] = $headers[$k] }
            try {
                $wc.DownloadFile($Url, $OutFile)
            } finally {
                $wc.Dispose()
            }
        } catch {
            $code = $null
            if ($_.Exception.InnerException -and $_.Exception.InnerException.Response) {
                try { $code = [int]$_.Exception.InnerException.Response.StatusCode } catch { }
            }
            if ($_.Exception.Response) {
                try { $code = [int]$_.Exception.Response.StatusCode } catch { }
            }
            if ($code -eq 404) {
                throw "Файл релиза не найден (HTTP 404): $Url"
            }
            throw "Не удалось скачать zip: $($_.Exception.Message)`n  $Url"
        }

        if (-not (Test-Path -LiteralPath $OutFile -PathType Leaf)) {
            throw "После загрузки нет файла: $OutFile"
        }
        $len = (Get-Item -LiteralPath $OutFile).Length
        if ($len -lt 64) {
            throw "Скачанный файл слишком маленький ($len байт) — не zip."
        }
        if ($ExpectedSize -gt 0 -and $len -ne $ExpectedSize) {
            throw "Размер zip не совпал: скачано $len байт, в релизе $ExpectedSize."
        }
        $fs = [IO.File]::OpenRead($OutFile)
        try {
            $b0 = $fs.ReadByte(); $b1 = $fs.ReadByte()
            if ($b0 -ne 0x50 -or $b1 -ne 0x4B) {
                throw "Это не zip (нет сигнатуры PK). Проверьте URL / прокси."
            }
        } finally { $fs.Dispose() }
    }

    function Expand-ReleaseZip {
        param([string]$ZipPath, [string]$DestDir)
        New-Item -ItemType Directory -Force -Path $DestDir | Out-Null
        try {
            Add-Type -AssemblyName System.IO.Compression.FileSystem
            [System.IO.Compression.ZipFile]::ExtractToDirectory($ZipPath, $DestDir)
        } catch {
            throw "Не удалось распаковать архив: $($_.Exception.Message)"
        }
    }

    function Resolve-PayloadRoot {
        param([string]$ExtractDir)
        $exes = @(Get-ChildItem -LiteralPath $ExtractDir -Filter 'TGManager.exe' -Recurse -File -ErrorAction Stop)
        if ($exes.Count -eq 0) {
            throw "В архиве нет TGManager.exe — это не портативная сборка TG Manager."
        }
        $withWorker = @($exes | Where-Object {
                Test-Path -LiteralPath (Join-Path $_.Directory.FullName 'TGWorker.exe')
            })
        if ($withWorker.Count -gt 0) { $exes = $withWorker }
        $pick = $exes | Sort-Object { $_.FullName.Length } | Select-Object -First 1
        return $pick.Directory.FullName
    }

    function Test-PreservedName {
        param([string]$Name)
        $n = $Name.ToLowerInvariant()
        $files = @('config.json', 'config.json.tmp', 'error.log')
        $dirs = @('accounts', 'telegram', 'tools')
        return ($files -contains $n) -or ($dirs -contains $n) -or ($n -like 'config.broken-*.json')
    }

    function Stop-LockedInstallProcesses {
        param([string]$Dir)
        $root = [IO.Path]::GetFullPath($Dir).TrimEnd('\', '/')
        $killed = 0
        $procs = @(Get-Process -ErrorAction SilentlyContinue | Where-Object {
                $_.Name -match '^(TGManager|TGWorker)$'
            })
        foreach ($p in $procs) {
            $ppath = $null
            try { $ppath = $p.Path } catch { }
            if (-not $ppath) { continue }
            try {
                $full = [IO.Path]::GetFullPath($ppath)
            } catch { continue }
            if ($full.StartsWith($root, [StringComparison]::OrdinalIgnoreCase)) {
                Write-WarnLine "  закрываю $($p.Name) PID $($p.Id)"
                Stop-Process -Id $p.Id -Force -ErrorAction Stop
                $killed++
            }
        }
        if ($killed -gt 0) { Start-Sleep -Seconds 1 }
        return $killed
    }

    function Copy-PayloadToInstall {
        param(
            [string]$PayloadRoot,
            [string]$DestDir,
            [switch]$CanKill
        )

        if (-not (Test-Path -LiteralPath $DestDir -PathType Container)) {
            New-Item -ItemType Directory -Force -Path $DestDir -ErrorAction Stop | Out-Null
        }

        $items = @(Get-ChildItem -LiteralPath $PayloadRoot -Force)
        if ($items.Count -eq 0) {
            throw "Папка сборки в zip пуста: $PayloadRoot"
        }

        $copied = 0
        $kept = 0
        foreach ($item in $items) {
            $dest = Join-Path $DestDir $item.Name
            if ((Test-Path -LiteralPath $dest) -and (Test-PreservedName $item.Name)) {
                Write-Host "  сохранено  $($item.Name)"
                $kept++
                continue
            }

            $attempt = {
                Copy-Item -LiteralPath $item.FullName -Destination $dest -Recurse -Force -ErrorAction Stop
            }

            try {
                & $attempt
            } catch {
                if (-not $CanKill) {
                    throw "Не удалось записать '$($item.Name)' (файл занят?). Закройте TG Manager или повторите с -Force.`n  $($_.Exception.Message)"
                }
                Write-WarnLine "  файл занят ($($item.Name)) — пробую закрыть процессы…"
                [void](Stop-LockedInstallProcesses -Dir $DestDir)
                try {
                    & $attempt
                } catch {
                    throw "Нет прав или файл всё ещё занят: $($item.Name)`n  $($_.Exception.Message)"
                }
            }
            Write-Host "  обновлено  $($item.Name)"
            $copied++
        }

        $exe = Join-Path $DestDir 'TGManager.exe'
        $worker = Join-Path $DestDir 'TGWorker.exe'
        if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) {
            throw "После копирования нет TGManager.exe в $DestDir"
        }
        if (-not (Test-Path -LiteralPath $worker -PathType Leaf)) {
            Write-WarnLine "  нет TGWorker.exe рядом — чистка/експорт не заработают."
        }
        return [pscustomobject]@{ Copied = $copied; Kept = $kept }
    }

    function New-DesktopShortcut {
        param([string]$TargetExe, [string]$WorkDir)
        $desktop = $null
        try { $desktop = Get-DesktopPath } catch { }
        if (-not $desktop) {
            throw "Рабочий стол не найден — ярлык не создан."
        }
        $lnk = Join-Path $desktop 'TG Manager.lnk'
        $type = [Type]::GetTypeFromProgID('WScript.Shell')
        if (-not $type) { throw "WScript.Shell недоступен." }
        $shell = [Activator]::CreateInstance($type)
        $s = $shell.CreateShortcut($lnk)
        $s.TargetPath = $TargetExe
        $s.WorkingDirectory = $WorkDir
        $s.WindowStyle = 1
        $s.Description = 'TG Manager'
        $s.IconLocation = "$TargetExe,0"
        $s.Save()
        return $lnk
    }

    if ($Help) {
        Write-Host @"
TG Manager installer  (PowerShell 5.1+, без админа)

  irm https://raw.githubusercontent.com/scarrymany/tg-manager/main/install.ps1 | iex
  iwr https://raw.githubusercontent.com/scarrymany/tg-manager/main/install.ps1 | iex

  powershell -ExecutionPolicy Bypass -File install.ps1
  powershell -ExecutionPolicy Bypass -File install.ps1 -InstallDir D:\TG-Manager -Force -NoShortcut

Ключи:
  -InstallDir <path>  папка (по умолчанию <Desktop>\TG-Manager, в т.ч. OneDrive)
  -Force              закрыть занятые TGManager/TGWorker из этой папки и перезаписать exe
  -NoShortcut         не создавать ярлык «TG Manager.lnk» на рабочем столе
  -Repo owner/name    другой GitHub репозиторий (по умолчанию scarrymany/tg-manager)
  -LocalZip <zip>     готовый архив, без GitHub API
  -Help               этот текст

Env (для one-liner): TGMANAGER_INSTALL_DIR, TGMANAGER_FORCE=1, TGMANAGER_NO_SHORTCUT=1, TGMANAGER_REPO, TGMANAGER_LOCAL_ZIP

Обновление на месте: config.json, accounts\, telegram\, tools\ не затираются.
"@
        return
    }

    # --- env fallbacks for irm | iex ---
    if ([string]::IsNullOrWhiteSpace($InstallDir) -and $env:TGMANAGER_INSTALL_DIR) {
        $InstallDir = $env:TGMANAGER_INSTALL_DIR
    }
    if (-not $Force -and (Test-EnvFlag $env:TGMANAGER_FORCE)) { $Force = $true }
    if (-not $NoShortcut -and (Test-EnvFlag $env:TGMANAGER_NO_SHORTCUT)) { $NoShortcut = $true }
    if ($env:TGMANAGER_REPO) { $Repo = $env:TGMANAGER_REPO }
    if ([string]::IsNullOrWhiteSpace($LocalZip) -and $env:TGMANAGER_LOCAL_ZIP) {
        $LocalZip = $env:TGMANAGER_LOCAL_ZIP
    }

    Enable-Tls12

    $work = $null
    try {
        Write-Host ""
        Write-Host "TG Manager — установка с GitHub Releases" -ForegroundColor White
        Write-Host ""

        try {
            $target = Resolve-InstallDir $InstallDir
        } catch {
            Fail -Message $_.Exception.Message -Exception $_
        }

        $existed = Test-Path -LiteralPath $target -PathType Container
        Write-Info "[1/4] Папка   $target"
        if ($existed) {
            Write-Host "  уже есть — обновление на месте (config.json / accounts не затираются)"
        } else {
            try {
                New-Item -ItemType Directory -Force -Path $target -ErrorAction Stop | Out-Null
            } catch {
                Fail -Message "Нет прав создать папку: $target" -Exception $_
            }
        }

        $work = Join-Path ([IO.Path]::GetTempPath()) ("TG-Manager-install-" + [guid]::NewGuid().ToString('N'))
        $extractDir = Join-Path $work 'extract'
        try {
            New-Item -ItemType Directory -Force -Path $work -ErrorAction Stop | Out-Null
        } catch {
            Fail -Message "Не удалось создать TEMP: $work" -Exception $_
        }

        $zipPath = $null
        if (-not [string]::IsNullOrWhiteSpace($LocalZip)) {
            $zipPath = $LocalZip.Trim().Trim('"')
            if (-not [IO.Path]::IsPathRooted($zipPath)) {
                $zipPath = Join-Path (Get-Location).Path $zipPath
            }
            $zipPath = [IO.Path]::GetFullPath($zipPath)
            if (-not (Test-Path -LiteralPath $zipPath -PathType Leaf)) {
                Fail -Message "LocalZip не найден: $zipPath"
            }
            $rel = [pscustomobject]@{
                Tag   = 'local'
                Name  = 'local zip'
                Asset = [IO.Path]::GetFileName($zipPath)
                Url   = $zipPath
                Size  = [long](Get-Item -LiteralPath $zipPath).Length
            }
            Write-Info "[2/4] Локальный zip (без GitHub)"
            Write-Host "  $($rel.Asset)  ($(ConvertTo-SizeText $rel.Size))"
            Write-Host "  $zipPath"
        } else {
            Write-Info "[2/4] Релиз  GitHub $Repo"
            try {
                $rel = Get-LatestReleaseZip -RepoName $Repo
            } catch {
                Fail -Message $_.Exception.Message -Exception $_
            }
            $sizeText = if ($rel.Size -gt 0) { ConvertTo-SizeText $rel.Size } else { '?' }
            Write-Host "  $($rel.Tag)  $($rel.Asset)  ($sizeText)"
            $zipPath = Join-Path $work $rel.Asset
            Write-Info "[3/4] Скачиваю $($rel.Url)"
            try {
                Get-RemoteFile -Url $rel.Url -OutFile $zipPath -ExpectedSize $rel.Size
            } catch {
                Fail -Message $_.Exception.Message -Exception $_
            }
            Write-Host "  ок  $(ConvertTo-SizeText ((Get-Item -LiteralPath $zipPath).Length))"
        }

        Write-Info "[4/4] Распаковка и копирование"
        try {
            Expand-ReleaseZip -ZipPath $zipPath -DestDir $extractDir
            $payload = Resolve-PayloadRoot -ExtractDir $extractDir
            Write-Host "  payload  $payload"
            [void](Copy-PayloadToInstall -PayloadRoot $payload -DestDir $target -CanKill:$Force)
        } catch {
            Fail -Message $_.Exception.Message -Exception $_
        }

        $exe = Join-Path $target 'TGManager.exe'
        $lnk = $null
        if (-not $NoShortcut) {
            try {
                $lnk = New-DesktopShortcut -TargetExe $exe -WorkDir $target
                Write-Host "  ярлык   $lnk"
            } catch {
                Write-WarnLine "  ярлык не создан: $($_.Exception.Message)"
            }
        }

        Write-Host ""
        Write-Ok "============================================================"
        Write-Ok "  TG Manager готов"
        Write-Ok "  Релиз:    $($rel.Tag)"
        Write-Ok "  Папка:    $target"
        Write-Ok "  Запуск:   $exe"
        if ($lnk) { Write-Ok "  Ярлык:    $lnk" }
        Write-Ok "============================================================"
        Write-Host ""
        Write-Host "Запустите TGManager.exe (двойной щелчок или ярлык «TG Manager»)."
        Write-Host "TGWorker.exe должен лежать рядом — не удаляйте."
        Write-Host "При обновлении сохранены: config.json, accounts\, telegram\, tools\."
        Write-Host ""
    } finally {
        if ($work -and (Test-Path -LiteralPath $work)) {
            Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
} @args
