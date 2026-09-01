using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Interop;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.Windows.Shell;
using TGManager.Native;

namespace TGManager.Services;

public static class Chrome
{
    static readonly Duration FadeIn = new(TimeSpan.FromMilliseconds(160));

    /// <summary>
    /// Общий «хром» для всех окон: тёмный DWM, скругление, клип содержимого,
    /// корректный maximize (не наезжаем на панель задач) и плавное появление.
    /// </summary>
    public static void Attach(Window window, Border frame)
    {
        window.SourceInitialized += (_, _) =>
        {
            AcrylicHelper.Apply(window);
            WindowCorners.Apply(window);
            WindowCorners.ClipFrame(frame, window);
            if (window.ResizeMode is ResizeMode.CanResize or ResizeMode.CanResizeWithGrip)
            {
                var hwnd = new WindowInteropHelper(window).Handle;
                HwndSource.FromHwnd(hwnd)?.AddHook((IntPtr h, int msg, IntPtr wp, IntPtr lp, ref bool handled) =>
                    MinMaxHook(window, h, msg, lp, ref handled));
            }
        };
        frame.SizeChanged += (_, _) => WindowCorners.ClipFrame(frame, window);
        window.StateChanged += (_, _) => WindowCorners.ClipFrame(frame, window);
        window.DpiChanged += (_, _) => WindowCorners.ClipFrame(frame, window);

        // Плавное появление. Opacity анимируется только у окон с AllowsTransparency — у нас все такие.
        if (window.AllowsTransparency)
        {
            window.Opacity = 0;
            window.Loaded += (_, _) =>
            {
                var anim = new DoubleAnimation(0, 1, FadeIn) { EasingFunction = new CubicEase { EasingMode = EasingMode.EaseOut } };
                window.BeginAnimation(UIElement.OpacityProperty, anim);
            };
        }
    }

    /// <summary>
    /// WM_GETMINMAXINFO: у окон без рамки (WindowStyle=None + AllowsTransparency) maximize
    /// по умолчанию накрывает панель задач и вылезает за края монитора. Ограничиваем рабочей областью.
    /// </summary>
    static IntPtr MinMaxHook(Window window, IntPtr hwnd, int msg, IntPtr lParam, ref bool handled)
    {
        if (msg != NativeMethods.WM_GETMINMAXINFO) return IntPtr.Zero;
        try
        {
            var mmi = Marshal.PtrToStructure<NativeMethods.MINMAXINFO>(lParam);
            var monitor = NativeMethods.MonitorFromWindow(hwnd, NativeMethods.MONITOR_DEFAULTTONEAREST);
            if (monitor != IntPtr.Zero)
            {
                var info = new NativeMethods.MONITORINFO { cbSize = Marshal.SizeOf<NativeMethods.MONITORINFO>() };
                if (NativeMethods.GetMonitorInfo(monitor, ref info))
                {
                    var work = info.rcWork;
                    var mon = info.rcMonitor;
                    mmi.ptMaxPosition.x = Math.Abs(work.left - mon.left);
                    mmi.ptMaxPosition.y = Math.Abs(work.top - mon.top);
                    mmi.ptMaxSize.x = Math.Abs(work.right - work.left);
                    mmi.ptMaxSize.y = Math.Abs(work.bottom - work.top);
                    mmi.ptMaxTrackSize.x = mmi.ptMaxSize.x;
                    mmi.ptMaxTrackSize.y = mmi.ptMaxSize.y;
                }
            }
            var dpi = VisualTreeHelper.GetDpi(window);
            if (!double.IsNaN(window.MinWidth) && window.MinWidth > 0)
                mmi.ptMinTrackSize.x = (int)Math.Ceiling(window.MinWidth * dpi.DpiScaleX);
            if (!double.IsNaN(window.MinHeight) && window.MinHeight > 0)
                mmi.ptMinTrackSize.y = (int)Math.Ceiling(window.MinHeight * dpi.DpiScaleY);
            Marshal.StructureToPtr(mmi, lParam, true);
            handled = true;
        }
        catch { /* оставляем системные значения */ }
        return IntPtr.Zero;
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

    /// <summary>Плавная смена страниц: показать <paramref name="show"/>, скрыть <paramref name="hide"/>.</summary>
    public static void CrossFade(UIElement show, UIElement hide, int ms = 140)
    {
        if (ReferenceEquals(show, hide)) return;
        hide.Visibility = Visibility.Collapsed;
        hide.BeginAnimation(UIElement.OpacityProperty, null);
        hide.Opacity = 1;
        show.Opacity = 0;
        show.Visibility = Visibility.Visible;
        var anim = new DoubleAnimation(0, 1, new Duration(TimeSpan.FromMilliseconds(ms)))
        {
            EasingFunction = new CubicEase { EasingMode = EasingMode.EaseOut },
        };
        show.BeginAnimation(UIElement.OpacityProperty, anim);
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
