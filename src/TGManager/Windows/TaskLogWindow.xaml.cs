using System.Collections.Specialized;
using System.Windows;
using System.Windows.Input;
using TGManager.Services;
using TGManager.ViewModels;

namespace TGManager.Windows;

/// <summary>Живой журнал задачи: новые строки дописываются по мере работы воркера.</summary>
public partial class TaskLogWindow : Window
{
    readonly TaskVm _task;

    public TaskLogWindow(TaskVm task)
    {
        _task = task;
        InitializeComponent();
        Chrome.Attach(this, WindowFrame);
        TitleText.Text = $"Журнал — {task.Account.Name}";
        Title = TitleText.Text;
        LogBox.Text = string.Join("\n", task.Log);
        LogBox.CaretIndex = LogBox.Text.Length;
        LogBox.ScrollToEnd();
        task.Log.CollectionChanged += OnLog;
        Closed += (_, _) => task.Log.CollectionChanged -= OnLog;
        PreviewKeyDown += (_, e) =>
        {
            if (e.Key == Key.Escape) { Close(); e.Handled = true; }
        };
    }

    void OnLog(object? sender, NotifyCollectionChangedEventArgs e)
    {
        switch (e.Action)
        {
            case NotifyCollectionChangedAction.Add when e.NewItems is not null:
                foreach (var item in e.NewItems)
                {
                    if (item is not string line) continue;
                    if (LogBox.Text.Length > 0) LogBox.AppendText("\n");
                    LogBox.AppendText(line);
                }
                LogBox.ScrollToEnd();
                break;
            case NotifyCollectionChangedAction.Reset:
                LogBox.Text = string.Join("\n", _task.Log);
                LogBox.ScrollToEnd();
                break;
        }
    }

    void OnClose(object sender, RoutedEventArgs e) => Close();
}
