using TGManager.Services;
using TGManager.ViewModels;

var renderOutput = args.Length == 2 && args[0] == "--render" ? System.IO.Path.GetFullPath(args[1]) : null;

var account = new AccountVm(new Account
{
    Name = "Рабочий аккаунт",
    Notes = "Support Europe",
    Proxy = new ProxyCfg { Type = ProxyKinds.Socks5, Host = "proxy.local", Port = 1080 }
});
void Check(bool condition, string message)
{
    if (!condition) throw new InvalidOperationException(message);
    Console.WriteLine("PASS " + message);
}
Check(AccountFilter.Matches(account, " РАБОЧИЙ ", AccountStatusFilter.All), "Name search ignores case and surrounding spaces");
Check(AccountFilter.Matches(account, "support", AccountStatusFilter.All), "Notes are searchable");
Check(AccountFilter.Matches(account, "proxy.local", AccountStatusFilter.All), "Proxy host is searchable");
Check(!AccountFilter.Matches(account, "absent", AccountStatusFilter.All), "Unmatched query hides account");
Check(AccountFilter.Matches(account, "", AccountStatusFilter.Stopped), "Idle account matches stopped filter");
account.Running = true;
Check(AccountFilter.Matches(account, "", AccountStatusFilter.Running), "Running state matches");
Check(!AccountFilter.Matches(account, "", AccountStatusFilter.Stopped), "Running account is excluded from stopped");
account.Busy = true;
Check(AccountFilter.Matches(account, "", AccountStatusFilter.Busy), "Busy state matches");
Check(!AccountFilter.Matches(account, "", AccountStatusFilter.Running), "Busy state takes precedence");
account.HasTdata = false;
Check(AccountFilter.Matches(account, "", AccountStatusFilter.MissingData), "Missing data matches");
account.HasTdata = true;
Check(!AccountFilter.Matches(account, "", AccountStatusFilter.MissingData), "Present data is excluded");
account.Model.Proxy.Password = "secret-not-searchable";
Check(!AccountFilter.Matches(account, "secret-not-searchable", AccountStatusFilter.All), "Proxy credentials are not searchable");
account.Model.Folder = "Работа";
Check(AccountFilter.Matches(account, "", AccountStatusFilter.All, "Работа"), "Folder includes its accounts");
Check(!AccountFilter.Matches(account, "", AccountStatusFilter.All, "Личное"), "Folder excludes other accounts");
Check(!AccountFilter.Matches(account, "", AccountStatusFilter.All, ""), "Unassigned folder excludes grouped accounts");
Check(AccountFilter.Matches(account, "", AccountStatusFilter.All, null), "All folders includes grouped accounts");
Check(!AccountFilter.Matches(account, "missing", AccountStatusFilter.All, "Работа"), "Folder combines with search");
StoreChecks.Run();
if (renderOutput is not null) UiChecks.Run(renderOutput);
