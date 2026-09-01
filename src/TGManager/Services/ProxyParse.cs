namespace TGManager.Services;

public readonly record struct ParsedProxy(string Host, int Port, string User, string Pass, string? Scheme);

public static class ProxyParse
{
    /// <summary>
    /// Разбирает строку прокси. Поддерживаются: host:port, host:port:user:pass,
    /// user:pass@host:port, а также с префиксом схемы (http://, socks5://, socks://).
    /// </summary>
    public static ParsedProxy? Parse(string line)
    {
        if (string.IsNullOrWhiteSpace(line)) return null;
        var s = line.Trim();
        string? scheme = null;
        var idx = s.IndexOf("://", StringComparison.Ordinal);
        if (idx > 0)
        {
            scheme = s[..idx].Trim().ToLowerInvariant();
            s = s[(idx + 3)..];
        }
        s = s.TrimEnd('/');
        string user = "", pass = "", host;
        string portStr;
        var at = s.LastIndexOf('@');
        if (at >= 0)
        {
            var creds = s[..at].Split(':', 2);
            user = creds.ElementAtOrDefault(0) ?? "";
            pass = creds.ElementAtOrDefault(1) ?? "";
            var hp = s[(at + 1)..].Split(':');
            if (hp.Length < 2) return null;
            host = hp[0];
            portStr = hp[1];
        }
        else
        {
            var parts = s.Split(':');
            if (parts.Length == 2) { host = parts[0]; portStr = parts[1]; }
            else if (parts.Length == 3) { host = parts[0]; portStr = parts[1]; user = parts[2]; }
            else if (parts.Length >= 4)
            {
                host = parts[0]; portStr = parts[1]; user = parts[2];
                pass = string.Join(':', parts.Skip(3));
            }
            else return null;
        }
        if (!int.TryParse(portStr.Trim(), out var port) || port is < 1 or > 65535) return null;
        if (string.IsNullOrWhiteSpace(host)) return null;
        var kind = scheme switch
        {
            "http" or "https" => ProxyKinds.Http,
            "socks5" or "socks5h" or "socks" or "socks4" => ProxyKinds.Socks5,
            _ => null,
        };
        return new ParsedProxy(host.Trim(), port, user.Trim(), pass, kind);
    }
}
