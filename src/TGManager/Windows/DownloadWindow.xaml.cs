using System.IO;
using System.Windows;
using TGManager.Services;

namespace TGManager.Windows;

public enum DownloadKind { Telegram, Proxychains, PrepareTelegram }

public partial class DownloadWindow : Window
{
    readonly DownloadKind _kind;
    readonly CancellationTokenSource _cts = new();
    bool _finished;
    public bool Succeeded { get; private set; }

    public DownloadWindow(string title, string hint, DownloadKind kind)
    {
        _kind = kind;
        InitializeComponent();
        Chrome.Attach(this, WindowFrame);
        Title = title;
        TitleText.Text = title;
        HintText.Text = hint;
        Loaded += async (_, _) => await Run();
        Closing += (_, _) => { if (!_finished) _cts.Cancel(); };
    }

    async Task Run()
    {
        Append("Скачивание…");
        try
        {
            switch (_kind)
            {
                case DownloadKind.Telegram:
                    await Bundle.DownloadTelegram(LogUi, ProgressUi, _cts.Token);
                    Succeeded = Bundle.TelegramReady();
                    break;
                case DownloadKind.Proxychains:
                    await Bundle.DownloadProxychains(LogUi, ProgressUi, _cts.Token);
                    Succeeded = Bundle.ProxychainsReady();
                    break;
                case DownloadKind.PrepareTelegram:
                    Directory.CreateDirectory(Paths.AccountsDir);
                    if (Bundle.TelegramReady())
                    {
                        Append("✓ Переносной Telegram уже установлен.");
                        Succeeded = true;
                    }
                    else
                    {
                        await Bundle.DownloadTelegram(LogUi, ProgressUi, _cts.Token);
                        Succeeded = Bundle.TelegramReady();
                    }
                    break;
            }
        }
        catch (OperationCanceledException)
        {
            Append("Отменено.");
        }
        catch (Exception ex)
        {
            Append("✗ " + ex.Message);
        }

        _finished = true;
        Bar.IsIndeterminate = false;
        Bar.Maximum = 1;
        Bar.Value = Succeeded ? 1 : 0;
        CloseBtn.Content = Succeeded ? "Готово" : "Закрыть";
        if (Succeeded)
        {
            Append("✓ Готово.");
            // Если всё уже стояло — не заставляем нажимать «Готово».
            if (_kind == DownloadKind.PrepareTelegram && LogBox.LineCount <= 3)
            {
                await Task.Delay(350);
                if (IsVisible) { DialogResult = true; Close(); }
            }
        }
    }

    void LogUi(string line) => Dispatcher.BeginInvoke(() => Append(line));

    void ProgressUi(DownloadProgress p) => Dispatcher.BeginInvoke(() =>
    {
        if (_finished) return;
        if (p.Total <= 0)
        {
            Bar.IsIndeterminate = true;
            return;
        }
        Bar.IsIndeterminate = false;
        Bar.Maximum = 1;
        Bar.Value = p.Fraction;
    });

    void Append(string line)
    {
        if (LogBox.Text.Length > 0) LogBox.AppendText("\n");
        LogBox.AppendText(line);
        LogBox.ScrollToEnd();
    }

    void OnClose(object sender, RoutedEventArgs e)
    {
        if (!_finished) _cts.Cancel();
        DialogResult = Succeeded;
        Close();
    }
}
