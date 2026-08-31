using System.Windows;
using System.Windows.Media;
using TGManager.Services;

namespace TGManager.Windows;

public sealed record CleanupRequest(IReadOnlyList<string> Actions, bool Revoke);

public partial class CleanupWindow : Window
{
    readonly Account _account;
    readonly string _workdir;
    WorkerHost? _host;
    bool _running;
    bool _dry;

    public CleanupRequest? Requested { get; private set; }

    public CleanupWindow(Account account)
    {
        _account = account;
        _workdir = Paths.AccountWorkdir(account.Id);
        InitializeComponent();
        Chrome.Attach(this, WindowFrame);
        TitleText.Text = $"Автоматизация — «{account.Name}»";
        ConnLabel.Text = account.Proxy.Enabled
            ? "Подключение: через " + account.Proxy.Summary()
            : "Подключение: напрямую (у контейнера не задан прокси)";
        Closed += (_, _) =>
        {
            if (_running) _host?.Stop();
            WorkerHost.ClearLock(_workdir);
            _host?.Dispose();
        };
    }

    List<string> Selected()
    {
        var list = new List<string>();
        if (ChkChannels.IsChecked == true) list.Add("channels");
        if (ChkGroups.IsChecked == true) list.Add("groups");
        if (ChkPrivate.IsChecked == true) list.Add("private");
        if (ChkBots.IsChecked == true) list.Add("bots");
        if (ChkSaved.IsChecked == true) list.Add("saved");
        if (ChkContacts.IsChecked == true) list.Add("contacts");
        if (ChkPhotos.IsChecked == true) list.Add("photos");
        return list;
    }

    void OnConfirm(object sender, RoutedEventArgs e) => SyncButtons();

    void SyncButtons()
    {
        RunBtn.IsEnabled = ConfirmChk.IsChecked == true && !_running;
        DryBtn.IsEnabled = !_running;
    }

    void SetInputs(bool enabled)
    {
        foreach (var c in new[] { ChkChannels, ChkGroups, ChkPrivate, ChkBots, ChkSaved, ChkContacts, ChkPhotos, ChkRevoke, ConfirmChk })
            c.IsEnabled = enabled;
        SyncButtons();
    }

    void OnRun(object sender, RoutedEventArgs e)
    {
        if (_running) return;
        var actions = Selected();
        if (actions.Count == 0)
        {
            ConfirmWindow.Info(this, "Ничего не выбрано", "Отметьте, что чистить.");
            return;
        }
        if (Launcher.IsRunning(_workdir))
        {
            ConfirmWindow.Info(this, "Telegram запущен", "Сначала остановите Telegram этого контейнера («Стоп»).");
            return;
        }
        if (!ConfirmWindow.Ask(this, "Подтверждение",
                "Запустить необратимую чистку выбранных разделов в фоне?\nРазделы: " + string.Join(", ", actions)
                + (ChkRevoke.IsChecked == true ? "\nЛичные — с revoke (у обеих сторон)." : "")))
            return;
        Requested = new CleanupRequest(actions, ChkRevoke.IsChecked == true);
        DialogResult = true;
        Close();
    }

    void OnDryRun(object sender, RoutedEventArgs e) => StartDry();

    void StartDry()
    {
        if (_running) return;
        if (!WorkerHost.WorkerAvailable())
        {
            ConfirmWindow.Info(this, "Нет воркера чистки",
                "Рядом с программой должен лежать TGWorker.exe, либо установите Python с telethon и opentele-ng.");
            return;
        }
        var actions = Selected();
        if (actions.Count == 0)
        {
            ConfirmWindow.Info(this, "Ничего не выбрано", "Отметьте, что чистить.");
            return;
        }
        if (Launcher.IsRunning(_workdir))
        {
            ConfirmWindow.Info(this, "Telegram запущен",
                "Сначала остановите Telegram этого контейнера (кнопка «Стоп»), иначе сессию выбросит.");
            return;
        }

        _dry = true;
        LogBox.Clear();
        Bar.IsIndeterminate = true;
        StatusLabel.Text = "Проверка…";
        StatusLabel.Foreground = (Brush)FindResource("MutedBrush");
        _running = true;
        SetInputs(false);
        CloseBtn.Content = "Остановить";

        _host?.Dispose();
        _host = new WorkerHost();
        _host.Event += ev => Dispatcher.BeginInvoke(() => Handle(ev));
        _host.Exited += _ => Dispatcher.BeginInvoke(Finished);
        if (!_host.Start(_account, actions, ChkRevoke.IsChecked == true, dryRun: true))
        {
            ConfirmWindow.Info(this, "Не удалось запустить", "Воркер не стартовал.");
            Finished();
        }
    }

