using System.Windows;
using TGManager.Services;

namespace TGManager.Windows;

public partial class FolderWindow : Window
{
    readonly HashSet<string> _existing;
    public string Result { get; private set; } = "";

    public FolderWindow(IEnumerable<string> existing, string? current = null)
    {
        _existing = new HashSet<string>(existing.Where(name =>
            !string.Equals(name, current, StringComparison.OrdinalIgnoreCase)), StringComparer.OrdinalIgnoreCase);
        InitializeComponent();
        Chrome.Attach(this, WindowFrame);
        Heading.Text = current is null ? "Новая папка" : "Переименовать папку";
        NameBox.Text = current ?? "";
        Loaded += (_, _) => { NameBox.Focus(); NameBox.SelectAll(); };
    }

    void OnSave(object sender, RoutedEventArgs e)
    {
        var name = NameBox.Text.Trim();
        if (name.Length == 0 || _existing.Contains(name))
        {
            ErrorText.Text = name.Length == 0 ? "Введите название папки." : "Папка с таким именем уже существует.";
            NameBox.Focus();
            return;
        }
        Result = name;
        DialogResult = true;
    }
}
