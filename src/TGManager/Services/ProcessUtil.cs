using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using TGManager.Native;

namespace TGManager.Services;

public static class ProcessUtil
{
    public const string PidFile = "telegram.pid";
    public const string BridgePidFile = "http_bridge.pid";

    public static void WritePid(string workdir, int pid, string name = PidFile)
    {
        try { File.WriteAllText(Path.Combine(workdir, name), pid.ToString()); }
        catch { /* ignore */ }
    }

    public static void ClearPid(string workdir, string name = PidFile)
    {
        try { File.Delete(Path.Combine(workdir, name)); }
        catch { /* ignore */ }
    }

    static int ReadPid(string workdir, string name)
    {
        try
        {
            return int.TryParse(File.ReadAllText(Path.Combine(workdir, name)).Trim(), out var pid) ? pid : 0;
        }
        catch { return 0; }
    }

    public static bool IsRunning(string workdir) => PidsForWorkdir(workdir).Count > 0;

    public static List<int> PidsForWorkdir(string workdir)
    {
        var found = new List<int>();
        var seen = new HashSet<int>();
        var marker = Path.GetFullPath(workdir).ToLowerInvariant().TrimEnd('\\', '/');
        var my = Environment.ProcessId;
        var snap = Snapshot();

        void Add(int pid)
        {
            if (pid <= 0 || pid == my || !seen.Add(pid)) return;
            if (NativeMethods.IsAlive(pid)) found.Add(pid);
        }

        void AddTree(int pid)
        {
            Add(pid);
            foreach (var c in snap.Where(x => x.Parent == pid).Select(x => x.Pid))
                AddTree(c);
        }

        var pf = ReadPid(workdir, PidFile);
        if (pf > 0) AddTree(pf);
        var br = ReadPid(workdir, BridgePidFile);
        if (br > 0) AddTree(br);

        foreach (var row in snap)
        {
            if (row.Pid == my) continue;
            var name = row.Name.ToLowerInvariant();
            var cmd = (GetCommandLine(row.Pid) ?? "").ToLowerInvariant();
            var blob = name + " " + cmd;
            var isTarget = blob.Contains("telegram") || blob.Contains("proxychains")
                           || blob.Contains("--tg-http-bridge");
            if (!isTarget) continue;
            if (blob.Contains("--tg-worker")) continue;
            var norm = blob.Replace('/', '\\');
            if (norm.Contains(marker) || blob.Contains(marker.Replace('\\', '/')))
                AddTree(row.Pid);
        }
        return found;
    }

    public static int Terminate(string workdir)
    {
        var count = 0;
        for (var round = 0; round < 4; round++)
        {
            var pids = PidsForWorkdir(workdir);
            if (pids.Count == 0 && round > 0) break;
            foreach (var pid in pids)
            {
                if (KillTree(pid)) count++;
            }
            if (round < 3) Thread.Sleep(120);
        }
        ClearPid(workdir, PidFile);
        ClearPid(workdir, BridgePidFile);
        try { File.Delete(Path.Combine(workdir, "http_bridge.ready")); } catch { /* ignore */ }
        return count;
    }

    public static bool KillTree(int pid)
    {
        var ok = NativeMethods.KillPid(pid);
        try
        {
            using var p = Process.Start(new ProcessStartInfo
            {
                FileName = "taskkill",
                Arguments = $"/F /T /PID {pid}",
                UseShellExecute = false,
                CreateNoWindow = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
            });
            p?.WaitForExit(6000);
            ok = true;
        }
        catch { /* ignore */ }
        if (NativeMethods.IsAlive(pid))
            ok = NativeMethods.KillPid(pid) || ok;
        return ok;
    }

    record Snap(int Pid, int Parent, string Name);

    static List<Snap> Snapshot()
    {
        var list = new List<Snap>();
        var snap = CreateToolhelp32Snapshot(2, 0); // TH32CS_SNAPPROCESS
        if (snap == new IntPtr(-1)) return list;
        try
        {
            var pe = new PROCESSENTRY32 { dwSize = (uint)Marshal.SizeOf<PROCESSENTRY32>() };
            if (!Process32First(snap, ref pe)) return list;
            do
            {
                list.Add(new Snap((int)pe.th32ProcessID, (int)pe.th32ParentProcessID, pe.szExeFile ?? ""));
            } while (Process32Next(snap, ref pe));
        }
        finally { NativeMethods.CloseHandle(snap); }
        return list;
    }

    static string? GetCommandLine(int pid)
    {
        var h = NativeMethods.OpenProcess(NativeMethods.PROCESS_QUERY_LIMITED_INFORMATION, false, pid);
        if (h == IntPtr.Zero) return null;
        try
        {
            var status = NtQueryInformationProcess(h, 70, IntPtr.Zero, 0, out var len);
            if (len <= 0 || len > 1_000_000) return null;
            var buf = Marshal.AllocHGlobal(len);
            try
            {
                status = NtQueryInformationProcess(h, 70, buf, len, out len);
                if (status != 0) return null;
                var us = Marshal.PtrToStructure<UNICODE_STRING>(buf);
                if (us.Buffer == IntPtr.Zero || us.Length == 0) return null;
                return Marshal.PtrToStringUni(us.Buffer, us.Length / 2);
            }
            finally { Marshal.FreeHGlobal(buf); }
        }
        catch { return null; }
        finally { NativeMethods.CloseHandle(h); }
    }

    [DllImport("ntdll.dll")]
    static extern int NtQueryInformationProcess(IntPtr h, int cls, IntPtr buf, int len, out int ret);

    [DllImport("kernel32.dll", SetLastError = true)]
    static extern IntPtr CreateToolhelp32Snapshot(uint flags, uint pid);

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    static extern bool Process32First(IntPtr snap, ref PROCESSENTRY32 pe);

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    static extern bool Process32Next(IntPtr snap, ref PROCESSENTRY32 pe);

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    struct PROCESSENTRY32
    {
        public uint dwSize;
        public uint cntUsage;
        public uint th32ProcessID;
        public nint th32DefaultHeapID;
        public uint th32ModuleID;
        public uint cntThreads;
        public uint th32ParentProcessID;
        public int pcPriClassBase;
        public uint dwFlags;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 260)]
        public string szExeFile;
    }

    [StructLayout(LayoutKind.Sequential)]
    struct UNICODE_STRING
    {
        public ushort Length;
        public ushort MaximumLength;
        public IntPtr Buffer;
    }
}
