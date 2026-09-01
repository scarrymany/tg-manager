using System.IO;
using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace TGManager.Services;

public sealed class Store
{
    public Settings Settings { get; set; } = new();
    public List<Account> Accounts { get; set; } = [];

    /// <summary>Если config.json не прочитался — сюда кладём копию, чтобы не затереть данные при Save().</summary>
    public string? RecoveredBackup { get; private set; }

    static readonly JsonSerializerOptions JsonOpt = new()
    {
        WriteIndented = true,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
        PropertyNamingPolicy = null,
        Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
    };

    public static Store Load()
    {
        Paths.EnsureDirs();
        if (!File.Exists(Paths.ConfigFile))
            return new Store();
        try
        {
            var json = File.ReadAllText(Paths.ConfigFile, Encoding.UTF8);
            var data = JsonSerializer.Deserialize<StoreFile>(json, JsonOpt);
            if (data is null) throw new InvalidDataException("empty config");
            var store = new Store
            {
                Settings = data.Settings ?? new Settings(),
                Accounts = data.Accounts ?? [],
            };
            store.Sanitize();
            return store;
        }
        catch
        {
            var store = new Store();
            try
            {
                var backup = Path.Combine(Paths.AppRoot, $"config.broken-{DateTime.Now:yyyyMMdd-HHmmss}.json");
                File.Copy(Paths.ConfigFile, backup, true);
                store.RecoveredBackup = backup;
            }
            catch { /* ignore */ }
            return store;
        }
    }

    void Sanitize()
    {
        var idsRewritten = false;
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var a in Accounts)
        {
            if (string.IsNullOrWhiteSpace(a.Id) || !Paths.IsSafeAccountId(a.Id) || !seen.Add(a.Id))
            {
                string fresh;
                do { fresh = Guid.NewGuid().ToString("N")[..12]; }
                while (!seen.Add(fresh));
                a.Id = fresh;
                idsRewritten = true;
            }
            if (string.IsNullOrWhiteSpace(a.Name)) a.Name = "Аккаунт";
            a.Proxy ??= new ProxyCfg();
            a.Proxy.Type = (a.Proxy.Type ?? "").Trim().ToLowerInvariant();
            if (a.Proxy.Type is not (ProxyKinds.Http or ProxyKinds.Socks5)) a.Proxy.Type = ProxyKinds.None;
            a.Proxy.Host ??= "";
            a.Proxy.Username ??= "";
            a.Proxy.Password ??= "";
            if (string.IsNullOrWhiteSpace(a.Color)) a.Color = "#FFFFFF";
        }
        Settings.TelegramBinary ??= "";
        Settings.ProxychainsBinary ??= "";
        if (idsRewritten)
        {
            try { Save(); } catch { /* загрузку не блокируем */ }
        }
    }

    public void Save()
    {
        Paths.EnsureDirs();
        var tmp = Paths.ConfigFile + ".tmp";
        var json = JsonSerializer.Serialize(new StoreFile { Settings = Settings, Accounts = Accounts }, JsonOpt);
        File.WriteAllText(tmp, json, new UTF8Encoding(encoderShouldEmitUTF8Identifier: false));
        File.Move(tmp, Paths.ConfigFile, overwrite: true);
    }

    public void Add(Account account)
    {
        Directory.CreateDirectory(Paths.AccountWorkdir(account.Id));
        Accounts.Add(account);
        Save();
    }

    public void Update(Account account)
    {
        var i = Accounts.FindIndex(a => a.Id == account.Id);
        if (i >= 0) Accounts[i] = account;
        else Accounts.Add(account);
        Save();
    }

    public void Remove(string id)
    {
        Accounts.RemoveAll(a => a.Id == id);
        Save();
    }

    public Account? Get(string id) => Accounts.FirstOrDefault(a => a.Id == id);

    sealed class StoreFile
    {
        [JsonPropertyName("settings")] public Settings? Settings { get; set; }
        [JsonPropertyName("accounts")] public List<Account>? Accounts { get; set; }
    }
}
