import { useCallback, useEffect, useMemo, useState } from "react";
import { api, ApiError, tokenStore, type Summary, type TimeEntry } from "../api";
import { useAuth } from "../auth";
import {
  elapsed,
  fmtDate,
  fmtHours,
  fmtMoney,
  fmtTime,
} from "../format";
import WeekBarChart from "../components/WeekBarChart";

export default function EmployeeDashboard() {
  const { meta } = useAuth();
  const tz = meta?.display_timezone ?? "UTC";
  const [summary, setSummary] = useState<Summary | null>(null);
  const [entries, setEntries] = useState<TimeEntry[]>([]);
  const [now, setNow] = useState(Date.now());
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const pageSize = 8;

  const refresh = useCallback(async () => {
    const [s, e] = await Promise.all([api.summary(), api.myEntries()]);
    setSummary(s);
    setEntries(e);
  }, []);

  useEffect(() => {
    refresh().catch((err) =>
      setError(err instanceof ApiError ? err.message : "Failed to load")
    );
  }, [refresh]);

  // Live ticking clock for the running-shift timer.
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);

  const open = summary?.open_entry ?? null;

  async function toggle() {
    setBusy(true);
    setError(null);
    setMsg(null);
    try {
      const res = open ? await api.clockOut() : await api.clockIn();
      setMsg(res.message);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Action failed");
    } finally {
      setBusy(false);
    }
  }

  async function downloadCsv() {
    setError(null);
    try {
      const resp = await fetch(api.exportUrl(), {
        headers: { Authorization: `Bearer ${tokenStore.get()}` },
      });
      if (!resp.ok) throw new ApiError(resp.status, "Export failed");
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "timesheet.csv";
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Export failed");
    }
  }

  const pageEntries = useMemo(
    () => entries.slice(page * pageSize, page * pageSize + pageSize),
    [entries, page]
  );
  const pageCount = Math.ceil(entries.length / pageSize) || 1;

  return (
    <div className="space-y-5">
      {/* Big state-aware clock button */}
      <div className="card flex flex-col items-center gap-4 py-8">
        {open ? (
          <>
            <div className="text-center">
              <p className="text-sm font-medium uppercase tracking-wide text-slate-500">
                On the clock since {fmtTime(open.clock_in_at, tz)}
              </p>
              <p className="mt-1 font-mono text-4xl font-bold tabular-nums text-brand">
                {elapsed(open.clock_in_at, now)}
              </p>
            </div>
            <button
              onClick={toggle}
              disabled={busy}
              className="btn min-h-[88px] w-full max-w-xs bg-red-600 text-2xl text-white hover:bg-red-700 focus:ring-red-500"
            >
              {busy ? "…" : "Clock Out"}
            </button>
          </>
        ) : (
          <>
            <p className="text-sm font-medium uppercase tracking-wide text-slate-500">
              You're clocked out
            </p>
            <button
              onClick={toggle}
              disabled={busy}
              className="btn min-h-[88px] w-full max-w-xs bg-green-600 text-2xl text-white hover:bg-green-700 focus:ring-green-500"
            >
              {busy ? "…" : "Clock In"}
            </button>
          </>
        )}
        {msg && <p className="text-center text-sm text-slate-600">{msg}</p>}
        {error && <p className="text-center text-sm text-red-600">{error}</p>}
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard title="Today" period={summary?.today} />
        <StatCard title="This week" period={summary?.week} />
        <StatCard title="This month" period={summary?.month} />
      </div>

      {/* Week chart */}
      <div className="card">
        <h2 className="mb-3 font-semibold text-slate-700">Hours this week</h2>
        <WeekBarChart entries={entries} tz={tz} />
      </div>

      {/* History table */}
      <div className="card">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-semibold text-slate-700">Shift history</h2>
          <button className="btn-accent text-sm" onClick={downloadCsv}>
            Export CSV
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500">
                <th className="py-2 pr-3 font-medium">Date</th>
                <th className="py-2 pr-3 font-medium">In</th>
                <th className="py-2 pr-3 font-medium">Out</th>
                <th className="py-2 pr-3 font-medium">Hours</th>
                <th className="py-2 pr-3 font-medium">Pay</th>
                <th className="py-2 pr-3 font-medium">Status</th>
                <th className="py-2 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {pageEntries.map((e) => (
                <EntryRow key={e.id} entry={e} tz={tz} onSaved={refresh} />
              ))}
              {entries.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-6 text-center text-slate-400">
                    No shifts yet — clock in to get started.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        {pageCount > 1 && (
          <div className="mt-3 flex items-center justify-between text-sm">
            <button
              className="btn bg-slate-100 text-slate-700 disabled:opacity-40"
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
            >
              Prev
            </button>
            <span className="text-slate-500">
              Page {page + 1} of {pageCount}
            </span>
            <button
              className="btn bg-slate-100 text-slate-700 disabled:opacity-40"
              onClick={() => setPage((p) => Math.min(pageCount - 1, p + 1))}
              disabled={page >= pageCount - 1}
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({ title, period }: { title: string; period?: { total_minutes: number; total_pay: string } }) {
  return (
    <div className="card">
      <p className="text-sm font-medium uppercase tracking-wide text-slate-500">{title}</p>
      <p className="mt-2 text-2xl font-bold text-brand">{fmtHours(period?.total_minutes ?? 0)}</p>
      <p className="text-lg font-semibold text-accent-dark">{fmtMoney(period?.total_pay ?? 0)}</p>
    </div>
  );
}

export function StatusPill({ status }: { status: string }) {
  const styles: Record<string, string> = {
    open: "bg-blue-100 text-blue-700",
    closed: "bg-green-100 text-green-700",
    flagged: "bg-amber-100 text-amber-800",
  };
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${styles[status] ?? ""}`}>
      {status}
    </span>
  );
}

function EntryRow({
  entry,
  tz,
  onSaved,
}: {
  entry: TimeEntry;
  tz: string;
  onSaved: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [inAt, setInAt] = useState(entry.clock_in_at.slice(0, 16));
  const [outAt, setOutAt] = useState((entry.clock_out_at ?? "").slice(0, 16));
  const [status, setStatus] = useState(entry.status);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function save() {
    setBusy(true);
    setErr(null);
    try {
      await api.correctEntry(entry.id, {
        clock_in_at: new Date(inAt).toISOString(),
        clock_out_at: outAt ? new Date(outAt).toISOString() : null,
        status,
        reason: reason || "manual correction",
      });
      setEditing(false);
      onSaved();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  if (!editing) {
    return (
      <tr className="border-t border-slate-100">
        <td className="py-2 pr-3">{fmtDate(entry.clock_in_at, tz)}</td>
        <td className="py-2 pr-3">{fmtTime(entry.clock_in_at, tz)}</td>
        <td className="py-2 pr-3">
          {entry.clock_out_at ? fmtTime(entry.clock_out_at, tz) : "—"}
        </td>
        <td className="py-2 pr-3">{fmtHours(entry.total_minutes)}</td>
        <td className="py-2 pr-3">{fmtMoney(entry.total_pay)}</td>
        <td className="py-2 pr-3">
          <StatusPill status={entry.status} />
          {entry.edited_by && <span className="ml-1 text-xs text-slate-400">(edited)</span>}
        </td>
        <td className="py-2">
          <button
            className="text-sm font-medium text-brand hover:underline"
            onClick={() => setEditing(true)}
          >
            Edit
          </button>
        </td>
      </tr>
    );
  }

  return (
    <tr className="border-t border-slate-100 bg-slate-50">
      <td className="py-2 pr-3" colSpan={7}>
        <div className="grid gap-2 sm:grid-cols-2">
          <label className="text-xs text-slate-600">
            Clock in
            <input
              type="datetime-local"
              className="input"
              value={inAt}
              onChange={(e) => setInAt(e.target.value)}
            />
          </label>
          <label className="text-xs text-slate-600">
            Clock out
            <input
              type="datetime-local"
              className="input"
              value={outAt}
              onChange={(e) => setOutAt(e.target.value)}
            />
          </label>
          <label className="text-xs text-slate-600">
            Status
            <select
              className="input"
              value={status}
              onChange={(e) => setStatus(e.target.value as TimeEntry["status"])}
            >
              <option value="open">open</option>
              <option value="closed">closed</option>
              <option value="flagged">flagged</option>
            </select>
          </label>
          <label className="text-xs text-slate-600">
            Reason (logged)
            <input
              className="input"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. forgot to clock out"
            />
          </label>
        </div>
        {err && <p className="mt-2 text-sm text-red-600">{err}</p>}
        <div className="mt-2 flex gap-2">
          <button className="btn-primary" onClick={save} disabled={busy}>
            {busy ? "Saving…" : "Save"}
          </button>
          <button className="btn bg-slate-200 text-slate-700" onClick={() => setEditing(false)}>
            Cancel
          </button>
        </div>
      </td>
    </tr>
  );
}
