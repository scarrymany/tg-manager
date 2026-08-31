using System.Windows;
using System.Windows.Interop;
using System.Windows.Media;
using TGManager.Native;

namespace TGManager.Services;

public static class AcrylicHelper
{
    public static bool Apply(Window window)
    {
        var hwnd = new WindowInteropHelper(window).EnsureHandle();
        var source = HwndSource.FromHwnd(hwnd);
        if (source?.CompositionTarget is { } target)
            target.BackgroundColor = Colors.Transparent;

        var dark = 1;
        NativeMethods.DwmSetWindowAttribute(hwnd, NativeMethods.DWMWA_USE_IMMERSIVE_DARK_MODE, ref dark, sizeof(int));
        NativeMethods.DwmSetWindowAttribute(hwnd, NativeMethods.DWMWA_USE_IMMERSIVE_DARK_MODE_OLD, ref dark, sizeof(int));

        var none = NativeMethods.DWMSBT_NONE;
        NativeMethods.DwmSetWindowAttribute(hwnd, NativeMethods.DWMWA_SYSTEMBACKDROP_TYPE, ref none, sizeof(int));
        var micaOff = 0;
        NativeMethods.DwmSetWindowAttribute(hwnd, NativeMethods.DWMWA_MICA_EFFECT, ref micaOff, sizeof(int));

        var margins = new NativeMethods.Margins();
        NativeMethods.DwmExtendFrameIntoClientArea(hwnd, ref margins);

        NativeMethods.SetWindowRgn(hwnd, IntPtr.Zero, true);
        var square = NativeMethods.DWMWCP_DONOTROUND;
        NativeMethods.DwmSetWindowAttribute(hwnd, NativeMethods.DWMWA_WINDOW_CORNER_PREFERENCE, ref square, sizeof(int));

        window.Background = Brushes.Transparent;
        return NativeMethods.IsWindows11();
    }
}
