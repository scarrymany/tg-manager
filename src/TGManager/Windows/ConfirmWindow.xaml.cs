using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using TGManager.Services;

namespace TGManager.Windows;

public partial class ConfirmWindow : Window
{
    public enum Choice { Cancel, Accept, Destructive }

    public Choice ResultChoice { get; private set; } = Choice.Cancel;

    public ConfirmWindow()
    {
        InitializeComponent();
        Chrome.Attach(this, WindowFrame);
        PreviewKeyDown += (_, e) =>
        {
            if (e.Key != Key.Escape) return;
            ResultChoice = Choice.Cancel;
            DialogResult = false;
            Close();
            e.Handled = true;
        };
    }

    public static bool Ask(Window? owner, string title, string text, string yes = "Да", string no = "Отмена")
    {
        var w = Build(owner, title, text);
        w.AddGhost(no, Choice.Cancel, isCancel: true);
        w.AddPrimary(yes, Choice.Accept, isDefault: true);
        w.ShowDialog();
        return w.ResultChoice == Choice.Accept;
    }

    public static void Info(Window? owner, string title, string text)
    {
        var w = Build(owner, title, text);
        w.AddPrimary("ОК", Choice.Accept, isDefault: true);
        w.ShowDialog();
    }

    public static Choice AskDelete(Window? owner, string title, string text)
    {
        var w = Build(owner, title, text);
        w.AddGhost("Отмена", Choice.Cancel, isCancel: true);
        w.AddGhost("Удалить, папку оставить", Choice.Accept);
        w.AddDanger("Удалить с данными", Choice.Destructive);
        w.ShowDialog();
        return w.ResultChoice;
    }

    static ConfirmWindow Build(Window? owner, string title, string text)
    {
        var w = new ConfirmWindow();
        if (owner is { IsLoaded: true }) w.Owner = owner;
        w.Title = title;
        w.TitleText.Text = title;
        w.BodyText.Text = text;
        return w;
    }

    void AddGhost(string label, Choice choice, bool isCancel = false)
        => Add(label, (Style)FindResource("GhostButton"), choice, isDefault: false, isCancel);
    void AddPrimary(string label, Choice choice, bool isDefault = false)
        => Add(label, (Style)FindResource("PrimaryButton"), choice, isDefault, isCancel: false);
    void AddDanger(string label, Choice choice)
        => Add(label, (Style)FindResource("DangerButton"), choice, isDefault: false, isCancel: false);

    void Add(string label, Style style, Choice choice, bool isDefault, bool isCancel)
    {
        var b = new Button
        {
            Content = label,
            Style = style,
            Margin = new Thickness(8, 0, 0, 0),
            MinWidth = 88,
            Padding = new Thickness(14, 8, 14, 8),
            IsDefault = isDefault,
            IsCancel = isCancel,
        };
        b.Click += (_, _) =>
        {
            ResultChoice = choice;
            DialogResult = choice != Choice.Cancel;
            Close();
        };
        Buttons.Children.Add(b);
        if (isDefault)
            Loaded += (_, _) => b.Focus();
    }
}
