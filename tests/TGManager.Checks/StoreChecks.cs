using System.IO;
using TGManager.Services;

internal static class StoreChecks
{
    public static void Run()
    {
        var original = File.Exists(Paths.ConfigFile) ? File.ReadAllBytes(Paths.ConfigFile) : null;
        try
        {
            var store = new Store();
            var account = new Account { Name = "Folder test", Folder = "Work" };
            store.Accounts.Add(account);
            store.Save();
            account.Folder = "";
            store.Save();
            if (!Store.Load().Settings.ContainerFolders.Contains("Work"))
                throw new InvalidOperationException("Folder created by account edit must survive becoming empty");
            store.ChangeFolder(null, "Archive");
            if (!Store.Load().Settings.ContainerFolders.Contains("Archive")) throw new InvalidOperationException("Empty folder persistence failed");
            var blockedPath = Paths.ConfigFile + ".tmp";
            Directory.CreateDirectory(blockedPath);
            try
            {
                var failed = false;
                try { store.ChangeFolder("Archive", "Failed rename"); }
                catch (UnauthorizedAccessException) { failed = true; }
                if (!failed || !store.Settings.ContainerFolders.Contains("Archive") || store.Settings.ContainerFolders.Contains("Failed rename"))
                    throw new InvalidOperationException("Failed save must restore folder state");
            }
            finally { Directory.Delete(blockedPath); }
            account.Folder = "Work";
            store.ChangeFolder("Work", "Projects");
            var loaded = Store.Load();
            if (loaded.Accounts.Single().Folder != "Projects" || loaded.Settings.ContainerFolders.Contains("Work"))
                throw new InvalidOperationException("Folder rename persistence failed");
            store.ChangeFolder("Projects", "");
            loaded = Store.Load();
            if (loaded.Accounts.Single().Folder != "" || loaded.Accounts.Single().Id != account.Id)
                throw new InvalidOperationException("Folder removal must preserve account identity");
            File.WriteAllText(Paths.ConfigFile, "{\"settings\":{},\"accounts\":[{\"id\":\"legacy\",\"name\":\"Legacy\"}]}");
            loaded = Store.Load();
            if (loaded.Accounts.Single().Folder != "" || loaded.Settings.ContainerFolders.Count != 0)
                throw new InvalidOperationException("Legacy config compatibility failed");
            Console.WriteLine("PASS Folder creation, empty persistence, rename, removal and legacy config");
        }
        finally
        {
            if (original is null) File.Delete(Paths.ConfigFile);
            else File.WriteAllBytes(Paths.ConfigFile, original);
        }
    }
}
