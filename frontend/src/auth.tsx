import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { api, type Meta, tokenStore, type User } from "./api";

type AuthState = {
  user: User | null;
  meta: Meta | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<User>;
  logout: () => void;
};

const Ctx = createContext<AuthState | null>(null);

// Auto-logout after this much inactivity, in case the device is left unlocked.
const IDLE_MS = 30 * 60 * 1000;

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [loading, setLoading] = useState(true);
  const idleTimer = useRef<number | undefined>(undefined);

  const logout = useCallback(() => {
    tokenStore.clear();
    setUser(null);
  }, []);

  const resetIdle = useCallback(() => {
    window.clearTimeout(idleTimer.current);
    idleTimer.current = window.setTimeout(logout, IDLE_MS);
  }, [logout]);

  // Bootstrap: load branding + restore session from a stored token.
  useEffect(() => {
    (async () => {
      try {
        setMeta(await api.meta());
      } catch {
        /* backend may be down; login page still renders */
      }
      if (tokenStore.get()) {
        try {
          setUser(await api.me());
        } catch {
          tokenStore.clear();
        }
      }
      setLoading(false);
    })();
  }, []);

  // Idle auto-logout wiring.
  useEffect(() => {
    if (!user) return;
    const events = ["mousedown", "keydown", "touchstart", "scroll"];
    events.forEach((e) => window.addEventListener(e, resetIdle));
    resetIdle();
    return () => {
      window.clearTimeout(idleTimer.current);
      events.forEach((e) => window.removeEventListener(e, resetIdle));
    };
  }, [user, resetIdle]);

  const login = useCallback(async (username: string, password: string) => {
    const res = await api.login(username, password);
    tokenStore.set(res.access_token);
    setUser(res.user);
    return res.user;
  }, []);

  const value = useMemo(
    () => ({ user, meta, loading, login, logout }),
    [user, meta, loading, login, logout]
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
