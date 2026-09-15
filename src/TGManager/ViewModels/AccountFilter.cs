namespace TGManager.ViewModels;

public enum AccountStatusFilter { All, Running, Stopped, Busy, MissingData }

public static class AccountFilter
{
    public static bool Matches(AccountVm account, string query, AccountStatusFilter status, string? folder = null)
    {
        if (folder is not null && !string.Equals(account.Folder, folder, StringComparison.OrdinalIgnoreCase))
            return false;
        var matchesStatus = status switch
        {
            AccountStatusFilter.Running => account.Running && !account.Busy && !account.Stopping,
            AccountStatusFilter.Stopped => !account.Running && !account.Busy && !account.Stopping,
            AccountStatusFilter.Busy => account.Busy || account.Stopping,
            AccountStatusFilter.MissingData => !account.HasTdata,
            _ => true,
        };
        if (!matchesStatus) return false;
        var term = query.Trim();
        return term.Length == 0
            || account.Name.Contains(term, StringComparison.OrdinalIgnoreCase)
            || account.Id.Contains(term, StringComparison.OrdinalIgnoreCase)
            || account.Notes.Contains(term, StringComparison.OrdinalIgnoreCase)
            || account.ProxySummary.Contains(term, StringComparison.OrdinalIgnoreCase);
    }
}
