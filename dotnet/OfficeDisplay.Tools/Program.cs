using System.Globalization;
using System.Text.Json;

namespace OfficeDisplay.Tools;

/// <summary>
/// Erzeugt eine lokale Farbreihe aus einem Startton. Kein Netz, keine Telemetrie.
/// </summary>
public static class Palette
{
    public static string[] FromSeed(string seed)
    {
        var hex = (seed ?? "").Trim().TrimStart('#');
        if (hex.Length != 6)
        {
            hex = "0B63E5";
        }
        var r = Convert.ToInt32(hex.Substring(0, 2), 16) / 255.0;
        var g = Convert.ToInt32(hex.Substring(2, 2), 16) / 255.0;
        var b = Convert.ToInt32(hex.Substring(4, 2), 16) / 255.0;
        RgbToHsl(r, g, b, out var h, out var s, out var l);
        var colors = new string[5];
        for (var step = 0; step < 5; step++)
        {
            colors[step] = HslToHex((h + step * 0.08) % 1.0, Math.Min(1, s + 0.05), Math.Min(0.72, Math.Max(0.28, l)));
        }
        return colors;
    }

    private static void RgbToHsl(double r, double g, double b, out double h, out double s, out double l)
    {
        var max = Math.Max(r, Math.Max(g, b));
        var min = Math.Min(r, Math.Min(g, b));
        l = (max + min) / 2.0;
        if (Math.Abs(max - min) < 0.0001)
        {
            h = s = 0;
            return;
        }
        var d = max - min;
        s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
        if (Math.Abs(max - r) < 0.0001)
        {
            h = ((g - b) / d) % 6;
        }
        else if (Math.Abs(max - g) < 0.0001)
        {
            h = (b - r) / d + 2;
        }
        else
        {
            h = (r - g) / d + 4;
        }
        h /= 6;
        if (h < 0) h += 1;
    }

    private static string HslToHex(double h, double s, double l)
    {
        double r, g, b;
        if (s <= 0)
        {
            r = g = b = l;
        }
        else
        {
            var q = l < 0.5 ? l * (1 + s) : l + s - l * s;
            var p = 2 * l - q;
            r = Hue(p, q, h + 1.0 / 3);
            g = Hue(p, q, h);
            b = Hue(p, q, h - 1.0 / 3);
        }
        return string.Create(CultureInfo.InvariantCulture, $"#{(int)(r * 255):X2}{(int)(g * 255):X2}{(int)(b * 255):X2}");
    }

    private static double Hue(double p, double q, double t)
    {
        if (t < 0) t += 1;
        if (t > 1) t -= 1;
        if (t < 1.0 / 6) return p + (q - p) * 6 * t;
        if (t < 0.5) return q;
        if (t < 2.0 / 3) return p + (q - p) * (2.0 / 3 - t) * 6;
        return p;
    }
}

public static class Program
{
    public static int Main(string[] args)
    {
        var seed = args.Length > 0 ? args[0] : "0B63E5";
        Console.WriteLine(JsonSerializer.Serialize(Palette.FromSeed(seed)));
        return 0;
    }
}
