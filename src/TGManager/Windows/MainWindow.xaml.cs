using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Runtime.CompilerServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Threading;
using TGManager.Services;
using TGManager.ViewModels;

namespace TGManager.Windows;

public partial class MainWindow : Window, INotifyPropertyChanged
{
    readonly Store _store;
    readonly DispatcherTimer _poll;
    readonly Dictionary<string, TaskVm> _tasks = [];
    readonly Dictionary<string, TaskLogWindow> _logWindows = [];
    bool _polling;
    bool _closing;

    public ObservableCollection<AccountVm> Accounts { get; } = [];
    public ObservableCollection<TaskVm> Tasks { get; } = [];

    bool _hasAccounts;
    bool _hasTasks;
    public bool HasAccounts { get => _hasAccounts; set { if (_hasAccounts == value) return; _hasAccounts = value; Raise(); } }
    public bool HasTasks { get => _hasTasks; set { if (_hasTasks == value) return; _hasTasks = value; Raise(); } }

    public MainWindow(Store store)
    {
        _store = store;
        DataContext = this;
        InitializeComponent();
        Chrome.Attach(this, WindowFrame);
        AccountList.ItemsSource = Accounts;
        TaskList.ItemsSource = Tasks;
        VersionText.Text = "v" + App.VersionString;
        StateChanged += (_, _) => SyncMaxIcon();
        ReloadAccounts();
        _poll = new DispatcherTimer { Interval = TimeSpan.FromSeconds(2) };
        _poll.Tick += (_, _) => PollStatus();
        _poll.Start();
        Status("Готово");
    }

    void ReloadAccounts()
    {
        Accounts.Clear();
        foreach (var a in _store.Accounts)
            Accounts.Add(new AccountVm(a));
        HasAccounts = Accounts.Count > 0;
        PollStatus();
    }

    AccountVm? Find(string id) => Accounts.FirstOrDefault(a => a.Id == id);

    /// <summary>
    /// Опрос состояния контейнеров. Снимок процессов и чтение командных строк — в фоне,
    /// иначе при десятках карточек UI подвисает каждые 2 секунды.
    /// </summary>
    async void PollStatus()
    {
        if (_polling || _closing) return;
        _polling = true;
        try
        {
            var ids = Accounts.Select(a => a.Id).ToList();
            var result = await Task.Run(() =>
            {
                var scan = ProcessScan.Take();
                var dict = new Dictionary<string, (bool Locked, bool Running)>(ids.Count);
                foreach (var id in ids)
                {
                    var wd = Paths.AccountWorkdir(id);
                    dict[id] = (WorkerHost.IsLocked(wd), Launcher.IsRunning(wd, scan));
                }
                return dict;
            });
            foreach (var vm in Accounts)
            {
                if (!result.TryGetValue(vm.Id, out var st)) continue;
                var busy = st.Locked || (_tasks.TryGetValue(vm.Id, out var t) && t.IsRunning);
                vm.Busy = busy;
                if (!vm.Stopping) vm.Running = !busy && st.Running;
                vm.RefreshMeta();
            }
        }
        catch { /* опрос не должен ронять окно */ }
        finally { _polling = false; }
    }

    void OnNavContainers(object sender, RoutedEventArgs e)
    {
        if (ContainersPage.Visibility == Visibility.Visible) return;
        Chrome.CrossFade(ContainersPage, TasksPage);
        NavContainers.Tag = "active";
        NavTasks.Tag = null;
    }

    void OnNavTasks(object sender, RoutedEventArgs e)
    {
        if (TasksPage.Visibility == Visibility.Visible) return;
        Chrome.CrossFade(TasksPage, ContainersPage);
        NavContainers.Tag = null;
        NavTasks.Tag = "active";
    }

    void RefreshTasksNav()
    {
        var active = Tasks.Count(t => t.IsRunning);
        NavTasks.Content = active > 0 ? $"Активные задачи ({active})" : "Активные задачи";
        HasTasks = Tasks.Count > 0;
    }

    void OnAddAccount(object sender, RoutedEventArgs e)
    {
        var dlg = new AccountWindow { Owner = this };
        if (dlg.ShowDialog() != true || dlg.Result is null) return;
        var account = dlg.Result;
        Directory.CreateDirectory(Paths.AccountWorkdir(account.Id));
        _store.Add(account);
        Accounts.Add(new AccountVm(account));
        HasAccounts = true;

        var prep = new DownloadWindow("Подготовка контейнера",
            $"«{account.Name}» — создаю папку и проверяю переносной Telegram.",
            DownloadKind.PrepareTelegram)
        { Owner = this };
        prep.ShowDialog();
        Status(prep.Succeeded
            ? "Контейнер создан и подготовлен"
            : "Контейнер создан (переносной Telegram можно докачать позже)");
        OpenFolder(account.Id);
        PollStatus();
    }

