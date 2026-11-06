using System.ComponentModel;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Text;
using System.Windows;
using System.Windows.Media;
using System.Windows.Media.Imaging;

/// <summary>
/// Turns rendered scenes into a GIF storyboard: holds, eased cursor moves, clicks and cross-fades.
/// Every distinct frame is written once with its own duration, so long holds cost nothing.
/// </summary>
internal sealed class GifRecorder
{
    const int FrameMs = 40;
    const int ClickMs = 320;
    const double ClickRadiusFrom = 5;
    const double ClickRadiusTo = 19;

    static readonly Brush Backdrop = Frozen(new SolidColorBrush(Color.FromRgb(0x0A, 0x0A, 0x0A)));
    static readonly Brush CursorShadow = Frozen(new SolidColorBrush(Color.FromArgb(0x70, 0, 0, 0)));
    static readonly Pen CursorOutline = Frozen(new Pen(Brushes.Black, 1.1) { LineJoin = PenLineJoin.Round });
    static readonly Geometry Arrow = Frozen(Geometry.Parse("M0,0 L0,17 L4.6,12.9 L7.6,19.6 L10.4,18.4 L7.4,11.8 L13,11.8 Z"));

    readonly string _dir;
    readonly double _scale;
    readonly StringBuilder _list = new();
    BitmapSource _scene;
    Point _cursor;
    string? _lastFile;
    int _count;

    public GifRecorder(string dir, BitmapSource scene, Point cursor, double scale)
    {
        if (Directory.Exists(dir)) Directory.Delete(dir, recursive: true);
        Directory.CreateDirectory(dir);
        _dir = dir;
        _scene = scene;
        _cursor = cursor;
        _scale = scale;
    }

    /// <summary>Replaces the scene without emitting a frame; the next frame shows it.</summary>
    public void Cut(BitmapSource scene) => _scene = scene;

    public void Hold(int ms) => Emit(Compose(_scene), ms);

    public void Move(Point target, int ms)
    {
        var from = _cursor;
        var steps = Math.Max(1, ms / FrameMs);
        for (var i = 1; i <= steps; i++)
        {
            var t = EaseInOut((double)i / steps);
            _cursor = new Point(from.X + (target.X - from.X) * t, from.Y + (target.Y - from.Y) * t);
            Emit(Compose(_scene), FrameMs);
        }
    }

    /// <summary>Click ripple at the cursor. <paramref name="result"/> is the state the click produces.</summary>
    public void Click(BitmapSource? result = null)
    {
        if (result is not null) _scene = result;
        var steps = ClickMs / FrameMs;
        for (var i = 0; i < steps; i++)
            Emit(Compose(_scene, ripple: (double)i / (steps - 1)), FrameMs);
    }

    public void Fade(BitmapSource next, int ms)
    {
        var steps = Math.Max(1, ms / FrameMs);
        for (var i = 1; i < steps; i++)
            Emit(Compose(_scene, overlay: next, overlayOpacity: EaseInOut((double)i / steps)), FrameMs);
        _scene = next;
        Emit(Compose(_scene), FrameMs);
    }

    public void Encode(string output)
    {
        if (_lastFile is null) throw new InvalidOperationException("Nothing was recorded");
        // The concat demuxer ignores the duration of the final entry unless the file is listed again.
        _list.Append(CultureInfo.InvariantCulture, $"file '{_lastFile}'\n");
        var listPath = Path.Combine(_dir, "frames.txt");
        File.WriteAllText(listPath, _list.ToString());
        Directory.CreateDirectory(Path.GetDirectoryName(output)!);

        var ffmpeg = new ProcessStartInfo("ffmpeg") { UseShellExecute = false, RedirectStandardError = true, WorkingDirectory = _dir };
        foreach (var arg in new[]
        {
            "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", listPath,
            "-vf", "split[a][b];[a]palettegen=max_colors=256:stats_mode=full[p];[b][p]paletteuse=dither=none:diff_mode=rectangle",
            "-fps_mode", "vfr", "-loop", "0", output,
        })
            ffmpeg.ArgumentList.Add(arg);
        try
        {
            using var process = Process.Start(ffmpeg)!;
            var errors = process.StandardError.ReadToEnd();
            process.WaitForExit();
            if (process.ExitCode != 0) throw new InvalidOperationException("ffmpeg failed: " + errors);
        }
        catch (Win32Exception ex)
        {
            throw new InvalidOperationException("ffmpeg is required on PATH to build the GIF", ex);
        }
    }

    void Emit(BitmapSource frame, int ms)
    {
        var file = $"f{++_count:0000}.png";
        Capture.Save(frame, Path.Combine(_dir, file));
        _list.Append(CultureInfo.InvariantCulture, $"file '{file}'\nduration {ms / 1000.0:0.000}\n");
        _lastFile = file;
    }

    BitmapSource Compose(BitmapSource scene, BitmapSource? overlay = null, double overlayOpacity = 0, double? ripple = null)
    {
        var bounds = new Rect(0, 0, scene.PixelWidth, scene.PixelHeight);
        var visual = new DrawingVisual();
        using (var dc = visual.RenderOpen())
        {
            dc.DrawRectangle(Backdrop, null, bounds);
            dc.DrawImage(scene, bounds);
            if (overlay is not null)
            {
                dc.PushOpacity(overlayOpacity);
                dc.DrawImage(overlay, bounds);
                dc.Pop();
            }
            if (ripple is { } p)
            {
                var radius = (ClickRadiusFrom + (ClickRadiusTo - ClickRadiusFrom) * EaseOut(p)) * _scale;
                var ring = new Pen(new SolidColorBrush(Color.FromArgb((byte)(220 * (1 - p)), 255, 255, 255)), 2 * _scale);
                dc.DrawEllipse(null, ring, _cursor, radius, radius);
            }
            dc.PushTransform(new TranslateTransform(_cursor.X, _cursor.Y));
            dc.PushTransform(new ScaleTransform(_scale, _scale));
            dc.PushTransform(new TranslateTransform(1, 1.5));
            dc.DrawGeometry(CursorShadow, null, Arrow);
            dc.Pop();
            dc.DrawGeometry(Brushes.White, CursorOutline, Arrow);
            dc.Pop();
            dc.Pop();
        }
        var bitmap = new RenderTargetBitmap(scene.PixelWidth, scene.PixelHeight, 96, 96, PixelFormats.Pbgra32);
        bitmap.Render(visual);
        bitmap.Freeze();
        return bitmap;
    }

    static double EaseInOut(double t) => t < 0.5 ? 4 * t * t * t : 1 - Math.Pow(-2 * t + 2, 3) / 2;
    static double EaseOut(double t) => 1 - Math.Pow(1 - t, 3);

    static T Frozen<T>(T freezable) where T : Freezable
    {
        freezable.Freeze();
        return freezable;
    }
}
