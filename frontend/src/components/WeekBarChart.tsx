import { useMemo } from "react";
import type { TimeEntry } from "../api";

// Lightweight CSS bar chart of hours worked per day for the current (local) week.
export default function WeekBarChart({
  entries,
  tz,
}: {
  entries: TimeEntry[];
  tz: string;
}) {
  const days = useMemo(() => {
    // Build Mon..Sun buckets for the current local week.
    const fmt = new Intl.DateTimeFormat("en-US", { timeZone: tz, weekday: "short" });
    const labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
    const buckets: Record<string, number> = Object.fromEntries(labels.map((l) => [l, 0]));

    // Determine start of this local week (Monday 00:00).
    const nowParts = new Intl.DateTimeFormat("en-CA", {
      timeZone: tz,
      year: "numeric",
      month: "2-digit",
      day: "numeric",
      weekday: "short",
    }).formatToParts(new Date());
    const wd = nowParts.find((p) => p.type === "weekday")?.value ?? "Mon";
    const idx = labels.indexOf(wd);
    const today = new Date();
    const weekStart = new Date(today);
    weekStart.setDate(today.getDate() - (idx < 0 ? 0 : idx));
    weekStart.setHours(0, 0, 0, 0);

    for (const e of entries) {
      if (e.status !== "closed" || e.total_minutes == null) continue;
      const d = new Date(e.clock_in_at);
      if (d < weekStart) continue;
      const label = fmt.format(d);
      if (label in buckets) buckets[label] += e.total_minutes / 60;
    }
    return labels.map((l) => ({ label: l, hours: buckets[l] }));
  }, [entries, tz]);

  const max = Math.max(1, ...days.map((d) => d.hours));

  return (
    <div className="flex h-40 items-end gap-2 border-b border-ink-200 pb-0">
      {days.map((d) => (
        <div key={d.label} className="flex flex-1 flex-col items-center gap-1">
          <div className="flex w-full flex-1 items-end">
            <div
              className="w-full rounded-t-sm bg-accent transition-all"
              style={{ height: `${(d.hours / max) * 100}%` }}
              title={`${d.hours.toFixed(1)}h`}
            />
          </div>
          <span className="eyebrow pt-1 text-[11px]">{d.label}</span>
          <span className="text-[11px] font-medium text-ink-400">
            {d.hours > 0 ? `${d.hours.toFixed(1)}h` : ""}
          </span>
        </div>
      ))}
    </div>
  );
}
