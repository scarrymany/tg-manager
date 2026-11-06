// Regenerates README media from the real WPF windows: docs/screens/*.png and docs/media/showcase.gif.
// Windows only. Run from the repository root:  dotnet run --project docs/showcase -c Release
// Needs ffmpeg on PATH for the GIF. Nothing is launched and no window is shown.
using System.IO;
using System.Reflection;
using System.Windows;
using System.Windows.Automation;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using TGManager.Services;
using TGManager.ViewModels;
using TGManager.Windows;

const int MainWidth = 1260;
const int MainHeight = 820;
const double ShotScale = 2;
const int GifWidth = 1100;
const int GifHeight = 680;
const double GifScale = 0.85;
const string LaunchAction = "Запуск";
const string SearchQuery = "клиент";
const int PageFadeMs = 450;
const string DemoAccountsDir = @"D:\TG-Manager\accounts";
const string SettingsListSection = "СПИСОК КОНТЕЙНЕРОВ";
const double SettingsScrollMargin = 24;
const int TaskTickMs = 40;
const int TaskSteps = 14;

var repo = FindRepoRoot();
var screens = Path.Combine(repo, "docs", "screens");
var gifPath = Path.Combine(repo, "docs", "media", "showcase.gif");
var framesDir = Path.Combine(Path.GetTempPath(), "tg-manager-showcase");

Exception? failure = null;
var thread = new Thread(() =>
{
    try
    {
        // Theme only, never App: its Startup takes the single-instance mutex of a running TG Manager.
        var app = new Application { ShutdownMode = ShutdownMode.OnExplicitShutdown };
        app.Resources.MergedDictionaries.Add(new ResourceDictionary
        {
            Source = new Uri("pack://application:,,,/TGManager;component/Themes/Scarp.xaml"),
        });
        var store = Demo.CreateStore();
        Demo.Materialize(store);
        RenderScreens(store);
        RecordGif(Demo.CreateStore());
        app.Shutdown();
    }
    catch (Exception ex) { failure = ex; }
    finally { Demo.Cleanup(); }
});
thread.SetApartmentState(ApartmentState.STA);
thread.Start();
thread.Join();
if (failure is not null)
{
    Console.Error.WriteLine(failure);
    return 1;
}
Console.WriteLine($"Screens: {screens}");
Console.WriteLine($"GIF: {gifPath} ({new FileInfo(gifPath).Length / 1024} KB)");
return 0;

void RenderScreens(Store store)
{
    var window = CreateMain(store);
    var demo = StartDemoTasks(window, store);
    Shot(window, "main.png", MainWidth, MainHeight);

    ApplyDensity(window, store, ListDensities.Comfortable);
    Shot(window, "main-comfortable.png", MainWidth, MainHeight);

    Navigate(window, "NavTasks");
    Shot(window, "tasks.png", MainWidth, MainHeight);

    var editor = new AccountWindow(store.Accounts[0], store.Settings.ContainerFolders);
    Shot(editor, "account.png", (int)editor.Width, (int)editor.Height);

    var cleanup = new CleanupWindow(store.Accounts[3]);
    Shot(cleanup, "cleanup.png", (int)cleanup.Width, (int)cleanup.Height);

    var settings = new SettingsWindow(store.Settings);
    ((ComboBox)settings.FindName("DensityBox")).SelectedIndex = 1;
    // The real label shows where this generator runs from; README should show an ordinary install.
    ((TextBlock)settings.FindName("DataLabel")).Text = "Данные контейнеров: " + DemoAccountsDir;
    Capture.Render(settings, (int)settings.Width, (int)settings.Height, ShotScale);
    var scroller = Capture.Descendants((DependencyObject)settings.Content).OfType<ScrollViewer>().First();
    var listSection = Capture.Descendants(scroller).OfType<TextBlock>().First(t => t.Text == SettingsListSection);
    scroller.ScrollToVerticalOffset(listSection.TransformToAncestor((Visual)scroller.Content).Transform(default).Y - SettingsScrollMargin);
    Shot(settings, "settings.png", (int)settings.Width, (int)settings.Height);

    var log = new TaskLogWindow(demo.Cleanup);
    Shot(log, "task-log.png", 580, 440);

    var folder = new FolderWindow(store.Settings.ContainerFolders);
    ((TextBox)folder.FindName("NameBox")).Text = "Проекты";
    Shot(folder, "folder.png", 440, 290);

    foreach (var dialog in new Window[] { editor, cleanup, settings, log, folder }) dialog.Close();
    CloseMain(window);
    demo.Dispose();
}

