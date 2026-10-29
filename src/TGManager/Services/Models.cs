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
    [JsonPropertyName("list_density")] public string ListDensity { get; set; } = ListDensities.Comfortable;
    [JsonPropertyName("card_padding")] public int CardPadding { get; set; } = ListDensities.Presets[ListDensities.Comfortable].Padding;
    [JsonPropertyName("button_size")] public string ButtonSize { get; set; } = ListDensities.Presets[ListDensities.Comfortable].ButtonSize;
    [JsonPropertyName("button_style")] public string ButtonStyle { get; set; } = ListDensities.Presets[ListDensities.Comfortable].ButtonStyle;
    [JsonPropertyName("card_buttons")] public List<string> CardButtons { get; set; } = [.. CardActions.All];

    /// <summary>Приводит настройки списка к допустимым значениям (старые и вручную правленные config.json).</summary>
    public void NormalizeList()
    {
        ListDensity = (ListDensity ?? "").Trim().ToLowerInvariant();
        if (!ListDensities.Presets.ContainsKey(ListDensity)) ListDensity = ListDensities.Comfortable;
        CardPadding = Math.Clamp(CardPadding, ListDensities.MinPadding, ListDensities.MaxPadding);
        ButtonSize = (ButtonSize ?? "").Trim().ToLowerInvariant();
        if (ButtonSize is not (ButtonSizes.Small or ButtonSizes.Medium or ButtonSizes.Large))
            ButtonSize = ListDensities.Presets[ListDensity].ButtonSize;
        ButtonStyle = (ButtonStyle ?? "").Trim().ToLowerInvariant();
        if (ButtonStyle is not (ButtonStyles.Text or ButtonStyles.Icon))
            ButtonStyle = ListDensities.Presets[ListDensity].ButtonStyle;
        CardButtons = (CardButtons ?? [.. CardActions.All]).Select(b => (b ?? "").Trim().ToLowerInvariant())
            .Where(b => CardActions.All.Contains(b)).Distinct().ToList();
    }
}

/// <summary>Плотность списка контейнеров: «Обычная» — просторные карточки, «Компактная» — одна строка на контейнер.</summary>
public static class ListDensities
{
    public const string Comfortable = "comfortable";
    public const string Compact = "compact";
    public const int MinPadding = 2;
    public const int MaxPadding = 24;

    /// <summary>Высота карточки (вертикальный отступ), размер и вид кнопок, которые выставляет плотность.</summary>
    public static readonly IReadOnlyDictionary<string, (int Padding, string ButtonSize, string ButtonStyle)> Presets =
        new Dictionary<string, (int, string, string)>
        {
            [Comfortable] = (16, ButtonSizes.Large, ButtonStyles.Text),
            [Compact] = (6, ButtonSizes.Medium, ButtonStyles.Icon),
        };
}

public static class ButtonSizes
{
    public const string Small = "small";
    public const string Medium = "medium";
    public const string Large = "large";
}

public static class ButtonStyles
{
    public const string Text = "text";
    public const string Icon = "icon";
}

/// <summary>Действия карточки контейнера, которые можно показать или скрыть кнопкой.</summary>
public static class CardActions
{
    public const string Launch = "launch";
    public const string Stop = "stop";
    public const string Folder = "folder";
    public const string Export = "export";
    public const string Cleanup = "cleanup";
    public const string Edit = "edit";
    public const string Delete = "delete";

    public static readonly IReadOnlyList<string> All = [Launch, Stop, Folder, Export, Cleanup, Edit, Delete];
}

public static class CardColors
{
    public static readonly string[] All =
    [
        "#71C7F5", "#6EE7B7", "#FBBF24", "#FB7185",
        "#C4B5FD", "#FDBA74", "#67E8F9", "#FFFFFF",
    ];
}
