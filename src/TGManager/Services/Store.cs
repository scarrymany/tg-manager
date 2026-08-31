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
            if (data is null) return new Store();
            return new Store
            {
                Settings = data.Settings ?? new Settings(),
                Accounts = data.Accounts ?? [],
            };
        }
        catch
        {
            return new Store();
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