    void Handle(WorkerEvent ev)
    {
        switch (ev.Type)
        {
            case "stage":
                StatusLabel.Text = ev.Msg ?? "";
                Append("• " + ev.Msg);
                break;
            case "summary":
                Bar.IsIndeterminate = false;
                Bar.Maximum = Math.Max(1, ev.Total);
                Bar.Value = 0;
                var c = ev.Counts ?? [];
                var parts = new List<string>
                {
                    $"каналы {Get(c, "channels")}",
                    $"группы {Get(c, "groups")}",
                    $"личные {Get(c, "private")}",
                    $"боты {Get(c, "bots")}",
                    $"избранное {Get(c, "saved")}",
                };
                if (ev.Contacts) parts.Add("контакты");
                if (ev.Photos) parts.Add("фото");
                var msg = "Найдено: " + string.Join(", ", parts) + $" · всего действий: {ev.Total}";
                StatusLabel.Text = msg;
                Append(msg);
                break;
            case "progress":
                Bar.IsIndeterminate = false;
                if (ev.Total > 0) Bar.Maximum = ev.Total;
                Bar.Value = ev.Done;
                StatusLabel.Text = $"{ev.Done}/{ev.Total} — {ev.Label}";
                Append($"[{ev.Cat}] {ev.Label}");
                break;
            case "flood":
                Append($"⏳ FloodWait: Telegram просит подождать {ev.Seconds} c — ждём…");
                StatusLabel.Text = $"Пауза по требованию Telegram: {ev.Seconds} c";
                break;
            case "warn":
                Append($"! {ev.Label}: {ev.Error}");
                break;
            case "done":
                StatusLabel.Text = ev.DryRun ? "Проверка завершена (ничего не удалено)." : $"Готово. Выполнено действий: {ev.Done}.";
                StatusLabel.Foreground = (Brush)FindResource("GreenBrush");
                break;
            case "error":
                Append("✗ " + ev.Error);
                StatusLabel.Text = "Ошибка: " + ev.Error;
                StatusLabel.Foreground = (Brush)FindResource("RedBrush");
                break;
            default:
                if (!string.IsNullOrEmpty(ev.Msg)) Append(ev.Msg);
                break;
        }
    }

    void Finished()
    {
        WorkerHost.ClearLock(_workdir);
        _running = false;
        Bar.IsIndeterminate = false;
        if (Bar.Maximum <= 0) Bar.Maximum = 1;
        Bar.Value = Bar.Maximum;
        SetInputs(true);
        CloseBtn.Content = "Закрыть";
        if (!_dry) ConfirmChk.IsChecked = false;
        _host?.Dispose();
        _host = null;
    }

    void OnClose(object sender, RoutedEventArgs e)
    {
        if (_running)
        {
            if (!ConfirmWindow.Ask(this, "Остановить?", "Остановить процесс автоматизации?"))
                return;
            _host?.Stop();
            WorkerHost.ClearLock(_workdir);
            _running = false;
            return;
        }
        DialogResult = Requested is not null;
        Close();
    }

    void Append(string line)
    {
        if (string.IsNullOrEmpty(line)) return;
        if (LogBox.Text.Length > 0) LogBox.AppendText("\n");
        LogBox.AppendText(line);
        LogBox.ScrollToEnd();
    }

    static int Get(Dictionary<string, int> c, string k) => c.TryGetValue(k, out var v) ? v : 0;
}
