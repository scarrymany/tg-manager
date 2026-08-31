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

    public static int? Start(string workdir, ProxyCfg http)
    {
        Stop(workdir);
        var listener = new TcpListener(IPAddress.Loopback, 0);
        listener.Start();
        var port = ((IPEndPoint)listener.LocalEndpoint).Port;
        Live[workdir] = listener;
        File.WriteAllText(Path.Combine(workdir, "http_bridge.ready"), $"READY 127.0.0.1:{port}\n");

        _ = Task.Run(async () =>
        {
            try
            {
                while (true)
                {
                    var client = await listener.AcceptTcpClientAsync();
                    _ = Task.Run(() => Handle(client, http));
                }
            }
            catch (ObjectDisposedException) { }
            catch (SocketException) { }
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

    static async Task Handle(TcpClient client, ProxyCfg http)
    {
        using var clientOwn = client;
        try
        {
            var stream = client.GetStream();
            var greet = new byte[2];
            if (await ReadExact(stream, greet) < 2 || greet[0] != 0x05) return;
            var n = greet[1];
            if (n > 0) await ReadExact(stream, new byte[n]);
            await stream.WriteAsync(new byte[] { 0x05, 0x00 });

            var req = new byte[4];
            if (await ReadExact(stream, req) < 4 || req[0] != 0x05 || req[1] != 0x01)
            {
                await stream.WriteAsync(new byte[] { 0x05, 0x07, 0x00, 0x01, 0, 0, 0, 0, 0, 0 });
                return;
            }
            string host;
            if (req[3] == 0x01)
            {
                var ip = new byte[4];
                await ReadExact(stream, ip);
                host = new IPAddress(ip).ToString();
            }
            else if (req[3] == 0x03)
            {
                var ln = new byte[1];
                await ReadExact(stream, ln);
                var name = new byte[ln[0]];
                await ReadExact(stream, name);
                host = Encoding.ASCII.GetString(name);
            }
            else return;
            var pb = new byte[2];
            await ReadExact(stream, pb);
            var port = (pb[0] << 8) | pb[1];

            using var up = new TcpClient();
            await up.ConnectAsync(http.Host, http.Port);
            var upStream = up.GetStream();
            var connect = $"CONNECT {host}:{port} HTTP/1.1\r\nHost: {host}:{port}\r\n";
            if (!string.IsNullOrEmpty(http.Username))
            {
                var token = Convert.ToBase64String(Encoding.UTF8.GetBytes($"{http.Username}:{http.Password}"));
                connect += $"Proxy-Authorization: Basic {token}\r\n";
            }
            connect += "\r\n";
            var bytes = Encoding.ASCII.GetBytes(connect);
            await upStream.WriteAsync(bytes);

            var header = new MemoryStream();
            while (true)
            {
                var b = upStream.ReadByte();
                if (b < 0) return;
                header.WriteByte((byte)b);
                if (header.Length > 8192) return;
                var arr = header.ToArray();
                if (arr.Length >= 4 && arr[^4] == '\r' && arr[^3] == '\n' && arr[^2] == '\r' && arr[^1] == '\n')
                    break;
            }
            var status = Encoding.ASCII.GetString(header.ToArray()).Split("\r\n")[0];
            var parts = status.Split(' ');
            if (parts.Length < 2 || !parts[1].StartsWith('2'))
            {
                await stream.WriteAsync(new byte[] { 0x05, 0x01, 0x00, 0x01, 0, 0, 0, 0, 0, 0 });
                return;
            }
            await stream.WriteAsync(new byte[] { 0x05, 0x00, 0x00, 0x01, 0, 0, 0, 0, 0, 0 });
            await Task.WhenAll(Pipe(stream, upStream), Pipe(upStream, stream));
        }
        catch { /* connection dropped */ }
    }

    static async Task<int> ReadExact(NetworkStream s, byte[] buf)
    {
        var off = 0;
        while (off < buf.Length)
        {
            var n = await s.ReadAsync(buf.AsMemory(off));
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
