using System.IO;
using System.Windows;
using TGManager.Services;

namespace TGManager.Windows;

public enum DownloadKind { Telegram, Proxychains, PrepareTelegram }

public partial class DownloadWindow : Window
{
    readonly DownloadKind _kind;
    readonly CancellationTokenSource _cts = new();
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
        Closed += (_, _) => _cts.Cancel();
    }

    async Task Run()
    {
        Append("Скачивание…");
        try
        {
            switch (_kind)
            {
                case DownloadKind.Telegram:
                    await Bundle.DownloadTelegram(LogUi, _cts.Token);
                    Succeeded = Bundle.TelegramReady();
                    break;
                case DownloadKind.Proxychains:
                    await Bundle.DownloadProxychains(LogUi, _cts.Token);
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
                        await Bundle.DownloadTelegram(LogUi, _cts.Token);
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

        Bar.IsIndeterminate = false;
        Bar.Maximum = 1;
        Bar.Value = Succeeded ? 1 : 0;
        CloseBtn.Content = Succeeded ? "Готово" : "Закрыть";
        if (Succeeded) Append("✓ Готово.");
    }

    void LogUi(string line) => Dispatcher.BeginInvoke(() => Append(line));

    void Append(string line)
    {
        if (LogBox.Text.Length > 0) LogBox.AppendText("\n");
        LogBox.AppendText(line);
        LogBox.ScrollToEnd();
    }

    void OnClose(object sender, RoutedEventArgs e)
    {
        if (!Succeeded) _cts.Cancel();
        DialogResult = Succeeded;
        Close();
    }
}
