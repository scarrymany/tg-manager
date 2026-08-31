using System.Globalization;
using System.Windows;
using System.Windows.Data;

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
