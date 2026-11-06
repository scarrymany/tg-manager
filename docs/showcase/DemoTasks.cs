using System.Reflection;
using TGManager.Services;
using TGManager.ViewModels;

/// <summary>
/// Cleanup and export tasks driven by the same events TGWorker.exe emits, without starting a worker.
/// </summary>
internal sealed class DemoTasks : IDisposable
{
    public const int CleanupAccountIndex = 6;
    public const int ExportAccountIndex = 7;
    const int FinishedAccountIndex = 5;
    const int CleanupTotal = 48;
    const int CleanupStart = 19;
    const int FloodAtStep = 11;
    const int FloodSeconds = 23;
    const int ExportTotal = 4;
    const int ExportDoneStep = 8;
    const string ExportZip = @"D:\Export\79000000007.zip";

    static readonly Dictionary<string, string[]> CleanupLabels = new()
    {
        ["channels"] = ["Канал «Рынок и аналитика»", "Канал «Дизайн каждый день»", "Канал «Вакансии IT»", "Канал «Новости города»"],
        ["groups"] = ["Группа «Чат проекта»", "Группа «Соседи · ЖК»", "Группа «Митап 2026»"],
        ["private"] = ["Диалог с Анной", "Диалог с Максимом", "Диалог с Ольгой"],
        ["bots"] = ["@weather_digest_bot", "@tasks_reminder_bot"],
    };

    static readonly (string Stage, string Label)[] ExportSteps =
    [
        ("Загрузка tdata…", "tdata"),
        ("Конвертация tdata → Telethon (без прокси)…", "telethon"),
        ("Чтение профиля…", "profile"),
        ("Пишу 79000000007.session + json…", "session"),
    ];

    public DemoTasks(Store store)
    {
        Cleanup = new TaskVm(store.Accounts[CleanupAccountIndex], ["channels", "groups", "private", "bots"], revoke: false);
        Apply(Cleanup, new WorkerEvent { Type = "stage", Msg = "Загрузка tdata…" });
        Apply(Cleanup, new WorkerEvent { Type = "stage", Msg = "Подключение к Telegram (без прокси)…" });
        Apply(Cleanup, new WorkerEvent { Type = "stage", Msg = "Сканирование диалогов (включая архив)…" });
        Apply(Cleanup, new WorkerEvent
        {
            Type = "summary", Total = CleanupTotal,
            Counts = new() { ["channels"] = 18, ["groups"] = 12, ["private"] = 11, ["bots"] = 7 },
        });
        for (var done = 1; done <= CleanupStart; done++)
        {
            AdvanceCleanup(done);
            if (done == FloodAtStep) Apply(Cleanup, new WorkerEvent { Type = "flood", Seconds = FloodSeconds });
        }

        Export = new TaskVm(store.Accounts[ExportAccountIndex], WorkerKind.ExportSession, @"D:\Export");
        AdvanceExport(1);

        Finished = new TaskVm(store.Accounts[FinishedAccountIndex], ["channels", "groups", "bots"], revoke: false);
        Apply(Finished, new WorkerEvent { Type = "summary", Total = 26, Counts = new() { ["channels"] = 14, ["groups"] = 9, ["bots"] = 3 } });
        Apply(Finished, new WorkerEvent { Type = "progress", Done = 26, Total = 26, Cat = "bots", Label = "@weather_digest_bot" });
        Apply(Finished, new WorkerEvent { Type = "done" });
        Exit(Finished);
    }

    public TaskVm Cleanup { get; }
    public TaskVm Export { get; }
    public TaskVm Finished { get; }
    public IReadOnlyList<TaskVm> All => [Cleanup, Export, Finished];

    /// <summary>One storyboard tick: cleanup moves on, export walks its stages and finishes at a fixed step.</summary>
    public void Advance(int step)
    {
        AdvanceCleanup(Math.Min(CleanupTotal - 1, CleanupStart + step * 2));
        if (step < ExportDoneStep)
        {
            AdvanceExport(1 + step * (ExportSteps.Length - 1) / ExportDoneStep);
            return;
        }
        if (step != ExportDoneStep) return;
        Apply(Export, new WorkerEvent { Type = "progress", Done = ExportTotal, Total = ExportTotal, Cat = "export", Label = "zip" });
        Apply(Export, new WorkerEvent { Type = "done", Zip = ExportZip, Phone = "79000000007" });
        Exit(Export);
    }

    public void Dispose()
    {
        foreach (var task in All) task.Host.Dispose();
    }

    void AdvanceCleanup(int done)
    {
        var category = done < 18 ? "channels" : done < 30 ? "groups" : done < 41 ? "private" : "bots";
        Apply(Cleanup, new WorkerEvent
        {
            Type = "progress", Done = done, Total = CleanupTotal, Cat = category,
            Label = CleanupLabels[category][done % CleanupLabels[category].Length],
        });
    }

    void AdvanceExport(int stage)
    {
        var (message, label) = ExportSteps[Math.Clamp(stage, 0, ExportSteps.Length - 1)];
        if (Export.Current == message) return;
        Apply(Export, new WorkerEvent { Type = "progress", Done = stage, Total = ExportTotal, Cat = "export", Label = label });
        Apply(Export, new WorkerEvent { Type = "stage", Msg = message });
    }

    static void Apply(TaskVm task, WorkerEvent ev) => Invoke(task, "Apply", ev);

    /// <summary>Same path as a worker exiting with code 0: the task turns "done" and frees its host.</summary>
    static void Exit(TaskVm task) => Invoke(task, "OnExited", 0);

    static void Invoke(TaskVm task, string method, params object[] args)
        => typeof(TaskVm).GetMethod(method, BindingFlags.Instance | BindingFlags.NonPublic)!.Invoke(task, args);
}
