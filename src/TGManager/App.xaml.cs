using System.Globalization;
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
            System.Windows.MessageBox.Show(
                args.Exception.Message,
                "TG Manager",
                MessageBoxButton.OK,
                MessageBoxImage.Error);
        };

        try
        {
            System.Windows.Forms.Application.EnableVisualStyles();
            System.Windows.Forms.Application.SetCompatibleTextRenderingDefault(false);
        }
        catch { /* optional */ }

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
        }
        catch (Exception ex)
        {
            System.Windows.MessageBox.Show(ex.ToString(), "TG Manager", MessageBoxButton.OK, MessageBoxImage.Error);
            Shutdown();
        }
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
        if (_mutex is not null)
        {
            try { _mutex.ReleaseMutex(); } catch { /* already released */ }
            _mutex.Dispose();
        }
        base.OnExit(e);
    }
}
