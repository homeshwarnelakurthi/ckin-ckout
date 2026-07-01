import { Link } from "react-router-dom";
import { useAuth } from "../auth";

export default function Layout({ children }: { children: React.ReactNode }) {
  const { meta, logout } = useAuth();

  return (
    <div className="mx-auto flex min-h-full max-w-4xl flex-col">
      <header className="sticky top-0 z-10 bg-brand text-white shadow">
        <div className="flex items-center justify-between px-4 py-3">
          <Link to="/" className="text-lg font-bold tracking-tight">
            {meta?.business_name ?? "CK_IN&CK_OUT"}
          </Link>
          <button
            onClick={logout}
            className="rounded-lg px-3 py-2 text-sm hover:bg-white/10"
            aria-label="Log out"
          >
            Log out
          </button>
        </div>
      </header>

      <main className="flex-1 px-4 py-5">{children}</main>

      <footer className="px-4 py-4 text-center text-xs text-slate-400">
        {meta?.business_name} · times shown in {meta?.display_timezone}
      </footer>
    </div>
  );
}
