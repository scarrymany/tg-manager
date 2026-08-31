using System.IO;
using System.Reflection;

namespace TGManager.Services;

public static class Paths
{
    public static string AppRoot { get; }

    static Paths()
    {
        var exe = Environment.ProcessPath
                  ?? Assembly.GetExecutingAssembly().Location
                  ?? AppContext.BaseDirectory;
        AppRoot = Path.GetDirectoryName(Path.GetFullPath(exe)) ?? AppContext.BaseDirectory;
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

    public static string AccountWorkdir(string id) => Path.Combine(AccountsDir, id);
    public static string AccountTdata(string id) => Path.Combine(AccountWorkdir(id), "tdata");

    public static void EnsureDirs()
    {
        Directory.CreateDirectory(AppRoot);
        Directory.CreateDirectory(AccountsDir);
    }
}