    void OnEdit(object sender, RoutedEventArgs e)
    {
        if (IdOf(sender) is not { } id) return;
        var acc = _store.Get(id);
        if (acc is null) return;
        var dlg = new AccountWindow(acc) { Owner = this };
        if (dlg.ShowDialog() != true || dlg.Result is null) return;
        _store.Update(dlg.Result);
        Find(id)?.Apply(dlg.Result);
        Status("Контейнер обновлён");
    }

    async void OnDelete(object sender, RoutedEventArgs e)
    {
        if (IdOf(sender) is not { } id) return;
        var acc = _store.Get(id);
        if (acc is null) return;
        var vm = Find(id);
        var workdir = Paths.AccountWorkdir(id);
        var running = vm?.Running == true || Launcher.IsRunning(workdir);
        var taskRunning = _tasks.TryGetValue(id, out var task) && task.IsRunning;
        var info = (running ? "Контейнер будет остановлен.\n" : "") +
                   (taskRunning ? "Идущая чистка будет прервана.\n" : "") +
                   "Также удалить папку с данными (tdata)?\n«Нет» — оставить папку на диске.";
        var choice = ConfirmWindow.AskDelete(this, $"Удалить «{acc.Name}»?", info);
        if (choice == ConfirmWindow.Choice.Cancel) return;

        if (vm is not null) vm.Stopping = true;
        if (task is not null)
        {
            task.Stop();
            Tasks.Remove(task);
            _tasks.Remove(id);
            CloseLogWindow(id);
            RefreshTasksNav();
        }
        if (running)
        {
            Status("Останавливаю Telegram…");
            await Task.Run(() => Launcher.Stop(workdir));
        }
        if (choice == ConfirmWindow.Choice.Destructive)
        {
            var err = await Task.Run(() =>
            {
                try { Directory.Delete(workdir, true); return (string?)null; }
                catch (Exception ex) { return ex.Message; }
            });
            if (err is not null)
                ConfirmWindow.Info(this, "Папка не удалена полностью",
                    "Часть файлов занята другим процессом:\n" + err + "\n\nУдалите папку вручную:\n" + workdir);
        }
        _store.Remove(id);
        if (vm is not null) Accounts.Remove(vm);
        HasAccounts = Accounts.Count > 0;
        Status("Контейнер удалён");
    }

    void OnFolder(object sender, RoutedEventArgs e)
    {
        if (IdOf(sender) is { } id) OpenFolder(id);
    }

    void OpenFolder(string id)
    {
        var workdir = Paths.AccountWorkdir(id);
        Directory.CreateDirectory(workdir);
        try { Process.Start(new ProcessStartInfo { FileName = workdir, UseShellExecute = true }); }
        catch { /* ignore */ }
        Status("Положите сюда папку tdata");
    }

    void OnLaunch(object sender, RoutedEventArgs e)
    {
        if (IdOf(sender) is not { } id) return;
        var acc = _store.Get(id);
        if (acc is null) return;
        var workdir = Paths.AccountWorkdir(id);
        if (WorkerHost.IsLocked(workdir) || (_tasks.TryGetValue(id, out var t) && t.IsRunning))
        {
            ConfirmWindow.Info(this, "Идёт автоматизация",
                "Сейчас выполняется чистка этого контейнера. Запуск заблокирован до завершения.");
            return;
        }
        if (Launcher.IsRunning(workdir))
        {
            if (Find(id) is { } already) already.Running = true;
            Status("Контейнер уже запущен");
            return;
        }

        if (Launcher.ResolveTelegram(_store.Settings.TelegramBinary) is null)
        {
            if (!ConfirmWindow.Ask(this, "Нужен переносной Telegram",
                    "Для запуска используется переносной Telegram, и он ещё не установлен.\nСкачать официальный Telegram Desktop сейчас (~50 МБ)?"))
                return;
            var dl = new DownloadWindow("Переносной Telegram",
                "Официальный Telegram Desktop (Windows 64-bit portable) будет установлен в папку программы.",
                DownloadKind.Telegram)
            { Owner = this };
            dl.ShowDialog();
            if (!dl.Succeeded)
            {
                Status("Переносной Telegram не установлен");
                return;
            }
        }

        if (acc.Proxy.Enabled && Launcher.ResolveProxychains(_store.Settings.ProxychainsBinary) is null)
        {
            if (ConfirmWindow.Ask(this, "Нужна прокси-обёртка",
                    "У контейнера задан прокси, но обёртка ещё не установлена.\nСкачать прокси-обёртку сейчас (~200 КБ)?"))
            {
                var pcd = new DownloadWindow("Прокси-обёртка",
                    "Windows-порт ProxyChains (x64). Нужен, чтобы HTTP/SOCKS5 прокси контейнера применялся к Telegram Desktop.",
                    DownloadKind.Proxychains)
                { Owner = this };
                pcd.ShowDialog();
            }
        }

        if (!Directory.Exists(Paths.AccountTdata(id)))
        {
            if (!ConfirmWindow.Ask(this, "Нет tdata",
                    "В папке аккаунта нет tdata. Запустить всё равно (откроется чистый Telegram для новой авторизации)?",
                    yes: "Запустить", no: "Отмена"))
                return;
        }

        var plan = Launcher.Build(_store.Settings, acc);
        if (!plan.Ok)
        {
            ConfirmWindow.Info(this, "Не удалось запустить", plan.Error ?? "Ошибка");
            return;
        }
        if (plan.ProxyRequested && !plan.ProxyApplied)
        {
            if (!ConfirmWindow.Ask(this, "Прокси не применён",
                    (plan.Warning ?? "Прокси не удалось применить.") + "\n\nЗапустить БЕЗ прокси?"))
                return;
        }

        var pid = Launcher.Launch(plan);
        if (pid is null)
        {
            ConfirmWindow.Info(this, "Ошибка", "Не удалось запустить процесс.");
            return;
        }
        if (Find(id) is { } vm)
        {
            vm.RefreshMeta();
            vm.Running = true;
        }
        Status("Запущен: " + acc.Name + (plan.ProxyApplied ? " (с прокси)" : ""));
    }

