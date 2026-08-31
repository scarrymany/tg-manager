using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using TGManager.Services;

namespace TGManager.Windows;

public partial class AccountWindow : Window
{
    readonly Account _account;
    readonly bool _editing;
    bool _applyingLine;

    public Account? Result { get; private set; }

    public AccountWindow(Account? existing = null)
    {
        _editing = existing is not null;
        _account = existing ?? new Account { Name = "" };
        InitializeComponent();
        Chrome.Attach(this, WindowFrame);
        TitleText.Text = _editing ? "Изменить контейнер" : "Новый контейнер";
        Title = TitleText.Text;
        NameBox.Text = _account.Name;
        foreach (var c in CardColors.All)
            ColorBox.Items.Add(c);
        var ci = Array.IndexOf(CardColors.All, _account.Color);
        ColorBox.SelectedIndex = ci >= 0 ? ci : 0;
        var ptype = _account.Proxy.Type switch
        {
            ProxyKinds.Http => 1,
            ProxyKinds.Socks5 => 2,
            _ => 0,
        };
        ProxyBox.SelectedIndex = ptype;
        HostBox.Text = _account.Proxy.Host;
        PortBox.Text = _account.Proxy.Port > 0 ? _account.Proxy.Port.ToString() : "1080";
        UserBox.Text = _account.Proxy.Username;
        PassBox.Password = _account.Proxy.Password;
        LineBox.TextChanged += OnLineChanged;
        ToggleProxy();
        PaintColor();
    }

    void OnColorChanged(object sender, SelectionChangedEventArgs e) => PaintColor();

    void PaintColor()
    {
        if (ColorBox.SelectedItem is string hex)
        {
            try { ColorBox.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString(hex)!); }
            catch { /* ignore */ }
        }
    }

    void OnProxyChanged(object sender, SelectionChangedEventArgs e) => ToggleProxy();

    void ToggleProxy()
    {
        var on = ProxyTag() != ProxyKinds.None;
        HpRow.IsEnabled = on;
        UpRow.IsEnabled = on;
        HpRow.Opacity = on ? 1 : 0.45;
        UpRow.Opacity = on ? 1 : 0.45;
    }

    string ProxyTag()
        => (ProxyBox.SelectedItem as ComboBoxItem)?.Tag as string ?? ProxyKinds.None;

    void OnLineChanged(object sender, TextChangedEventArgs e)
    {
        if (_applyingLine) return;
        var text = LineBox.Text.Trim();
        if (text.Length == 0)
        {
            LineHint.Text = "";
            return;
        }
        var parsed = ProxyParse.Parse(text);
        if (parsed is null)
        {
            LineHint.Text = "⚠ Не распознано. Формат: host:port:логин:пароль";
            LineHint.Foreground = (Brush)FindResource("YellowBrush");
            return;
        }
        _applyingLine = true;
        if (ProxyTag() == ProxyKinds.None)
            ProxyBox.SelectedIndex = 2;
        HostBox.Text = parsed.Value.Host;
        PortBox.Text = parsed.Value.Port.ToString();
        UserBox.Text = parsed.Value.User;
        PassBox.Password = parsed.Value.Pass;
        LineHint.Text = "✓ Распознано и подставлено ниже";
        LineHint.Foreground = (Brush)FindResource("GreenBrush");
        _applyingLine = false;
    }

    void OnSave(object sender, RoutedEventArgs e)
    {
        var name = NameBox.Text.Trim();
        if (name.Length == 0)
        {
            ConfirmWindow.Info(this, "Проверьте данные", "Введите название контейнера.");
            return;
        }
        var ptype = ProxyTag();
        if (ptype != ProxyKinds.None && string.IsNullOrWhiteSpace(HostBox.Text))
        {
            ConfirmWindow.Info(this, "Проверьте данные", "Укажите адрес прокси или выберите «Без прокси».");
            return;
        }
        if (!int.TryParse(PortBox.Text.Trim(), out var port) || port is < 1 or > 65535)
            port = 1080;
        _account.Name = name;
        _account.Color = ColorBox.SelectedItem as string ?? "#FFFFFF";
        _account.Proxy = new ProxyCfg
        {
            Type = ptype,
            Host = HostBox.Text.Trim(),
            Port = port,
            Username = UserBox.Text.Trim(),
            Password = PassBox.Password,
        };
        Result = _account;
        DialogResult = true;
        Close();
    }

    void OnClose(object sender, RoutedEventArgs e)
    {
        DialogResult = false;
        Close();
    }
}
