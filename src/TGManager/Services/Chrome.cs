using System.Windows;
using System.Windows.Controls;
using System.Windows.Interop;
using System.Windows.Shell;
using TGManager.Native;

namespace TGManager.Services;

public static class Chrome
{
    public static void Attach(Window window, Border frame)
    {
        window.SourceInitialized += (_, _) =>
        {
            AcrylicHelper.Apply(window);
            WindowCorners.Apply(window);
            WindowCorners.ClipFrame(frame, window);
        };
        window.SizeChanged += (_, _) => WindowCorners.ClipFrame(frame, window);
        window.StateChanged += (_, _) => WindowCorners.ClipFrame(frame, window);
        window.DpiChanged += (_, _) => WindowCorners.ClipFrame(frame, window);
    }

    public static void Minimize(Window w) => w.WindowState = WindowState.Minimized;

    public static void ToggleMax(Window w)
        => w.WindowState = w.WindowState == WindowState.Maximized ? WindowState.Normal : WindowState.Maximized;

    public static void Close(Window w) => w.Close();

    public static void ActivateExisting(Window? window)
    {
        if (window is null) return;
        if (!window.IsVisible) window.Show();
        if (window.WindowState == WindowState.Minimized) window.WindowState = WindowState.Normal;
        window.Activate();
        var hwnd = new WindowInteropHelper(window).Handle;
        if (hwnd == IntPtr.Zero) return;
        if (NativeMethods.IsIconic(hwnd))
            NativeMethods.ShowWindow(hwnd, NativeMethods.SW_RESTORE);
        NativeMethods.SetForegroundWindow(hwnd);
    }

    public static WindowChrome Make(double captionHeight = 48)
        => new()
        {
            CaptionHeight = captionHeight,
            ResizeBorderThickness = new Thickness(6),
            GlassFrameThickness = new Thickness(0),
            CornerRadius = new CornerRadius(16),
            UseAeroCaptionButtons = false,
            NonClientFrameEdges = NonClientFrameEdges.None,
        };
}
