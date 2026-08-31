using System.Windows;
using TGManager.Services;
using TGManager.ViewModels;

namespace TGManager.Windows;

public partial class TaskLogWindow : Window
{
    public TaskLogWindow(TaskVm task)
    {
        InitializeComponent();
        Chrome.Attach(this, WindowFrame);
        TitleText.Text = $"Журнал — {task.Account.Name}";
        Title = TitleText.Text;
        LogBox.Text = string.Join("\n", task.Log);
        LogBox.CaretIndex = LogBox.Text.Length;
        LogBox.ScrollToEnd();
    }

    void OnClose(object sender, RoutedEventArgs e) => Close();
}
