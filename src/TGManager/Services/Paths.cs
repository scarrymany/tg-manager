using System.IO;

namespace TGManager.Services;

public static class Paths
{
    public static string AppRoot { get; }

    static Paths()
    {
        var exe = Environment.ProcessPath;
        if (!string.IsNullOrEmpty(exe))
            AppRoot = Path.GetDirectoryName(Path.GetFullPath(exe)) ?? AppContext.BaseDirectory;
        else
            AppRoot = Path.GetFullPath(AppContext.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar));
        try { Directory.SetCurrentDirectory(AppRoot); } catch { /* ignore */ }
    }

    public static string ConfigFile => Path.Combine(AppRoot, "config.json");
    public static string AccountsDir => Path.Combine(AppRoot, "accounts");
    public static string TelegramDir => Path.Combine(AppRoot, "telegram");
    public static string TelegramExe => Path.Combine(TelegramDir, "Telegram.exe");
    public static string ToolsDir => Path.Combine(AppRoot, "tools");
    public static string ProxychainsDir => Path.Combine(ToolsDir, "proxychains");
    public static string ProxychainsExe => Path.Combine(ProxychainsDir, "proxychains_win32_x64.exe");
    public static string WorkerExe => Path.Combine(AppRoot, "TGWorker.exe");

    /// <summary>
    /// id — только имя папки внутри accounts\. Иначе config.json может увести
    /// работу/удаление на произвольный путь (C:\…, ..\…).
    /// </summary>
    static readonly HashSet<string> ReservedNames = new(StringComparer.OrdinalIgnoreCase)
    {
        "CON", "PRN", "AUX", "NUL",
        "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
        "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
    };

    public static bool IsSafeAccountId(string? id)
    {
        if (string.IsNullOrWhiteSpace(id)) return false;
        if (id.IndexOfAny(Path.GetInvalidFileNameChars()) >= 0) return false;
        if (id.Contains('/') || id.Contains('\\') || id.Contains("..")) return false;
        if (id is "." or "..") return false;
        if (Path.IsPathRooted(id)) return false;
        var stem = id.Split('.')[0];
        if (ReservedNames.Contains(id) || ReservedNames.Contains(stem)) return false;
        return true;
    }

    public static string AccountWorkdir(string id)
    {
        if (!IsSafeAccountId(id))
            throw new ArgumentException("Некорректный id контейнера.", nameof(id));
        var path = Path.GetFullPath(Path.Combine(AccountsDir, id));
        var root = Path.GetFullPath(AccountsDir);
        var prefix = root.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar)
                     + Path.DirectorySeparatorChar;
        if (!path.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException("id контейнера выходит за accounts\\.");
        return path;
    }

    public static string AccountTdata(string id) => Path.Combine(AccountWorkdir(id), "tdata");

    public static void EnsureDirs()
    {
        Directory.CreateDirectory(AppRoot);
        Directory.CreateDirectory(AccountsDir);
    }
}
