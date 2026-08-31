namespace TGManager.Services;

public static class ProxyParse
{
    public static (string Host, int Port, string User, string Pass)? Parse(string line)
    {
        if (string.IsNullOrWhiteSpace(line)) return null;
        var s = line.Trim();
        if (s.Contains("://")) s = s.Split("://", 2)[1];
        string user = "", pass = "", host;
        string portStr;
        if (s.Contains('@'))
        {
            var parts = s.Split('@');
            var creds = parts[0].Split(':');
            user = creds.ElementAtOrDefault(0) ?? "";
            pass = creds.ElementAtOrDefault(1) ?? "";
            var hp = string.Join("@", parts.Skip(1)).Split(':');
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
        if (!int.TryParse(portStr, out var port) || port is < 1 or > 65535) return null;
        if (string.IsNullOrWhiteSpace(host)) return null;
        return (host.Trim(), port, user.Trim(), pass);
    }
}
