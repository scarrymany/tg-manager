using System.Diagnostics;
using System.IO;

namespace TGManager.Services;

public sealed class LaunchPlan
{
    public List<string> Argv { get; set; } = [];
    public string Workdir { get; set; } = "";
    public string Telegram { get; set; } = "";
    public bool ProxyRequested { get; set; }
    public bool ProxyApplied { get; set; }
    public string? Error { get; set; }
    public string? Warning { get; set; }
    public ProxyCfg? HttpProxy { get; set; }
    public bool Ok => Error is null;
}

public static class Launcher
{
    public static string? ResolveTelegram(string configured)
    {
        if (!string.IsNullOrWhiteSpace(configured) && File.Exists(configured))
            return configured;
        if (File.Exists(Paths.TelegramExe))
            return Paths.TelegramExe;
        return null;
    }

    public static string? ResolveProxychains(string configured)
    {
        if (!string.IsNullOrWhiteSpace(configured) && File.Exists(configured))
            return configured;
        if (File.Exists(Paths.ProxychainsExe))
            return Paths.ProxychainsExe;
        return null;
    }

    public static LaunchPlan Build(Settings settings, Account account)
    {
        var workdir = Paths.AccountWorkdir(account.Id);
        Directory.CreateDirectory(workdir);
        var tg = ResolveTelegram(settings.TelegramBinary);
        if (tg is null)
        {
            return new LaunchPlan
            {
                Workdir = workdir,
                Error = "Переносной Telegram не установлен. Скачайте его в настройках.",
            };
        }

        var args = new List<string> { tg, "-workdir", workdir, "-noupdate" };
        if (settings.AllowMany) args.Add("-many");

        var plan = new LaunchPlan
        {
            Argv = args,
            Workdir = workdir,
            Telegram = tg,
            ProxyRequested = account.Proxy.Enabled,
        };
        if (!account.Proxy.Enabled)
            return plan;

        var pc = ResolveProxychains(settings.ProxychainsBinary);
        if (pc is null)
        {
            plan.Warning = "Прокси-обёртка не установлена — прокси не будет применён. Скачайте её в настройках.";
            return plan;
        }

        if (account.Proxy.Type == ProxyKinds.Http)
            plan.HttpProxy = account.Proxy;

        WriteProxychainsConf(account, workdir);
        plan.Argv = [pc, "-f", Path.Combine(workdir, "proxychains.conf"), .. args];
        plan.ProxyApplied = true;
        return plan;
    }

    public static void WriteProxychainsConf(Account account, string workdir, string? socksHost = null, int? socksPort = null)
    {
        string line;
        if (socksHost is not null && socksPort is not null)
            line = $"socks5 {socksHost} {socksPort}";
        else
            line = account.Proxy.ProxychainsLine();
        var body =
            "# Автогенерация TG Manager — не редактируйте вручную\n" +
            "strict_chain\nproxy_dns\nquiet_mode\nremote_dns_subnet 224\n" +
            "tcp_read_time_out 15000\ntcp_connect_time_out 8000\n\n[ProxyList]\n" +
            line + "\n";
        File.WriteAllText(Path.Combine(workdir, "proxychains.conf"), body);
    }

    public static int? Launch(LaunchPlan plan)
    {
        if (!plan.Ok || plan.Argv.Count == 0) return null;
        if (plan.HttpProxy is { } http)
        {
            var port = HttpBridge.Start(plan.Workdir, http);
            if (port is null) return null;
            WriteProxychainsConf(new Account { Proxy = http }, plan.Workdir, "127.0.0.1", port);
        }

        var file = plan.Argv[0];
        var psi = new ProcessStartInfo
        {
            FileName = file,
            WorkingDirectory = plan.Workdir,
            UseShellExecute = false,
            CreateNoWindow = Path.GetFileName(file).Contains("proxychains", StringComparison.OrdinalIgnoreCase),
        };
        foreach (var a in plan.Argv.Skip(1))
            psi.ArgumentList.Add(a);
        try
        {
            var p = Process.Start(psi);
            if (p is null) return null;
            ProcessUtil.WritePid(plan.Workdir, p.Id);
            return p.Id;
        }
        catch
        {
            return null;
        }
    }

    public static int Stop(string workdir)
    {
        HttpBridge.Stop(workdir);
        return ProcessUtil.Terminate(workdir);
    }

    public static bool IsRunning(string workdir) => ProcessUtil.IsRunning(workdir);
}
