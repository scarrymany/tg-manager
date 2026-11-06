using System.IO;
using TGManager.Services;

/// <summary>Demo workspace for README media. Proxies use RFC 5737 documentation addresses.</summary>
internal static class Demo
{
    public const string Work = "Работа";
    public const string Clients = "Клиенты";
    public const string Personal = "Личное";

    static readonly HashSet<string> WithoutTdata = [];
    static bool _materialized;

    public static Store CreateStore()
    {
        var store = new Store();
        store.Settings.ContainerFolders.AddRange([Work, Clients, Personal]);
        store.Settings.TelegramBinary = Paths.TelegramExe;
        store.Settings.ProxychainsBinary = Paths.ProxychainsExe;

        Add(store, "Поддержка клиентов", Clients, "#71C7F5", "Входящие обращения", Socks("203.0.113.24", 1080, "support"));
        Add(store, "Отдел продаж", Clients, "#6EE7B7", "Новые клиенты и сделки", Http("198.51.100.7", 8080));
        Add(store, "Маркетинг", Work, "#FB7185", "Рассылки и посевы", Socks("203.0.113.51", 1080));
        Add(store, "Рабочий аккаунт", Work, "#FBBF24", "Основной профиль", new ProxyCfg());
        Add(store, "Новостной канал", Work, "#C4B5FD", "Администрирование канала", Socks("198.51.100.33", 1080, "news"));
        Add(store, "Партнёры", Clients, "#FDBA74", "Клиенты B2B", Http("203.0.113.90", 3128));
        Add(store, "HR и найм", Work, "#67E8F9", "Отклики кандидатов", new ProxyCfg());
        Add(store, "Тестовый стенд", "", "#FFFFFF", "Проверка ботов", Socks("127.0.0.1", 1080));
        Add(store, "Личный архив", Personal, "#C4B5FD", "", new ProxyCfg());
        Add(store, "Резервный", Personal, "#6EE7B7", "Ждёт tdata", new ProxyCfg(), withTdata: false);
        return store;
    }

    /// <summary>Creates the files the UI checks for: tdata folders and the portable Telegram/proxy binaries.</summary>
    public static void Materialize(Store store)
    {
        // Paths.AppRoot follows the host process; under `dotnet app.dll` it would point at the SDK folder.
        var ownDir = Path.GetFullPath(AppContext.BaseDirectory).TrimEnd(Path.DirectorySeparatorChar);
        if (!string.Equals(Paths.AppRoot.TrimEnd(Path.DirectorySeparatorChar), ownDir, StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException($"Run the showcase apphost, not through dotnet: AppRoot is {Paths.AppRoot}");
        foreach (var account in store.Accounts.Where(a => !WithoutTdata.Contains(a.Id)))
            Directory.CreateDirectory(Paths.AccountTdata(account.Id));
        foreach (var binary in new[] { Paths.TelegramExe, Paths.ProxychainsExe })
        {
            Directory.CreateDirectory(Path.GetDirectoryName(binary)!);
            File.WriteAllBytes(binary, []);
        }
        _materialized = true;
    }

    public static void Cleanup()
    {
        if (!_materialized) return;
        foreach (var dir in new[] { Paths.AccountsDir, Paths.TelegramDir, Paths.ToolsDir })
            if (Directory.Exists(dir)) Directory.Delete(dir, recursive: true);
        if (File.Exists(Paths.ConfigFile)) File.Delete(Paths.ConfigFile);
    }

    static void Add(Store store, string name, string folder, string color, string notes, ProxyCfg proxy, bool withTdata = true)
    {
        var id = "demo" + (store.Accounts.Count + 1).ToString("00");
        if (!withTdata) WithoutTdata.Add(id);
        store.Accounts.Add(new Account { Id = id, Name = name, Folder = folder, Color = color, Notes = notes, Proxy = proxy });
    }

    static ProxyCfg Socks(string host, int port, string user = "")
        => new() { Type = ProxyKinds.Socks5, Host = host, Port = port, Username = user, Password = user.Length == 0 ? "" : "demo" };

    static ProxyCfg Http(string host, int port)
        => new() { Type = ProxyKinds.Http, Host = host, Port = port };
}
