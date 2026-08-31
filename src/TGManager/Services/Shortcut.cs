using System.IO;

namespace TGManager.Services;

public static class Shortcut
{
    public static string CreateDesktop()
    {
        var desktop = Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory);
        if (!Directory.Exists(desktop))
            desktop = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "Desktop");
        var lnk = Path.Combine(desktop, "TG Manager.lnk");
        var target = Environment.ProcessPath ?? Path.Combine(Paths.AppRoot, "TGManager.exe");
        var workdir = Paths.AppRoot;

        var type = Type.GetTypeFromProgID("WScript.Shell")
                   ?? throw new InvalidOperationException("WScript.Shell недоступен");
        dynamic shell = Activator.CreateInstance(type)!;
        dynamic s = shell.CreateShortcut(lnk);
        s.TargetPath = target;
        s.WorkingDirectory = workdir;
        s.Description = "TG Manager";
        s.IconLocation = target + ",0";
        s.Save();
        return lnk;
    }
}