    async void OnStop(object sender, RoutedEventArgs e)
    {
        if (IdOf(sender) is not { } id) return;
        var acc = _store.Get(id);
        var workdir = Paths.AccountWorkdir(id);
        var vm = Find(id);
        if (vm is { Stopping: true }) return;
        if (vm is not null) vm.Stopping = true;
        Status("Останавливаю" + (acc is null ? "…" : ": " + acc.Name + "…"));

        // Terminate + taskkill + ожидание — всё в фоне, UI не замирает.
        var alive = await Task.Run(() =>
        {
            Launcher.Stop(workdir);
            for (var attempt = 0; attempt < 10; attempt++)
            {
                if (!Launcher.IsRunning(workdir)) return false;
                if (attempt is 3 or 6) Launcher.Stop(workdir);
                Thread.Sleep(200);
            }
            return Launcher.IsRunning(workdir);
        });

        if (vm is not null)
        {
            vm.Stopping = false;
            vm.Running = alive;
        }
        Status(alive
            ? "Telegram не завершился. Закройте его из трея: Quit Telegram."
            : acc is null ? "Остановлен" : "Остановлен: " + acc.Name);
    }

    void OnCleanup(object sender, RoutedEventArgs e)
    {
        if (IdOf(sender) is not { } id) return;
        var acc = _store.Get(id);
        if (acc is null) return;
        if (_tasks.TryGetValue(id, out var existing) && existing.IsRunning)
        {
            OnNavTasks(sender, e);
            return;
        }
        var workdir = Paths.AccountWorkdir(id);
        if (Launcher.IsRunning(workdir))
        {
            ConfirmWindow.Info(this, "Telegram запущен",
                "Сначала остановите Telegram этого контейнера («Стоп») — иначе сессию выбросит при подключении.");
            return;
        }
        if (!WorkerHost.WorkerAvailable())
        {
            ConfirmWindow.Info(this, "Нет воркера чистки",
                "Рядом с программой должен лежать TGWorker.exe (есть в релизе).\nЛибо установите Python 3.10+ с telethon и opentele-ng.");
            return;
        }
        if (!Directory.Exists(Paths.AccountTdata(id)))
        {
            ConfirmWindow.Info(this, "Нет tdata", "В контейнере нет папки tdata — нечего чистить.");
            return;
        }

        var dlg = new CleanupWindow(acc) { Owner = this };
        if (dlg.ShowDialog() == true && dlg.Requested is { } req)
            StartTask(acc, req.Actions, req.Revoke);
        PollStatus();
    }

    void StartTask(Account acc, IReadOnlyList<string> actions, bool revoke)
    {
        if (_tasks.TryGetValue(acc.Id, out var old))
        {
            if (!old.Finished) return;
            Tasks.Remove(old);
            _tasks.Remove(acc.Id);
            CloseLogWindow(acc.Id);
        }
        var vm = new TaskVm(acc, actions, revoke);
        vm.PropertyChanged += (_, a) =>
        {
            if (a.PropertyName is nameof(TaskVm.State)) RefreshTasksNav();
        };
        if (!vm.Start())
        {
            ConfirmWindow.Info(this, "Не удалось запустить", "Воркер чистки не стартовал.");
            vm.Host.Dispose();
            return;
        }
        _tasks[acc.Id] = vm;
        Tasks.Insert(0, vm);
        if (Find(acc.Id) is { } avm) avm.Busy = true;
        RefreshTasksNav();
        OnNavTasks(this, new RoutedEventArgs());
    }

