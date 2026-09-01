using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Animation;
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
        var ci = Array.FindIndex(CardColors.All, c => string.Equals(c, _account.Color, StringComparison.OrdinalIgnoreCase));
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
        ToggleProxy(animate: false);
        Loaded += (_, _) => { NameBox.Focus(); NameBox.SelectAll(); };
    }

    void OnProxyChanged(object sender, SelectionChangedEventArgs e) => ToggleProxy(animate: IsLoaded);

    void ToggleProxy(bool animate)
    {
        var on = ProxyTag() != ProxyKinds.None;
        ProxyPanel.IsEnabled = on;
        var target = on ? 1.0 : 0.45;
        if (!animate)
        {
            ProxyPanel.Opacity = target;
            return;
        }
        ProxyPanel.BeginAnimation(OpacityProperty,
            new DoubleAnimation(target, new Duration(TimeSpan.FromMilliseconds(150))));
    }

    string ProxyTag()
        => (ProxyBox.SelectedItem as ComboBoxItem)?.Tag as string ?? ProxyKinds.None;

    void OnLineChanged(object sender, TextChangedEventArgs e)
    {
        if (_applyingLine) return;
        var text = LineBox.Text.Trim();
        if (text.Length == 0)
        {
            LineHint.Text = "host:port:логин:пароль, логин:пароль@host:port или socks5://…";
            LineHint.Foreground = (Brush)FindResource("SubtleBrush");
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
        var p = parsed.Value;
        if (p.Scheme == ProxyKinds.Http) ProxyBox.SelectedIndex = 1;
        else if (p.Scheme == ProxyKinds.Socks5) ProxyBox.SelectedIndex = 2;
        else if (ProxyTag() == ProxyKinds.None) ProxyBox.SelectedIndex = 2;
        HostBox.Text = p.Host;
        PortBox.Text = p.Port.ToString();
        UserBox.Text = p.User;
        PassBox.Password = p.Pass;
        LineHint.Text = "✓ Распознано и подставлено ниже" + (p.Scheme is null ? "" : $" ({(p.Scheme == ProxyKinds.Http ? "HTTP" : "SOCKS5")})");
        LineHint.Foreground = (Brush)FindResource("GreenBrush");
        _applyingLine = false;
    }

    void OnSave(object sender, RoutedEventArgs e)
    {
        var name = NameBox.Text.Trim();
        if (name.Length == 0)
        {
            ConfirmWindow.Info(this, "Проверьте данные", "Введите название контейнера.");
            NameBox.Focus();
            return;
        }
        var ptype = ProxyTag();
        var host = HostBox.Text.Trim();
        var port = 0;
        if (ptype != ProxyKinds.None)
        {
            if (string.IsNullOrWhiteSpace(host))
            {
                ConfirmWindow.Info(this, "Проверьте данные", "Укажите адрес прокси или выберите «Без прокси».");
                HostBox.Focus();
                return;
            }
            if (!int.TryParse(PortBox.Text.Trim(), out port) || port is < 1 or > 65535)
            {
                ConfirmWindow.Info(this, "Проверьте данные", "Порт прокси должен быть числом от 1 до 65535.");
                PortBox.Focus();
                PortBox.SelectAll();
                return;
            }
        }
        _account.Name = name;
        _account.Color = ColorBox.SelectedItem as string ?? "#FFFFFF";
        _account.Proxy = ptype == ProxyKinds.None
            ? new ProxyCfg()
            : new ProxyCfg
            {
                Type = ptype,
                Host = host,
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
