using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using TGManager;
using TGManager.Services;
using TGManager.Windows;

internal static class UiChecks
{
    public static void Run(string output)
    {
        Exception? failure = null;
        var thread = new Thread(() =>
        {
            try
            {
                var app = new App();
                app.InitializeComponent();
                var store = new Store();
                store.Settings.ContainerFolders.Add("Архив");
                store.Accounts.Add(new Account { Name = "Поддержка клиентов", Notes = "Входящие обращения", Folder = "Работа", Color = "#71C7F5" });
                store.Accounts.Add(new Account { Name = "Рабочий аккаунт", Notes = "Основной профиль", Color = "#6EE7B7",
                    Proxy = new ProxyCfg { Type = ProxyKinds.Socks5, Host = "127.0.0.1", Port = 1080 } });
                store.Accounts.Add(new Account { Name = "Личный архив", Color = "#C4B5FD" });
                var window = new MainWindow(store);
                var search = (TextBox)window.FindName("SearchBox");
                var list = (ItemsControl)window.FindName("AccountList");
                search.Text = "поддержка";
                if (list.Items.Count != 1) throw new InvalidOperationException("Search binding failed");
                search.Text = "missing";
                if (!window.NoResults || list.Items.Count != 0) throw new InvalidOperationException("Empty search state failed");
                search.Clear();
                var sort = (ComboBox)window.FindName("SortBox");
                sort.SelectedIndex = 1;
                if (((TGManager.ViewModels.AccountVm)list.Items[0]).Name != "Личный архив")
                    throw new InvalidOperationException("Name sorting failed");
                sort.SelectedIndex = 0;
                var folders = (ComboBox)window.FindName("FolderFilter");
                folders.SelectedItem = folders.Items.Cast<ComboBoxItem>().Single(item => item.Tag as string == "Работа");
                if (list.Items.Count != 1 || !window.CanManageFolder) throw new InvalidOperationException("Folder selection failed");
                folders.SelectedItem = folders.Items.Cast<ComboBoxItem>().Single(item => item.Tag as string == "Архив");
                if (!window.NoResults) throw new InvalidOperationException("Empty folder failed");
                folders.SelectedIndex = 0;
                Directory.CreateDirectory(output);
                Render(window, Path.Combine(output, "main.png"), 1220, 800);
                Render(window, Path.Combine(output, "main-small.png"), 1040, 560);
                var editor = new AccountWindow(store.Accounts[0], ["Работа", "Архив"]);
                Render(editor, Path.Combine(output, "account.png"), (int)editor.Width, (int)editor.Height);
                var settings = new SettingsWindow(store.Settings);
                Render(settings, Path.Combine(output, "settings.png"), (int)settings.Width, (int)settings.Height);
                var cleanup = new CleanupWindow(store.Accounts[0]);
                Render(cleanup, Path.Combine(output, "cleanup.png"), (int)cleanup.Width, (int)cleanup.Height);
                search.Text = "missing";
                Render(window, Path.Combine(output, "search-empty.png"), 1040, 560);
                search.Clear();
                Render(new FolderWindow(["Работа", "Архив"]), Path.Combine(output, "folder.png"), 440, 290);
                ((FrameworkElement)window.FindName("ContainersPage")).Visibility = Visibility.Collapsed;
                ((FrameworkElement)window.FindName("TasksPage")).Visibility = Visibility.Visible;
                Render(window, Path.Combine(output, "tasks.png"), 1220, 800);
                window.Close();
                app.Shutdown();
                Console.WriteLine("PASS WPF search, empty state, sorting and window rendering");
            }
            catch (Exception ex) { failure = ex; }
        });
        thread.SetApartmentState(ApartmentState.STA);
        thread.Start();
        thread.Join();
        if (failure is not null) throw new InvalidOperationException("WPF checks failed", failure);
    }

    static void Render(Window window, string path, int width, int height)
    {
        var content = (FrameworkElement)window.Content;
        content.Measure(new Size(width, height));
        content.Arrange(new Rect(0, 0, width, height));
        content.UpdateLayout();
        var bitmap = new RenderTargetBitmap(width, height, 96, 96, PixelFormats.Pbgra32);
        bitmap.Render(content);
        var encoder = new PngBitmapEncoder();
        encoder.Frames.Add(BitmapFrame.Create(bitmap));
        using var file = File.Create(path);
        encoder.Save(file);
    }
}
