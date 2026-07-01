// Thin fetch wrapper. Attaches the JWT and normalizes errors.

const API_BASE = import.meta.env.VITE_API_BASE ?? ""; // "" => same-origin (dev proxy)

export type User = {
  id: string;
  full_name: string;
  username: string;
  hourly_rate: string;
  is_active: boolean;
};

export type TimeEntry = {
  id: string;
  user_id: string;
  clock_in_at: string;
  clock_out_at: string | null;
  total_minutes: number | null;
  total_pay: string | null;
  status: "open" | "closed" | "flagged";
  edited_by: string | null;
  notes: string | null;
};

export type Period = { total_minutes: number; total_hours: number; total_pay: string };
export type Summary = {
  today: Period;
  week: Period;
  month: Period;
  open_entry: TimeEntry | null;
};
export type Meta = {
  business_name: string;
  manager_name: string;
  display_timezone: string;
  default_hourly_rate: number;
};

const TOKEN_KEY = "ckin_token";

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  const token = tokenStore.get();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const resp = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (resp.status === 204) return undefined as T;

  const contentType = resp.headers.get("content-type") || "";
  if (!resp.ok) {
    let detail = resp.statusText;
    if (contentType.includes("application/json")) {
      const body = await resp.json().catch(() => null);
      detail = body?.detail ?? detail;
    }
    // Auto-logout on auth failure.
    if (resp.status === 401) tokenStore.clear();
    throw new ApiError(resp.status, detail);
  }
  if (contentType.includes("text/csv")) return (await resp.text()) as unknown as T;
  return (await resp.json()) as T;
}

export const api = {
  meta: () => request<Meta>("/api/meta"),
  login: (username: string, password: string) =>
    request<{ access_token: string; user: User }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  me: () => request<User>("/api/me"),
  clockIn: () => request<{ entry: TimeEntry; message: string }>("/api/clock-in", { method: "POST" }),
  clockOut: () => request<{ entry: TimeEntry; message: string }>("/api/clock-out", { method: "POST" }),
  summary: () => request<Summary>("/api/timesheet/me/summary"),
  myEntries: () => request<TimeEntry[]>("/api/timesheet/me"),
  correctEntry: (entryId: string, payload: Record<string, unknown>) =>
    request<TimeEntry>(`/api/timesheet/me/entries/${entryId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  exportUrl: () => `${API_BASE}/api/timesheet/me/export?format=csv`,
};
