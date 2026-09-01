using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Runtime.CompilerServices;
using System.Windows.Media;
using TGManager.Services;

namespace TGManager.ViewModels;

public sealed class TaskVm : INotifyPropertyChanged
{
    static readonly Dictionary<string, string> ActionLabels = new()
    {
        ["channels"] = "каналы",
        ["groups"] = "группы",
        ["private"] = "личные",
        ["bots"] = "боты",
        ["saved"] = "избранное",
        ["contacts"] = "контакты",
        ["photos"] = "фото",
    };

    public TaskVm(Account account, IReadOnlyList<string> actions, bool revoke)
    {
        Account = account;
        Actions = actions;
        Revoke = revoke;
        Host = new WorkerHost();
        Host.Event += OnEvent;
        Host.Exited += OnExited;
    }

    public Account Account { get; }
    public IReadOnlyList<string> Actions { get; }
    public bool Revoke { get; }
    public WorkerHost Host { get; }
    public string Id => Account.Id;

    public ObservableCollection<string> Log { get; } = [];

    string _state = "running";
    int _done;
    int _total;
    string _current = "";
    string _error = "";

    public string State { get => _state; private set { if (_state == value) return; _state = value; RaiseState(); } }
    public int Done { get => _done; private set { _done = value; Raise(nameof(Done)); Raise(nameof(CountText)); Raise(nameof(ProgressValue)); } }
    public int Total { get => _total; private set { _total = value; Raise(nameof(Total)); Raise(nameof(CountText)); Raise(nameof(IsIndeterminate)); Raise(nameof(ProgressMax)); Raise(nameof(ProgressValue)); } }
    public string Current { get => _current; private set { _current = value; Raise(nameof(Current)); Raise(nameof(SubLabel)); } }
    public string Error { get => _error; private set { _error = value; Raise(nameof(Error)); } }

    public bool IsRunning => State == "running";
    public bool Finished => State is "done" or "error" or "stopped";
    public bool IsIndeterminate => IsRunning && Total <= 0;

    // ProgressBar.Value/Maximum биндятся TwoWay по умолчанию — сеттер обязателен, иначе каскад InvalidOperationException.
    public double ProgressMax
    {
        get => Math.Max(1, Total);
        set { /* ignore */ }
    }

    public double ProgressValue
    {
        get => Total <= 0 ? (Finished ? 1 : 0) : Done;
        set { /* ignore */ }
    }
    public string CountText
    {
        get
        {
            if (IsRunning && Total <= 0) return "…";
            if (Total <= 0) return "";
            var pct = (int)(Done * 100.0 / Total);
            return $"{Done}/{Total} · {pct}%";
        }
    }

    public string PillText => State switch
    {
        "running" => "● Идёт",
        "done" => "✓ Готово",
        "error" => "✗ Ошибка",
        "stopped" => "■ Остановлено",
        _ => "—",
    };

    public Brush PillFg => State is "running" or "done"
        ? (Brush)App.Current.FindResource("GreenBrush")
        : State == "error"
            ? (Brush)App.Current.FindResource("RedBrush")
            : (Brush)App.Current.FindResource("YellowBrush");

    public string ActionButtonText => IsRunning ? "Стоп" : "Убрать";
    public string Name => Account.Name;
    public string Color => Account.Color;
    public Brush ColorBrush
    {
        get
        {
            try { return new SolidColorBrush((Color)ColorConverter.ConvertFromString(Color)!); }
            catch { return Brushes.White; }
        }
    }

    public string ActionsHuman => string.Join(", ", Actions.Select(a => ActionLabels.GetValueOrDefault(a, a)));
    public string SubLabel => string.IsNullOrEmpty(Current) ? ActionsHuman : $"{ActionsHuman}  ·  {Current}";

    public bool Start() => Host.Start(Account, Actions, Revoke, dryRun: false);

    public void Stop()
    {
        State = "stopped";
        Current = "Остановлено";
        Host.Stop();
        // automation.lock снимается в OnExited, когда процесс реально мёртв.
        // Иначе можно запустить Telegram, пока Telethon ещё держит сессию.
    }

    public bool WaitStopped(int timeoutMs = 10_000) => Host.WaitForExit(timeoutMs);

    void OnEvent(WorkerEvent ev)
    {
        var apply = () => Apply(ev);
        var d = App.Current?.Dispatcher;
        if (d is null || d.CheckAccess()) apply();
        else d.BeginInvoke(apply);
    }

    void Apply(WorkerEvent ev)
    {
        switch (ev.Type)
        {
            case "stage":
                Current = ev.Msg ?? "";
                Append("• " + (ev.Msg ?? ""));
                break;
            case "summary":
                Total = ev.Total;
                var c = ev.Counts ?? [];
                Append($"Найдено: каналы {Get(c, "channels")}, группы {Get(c, "groups")}, " +
                       $"личные {Get(c, "private")}, боты {Get(c, "bots")}, " +
                       $"избранное {Get(c, "saved")} · всего {Total}");
                break;
            case "progress":
                Done = ev.Done;
                if (ev.Total > 0) Total = ev.Total;
                Current = ev.Label ?? "";
                Append($"[{ev.Cat}] {ev.Label}");
                break;
            case "flood":
                Current = $"Пауза Telegram: {ev.Seconds} c";
                Append($"⏳ FloodWait {ev.Seconds} c — ждём…");
                break;
            case "warn":
                Append($"! {ev.Label}: {ev.Error}");
                break;
            case "done":
                Current = ev.DryRun ? "Проверка завершена" : "Готово" + (ev.Skipped > 0 ? $" · пропущено {ev.Skipped}" : "");
                break;
            case "error":
                Error = ev.Error ?? "";
                Append("✗ " + Error);
                break;
            default:
                if (!string.IsNullOrEmpty(ev.Msg)) Append(ev.Msg);
                break;
        }
    }

    void OnExited(int code)
    {
        var apply = () =>
        {
            WorkerHost.ClearLock(Paths.AccountWorkdir(Account.Id));
            if (State == "stopped") { /* keep */ }
            else if (!string.IsNullOrEmpty(Error) || code != 0) State = "error";
            else State = "done";
            Host.Dispose();
        };
        var d = App.Current?.Dispatcher;
        if (d is null || d.CheckAccess()) apply();
        else d.BeginInvoke(apply);
    }

    void Append(string line)
    {
        Log.Add(line);
        while (Log.Count > 2000) Log.RemoveAt(0);
    }

    static int Get(Dictionary<string, int> c, string k) => c.TryGetValue(k, out var v) ? v : 0;

    void RaiseState()
    {
        Raise(nameof(State));
        Raise(nameof(IsRunning));
        Raise(nameof(Finished));
        Raise(nameof(IsIndeterminate));
        Raise(nameof(PillText));
        Raise(nameof(PillFg));
        Raise(nameof(ActionButtonText));
        Raise(nameof(CountText));
        Raise(nameof(ProgressValue));
        Raise(nameof(ProgressMax));
    }

    public event PropertyChangedEventHandler? PropertyChanged;
    void Raise([CallerMemberName] string? name = null)
        => PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
}
