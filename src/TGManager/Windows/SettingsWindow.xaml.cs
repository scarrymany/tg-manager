using System.Diagnostics;
using System.IO;
using System.Windows;
using System.Windows.Media;
using Microsoft.Win32;
using TGManager.Services;

namespace TGManager.Windows;

public partial class SettingsWindow : Window
{
    readonly Settings _settings;

    public SettingsWindow(Settings settings)
    {
        _settings = settings;
        InitializeComponent();
        Chrome.Attach(this, WindowFrame);
        PreviewKeyDown += (_, e) =>
        {
            if (e.Key != System.Windows.Input.Key.Escape) return;
            OnCancel(this, new RoutedEventArgs());
            e.Handled = true;
        };
        TgBox.Text = settings.TelegramBinary;
        PcBox.Text = settings.ProxychainsBinary;
        ManyChk.IsChecked = settings.AllowMany;
        DataLabel.Text = "Данные контейнеров: " + Paths.AccountsDir;
        TgBox.TextChanged += (_, _) => RefreshStatus();
        PcBox.TextChanged += (_, _) => RefreshStatus();
        RefreshStatus();
    }

    void RefreshStatus()
    {
        var tg = Launcher.ResolveTelegram(TgBox.Text.Trim());
        if (tg is null)
        {
            TgStatus.Text = "⚠ Переносной Telegram не установлен — нажмите «Скачать переносной Telegram».";
            TgStatus.Foreground = (Brush)FindResource("YellowBrush");
        }
        else
        {
            TgStatus.Text = "✓ Будет использован: " + tg;
            TgStatus.Foreground = (Brush)FindResource("GreenBrush");
        }

        var pc = Launcher.ResolveProxychains(PcBox.Text.Trim());
        if (pc is null)
        {
            PcStatus.Text = "⚠ Прокси-обёртка не найдена. Нажмите «Скачать прокси-обёртку», если будете запускать контейнеры через HTTP/SOCKS5.";
            PcStatus.Foreground = (Brush)FindResource("YellowBrush");
        }
        else
        {
            PcStatus.Text = "✓ Прокси-обёртка: " + pc;
            PcStatus.Foreground = (Brush)FindResource("GreenBrush");
        }
    }

    void OnBrowseTg(object sender, RoutedEventArgs e)
    {
        var dlg = new OpenFileDialog
        {
            Title = "Выберите Telegram.exe",
            Filter = "Telegram (Telegram.exe)|Telegram.exe|Все файлы (*.*)|*.*",
        };
        if (dlg.ShowDialog(this) == true)
            TgBox.Text = dlg.FileName;
    }

    void OnAutoTg(object sender, RoutedEventArgs e)
    {
        var found = Launcher.ResolveTelegram("");
        if (found is not null) TgBox.Text = found;
        RefreshStatus();
    }

    void OnAutoPc(object sender, RoutedEventArgs e)
    {
        var found = Launcher.ResolveProxychains("");
        if (found is not null) PcBox.Text = found;
        RefreshStatus();
    }

    void OnDownloadTg(object sender, RoutedEventArgs e)
    {
        var dl = new DownloadWindow("Переносной Telegram",
            "Официальный Telegram Desktop (Windows 64-bit portable) будет установлен в папку программы.",
            DownloadKind.Telegram)
        { Owner = this };
        dl.ShowDialog();
        if (dl.Succeeded && !string.IsNullOrWhiteSpace(TgBox.Text) && !File.Exists(TgBox.Text.Trim()))
            TgBox.Clear();
        RefreshStatus();
    }

    void OnDownloadPc(object sender, RoutedEventArgs e)
    {
        var dl = new DownloadWindow("Прокси-обёртка",
            "Windows-порт ProxyChains (x64). Нужен, чтобы HTTP/SOCKS5 прокси контейнера применялся к Telegram Desktop.",
            DownloadKind.Proxychains)
        { Owner = this };
        dl.ShowDialog();
        if (dl.Succeeded) PcBox.Clear();
        RefreshStatus();
    }

    void OnOpenData(object sender, RoutedEventArgs e)
    {
        Directory.CreateDirectory(Paths.AccountsDir);
        try { Process.Start(new ProcessStartInfo { FileName = Paths.AccountsDir, UseShellExecute = true }); }
        catch { /* ignore */ }
    }

    void OnShortcut(object sender, RoutedEventArgs e)
    {
        try
        {
            var lnk = Shortcut.CreateDesktop();
            ConfirmWindow.Info(this, "Ярлык", "Создан:\n" + lnk);
        }
        catch (Exception ex)
        {
            ConfirmWindow.Info(this, "Ярлык", "Не удалось создать ярлык:\n" + ex.Message);
        }
    }

    void OnSave(object sender, RoutedEventArgs e)
    {
        _settings.TelegramBinary = TgBox.Text.Trim();
        _settings.ProxychainsBinary = PcBox.Text.Trim();
        _settings.AllowMany = ManyChk.IsChecked == true;
        DialogResult = true;
        Close();
    }

    void OnCancel(object sender, RoutedEventArgs e)
    {
        DialogResult = false;
        Close();
    }
}
