using System.ComponentModel;
using System.Windows;
using TGManager.Services;

namespace TGManager.ViewModels;

/// <summary>
/// Размеры и состав карточек контейнеров и шапки списка. Рассчитывается из <see cref="Settings"/>;
/// <see cref="Apply"/> уведомляет привязки, поэтому смена настроек действует без перезапуска.
/// </summary>
public sealed class ListLayout : INotifyPropertyChanged
{
    public ListLayout(Settings settings) => Apply(settings);

    public bool Compact { get; private set; }
    /// <summary>Кнопки действий стоят в одной строке с названием (компактная карточка), иначе — под ним.</summary>
    public bool Inline => Compact;

    public Thickness CardPadding { get; private set; }
    public Thickness CardGap { get; private set; }
    public Thickness InfoMargin { get; private set; }
    public Thickness MetaMargin { get; private set; }
    public Thickness StatusPadding { get; private set; }
    public Thickness FolderMargin { get; private set; }
    public double AccentBarHeight { get; private set; }
    public double NameSize { get; private set; }

    public Thickness ActionsMargin { get; private set; }
    public Thickness ButtonMargin { get; private set; }
    public Thickness ButtonPadding { get; private set; }
    public double ButtonHeight { get; private set; }
    public double ButtonMinWidth { get; private set; }
    public double ButtonFontSize { get; private set; }
    public double IconSize { get; private set; }
    public bool IconsOnly { get; private set; }
    public bool ShowLabels => !IconsOnly;
    public string ExportLabel => Compact ? "Экспорт" : "Экспорт session";

    public bool ShowLaunch { get; private set; }
    public bool ShowStop { get; private set; }
    public bool ShowFolder { get; private set; }
    public bool ShowExport { get; private set; }
    public bool ShowCleanup { get; private set; }
    public bool ShowEdit { get; private set; }
    public bool ShowDelete { get; private set; }
    public bool HasActions { get; private set; }

    public Thickness HeaderMargin { get; private set; }
    public Thickness SectionGap { get; private set; }
    public Thickness FilterMargin { get; private set; }
    public Thickness StatPadding { get; private set; }
    public double StatValueSize { get; private set; }
    public Thickness StatLabelMargin { get; private set; }
    public Thickness ResultMargin { get; private set; }
    public bool ShowSubtitle => !Compact;

    public void Apply(Settings settings)
    {
        Compact = settings.ListDensity == ListDensities.Compact;

        var vertical = settings.CardPadding;
        var horizontal = vertical <= 10 ? 12 : 18;
        CardPadding = new Thickness(horizontal, vertical, horizontal, vertical);
        CardGap = new Thickness(0, 0, 0, Compact ? 6 : 12);
        InfoMargin = Compact ? new Thickness(10, 0, 12, 0) : new Thickness(12, 0, 16, 0);
        MetaMargin = new Thickness(0, Compact ? 1 : 6, 0, 0);
        StatusPadding = Compact ? new Thickness(6, 2, 6, 2) : new Thickness(8, 4, 8, 4);
        FolderMargin = new Thickness(0, Compact ? 2 : 5, 0, 0);
        AccentBarHeight = Compact ? 30 : 36;
        NameSize = Compact ? 13 : 14;

        (ButtonHeight, IconSize, ButtonFontSize) = settings.ButtonSize switch
        {
            ButtonSizes.Small => (24d, 14d, 12d),
            ButtonSizes.Medium => (28d, 16d, 12d),
            _ => (36d, 18d, 13d),
        };
        IconsOnly = settings.ButtonStyle == ButtonStyles.Icon;
        ButtonMinWidth = IconsOnly ? ButtonHeight + 4 : 0;
        ButtonPadding = IconsOnly ? new Thickness(0)
            : settings.ButtonSize == ButtonSizes.Large ? new Thickness(12, 6, 12, 6) : new Thickness(10, 0, 10, 0);
        ActionsMargin = Compact ? new Thickness(0) : new Thickness(12, 10, 0, 0);
        ButtonMargin = Compact ? new Thickness(4, 0, 0, 0) : new Thickness(0, 4, 6, 0);

        var shown = settings.CardButtons;
        ShowLaunch = shown.Contains(CardActions.Launch);
        ShowStop = shown.Contains(CardActions.Stop);
        ShowFolder = shown.Contains(CardActions.Folder);
        ShowExport = shown.Contains(CardActions.Export);
        ShowCleanup = shown.Contains(CardActions.Cleanup);
        ShowEdit = shown.Contains(CardActions.Edit);
        ShowDelete = shown.Contains(CardActions.Delete);
        HasActions = shown.Count > 0;

        HeaderMargin = Compact ? new Thickness(26, 14, 26, 10) : new Thickness(26, 22, 26, 16);
        SectionGap = new Thickness(0, 0, 0, Compact ? 10 : 20);
        FilterMargin = new Thickness(0, Compact ? 10 : 20, 0, 0);
        StatPadding = Compact ? new Thickness(14, 8, 14, 8) : new Thickness(18, 14, 18, 14);
        StatValueSize = Compact ? 18 : 24;
        StatLabelMargin = new Thickness(0, Compact ? 0 : 4, 0, 0);
        ResultMargin = new Thickness(0, Compact ? 8 : 12, 0, 0);

        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(string.Empty));
    }

    public event PropertyChangedEventHandler? PropertyChanged;
}
