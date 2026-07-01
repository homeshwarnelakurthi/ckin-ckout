import { Link } from "react-router-dom";
import { useAuth } from "../auth";

export default function Layout({ children }: { children: React.ReactNode }) {
  const { meta, logout } = useAuth();

  return (
    <div className="mx-auto flex min-h-full max-w-4xl flex-col">
      <header className="sticky top-0 z-10 border-b border-accent/20 bg-brand text-white">
        <div className="flex items-center justify-between px-4 py-4">
          <Link
            to="/"
            className="font-display text-xl tracking-wide text-white"
          >
            {meta?.business_name ?? "CK_IN&CK_OUT"}
          </Link>
          <button
            onClick={logout}
            className="rounded-md border border-white/20 px-3 py-1.5 text-xs font-semibold
              uppercase tracking-wider text-white/90 transition hover:border-accent/50 hover:text-accent-light"
            aria-label="Log out"
          >
            Log out
          </button>
        </div>
      </header>

      <main className="flex-1 px-4 py-6">{children}</main>

      <footer className="border-t border-ink-200 px-4 py-4 text-center text-xs text-ink-400">
        {meta?.business_name} · times shown in {meta?.display_timezone}
      </footer>
    </div>
  );
}