    void OnTaskLog(object sender, RoutedEventArgs e)
    {
        if (IdOf(sender) is not { } id) return;
        if (!_tasks.TryGetValue(id, out var t)) return;
        if (_logWindows.TryGetValue(id, out var open))
        {
            Chrome.ActivateExisting(open);
            return;
        }
        var w = new TaskLogWindow(t) { Owner = this };
        _logWindows[id] = w;
        w.Closed += (_, _) => _logWindows.Remove(id);
        w.Show();
    }

    void CloseLogWindow(string id)
    {
        if (_logWindows.TryGetValue(id, out var w))
        {
            try { w.Close(); } catch { /* ignore */ }
            _logWindows.Remove(id);
        }
    }

    void OnTaskAction(object sender, RoutedEventArgs e)
    {
        if (IdOf(sender) is not { } id) return;
        if (!_tasks.TryGetValue(id, out var t)) return;
        if (t.IsRunning) t.Stop();
        else
        {
            Tasks.Remove(t);
            _tasks.Remove(id);
            CloseLogWindow(id);
        }
        RefreshTasksNav();
        PollStatus();
    }

    void OnClearFinished(object sender, RoutedEventArgs e)
    {
        foreach (var t in Tasks.Where(x => x.Finished).ToList())
        {
            Tasks.Remove(t);
            _tasks.Remove(t.Id);
            CloseLogWindow(t.Id);
        }
        RefreshTasksNav();
    }

    void OnStopAll(object sender, RoutedEventArgs e)
    {
        var running = Tasks.Where(x => x.IsRunning).ToList();
        if (running.Count == 0) return;
        if (!ConfirmWindow.Ask(this, "Остановить все",
                $"Прервать задач: {running.Count}?", yes: "Остановить"))
            return;
        foreach (var t in running)
            t.Stop();
        RefreshTasksNav();
        PollStatus();
    }

    void OnOpenSettings(object sender, RoutedEventArgs e)
    {
        var dlg = new SettingsWindow(_store.Settings) { Owner = this };
        if (dlg.ShowDialog() == true)
        {
            _store.Save();
            Status("Настройки сохранены");
        }
    }

    public const string RepoUrl = "https://github.com/scarrymany/tg-manager";
    public const string DeveloperTelegram = "https://t.me/yeet17";

    void OnGitHub(object sender, RoutedEventArgs e) => OpenUrl(RepoUrl);
    void OnTelegram(object sender, RoutedEventArgs e) => OpenUrl(DeveloperTelegram);

    void OpenUrl(string url)
    {
        try { Process.Start(new ProcessStartInfo { FileName = url, UseShellExecute = true }); }
        catch { Status("Не удалось открыть ссылку: " + url); }
    }

    void OnMinimize(object sender, RoutedEventArgs e) => Chrome.Minimize(this);
    void OnMaximize(object sender, RoutedEventArgs e) => Chrome.ToggleMax(this);

    void SyncMaxIcon()
    {
        var max = WindowState == WindowState.Maximized;
        MaxIcon.Data = System.Windows.Media.Geometry.Parse(max
            ? "M8,8 H16 V16 H8 Z M5,11 V5 H15"
            : "M5,5 H15 V15 H5 Z");
        MaxButton.ToolTip = max ? "Восстановить" : "Развернуть";
    }

    void OnCloseClick(object sender, RoutedEventArgs e) => Close();

    void OnClosing(object sender, CancelEventArgs e)
    {
        var active = Tasks.Count(t => t.IsRunning);
        if (active > 0)
        {
            if (!ConfirmWindow.Ask(this, "Идут задачи",
                    $"Выполняется задач: {active}. Закрыть программу и прервать их?"))
            {
                e.Cancel = true;
                return;
            }
        }
        if (HttpBridge.AnyLive)
        {
            if (!ConfirmWindow.Ask(this, "HTTP-прокси через TG Manager",
                    "Контейнеры с HTTP-прокси ходят через мост внутри TG Manager.\n" +
                    "После закрытия программы их Telegram потеряет соединение через прокси\n(SOCKS5-контейнеров это не касается).\n\nВсё равно закрыть?",
                    yes: "Закрыть"))
            {
                e.Cancel = true;
                return;
            }
        }
        _closing = true;
        foreach (var t in Tasks.Where(x => x.IsRunning).ToList())
            t.Stop();
        foreach (var w in _logWindows.Values.ToList())
        {
            try { w.Close(); } catch { /* ignore */ }
        }
        _poll.Stop();
    }

    static string? IdOf(object sender) => (sender as FrameworkElement)?.Tag as string;

    void Status(string text)
    {
        StatusText.Text = text;
    }

    public event PropertyChangedEventHandler? PropertyChanged;
    void Raise([CallerMemberName] string? name = null)
        => PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
}
