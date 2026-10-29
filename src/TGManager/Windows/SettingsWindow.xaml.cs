using System.Diagnostics;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using Microsoft.Win32;
using TGManager.Services;

namespace TGManager.Windows;

public partial class SettingsWindow : Window
{
    readonly Settings _settings;
    readonly (string Key, CheckBox Box)[] _cardButtons;
    bool _loading = true;

    public SettingsWindow(Settings settings)
    {
        _settings = settings;
        InitializeComponent();
        _cardButtons =
        [
            (CardActions.Launch, LaunchChk), (CardActions.Stop, StopChk), (CardActions.Folder, FolderChk),
            (CardActions.Export, ExportChk), (CardActions.Cleanup, CleanupChk), (CardActions.Edit, EditChk),
            (CardActions.Delete, DeleteChk),
        ];
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
        Select(DensityBox, settings.ListDensity);
        SelectNearestHeight(settings.CardPadding);
        Select(SizeBox, settings.ButtonSize);
        Select(StyleBox, settings.ButtonStyle);
        foreach (var (key, box) in _cardButtons) box.IsChecked = settings.CardButtons.Contains(key);
        _loading = false;
        DataLabel.Text = "Данные контейнеров: " + Paths.AccountsDir;
        TgBox.TextChanged += (_, _) => RefreshStatus();
        PcBox.TextChanged += (_, _) => RefreshStatus();
        RefreshStatus();
    }

    static void Select(ComboBox box, string tag)
        => box.SelectedItem = box.Items.Cast<ComboBoxItem>().FirstOrDefault(i => (string)i.Tag == tag) ?? box.Items[0];

    void SelectNearestHeight(int padding)
        => HeightBox.SelectedItem = HeightBox.Items.Cast<ComboBoxItem>()
            .MinBy(i => Math.Abs(int.Parse((string)i.Tag) - padding));

    /// <summary>Плотность выставляет рекомендуемые высоту карточки и вид кнопок; набор кнопок остаётся как выбран.</summary>
    void OnDensityChanged(object sender, SelectionChangedEventArgs e)
    {
        if (_loading || DensityBox.SelectedItem is not ComboBoxItem { Tag: string density }) return;
        var preset = ListDensities.Presets[density];
        SelectNearestHeight(preset.Padding);
        Select(SizeBox, preset.ButtonSize);
        Select(StyleBox, preset.ButtonStyle);
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
        _settings.ListDensity = (string)((ComboBoxItem)DensityBox.SelectedItem).Tag;
        _settings.CardPadding = int.Parse((string)((ComboBoxItem)HeightBox.SelectedItem).Tag);
        _settings.ButtonSize = (string)((ComboBoxItem)SizeBox.SelectedItem).Tag;
        _settings.ButtonStyle = (string)((ComboBoxItem)StyleBox.SelectedItem).Tag;
        _settings.CardButtons = _cardButtons.Where(b => b.Box.IsChecked == true).Select(b => b.Key).ToList();
        DialogResult = true;
        Close();
    }

    void OnCancel(object sender, RoutedEventArgs e)
    {
        DialogResult = false;
        Close();
    }
}