void RecordGif(Store store)
{
    var window = CreateMain(store);
    var demo = StartDemoTasks(window, store);
    var accounts = window.Accounts;
    var opening = Scene();
    var rest = new Point(opening.PixelWidth * 0.72, opening.PixelHeight * 0.86);
    var rec = new GifRecorder(framesDir, opening, rest, GifScale);
    rec.Hold(1200);

    foreach (var index in new[] { 1, 5 })
    {
        rec.Move(Locate(LaunchButton(window, index)), 620);
        accounts[index].Running = true;
        rec.Click(Scene());
        rec.Hold(450);
    }

    var search = (TextBox)window.FindName("SearchBox");
    rec.Move(Locate(search, 0.12), 650);
    rec.Click();
    for (var length = 1; length <= SearchQuery.Length; length++)
    {
        search.Text = SearchQuery[..length];
        rec.Cut(Scene());
        rec.Hold(110);
    }
    rec.Hold(1300);
    search.Clear();
    rec.Fade(Scene(), 280);

    var folders = (ComboBox)window.FindName("FolderFilter");
    rec.Move(Locate(folders, 0.3), 700);
    folders.SelectedItem = folders.Items.Cast<ComboBoxItem>().Single(item => item.Tag as string == Demo.Work);
    rec.Click();
    rec.Fade(Scene(), 280);
    rec.Hold(1300);

    rec.Move(Locate((FrameworkElement)window.FindName("NavTasks"), 0.3), 650);
    rec.Click();
    folders.SelectedIndex = 0;
    Navigate(window, "NavTasks");
    rec.Fade(Scene(), 300);
    for (var step = 1; step <= TaskSteps; step++)
    {
        demo.Advance(step);
        if (demo.Export.Finished && accounts[DemoTasks.ExportAccountIndex].Busy)
        {
            accounts[DemoTasks.ExportAccountIndex].Busy = false;
            RefreshTasksNav(window);
        }
        Capture.Wait(TaskTickMs);
        rec.Cut(Scene());
        rec.Hold(150);
    }
    rec.Hold(1300);

    rec.Move(Locate((FrameworkElement)window.FindName("NavContainers"), 0.3), 600);
    rec.Click();
    Navigate(window, "NavContainers");
    rec.Fade(Scene(), 300);
    rec.Hold(700);
    rec.Move(rest, 650);
    rec.Fade(opening, 400);
    rec.Encode(gifPath);

    CloseMain(window);
    demo.Dispose();

    BitmapSource Scene() => Capture.Render(window, GifWidth, GifHeight, GifScale);
    Point Locate(FrameworkElement element, double rx = 0.5) => Capture.Locate(window, element, GifScale, rx);
}

void Shot(Window window, string name, int width, int height)
    => Capture.Save(Capture.Render(window, width, height, ShotScale), Path.Combine(screens, name));

static MainWindow CreateMain(Store store)
{
    var window = new MainWindow(store);
    // The status poll would reset demo states from the real process list.
    ((DispatcherTimer)typeof(MainWindow).GetField("_poll", BindingFlags.Instance | BindingFlags.NonPublic)!.GetValue(window)!).Stop();
    ApplyDensity(window, store, ListDensities.Compact);
    var accounts = window.Accounts;
    foreach (var index in new[] { 0, 2, 4 }) accounts[index].Running = true;
    return window;
}

// Closing with running tasks asks for confirmation in a modal dialog that nobody could answer.
static void CloseMain(MainWindow window)
{
    window.Tasks.Clear();
    window.Close();
}

static void ApplyDensity(MainWindow window, Store store, string density)
{
    var preset = ListDensities.Presets[density];
    store.Settings.ListDensity = density;
    store.Settings.CardPadding = preset.Padding;
    store.Settings.ButtonSize = preset.ButtonSize;
    store.Settings.ButtonStyle = preset.ButtonStyle;
    window.Layout.Apply(store.Settings);
}

static void Navigate(MainWindow window, string button)
{
    ((Button)window.FindName(button)).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
    Capture.Wait(PageFadeMs);
}

static DemoTasks StartDemoTasks(MainWindow window, Store store)
{
    var demo = new DemoTasks(store);
    foreach (var task in demo.All) window.Tasks.Add(task);
    window.Accounts[DemoTasks.CleanupAccountIndex].BusyLabel = "Чистка…";
    window.Accounts[DemoTasks.CleanupAccountIndex].Busy = true;
    // Same labels MainWindow sets when it starts these tasks.
    window.Accounts[DemoTasks.ExportAccountIndex].BusyLabel = "Експорт…";
    window.Accounts[DemoTasks.ExportAccountIndex].Busy = true;
    RefreshTasksNav(window);
    return demo;
}

static void RefreshTasksNav(MainWindow window)
    => typeof(MainWindow).GetMethod("RefreshTasksNav", BindingFlags.Instance | BindingFlags.NonPublic)!.Invoke(window, null);

static FrameworkElement LaunchButton(MainWindow window, int index)
{
    var list = (ItemsControl)window.FindName("AccountList");
    var card = (DependencyObject)list.ItemContainerGenerator.ContainerFromIndex(index);
    return Capture.Descendants(card).OfType<Button>().First(b => AutomationProperties.GetName(b) == LaunchAction);
}

static string FindRepoRoot()
{
    for (var dir = new DirectoryInfo(AppContext.BaseDirectory); dir is not null; dir = dir.Parent)
        if (File.Exists(Path.Combine(dir.FullName, "TGManager.sln"))) return dir.FullName;
    throw new InvalidOperationException("TGManager.sln not found above " + AppContext.BaseDirectory);
}
