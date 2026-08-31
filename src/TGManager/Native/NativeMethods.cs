using System.Runtime.InteropServices;

namespace TGManager.Native;

internal static class NativeMethods
{
    public const int DWMWA_USE_IMMERSIVE_DARK_MODE_OLD = 19;
    public const int DWMWA_USE_IMMERSIVE_DARK_MODE = 20;
    public const int DWMWA_WINDOW_CORNER_PREFERENCE = 33;
    public const int DWMWA_SYSTEMBACKDROP_TYPE = 38;
    public const int DWMWA_MICA_EFFECT = 1029;

    public const int DWMSBT_NONE = 1;
    public const int DWMWCP_DONOTROUND = 1;

    public const int SW_RESTORE = 9;
    public const uint PROCESS_TERMINATE = 0x0001;
    public const uint PROCESS_QUERY_LIMITED_INFORMATION = 0x1000;
    public const uint STILL_ACTIVE = 259;
    public const uint CREATE_NO_WINDOW = 0x08000000;
    public const uint CREATE_NEW_PROCESS_GROUP = 0x00000200;
    public const uint DETACHED_PROCESS = 0x00000008;
    public const uint CREATE_BREAKAWAY_FROM_JOB = 0x01000000;

    public static readonly IntPtr HWND_BROADCAST = new(0xFFFF);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    public static extern uint RegisterWindowMessage(string lpString);

    [DllImport("user32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool PostMessage(IntPtr hWnd, uint msg, IntPtr wParam, IntPtr lParam);

    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

    [DllImport("user32.dll")]
    public static extern bool IsIconic(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern int SetWindowRgn(IntPtr hWnd, IntPtr hRgn, [MarshalAs(UnmanagedType.Bool)] bool bRedraw);

    [DllImport("dwmapi.dll")]
    public static extern int DwmSetWindowAttribute(IntPtr hwnd, int attribute, ref int value, int size);

    [DllImport("dwmapi.dll")]
    public static extern int DwmExtendFrameIntoClientArea(IntPtr hwnd, ref Margins margins);

    [DllImport("ntdll.dll")]
    public static extern int RtlGetVersion(ref OsVersionInfoW info);

    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern IntPtr OpenProcess(uint access, bool inherit, int pid);

    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool TerminateProcess(IntPtr handle, uint code);

    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool GetExitCodeProcess(IntPtr handle, out uint code);

    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool CloseHandle(IntPtr handle);

    [DllImport("shell32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    public static extern int SetCurrentProcessExplicitAppUserModelID(string appID);

    [StructLayout(LayoutKind.Sequential)]
    public struct Margins
    {
        public int cxLeftWidth;
        public int cxRightWidth;
        public int cyTopHeight;
        public int cyBottomHeight;
    }

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    public struct OsVersionInfoW
    {
        public uint dwOSVersionInfoSize;
        public uint dwMajorVersion;
        public uint dwMinorVersion;
        public uint dwBuildNumber;
        public uint dwPlatformId;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)]
        public string szCSDVersion;
    }

    public static bool IsWindows11()
    {
        var info = new OsVersionInfoW
        {
            dwOSVersionInfoSize = (uint)Marshal.SizeOf<OsVersionInfoW>(),
            szCSDVersion = string.Empty,
        };
        if (RtlGetVersion(ref info) != 0)
            return false;
        return info.dwMajorVersion >= 10 && info.dwBuildNumber >= 22000;
    }

    public static bool IsAlive(int pid)
    {
        if (pid <= 0) return false;
        var h = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, false, pid);
        if (h == IntPtr.Zero) return false;
        try
        {
            return GetExitCodeProcess(h, out var code) && code == STILL_ACTIVE;
        }
        finally { CloseHandle(h); }
    }

    public static bool KillPid(int pid)
    {
        if (pid <= 0) return false;
        var h = OpenProcess(PROCESS_TERMINATE | PROCESS_QUERY_LIMITED_INFORMATION, false, pid);
        if (h == IntPtr.Zero) return false;
        try
        {
            return TerminateProcess(h, 1);
        }
        finally { CloseHandle(h); }
    }
}
