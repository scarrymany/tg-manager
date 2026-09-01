using System.Globalization;
using System.IO;
using System.Windows;
using System.Windows.Interop;
using TGManager.Native;
using TGManager.Services;
using TGManager.Windows;

namespace TGManager;

public partial class App : System.Windows.Application
{
    public const string MutexName = @"Local\Scarry.TGManager.single";
    public const string ShowMessageName = "Scarry.TGManager.Show";

    Mutex? _mutex;
    uint _showMessage;
    MainWindow? _window;
    int _excDialog;

    public static string VersionString
    {
        get
        {
            var v = typeof(App).Assembly.GetName().Version;
            return v is null ? "1.2.2" : $"{v.Major}.{v.Minor}.{v.Build}";
        }
    }

    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);

        var ru = CultureInfo.GetCultureInfo("ru-RU");
        CultureInfo.DefaultThreadCurrentCulture = ru;
        CultureInfo.DefaultThreadCurrentUICulture = ru;

        try { NativeMethods.SetCurrentProcessExplicitAppUserModelID("Scarry.TGManager"); }
        catch { /* optional */ }

        _mutex = new Mutex(initiallyOwned: true, MutexName, out var created);
        _showMessage = NativeMethods.RegisterWindowMessage(ShowMessageName);

        if (!created)
        {
            NativeMethods.PostMessage(NativeMethods.HWND_BROADCAST, _showMessage, IntPtr.Zero, IntPtr.Zero);
            Shutdown();
            return;
        }

        DispatcherUnhandledException += (_, args) =>
        {
            args.Handled = true;
            LogError(args.Exception);
            var msg = args.Exception?.Message ?? "";
            // Шум привязок (TwoWay на read-only и т.п.) — только в лог, без окна.
            if (msg.Contains("привязк", StringComparison.OrdinalIgnoreCase)
                || msg.Contains("Binding", StringComparison.OrdinalIgnoreCase)
                || msg.Contains("TwoWay", StringComparison.OrdinalIgnoreCase)
                || msg.Contains("OneWayToSource", StringComparison.OrdinalIgnoreCase))
                return;
            // Один диалог за раз: повторные исключения не должны плодить окна.
            if (Interlocked.Exchange(ref _excDialog, 1) == 1)
                return;
            try
            {
                System.Windows.MessageBox.Show(
                    msg + "\n\nПодробности записаны в error.log рядом с программой.",
                    "TG Manager",
                    MessageBoxButton.OK,
                    MessageBoxImage.Error);
            }
            finally
            {
                Interlocked.Exchange(ref _excDialog, 0);
            }
        };
        AppDomain.CurrentDomain.UnhandledException += (_, args) =>
        {
            if (args.ExceptionObject is Exception ex) LogError(ex);
        };
        TaskScheduler.UnobservedTaskException += (_, args) =>
        {
            LogError(args.Exception);
            args.SetObserved();
        };

        try
        {
            Paths.EnsureDirs();
            var store = Store.Load();
            _window = new MainWindow(store);
            MainWindow = _window;
            _window.SourceInitialized += (_, _) =>
            {
                var hwnd = new WindowInteropHelper(_window).Handle;
                var src = HwndSource.FromHwnd(hwnd);
                src?.AddHook(SingleInstanceHook);
            };
            _window.Show();
            if (store.RecoveredBackup is { } backup)
            {
                ConfirmWindow.Info(_window, "Конфиг не прочитался",
                    "config.json повреждён и был заменён пустым. Старый файл сохранён:\n" + backup +
                    "\n\nПапки контейнеров в accounts\\ не тронуты.");
            }
        }
        catch (Exception ex)
        {
            LogError(ex);
            System.Windows.MessageBox.Show(ex.ToString(), "TG Manager", MessageBoxButton.OK, MessageBoxImage.Error);
            Shutdown();
        }
    }

    static void LogError(Exception ex)
    {
        try
        {
            var path = Path.Combine(Paths.AppRoot, "error.log");
            File.AppendAllText(path, $"[{DateTime.Now:yyyy-MM-dd HH:mm:ss}] {ex}\n\n");
        }
        catch { /* ignore */ }
    }

    IntPtr SingleInstanceHook(IntPtr hwnd, int msg, IntPtr wParam, IntPtr lParam, ref bool handled)
    {
        if ((uint)msg == _showMessage)
        {
            Dispatcher.Invoke(() => Chrome.ActivateExisting(_window));
            handled = true;
        }
        return IntPtr.Zero;
    }

    protected override void OnExit(ExitEventArgs e)
    {
        HttpBridge.StopAll();
        if (_mutex is not null)
        {
            try { _mutex.ReleaseMutex(); } catch { /* already released */ }
            _mutex.Dispose();
        }
        base.OnExit(e);
    }
}
