using System.ComponentModel;
using System.IO;
using System.Runtime.CompilerServices;
using System.Windows.Media;
using TGManager.Services;

namespace TGManager.ViewModels;

public sealed class AccountVm : INotifyPropertyChanged
{
    public Account Model { get; private set; }

    public AccountVm(Account account)
    {
        Model = account;
        RefreshMeta();
    }

    public string Id => Model.Id;
    public string Name => Model.Name;
    public string Color => string.IsNullOrWhiteSpace(Model.Color) ? "#FFFFFF" : Model.Color;
    public Brush ColorBrush
    {
        get
        {
            try { return new SolidColorBrush((Color)ColorConverter.ConvertFromString(Color)!); }
            catch { return Brushes.White; }
        }
    }

    public string ProxySummary => Model.Proxy.Summary();

    bool _running;
    bool _busy;
    bool _stopping;
    bool _hasTdata;

    public bool Running { get => _running; set { if (_running == value) return; _running = value; Raise(nameof(Running)); RaiseState(); } }
    public bool Busy { get => _busy; set { if (_busy == value) return; _busy = value; Raise(nameof(Busy)); RaiseState(); } }
    /// <summary>Идёт остановка Telegram (кнопки заблокированы, чтобы не нажать дважды).</summary>
    public bool Stopping { get => _stopping; set { if (_stopping == value) return; _stopping = value; Raise(nameof(Stopping)); RaiseState(); } }
    public bool HasTdata { get => _hasTdata; set { if (_hasTdata == value) return; _hasTdata = value; Raise(nameof(HasTdata)); Raise(nameof(TdataLabel)); Raise(nameof(TdataBrush)); } }

    string _busyLabel = "Чистка…";
    public string BusyLabel
    {
        get => _busyLabel;
        set
        {
            if (_busyLabel == value) return;
            _busyLabel = value;
            if (Busy) Raise(nameof(StatusText));
        }
    }

    public string StatusText => Busy ? BusyLabel : Stopping ? "Остановка…" : Running ? "Запущен" : "Остановлен";
    public Brush StatusFg => Busy || Stopping ? (Brush)App.Current.FindResource("YellowBrush")
                           : Running ? (Brush)App.Current.FindResource("GreenBrush")
                           : (Brush)App.Current.FindResource("MutedBrush");
    public Brush StatusBg => Running && !Busy && !Stopping
        ? (Brush)App.Current.FindResource("GreenBgBrush")
        : (Brush)App.Current.FindResource("HoverBrush");

    public bool CanLaunch => !Running && !Busy && !Stopping;
    public bool CanStop => Running && !Busy && !Stopping;
    public bool CanCleanup => !Running && !Stopping;
    public bool CanExport => !Running && !Stopping;
    public bool CanEdit => !Busy && !Stopping;

    public string TdataLabel => HasTdata ? "✓ tdata" : "✗ нет tdata";
    public Brush TdataBrush => HasTdata
        ? (Brush)App.Current.FindResource("MutedBrush")
        : (Brush)App.Current.FindResource("YellowBrush");

    public string MetaLeft => ProxySummary + "  ·  ";

    public void Apply(Account account)
    {
        Model = account;
        Raise(nameof(Name));
        Raise(nameof(Color));
        Raise(nameof(ColorBrush));
        Raise(nameof(ProxySummary));
        Raise(nameof(MetaLeft));
        RefreshMeta();
    }

    /// <summary>Перечитывает наличие tdata. Уведомления идут только при реальном изменении.</summary>
    public void RefreshMeta()
    {
        HasTdata = Paths.IsSafeAccountId(Id) && Directory.Exists(Paths.AccountTdata(Id));
    }

    void RaiseState()
    {
        Raise(nameof(StatusText));
        Raise(nameof(StatusFg));
        Raise(nameof(StatusBg));
        Raise(nameof(CanLaunch));
        Raise(nameof(CanStop));
        Raise(nameof(CanCleanup));
        Raise(nameof(CanExport));
        Raise(nameof(CanEdit));
    }

    public event PropertyChangedEventHandler? PropertyChanged;
    void Raise([CallerMemberName] string? name = null)
        => PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
}
