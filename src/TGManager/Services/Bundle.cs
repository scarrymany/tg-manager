using System.IO;
using System.IO.Compression;
using System.Net.Http;

namespace TGManager.Services;

public readonly record struct DownloadProgress(long Read, long Total)
{
    public double Fraction => Total > 0 ? Math.Clamp((double)Read / Total, 0, 1) : 0;
}

public static class Bundle
{
    public const string TelegramUrl = "https://telegram.org/dl/desktop/win64_portable";
    public const string ProxychainsUrl =
        "https://github.com/shunf4/proxychains-windows/releases/download/0.6.8/proxychains_0.6.8_win32_x64.zip";

    static readonly HttpClient Http = new()
    {
        // Таймаут — только на заголовки; тело качаем потоком и отменяем через CancellationToken.
        Timeout = TimeSpan.FromSeconds(60),
        DefaultRequestHeaders = { { "User-Agent", "TGManager/1.2 (+https://github.com/scarrymany/tg-manager)" } },
    };

    public static bool TelegramReady() => File.Exists(Paths.TelegramExe);
    public static bool ProxychainsReady() => File.Exists(Paths.ProxychainsExe);

    public static async Task DownloadTelegram(Action<string> log, Action<DownloadProgress>? progress = null, CancellationToken ct = default)
    {
        Paths.EnsureDirs();
        Directory.CreateDirectory(Paths.TelegramDir);
        var tmp = Path.Combine(Path.GetTempPath(), "tgman-" + Guid.NewGuid().ToString("N")[..8]);
        Directory.CreateDirectory(tmp);
        try
        {
            var zip = Path.Combine(tmp, "telegram.zip");
            log("Скачиваю официальный Telegram Desktop (win64 portable)…");
            await Download(TelegramUrl, zip, log, "Telegram", progress, ct);
            log("Распаковываю…");
            var extract = Path.Combine(tmp, "extract");
            await Task.Run(() => ZipFile.ExtractToDirectory(zip, extract, overwriteFiles: true), ct);
            var exe = FindFile(extract, "Telegram.exe");
            if (exe is null) throw new InvalidOperationException("В архиве не найден Telegram.exe");
            var srcDir = Path.GetDirectoryName(exe)!;
            await Task.Run(() =>
            {
                foreach (var item in Directory.GetFileSystemEntries(srcDir))
                {
                    var dest = Path.Combine(Paths.TelegramDir, Path.GetFileName(item));
                    if (Directory.Exists(item))
                    {
                        if (Directory.Exists(dest)) Directory.Delete(dest, true);
                        CopyDir(item, dest);
                    }
                    else File.Copy(item, dest, true);
                }
                if (!File.Exists(Paths.TelegramExe))
                    File.Copy(exe, Paths.TelegramExe, true);
            }, ct);
            log("✓ Готово: " + Paths.TelegramExe);
        }
        finally
        {
            try { Directory.Delete(tmp, true); } catch { /* ignore */ }
        }
    }

    public static async Task DownloadProxychains(Action<string> log, Action<DownloadProgress>? progress = null, CancellationToken ct = default)
    {
        Paths.EnsureDirs();
        Directory.CreateDirectory(Paths.ProxychainsDir);
        var tmp = Path.Combine(Path.GetTempPath(), "tgman-pc-" + Guid.NewGuid().ToString("N")[..8]);
        Directory.CreateDirectory(tmp);
        try
        {
            var zip = Path.Combine(tmp, "pc.zip");
            log("Скачиваю прокси-обёртку для Windows (ProxyChains)…");
            await Download(ProxychainsUrl, zip, log, "ProxyChains", progress, ct);
            log("Распаковываю…");
            await Task.Run(() => ZipFile.ExtractToDirectory(zip, Paths.ProxychainsDir, overwriteFiles: true), ct);
            if (!File.Exists(Paths.ProxychainsExe))
            {
                var found = FindFile(Paths.ProxychainsDir, "proxychains_win32_x64.exe")
                            ?? FindFile(Paths.ProxychainsDir, "proxychains.exe");
                if (found is null) throw new InvalidOperationException("В архиве не найден proxychains_win32_x64.exe");
                File.Copy(found, Paths.ProxychainsExe, true);
            }
            log("✓ Готово: " + Paths.ProxychainsExe);
        }
        finally
        {
            try { Directory.Delete(tmp, true); } catch { /* ignore */ }
        }
    }

    static async Task Download(string url, string dest, Action<string> log, string label,
        Action<DownloadProgress>? progress, CancellationToken ct)
    {
        using var resp = await Http.GetAsync(url, HttpCompletionOption.ResponseHeadersRead, ct);
        resp.EnsureSuccessStatusCode();
        var total = resp.Content.Headers.ContentLength ?? 0;
        await using var input = await resp.Content.ReadAsStreamAsync(ct);
        await using var output = File.Create(dest);
        var buf = new byte[256 * 1024];
        long read = 0;
        var lastPct = -1;
        var lastLogKb = -1L;
        while (true)
        {
            var n = await input.ReadAsync(buf, ct);
            if (n == 0) break;
            await output.WriteAsync(buf.AsMemory(0, n), ct);
            read += n;
            progress?.Invoke(new DownloadProgress(read, total));
            if (total > 0)
            {
                var pct = (int)(read * 100 / total);
                if (pct / 10 != lastPct / 10 || pct == 100)
                {
                    lastPct = pct;
                    log($"↓ {label}: {pct}% ({read / (1024 * 1024)} / {total / (1024 * 1024)} МБ)");
                }
            }
            else
            {
                var kb = read / 1024;
                if (kb / 2048 != lastLogKb / 2048)
                {
                    lastLogKb = kb;
                    log($"↓ {label}: {kb} КБ");
                }
            }
        }
        if (total > 0 && read < total)
            throw new IOException($"Скачано {read} из {total} байт — соединение оборвалось.");
    }

    static string? FindFile(string root, string name)
    {
        foreach (var f in Directory.EnumerateFiles(root, name, SearchOption.AllDirectories))
            return f;
        return null;
    }

    static void CopyDir(string src, string dest)
    {
        Directory.CreateDirectory(dest);
        foreach (var file in Directory.GetFiles(src))
            File.Copy(file, Path.Combine(dest, Path.GetFileName(file)), true);
        foreach (var dir in Directory.GetDirectories(src))
            CopyDir(dir, Path.Combine(dest, Path.GetFileName(dir)));
    }
}
