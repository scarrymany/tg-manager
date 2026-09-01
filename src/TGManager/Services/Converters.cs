using System.Globalization;
using System.Windows;
using System.Windows.Data;
using System.Windows.Media;

namespace TGManager.Services;

public sealed class BoolToVis : IValueConverter
{
    public object Convert(object value, Type t, object parameter, CultureInfo culture)
        => value is true ? Visibility.Visible : Visibility.Collapsed;
    public object ConvertBack(object value, Type t, object parameter, CultureInfo culture)
        => value is Visibility.Visible;
}

public sealed class InvBoolToVis : IValueConverter
{
    public object Convert(object value, Type t, object parameter, CultureInfo culture)
        => value is true ? Visibility.Collapsed : Visibility.Visible;
    public object ConvertBack(object value, Type t, object parameter, CultureInfo culture)
        => value is Visibility.Collapsed;
}

/// <summary>"#RRGGBB" → SolidColorBrush (для свотчей цвета карточки).</summary>
public sealed class HexToBrush : IValueConverter
{
    public object Convert(object value, Type t, object parameter, CultureInfo culture)
    {
        try
        {
            if (value is string hex && !string.IsNullOrWhiteSpace(hex))
            {
                var brush = new SolidColorBrush((Color)ColorConverter.ConvertFromString(hex)!);
                brush.Freeze();
                return brush;
            }
        }
        catch { /* fallthrough */ }
        return Brushes.White;
    }

    public object ConvertBack(object value, Type t, object parameter, CultureInfo culture)
        => throw new NotSupportedException();
}
