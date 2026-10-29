using System.IO;
using System.Reflection;
using System.Windows;
using System.Windows.Automation;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
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
                // Load only the production theme, never App: its queued Startup acquires the
                // live single-instance mutex and can broadcast activation to the user's app.
                var app = new Application { ShutdownMode = ShutdownMode.OnExplicitShutdown };
                app.Resources.MergedDictionaries.Add(new ResourceDictionary
                {
                    Source = new Uri("pack://application:,,,/TGManager;component/Themes/Scarp.xaml")
                });
                var store = new Store();
                store.Settings.ContainerFolders.Add("Архив");
                store.Accounts.Add(new Account { Name = "Поддержка клиентов", Notes = "Входящие обращения", Folder = "Работа", Color = "#71C7F5" });
                store.Accounts.Add(new Account { Name = "Рабочий аккаунт", Notes = "Основной профиль", Color = "#6EE7B7",
                    Proxy = new ProxyCfg { Type = ProxyKinds.Socks5, Host = "127.0.0.1", Port = 1080 } });
                store.Accounts.Add(new Account { Name = "Личный архив", Color = "#C4B5FD" });
                var window = new MainWindow(store);
                if (!window.UseLayoutRounding || !window.SnapsToDevicePixels)
                    throw new InvalidOperationException("Main window must round native layout at every DPI");
                if (!window.FontFamily.Source.Contains("Assets/Fonts/#Inter") || !window.FontFamily.GetTypefaces().Any(typeface =>
                        typeface.TryGetGlyphTypeface(out var glyph) && glyph.FontUri.OriginalString.Contains("Assets/Fonts/")))
                    throw new InvalidOperationException("Main window must resolve bundled Inter instead of a system fallback");
                Pump();
                if (app.GetType() != typeof(Application) || app.Windows.Cast<Window>().Any(w => w.IsVisible))
                    throw new InvalidOperationException("Offscreen checks must suppress production startup and never show windows");
                ((DispatcherTimer)typeof(MainWindow).GetField("_poll", BindingFlags.Instance | BindingFlags.NonPublic)!.GetValue(window)!).Stop();
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
                Render(window, Path.Combine(output, "main.png"), 1260, 820);
                var comfortableHeight = CardHeight(list);
                if (Visible(list, 0, "Удалить") is false || Visible(list, 0, "Запуск") is false)
                    throw new InvalidOperationException("Default card must show every action");
                store.Settings.ListDensity = ListDensities.Compact;
                store.Settings.CardPadding = ListDensities.Presets[ListDensities.Compact].Padding;
                store.Settings.ButtonSize = ListDensities.Presets[ListDensities.Compact].ButtonSize;
                store.Settings.ButtonStyle = ListDensities.Presets[ListDensities.Compact].ButtonStyle;
                window.Layout.Apply(store.Settings);
                Render(window, Path.Combine(output, "main-compact.png"), 1260, 820);
                Render(window, Path.Combine(output, "main-compact-small.png"), 1040, 560);
                if (comfortableHeight / CardHeight(list) < 5d / 3)
                    throw new InvalidOperationException($"Compact card must fit 5 where comfortable fits 3 ({comfortableHeight} vs {CardHeight(list)})");
                store.Settings.CardButtons = [CardActions.Launch, CardActions.Stop];
                window.Layout.Apply(store.Settings);
                Render(window, Path.Combine(output, "main-compact-two-buttons.png"), 1260, 820);
                if (Visible(list, 0, "Удалить") is not false || Visible(list, 0, "Запуск") is not true)
                    throw new InvalidOperationException("Hidden card actions must disappear without a restart");
                store.Settings.ListDensity = ListDensities.Comfortable;
                store.Settings.CardPadding = ListDensities.Presets[ListDensities.Comfortable].Padding;
                store.Settings.ButtonSize = ListDensities.Presets[ListDensities.Comfortable].ButtonSize;
                store.Settings.ButtonStyle = ListDensities.Presets[ListDensities.Comfortable].ButtonStyle;
                store.Settings.CardButtons = [.. CardActions.All];
                window.Layout.Apply(store.Settings);
                Render(window, Path.Combine(output, "main.png"), 1260, 820);
                Render(window, Path.Combine(output, "main-small.png"), 1040, 560);
                AssertWithin(window, "SearchBox", 1040, 560);
                AssertWithin(window, "FolderFilter", 1040, 560);
                AssertWithin(window, "VersionText", 1040, 560);
                foreach (var scale in new[] { 1.25, 1.5, 2.0 })
                    Render(window, Path.Combine(output, $"main-dpi-{scale * 100:0}.png"), 1040, 560, scale);
                var editor = new AccountWindow(store.Accounts[0], ["Работа", "Архив"]);
                Render(editor, Path.Combine(output, "account.png"), (int)editor.Width, (int)editor.Height);
                ((ComboBox)editor.FindName("ProxyBox")).SelectedIndex = 2;
                ((TextBox)editor.FindName("LineBox")).Text = "socks5://demo:password@127.0.0.1:1080";
                if (((TextBox)editor.FindName("HostBox")).Text != "127.0.0.1" || ((PasswordBox)editor.FindName("PassBox")).Password != "password")
                    throw new InvalidOperationException("Proxy editor parsing failed");
                ((PasswordBox)editor.FindName("PassBox")).Password = "";
                ((TextBox)editor.FindName("LineBox")).Clear();
                Render(editor, Path.Combine(output, "account-proxy.png"), (int)editor.Width, (int)editor.Height);
                var settings = new SettingsWindow(store.Settings);
                var density = (ComboBox)settings.FindName("DensityBox");
                density.SelectedIndex = 1;
                if (((ComboBoxItem)((ComboBox)settings.FindName("StyleBox")).SelectedItem).Tag as string != ButtonStyles.Icon ||
                    ((ComboBoxItem)((ComboBox)settings.FindName("HeightBox")).SelectedItem).Tag as string != "6")
                    throw new InvalidOperationException("Compact density must apply its recommended card height and icon buttons");
                Render(settings, Path.Combine(output, "settings-compact.png"), (int)settings.Width, (int)settings.Height);
                density.SelectedIndex = 0;
                Render(settings, Path.Combine(output, "settings.png"), (int)settings.Width, (int)settings.Height);
                Render(settings, Path.Combine(output, "settings-small.png"), 520, 480);
                var cleanup = new CleanupWindow(store.Accounts[0]);
                var cleanupRun = (Button)cleanup.FindName("RunBtn");
                var cleanupConfirm = (CheckBox)cleanup.FindName("ConfirmChk");
                if (cleanupRun.IsEnabled) throw new InvalidOperationException("Cleanup must initially require confirmation");
                cleanupConfirm.IsChecked = true;
                if (!cleanupRun.IsEnabled) throw new InvalidOperationException("Cleanup confirmation binding failed");
                cleanupConfirm.IsChecked = false;
                if (cleanupRun.IsEnabled) throw new InvalidOperationException("Cleanup confirmation must reset when unchecked");
                Render(cleanup, Path.Combine(output, "cleanup.png"), (int)cleanup.Width, (int)cleanup.Height);
                Render(cleanup, Path.Combine(output, "cleanup-small.png"), 500, 520);
                AssertWithin(cleanup, "DryBtn", 500, 520);
                AssertWithin(cleanup, "RunBtn", 500, 520);
                AssertWithin(cleanup, "CloseBtn", 500, 520);
                search.Text = "missing";
                Render(window, Path.Combine(output, "search-empty.png"), 1040, 560);
                search.Clear();
                var folder = new FolderWindow(["Работа", "Архив"]);
                Render(folder, Path.Combine(output, "folder.png"), 440, 290);
                ((TextBox)folder.FindName("NameBox")).Text = " Работа ";
                Invoke(folder, "OnSave", folder, new RoutedEventArgs());
                if (string.IsNullOrWhiteSpace(((TextBlock)folder.FindName("ErrorText")).Text) || folder.Result != "")
                    throw new InvalidOperationException("Duplicate folder validation failed");
                Render(folder, Path.Combine(output, "folder-error.png"), 440, 310);

                var confirm = new ConfirmWindow();
                ((TextBlock)confirm.FindName("TitleText")).Text = "Удалить контейнер?";
                ((TextBlock)confirm.FindName("BodyText")).Text = "Выберите, сохранять ли папку с данными (tdata). Отмена оставляет контейнер без изменений.";
                Invoke(confirm, "AddGhost", "Отмена", ConfirmWindow.Choice.Cancel, true);
                Invoke(confirm, "AddGhost", "Удалить, папку оставить", ConfirmWindow.Choice.Accept, false);
                Invoke(confirm, "AddDanger", "Удалить с данными", ConfirmWindow.Choice.Destructive);
                Render(confirm, Path.Combine(output, "confirm-delete.png"), 620, 230);
                if (confirm.ResultChoice != ConfirmWindow.Choice.Cancel || ((Panel)confirm.FindName("Buttons")).Children.Count != 3)
                    throw new InvalidOperationException("Deletion must retain all three choices and cancellation default");

                var download = new DownloadWindow("Переносной Telegram", "Официальный Telegram Desktop будет установлен в папку программы.", DownloadKind.Telegram);
                Render(download, Path.Combine(output, "download.png"), 520, 360);
                // Never raise Loaded for the download dialog: UI rendering must not download or install anything.
                download.Close();

                for (var repeat = 0; repeat < 12; repeat++)
                {
                    ((Button)window.FindName("NavTasks")).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
                    ((Button)window.FindName("NavContainers")).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
                }
                Pump();
                if (((FrameworkElement)window.FindName("ContainersPage")).Visibility != Visibility.Visible ||
                    ((FrameworkElement)window.FindName("TasksPage")).Visibility != Visibility.Collapsed ||
                    ((Button)window.FindName("NavContainers")).Tag as string != "active")
                    throw new InvalidOperationException("Interrupted navigation must leave only the last page active");
                ((Button)window.FindName("NavTasks")).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
                Pump();
                Render(window, Path.Combine(output, "tasks-empty.png"), 1260, 820);
                var task = new TGManager.ViewModels.TaskVm(store.Accounts[0], ["channels", "groups"], false);
                Invoke(task, "Apply", new WorkerEvent { Type = "summary", Total = 12 });
                Invoke(task, "Apply", new WorkerEvent { Type = "progress", Done = 5, Total = 12, Label = "Проверка выбранных разделов" });
                window.Tasks.Add(task);
                Invoke(window, "RefreshTasksNav");
                Render(window, Path.Combine(output, "tasks.png"), 1260, 820);
                Render(window, Path.Combine(output, "tasks-small.png"), 1040, 560);
                AssertWithin(window, "NavTasksLabel", 1040, 560);
                var log = new TaskLogWindow(task);
                Render(log, Path.Combine(output, "task-log.png"), 580, 440);
                Render(log, Path.Combine(output, "task-log-small.png"), 480, 320);
                log.Close();
                task.Stop();
                window.Tasks.Clear();
                task.Host.Dispose();

                foreach (var scale in new[] { 1.25, 1.5, 2.0 })
                {
                    Render(editor, Path.Combine(output, $"account-dpi-{scale * 100:0}.png"), 520, 720, scale);
                    Render(settings, Path.Combine(output, $"settings-dpi-{scale * 100:0}.png"), 520, 480, scale);
                    Render(cleanup, Path.Combine(output, $"cleanup-dpi-{scale * 100:0}.png"), 500, 520, scale);
                }
                editor.Close(); settings.Close(); cleanup.Close(); folder.Close(); confirm.Close();
                for (var repeat = 0; repeat < 5; repeat++)
                {
                    var cancelledEditor = new AccountWindow(store.Accounts[0]);
                    ((TextBox)cancelledEditor.FindName("NameBox")).Text = "Unsaved edit";
                    cancelledEditor.Close();
                    if (store.Accounts[0].Name != "Поддержка клиентов" || cancelledEditor.Result is not null)
                        throw new InvalidOperationException("Interrupted account edit must not change stored data");
                    var cancelledSettings = new SettingsWindow(store.Settings);
                    ((TextBox)cancelledSettings.FindName("TgBox")).Text = "Unsaved path";
                    ((CheckBox)cancelledSettings.FindName("ManyChk")).IsChecked = !store.Settings.AllowMany;
                    cancelledSettings.Close();
                    if (store.Settings.TelegramBinary == "Unsaved path" || !store.Settings.AllowMany)
                        throw new InvalidOperationException("Interrupted settings edit must not change stored data");
                }
                var empty = new MainWindow(new Store());
                Render(empty, Path.Combine(output, "containers-empty.png"), 1040, 560);
                empty.Close();
                window.Close();
                if (app.Windows.Cast<Window>().Any(w => w.IsVisible))
                    throw new InvalidOperationException("UI checks must never expose a window on the active desktop");
                app.Shutdown();
                Console.WriteLine("PASS Offscreen startup isolation: no production mutex, broadcast, app launch or visible windows");
                Console.WriteLine("PASS Bundled Inter, native layout, search, folders, sorting, proxy parsing and cleanup safeguards");
                Console.WriteLine("PASS Compact container cards fit 5 where comfortable fits 3; card actions and density apply live");
                Console.WriteLine("PASS Repeated/interrupted navigation and account/settings cancellation; all native dialogs");
                Console.WriteLine("PASS Offscreen WPF renders at minimum size and 100/125/150/200 percent DPI");
            }
            catch (Exception ex) { failure = ex; }
        });
        thread.SetApartmentState(ApartmentState.STA);
        thread.Start();
        thread.Join();
        if (failure is not null) throw new InvalidOperationException("WPF checks failed", failure);
    }

    static void Invoke(object target, string name, params object[] args)
        => target.GetType().GetMethod(name, BindingFlags.Instance | BindingFlags.NonPublic)!.Invoke(target, args);

    static void Pump()
    {
        var frame = new DispatcherFrame();
        var timer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(180) };
        timer.Tick += (_, _) => { timer.Stop(); frame.Continue = false; };
        timer.Start();
        Dispatcher.PushFrame(frame);
    }

    static double CardHeight(ItemsControl list)
        => ((FrameworkElement)list.ItemContainerGenerator.ContainerFromIndex(0)).ActualHeight;

    /// <summary>Показана ли кнопка карточки (Visibility; окно не отображается) с таким AutomationProperties.Name; null — кнопки нет.</summary>
    static bool? Visible(ItemsControl list, int index, string name)
    {
        var button = Descendants((DependencyObject)list.ItemContainerGenerator.ContainerFromIndex(index))
            .OfType<Button>().FirstOrDefault(b => AutomationProperties.GetName(b) == name);
        return button is null ? null : button.Visibility == Visibility.Visible;
    }

    static IEnumerable<DependencyObject> Descendants(DependencyObject parent)
    {
        for (var i = 0; i < VisualTreeHelper.GetChildrenCount(parent); i++)
        {
            var child = VisualTreeHelper.GetChild(parent, i);
            yield return child;
            foreach (var nested in Descendants(child)) yield return nested;
        }
    }

    static void AssertWithin(Window window, string name, int width, int height)
    {
        var element = (FrameworkElement)window.FindName(name);
        var bounds = element.TransformToAncestor((Visual)window.Content).TransformBounds(new Rect(element.RenderSize));
        if (bounds.Left < 0 || bounds.Top < 0 || bounds.Right > width + 1 || bounds.Bottom > height + 1 || bounds.Width <= 0)
            throw new InvalidOperationException($"{name} is clipped outside the minimum-size window: {bounds}");
    }

    static void Render(Window window, string path, int width, int height, double scale = 1)
    {
        var content = (FrameworkElement)window.Content;
        VisualTreeHelper.SetRootDpi(content, new DpiScale(scale, scale));
        content.Measure(new Size(width, height));
        content.Arrange(new Rect(0, 0, width, height));
        content.UpdateLayout();
        var bitmap = new RenderTargetBitmap((int)Math.Ceiling(width * scale), (int)Math.Ceiling(height * scale), 96 * scale, 96 * scale, PixelFormats.Pbgra32);
        bitmap.Render(content);
        var encoder = new PngBitmapEncoder();
        encoder.Frames.Add(BitmapFrame.Create(bitmap));
        using var file = File.Create(path);
        encoder.Save(file);
    }

}
