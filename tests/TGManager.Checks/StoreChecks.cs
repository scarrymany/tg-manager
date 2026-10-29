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
            store.Settings.TelegramBinary = "D:\\Apps\\Telegram.exe";
            store.Settings.ProxychainsBinary = "D:\\Apps\\proxychains.exe";
            store.Settings.AllowMany = false;
            store.Save();
            loaded = Store.Load();
            if (loaded.Settings.TelegramBinary != store.Settings.TelegramBinary ||
                loaded.Settings.ProxychainsBinary != store.Settings.ProxychainsBinary || loaded.Settings.AllowMany)
                throw new InvalidOperationException("Launcher settings must survive a restart");
            store.Settings.ListDensity = ListDensities.Compact;
            store.Settings.CardPadding = 4;
            store.Settings.ButtonSize = ButtonSizes.Small;
            store.Settings.ButtonStyle = ButtonStyles.Icon;
            store.Settings.CardButtons = [CardActions.Launch, CardActions.Stop];
            store.Save();
            loaded = Store.Load();
            if (loaded.Settings.ListDensity != ListDensities.Compact || loaded.Settings.CardPadding != 4 ||
                loaded.Settings.ButtonSize != ButtonSizes.Small || loaded.Settings.ButtonStyle != ButtonStyles.Icon ||
                !loaded.Settings.CardButtons.SequenceEqual([CardActions.Launch, CardActions.Stop]))
                throw new InvalidOperationException("List density and card panel settings must survive a restart");
            File.WriteAllText(Paths.ConfigFile, "{\"settings\":{\"list_density\":\"bogus\",\"card_padding\":999,\"button_size\":\"huge\"," +
                "\"button_style\":\"x\",\"card_buttons\":[\"edit\",\"EDIT\",\"nope\",null]},\"accounts\":[]}");
            loaded = Store.Load();
            if (loaded.Settings.ListDensity != ListDensities.Comfortable || loaded.Settings.CardPadding != ListDensities.MaxPadding ||
                loaded.Settings.ButtonSize != ButtonSizes.Large || loaded.Settings.ButtonStyle != ButtonStyles.Text ||
                !loaded.Settings.CardButtons.SequenceEqual([CardActions.Edit]))
                throw new InvalidOperationException("Invalid list settings must fall back to safe values");
            File.WriteAllText(Paths.ConfigFile, "{\"settings\":{},\"accounts\":[{\"id\":\"legacy\",\"name\":\"Legacy\"}]}");
            loaded = Store.Load();
            if (loaded.Accounts.Single().Folder != "" || loaded.Settings.ContainerFolders.Count != 0 ||
                loaded.Settings.ListDensity != ListDensities.Comfortable || loaded.Settings.CardButtons.Count != CardActions.All.Count)
                throw new InvalidOperationException("Legacy config compatibility failed");
            Console.WriteLine("PASS Folder creation, empty persistence, rename, removal, launcher and list settings, legacy config");
        }
        finally
        {
            if (original is null) File.Delete(Paths.ConfigFile);
            else File.WriteAllBytes(Paths.ConfigFile, original);
        }
    }
}
