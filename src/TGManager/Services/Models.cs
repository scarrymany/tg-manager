using System.Text.Json.Serialization;

namespace TGManager.Services;

public static class ProxyKinds
{
    public const string None = "none";
    public const string Http = "http";
    public const string Socks5 = "socks5";
}

public sealed class ProxyCfg
{
    [JsonPropertyName("type")] public string Type { get; set; } = ProxyKinds.None;
    [JsonPropertyName("host")] public string Host { get; set; } = "";
    [JsonPropertyName("port")] public int Port { get; set; }
    [JsonPropertyName("username")] public string Username { get; set; } = "";
    [JsonPropertyName("password")] public string Password { get; set; } = "";

    [JsonIgnore]
    public bool Enabled =>
        (Type is ProxyKinds.Http or ProxyKinds.Socks5) && !string.IsNullOrWhiteSpace(Host) && Port is > 0 and <= 65535;

    public string Summary()
    {
        if (!Enabled) return "Без прокси";
        var label = Type == ProxyKinds.Http ? "HTTP" : "SOCKS5";
        var auth = string.IsNullOrEmpty(Username) ? "" : " 🔑";
        return $"{label} {Host}:{Port}{auth}";
    }

    public string ProxychainsLine()
    {
        var kind = Type == ProxyKinds.Socks5 ? "socks5" : "http";
        var line = $"{kind} {Host} {Port}";
        if (!string.IsNullOrEmpty(Username))
        {
            line += " " + Username;
            if (!string.IsNullOrEmpty(Password))
                line += " " + Password;
        }
        return line;
    }
}

public sealed class Account
{
    [JsonPropertyName("id")] public string Id { get; set; } = Guid.NewGuid().ToString("N")[..12];
    [JsonPropertyName("name")] public string Name { get; set; } = "Аккаунт";
    [JsonPropertyName("proxy")] public ProxyCfg Proxy { get; set; } = new();
    [JsonPropertyName("color")] public string Color { get; set; } = "#FFFFFF";
    [JsonPropertyName("notes")] public string Notes { get; set; } = "";
    [JsonPropertyName("folder")] public string Folder { get; set; } = "";
    [JsonPropertyName("created_at")] public string CreatedAt { get; set; } = DateTime.UtcNow.ToString("o");
}

public sealed class Settings
{
    [JsonPropertyName("container_folders")] public List<string> ContainerFolders { get; set; } = [];
    [JsonPropertyName("telegram_binary")] public string TelegramBinary { get; set; } = "";
    [JsonPropertyName("proxychains_binary")] public string ProxychainsBinary { get; set; } = "";
    [JsonPropertyName("allow_many")] public bool AllowMany { get; set; } = true;
}

public static class CardColors
{
    public static readonly string[] All =
    [
        "#71C7F5", "#6EE7B7", "#FBBF24", "#FB7185",
        "#C4B5FD", "#FDBA74", "#67E8F9", "#FFFFFF",
    ];
}
