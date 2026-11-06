using System.IO;
using System.Windows;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;

/// <summary>Offscreen rendering of WPF windows that are never shown on the desktop.</summary>
internal static class Capture
{
    public static BitmapSource Render(Window window, int width, int height, double scale)
    {
        Settle();
        var content = (FrameworkElement)window.Content;
        VisualTreeHelper.SetRootDpi(content, new DpiScale(scale, scale));
        content.Measure(new Size(width, height));
        content.Arrange(new Rect(0, 0, width, height));
        content.UpdateLayout();
        var bitmap = new RenderTargetBitmap(Pixels(width, scale), Pixels(height, scale), 96 * scale, 96 * scale, PixelFormats.Pbgra32);
        bitmap.Render(content);
        bitmap.Freeze();
        return bitmap;
    }

    public static void Save(BitmapSource bitmap, string path)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        var encoder = new PngBitmapEncoder();
        encoder.Frames.Add(BitmapFrame.Create(bitmap));
        using var file = File.Create(path);
        encoder.Save(file);
    }

    /// <summary>
    /// Point inside an element in output pixels of a window rendered at <paramref name="scale"/>;
    /// <paramref name="rx"/> and <paramref name="ry"/> are fractions of its width and height.
    /// </summary>
    public static Point Locate(Window window, FrameworkElement element, double scale, double rx = 0.5, double ry = 0.5)
    {
        var point = element.TransformToAncestor((Visual)window.Content)
            .Transform(new Point(element.ActualWidth * rx, element.ActualHeight * ry));
        return new Point(point.X * scale, point.Y * scale);
    }

    /// <summary>Runs queued bindings, layout and render work without showing the window.</summary>
    public static void Settle() => Dispatcher.CurrentDispatcher.Invoke(DispatcherPriority.ContextIdle, () => { });

    /// <summary>Lets wall-clock animations (page cross-fades) finish.</summary>
    public static void Wait(int milliseconds)
    {
        var frame = new DispatcherFrame();
        var timer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(milliseconds) };
        timer.Tick += (_, _) => { timer.Stop(); frame.Continue = false; };
        timer.Start();
        Dispatcher.PushFrame(frame);
    }

    public static IEnumerable<DependencyObject> Descendants(DependencyObject parent)
    {
        for (var i = 0; i < VisualTreeHelper.GetChildrenCount(parent); i++)
        {
            var child = VisualTreeHelper.GetChild(parent, i);
            yield return child;
            foreach (var nested in Descendants(child)) yield return nested;
        }
    }

    static int Pixels(int size, double scale) => (int)Math.Ceiling(size * scale);
}
