using System.Collections.Concurrent;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;

namespace TGManager.Services;

/// <summary>Локальный SOCKS5 → HTTP CONNECT. Нужен, потому что proxychains-windows говорит SOCKS5.</summary>
public static class HttpBridge
{
    static readonly ConcurrentDictionary<string, TcpListener> Live = new();
    static readonly TimeSpan ConnectTimeout = TimeSpan.FromSeconds(15);
    static readonly TimeSpan HandshakeTimeout = TimeSpan.FromSeconds(20);

    public static bool AnyLive => !Live.IsEmpty;

    public static int? Start(string workdir, ProxyCfg http)
    {
        Stop(workdir);
        TcpListener listener;
        int port;
        try
        {
            listener = new TcpListener(IPAddress.Loopback, 0);
            listener.Start();
            port = ((IPEndPoint)listener.LocalEndpoint).Port;
        }
        catch
        {
            return null;
        }
        Live[workdir] = listener;
        try { File.WriteAllText(Path.Combine(workdir, "http_bridge.ready"), $"READY 127.0.0.1:{port}\n"); }
        catch { /* ignore */ }

        _ = Task.Run(async () =>
        {
            try
            {
                while (true)
                {
                    var client = await listener.AcceptTcpClientAsync();
                    _ = Handle(client, http);
                }
            }
            catch (ObjectDisposedException) { }
            catch (SocketException) { }
            catch (InvalidOperationException) { }
        });
        return port;
    }

    public static void Stop(string workdir)
    {
        if (Live.TryRemove(workdir, out var l))
        {
            try { l.Stop(); } catch { /* ignore */ }
        }
        try { File.Delete(Path.Combine(workdir, "http_bridge.ready")); } catch { /* ignore */ }
    }

    public static void StopAll()
    {
        foreach (var key in Live.Keys.ToList())
            Stop(key);
    }

    static async Task Handle(TcpClient client, ProxyCfg http)
    {
        using var clientOwn = client;
        client.NoDelay = true;
        using var handshakeCts = new CancellationTokenSource(HandshakeTimeout);
        var ct = handshakeCts.Token;
        try
        {
            var stream = client.GetStream();
            var greet = new byte[2];
            if (await ReadExact(stream, greet, ct) < 2 || greet[0] != 0x05) return;
            var n = greet[1];
            if (n > 0) await ReadExact(stream, new byte[n], ct);
            await stream.WriteAsync(new byte[] { 0x05, 0x00 }, ct);

            var req = new byte[4];
            if (await ReadExact(stream, req, ct) < 4 || req[0] != 0x05 || req[1] != 0x01)
            {
                await Reply(stream, 0x07);
                return;
            }
            string host;
            switch (req[3])
            {
                case 0x01:
                {
                    var ip = new byte[4];
                    if (await ReadExact(stream, ip, ct) < 4) return;
                    host = new IPAddress(ip).ToString();
                    break;
                }
                case 0x03:
                {
                    var ln = new byte[1];
                    if (await ReadExact(stream, ln, ct) < 1) return;
                    var name = new byte[ln[0]];
                    if (await ReadExact(stream, name, ct) < name.Length) return;
                    host = Encoding.ASCII.GetString(name);
                    break;
                }
                case 0x04:
                {
                    var ip = new byte[16];
                    if (await ReadExact(stream, ip, ct) < 16) return;
                    host = "[" + new IPAddress(ip) + "]";
                    break;
                }
                default:
                    await Reply(stream, 0x08);
                    return;
            }
            var pb = new byte[2];
            if (await ReadExact(stream, pb, ct) < 2) return;
            var port = (pb[0] << 8) | pb[1];
            if (!IsSafeSocksHost(host))
            {
                await Reply(stream, 0x01);
                return;
            }

            using var up = new TcpClient { NoDelay = true };
            using (var cts = new CancellationTokenSource(ConnectTimeout))
            {
                try { await up.ConnectAsync(http.Host, http.Port, cts.Token); }
                catch
                {
                    await Reply(stream, 0x01);
                    return;
                }
            }
            var upStream = up.GetStream();
            var connect = $"CONNECT {host}:{port} HTTP/1.1\r\nHost: {host}:{port}\r\n";
            if (!string.IsNullOrEmpty(http.Username))
            {
                var token = Convert.ToBase64String(Encoding.UTF8.GetBytes($"{http.Username}:{http.Password}"));
                connect += $"Proxy-Authorization: Basic {token}\r\n";
            }
            connect += "\r\n";
            await upStream.WriteAsync(Encoding.ASCII.GetBytes(connect), ct);

            var header = await ReadHeader(upStream, ct);
            if (header is null)
            {
                await Reply(stream, 0x01);
                return;
            }
            var status = header.Split("\r\n")[0];
            var parts = status.Split(' ');
            if (parts.Length < 2 || !parts[1].StartsWith('2'))
            {
                await Reply(stream, 0x01);
                return;
            }
            await Reply(stream, 0x00);
            await Task.WhenAll(Pipe(stream, upStream), Pipe(upStream, stream));
        }
        catch { /* connection dropped */ }
    }

    static bool IsSafeSocksHost(string host)
    {
        if (string.IsNullOrEmpty(host) || host.Length > 255) return false;
        foreach (var c in host)
        {
            if (c is '\r' or '\n' or '\0' or ' ' or '\t') return false;
        }
        return true;
    }

    static Task Reply(NetworkStream s, byte code)
        => s.WriteAsync(new byte[] { 0x05, code, 0x00, 0x01, 0, 0, 0, 0, 0, 0 }).AsTask();

    static async Task<string?> ReadHeader(NetworkStream s, CancellationToken ct)
    {
        var header = new MemoryStream();
        var one = new byte[1];
        while (true)
        {
            var n = await s.ReadAsync(one.AsMemory(0, 1), ct);
            if (n <= 0) return null;
            header.WriteByte(one[0]);
            if (header.Length > 8192) return null;
            if (header.Length >= 4)
            {
                var arr = header.GetBuffer();
                var len = (int)header.Length;
                if (arr[len - 4] == '\r' && arr[len - 3] == '\n' && arr[len - 2] == '\r' && arr[len - 1] == '\n')
                    break;
            }
        }
        return Encoding.ASCII.GetString(header.GetBuffer(), 0, (int)header.Length);
    }

    static async Task<int> ReadExact(NetworkStream s, byte[] buf, CancellationToken ct)
    {
        var off = 0;
        while (off < buf.Length)
        {
            var n = await s.ReadAsync(buf.AsMemory(off), ct);
            if (n <= 0) return off;
            off += n;
        }
        return off;
    }

    static async Task Pipe(Stream a, Stream b)
    {
        var buf = new byte[65536];
        try
        {
            while (true)
            {
                var n = await a.ReadAsync(buf);
                if (n <= 0) break;
                await b.WriteAsync(buf.AsMemory(0, n));
            }
        }
        catch { /* ignore */ }
        try { b.Close(); } catch { /* ignore */ }
    }
}
