using System.Diagnostics;
using System.IO;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace TGManager.Services;

public sealed class WorkerEvent
{
    [JsonPropertyName("type")] public string Type { get; set; } = "";
    [JsonPropertyName("msg")] public string? Msg { get; set; }
    [JsonPropertyName("label")] public string? Label { get; set; }
    [JsonPropertyName("error")] public string? Error { get; set; }
    [JsonPropertyName("cat")] public string? Cat { get; set; }
    [JsonPropertyName("done")] public int Done { get; set; }
    [JsonPropertyName("total")] public int Total { get; set; }
    [JsonPropertyName("seconds")] public int Seconds { get; set; }
    [JsonPropertyName("skipped")] public int Skipped { get; set; }
    [JsonPropertyName("dry_run")] public bool DryRun { get; set; }
    [JsonPropertyName("counts")] public Dictionary<string, int>? Counts { get; set; }
    [JsonPropertyName("contacts")] public bool Contacts { get; set; }
    [JsonPropertyName("photos")] public bool Photos { get; set; }
}

public sealed class WorkerHost : IDisposable
{
    Process? _proc;

    static readonly JsonSerializerOptions JsonOpt = new()
    {
        PropertyNameCaseInsensitive = true,
    };

    public event Action<WorkerEvent>? Event;
    public event Action<int>? Exited;
    public bool IsRunning => _proc is { HasExited: false };

    public bool Start(Account account, IEnumerable<string> actions, bool revoke, bool dryRun)
    {
        if (IsRunning) return false;
        var workdir = Paths.AccountWorkdir(account.Id);
        var args = new List<string> { "--workdir", workdir, "--actions", string.Join(",", actions) };
        if (revoke) args.Add("--revoke");
        if (dryRun) args.Add("--dry-run");
        if (account.Proxy.Enabled)
        {
            args.AddRange(["--proxy-type", account.Proxy.Type, "--proxy-host", account.Proxy.Host,
                           "--proxy-port", account.Proxy.Port.ToString()]);
            if (!string.IsNullOrEmpty(account.Proxy.Username))
                args.AddRange(["--proxy-user", account.Proxy.Username]);
            if (!string.IsNullOrEmpty(account.Proxy.Password))
                args.AddRange(["--proxy-pass", account.Proxy.Password]);
        }

        var psi = new ProcessStartInfo
        {
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true,
            StandardOutputEncoding = Encoding.UTF8,
            StandardErrorEncoding = Encoding.UTF8,
            WorkingDirectory = Paths.AppRoot,
        };
        psi.Environment["PYTHONIOENCODING"] = "utf-8";
        psi.Environment["PYTHONUTF8"] = "1";
        psi.Environment["PYTHONUNBUFFERED"] = "1";

        if (File.Exists(Paths.WorkerExe))
        {
            psi.FileName = Paths.WorkerExe;
        }
        else
        {
            var py = FindPython();
            if (py is null) return false;
            psi.FileName = py;
            if (py == "py") psi.ArgumentList.Add("-3");
            psi.ArgumentList.Add("-m");
            psi.ArgumentList.Add("tgmanager.automation.worker");
        }
        foreach (var a in args) psi.ArgumentList.Add(a);

        _proc = new Process { StartInfo = psi, EnableRaisingEvents = true };
        _proc.OutputDataReceived += (_, e) =>
        {
            if (string.IsNullOrEmpty(e.Data)) return;
            try
            {
                var ev = JsonSerializer.Deserialize<WorkerEvent>(e.Data, JsonOpt);
                if (ev is not null) Event?.Invoke(ev);
            }
            catch
            {
                Event?.Invoke(new WorkerEvent { Type = "log", Msg = e.Data });
            }
        };
        _proc.ErrorDataReceived += (_, e) =>
        {
            if (!string.IsNullOrEmpty(e.Data))
                Event?.Invoke(new WorkerEvent { Type = "log", Msg = e.Data });
        };
        _proc.Exited += (_, _) =>
        {
            var code = 1;
            try { code = _proc?.ExitCode ?? 1; } catch { /* ignore */ }
            Exited?.Invoke(code);
        };
        if (!_proc.Start()) return false;
        WriteLock(workdir, _proc.Id);
        _proc.BeginOutputReadLine();
        _proc.BeginErrorReadLine();
        return true;
    }

    public void Stop()
    {
        try { _proc?.Kill(entireProcessTree: true); } catch { /* ignore */ }
    }

    public void Dispose()
    {
        try { _proc?.Dispose(); } catch { /* ignore */ }
        _proc = null;
    }

    public static bool WorkerAvailable()
        => File.Exists(Paths.WorkerExe) || FindPython() is not null;

    static string? FindPython()
    {
        foreach (var name in new[] { "python", "py" })
        {
            try
            {
                var psi = new ProcessStartInfo
                {
                    FileName = name,
                    UseShellExecute = false,
                    RedirectStandardOutput = true,
                    CreateNoWindow = true,
                };
                if (name == "py") psi.ArgumentList.Add("-3");
                psi.ArgumentList.Add("-c");
                psi.ArgumentList.Add("print(1)");
                using var p = Process.Start(psi);
                if (p is null) continue;
                p.WaitForExit(3000);
                if (p.ExitCode == 0) return name;
            }
            catch { /* skip */ }
        }
        return null;
    }

    static void WriteLock(string workdir, int pid)
    {
        try
        {
            File.WriteAllText(Path.Combine(workdir, "automation.lock"),
                $"{{\"pid\":{pid},\"action\":\"cleanup\"}}");
        }
        catch { /* ignore */ }
    }

    public static void ClearLock(string workdir)
    {
        try { File.Delete(Path.Combine(workdir, "automation.lock")); } catch { /* ignore */ }
    }

    public static bool IsLocked(string workdir)
    {
        var path = Path.Combine(workdir, "automation.lock");
        if (!File.Exists(path)) return false;
        try
        {
            using var doc = JsonDocument.Parse(File.ReadAllText(path));
            var pid = doc.RootElement.TryGetProperty("pid", out var p) ? p.GetInt32() : 0;
            if (pid > 0 && !Native.NativeMethods.IsAlive(pid))
            {
                ClearLock(workdir);
                return false;
            }
            return true;
        }
        catch
        {
            return false;
        }
    }
}
