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
      <div className="card flex flex-col items-center gap-4 py-9">
        {open ? (
          <>
            <div className="text-center">
              <p className="eyebrow">On the clock since {fmtTime(open.clock_in_at, tz)}</p>
              <p className="mt-2 font-mono text-4xl font-semibold tabular-nums text-brand">
                {elapsed(open.clock_in_at, now)}
              </p>
            </div>
            <button
              onClick={toggle}
              disabled={busy}
              className="btn min-h-[88px] w-full max-w-xs rounded-md bg-red-800 text-xl uppercase
                tracking-wide text-white hover:bg-red-900 focus:ring-red-700"
            >
              {busy ? "…" : "Clock Out"}
            </button>
          </>
        ) : (
          <>
            <p className="eyebrow">You're clocked out</p>
            <button
              onClick={toggle}
              disabled={busy}
              className="btn min-h-[88px] w-full max-w-xs rounded-md bg-brand text-xl uppercase
                tracking-wide text-white hover:bg-brand-light focus:ring-brand"
            >
              {busy ? "…" : "Clock In"}
            </button>
          </>
        )}
        {msg && <p className="text-center text-sm text-ink-500">{msg}</p>}
        {error && <p className="text-center text-sm text-red-700">{error}</p>}
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard title="Today" period={summary?.today} />
        <StatCard title="This Week" period={summary?.week} />
        <StatCard title="This Month" period={summary?.month} />
      </div>

      {/* Week chart */}
      <div className="card">
        <h2 className="font-display mb-4 text-lg text-brand">Hours This Week</h2>
        <WeekBarChart entries={entries} tz={tz} />
      </div>

      {/* History table */}
      <div className="card">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-display text-lg text-brand">Shift History</h2>
          <button className="btn-accent text-xs" onClick={downloadCsv}>
            Export CSV
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-ink-200 text-left">
                <th className="eyebrow py-2 pr-3 font-semibold">Date</th>
                <th className="eyebrow py-2 pr-3 font-semibold">In</th>
                <th className="eyebrow py-2 pr-3 font-semibold">Out</th>
                <th className="eyebrow py-2 pr-3 font-semibold">Hours</th>
                <th className="eyebrow py-2 pr-3 font-semibold">Pay</th>
                <th className="eyebrow py-2 pr-3 font-semibold">Status</th>
                <th className="py-2 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {pageEntries.map((e) => (
                <EntryRow key={e.id} entry={e} tz={tz} onSaved={refresh} />
              ))}
              {entries.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-6 text-center text-ink-400">
                    No shifts yet — clock in to get started.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        {pageCount > 1 && (
          <div className="mt-4 flex items-center justify-between text-sm">
            <button
              className="btn border border-ink-200 bg-white text-ink-700 disabled:opacity-40"
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
            >
              Prev
            </button>
            <span className="text-ink-500">
              Page {page + 1} of {pageCount}
            </span>
            <button
              className="btn border border-ink-200 bg-white text-ink-700 disabled:opacity-40"
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
    <div className="card border-t-2 border-t-accent">
      <p className="eyebrow">{title}</p>
      <p className="font-display mt-2 text-2xl text-brand">{fmtHours(period?.total_minutes ?? 0)}</p>
      <p className="mt-0.5 text-lg font-semibold text-accent-dark">{fmtMoney(period?.total_pay ?? 0)}</p>
    </div>
  );
}

export function StatusPill({ status }: { status: string }) {
  const styles: Record<string, string> = {
    open: "border border-brand/20 bg-brand/5 text-brand",
    closed: "border border-ink-200 bg-ink-100 text-ink-700",
    flagged: "border border-accent/40 bg-accent/10 text-accent-dark",
  };
  return (
    <span
      className={`rounded-sm px-2 py-0.5 text-xs font-semibold uppercase tracking-wide ${styles[status] ?? ""}`}
    >
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
      <tr className="border-b border-ink-100">
        <td className="py-3 pr-3">{fmtDate(entry.clock_in_at, tz)}</td>
        <td className="py-3 pr-3">{fmtTime(entry.clock_in_at, tz)}</td>
        <td className="py-3 pr-3">
          {entry.clock_out_at ? fmtTime(entry.clock_out_at, tz) : "—"}
        </td>
        <td className="py-3 pr-3">{fmtHours(entry.total_minutes)}</td>
        <td className="py-3 pr-3">{fmtMoney(entry.total_pay)}</td>
        <td className="py-3 pr-3">
          <StatusPill status={entry.status} />
          {entry.edited_by && <span className="ml-1 text-xs text-ink-400">(edited)</span>}
        </td>
        <td className="py-3">
          <button
            className="text-xs font-semibold uppercase tracking-wide text-accent-dark hover:underline"
            onClick={() => setEditing(true)}
          >
            Edit
          </button>
        </td>
      </tr>
    );
  }

  return (
    <tr className="border-b border-ink-100 bg-ink-50">
      <td className="py-3 pr-3" colSpan={7}>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="label">
            Clock in
            <input
              type="datetime-local"
              className="input mt-1 normal-case tracking-normal"
              value={inAt}
              onChange={(e) => setInAt(e.target.value)}
            />
          </label>
          <label className="label">
            Clock out
            <input
              type="datetime-local"
              className="input mt-1 normal-case tracking-normal"
              value={outAt}
              onChange={(e) => setOutAt(e.target.value)}
            />
          </label>
          <label className="label">
            Status
            <select
              className="input mt-1 normal-case tracking-normal"
              value={status}
              onChange={(e) => setStatus(e.target.value as TimeEntry["status"])}
            >
              <option value="open">open</option>
              <option value="closed">closed</option>
              <option value="flagged">flagged</option>
            </select>
          </label>
          <label className="label">
            Reason (logged)
            <input
              className="input mt-1 normal-case tracking-normal"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. forgot to clock out"
            />
          </label>
        </div>
        {err && <p className="mt-2 text-sm text-red-700">{err}</p>}
        <div className="mt-3 flex gap-2">
          <button className="btn-primary" onClick={save} disabled={busy}>
            {busy ? "Saving…" : "Save"}
          </button>
          <button
            className="btn border border-ink-200 bg-white text-ink-700"
            onClick={() => setEditing(false)}
          >
            Cancel
          </button>
        </div>
      </td>
    </tr>
  );
}
