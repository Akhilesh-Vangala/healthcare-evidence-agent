import { Component, type ReactNode, createContext, useCallback, useContext, useEffect, useRef, useState } from "react";

/* ---------------------------------------------------------------- theme */
export type Theme = "light" | "dark";

function initialTheme(): Theme {
  try {
    const saved = localStorage.getItem("hea.theme");
    if (saved === "light" || saved === "dark") return saved;
  } catch { /* storage unavailable: fall back to the OS preference */ }
  return matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

export function useTheme(): [Theme, () => void] {
  const [theme, setTheme] = useState<Theme>(initialTheme);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem("hea.theme", theme); } catch { /* non-persistent is fine */ }
  }, [theme]);
  return [theme, () => setTheme((t) => (t === "dark" ? "light" : "dark"))];
}

export function ThemeToggle({ theme, onToggle }: { theme: Theme; onToggle: () => void }) {
  return (
    <button type="button" className="icon-btn" onClick={onToggle} aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}>
      {theme === "dark" ? "☀" : "☾"}
    </button>
  );
}

/* ---------------------------------------------------------------- tabs (WAI-ARIA tabs pattern) */
export function Tabs<T extends string>({ items, current, onSelect, label }: {
  items: { id: T; label: string; dot: string }[]; current: T; onSelect: (id: T) => void; label: string;
}) {
  const refs = useRef<Record<string, HTMLButtonElement | null>>({});
  function onKey(e: React.KeyboardEvent, i: number) {
    const n = items.length;
    const next = e.key === "ArrowRight" ? (i + 1) % n : e.key === "ArrowLeft" ? (i - 1 + n) % n
      : e.key === "Home" ? 0 : e.key === "End" ? n - 1 : -1;
    if (next < 0) return;
    e.preventDefault();
    onSelect(items[next].id);
    refs.current[items[next].id]?.focus();
  }
  return (
    <nav className="tabs" role="tablist" aria-label={label}>
      {items.map((t, i) => (
        <button key={t.id} ref={(el) => { refs.current[t.id] = el; }} role="tab" type="button" id={`tab-${t.id}`}
          aria-selected={current === t.id} aria-controls={`panel-${t.id}`} tabIndex={current === t.id ? 0 : -1}
          className={current === t.id ? "on" : ""} onClick={() => onSelect(t.id)} onKeyDown={(e) => onKey(e, i)}>
          <span className="dot" style={{ background: t.dot }} aria-hidden="true" />{t.label}
        </button>
      ))}
    </nav>
  );
}

/* ---------------------------------------------------------------- toasts */
type Toast = { id: number; text: string; tone: "ok" | "bad" };
const ToastCtx = createContext<(text: string, tone?: Toast["tone"]) => void>(() => {});
export const useToast = () => useContext(ToastCtx);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const push = useCallback((text: string, tone: Toast["tone"] = "ok") => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, text, tone }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 2600);
  }, []);
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="toasts" role="status" aria-live="polite">
        {toasts.map((t) => <div key={t.id} className={`toast ${t.tone}`}>{t.text}</div>)}
      </div>
    </ToastCtx.Provider>
  );
}

export function CopyButton({ text, label = "Copy" }: { text: string; label?: string }) {
  const toast = useToast();
  return (
    <button type="button" className="ghost sm" onClick={() => navigator.clipboard?.writeText(text).then(
      () => toast("Copied to clipboard"), () => toast("Copy failed", "bad"))}>{label}</button>
  );
}

/* ---------------------------------------------------------------- states */
export function Skeleton({ lines = 3 }: { lines?: number }) {
  return <div className="skeleton" aria-busy="true" aria-label="Loading">{Array.from({ length: lines }, (_, i) => <span key={i} style={{ width: `${92 - i * 14}%` }} />)}</div>;
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return <div className="empty"><b>{title}</b>{children && <p>{children}</p>}</div>;
}

export function ErrorBox({ error, onRetry }: { error: string; onRetry?: () => void }) {
  return (
    <div className="error-box" role="alert">
      <b>Something went wrong</b><span>{error}</span>
      {onRetry && <button type="button" className="ghost sm" onClick={onRetry}>Retry</button>}
    </div>
  );
}

export function Badge({ tone, children }: { tone: "teal" | "amber" | "rose" | "sky" | "violet"; children: ReactNode }) {
  return <span className={`badge b-${tone}`}>{children}</span>;
}

/** Keeps one broken page from taking down the console. */
export class ErrorBoundary extends Component<{ children: ReactNode; resetKey: string }, { error: string | null }> {
  state = { error: null as string | null };
  static getDerivedStateFromError(e: Error) { return { error: e.message }; }
  componentDidUpdate(prev: { resetKey: string }) { if (prev.resetKey !== this.props.resetKey && this.state.error) this.setState({ error: null }); }
  render() { return this.state.error ? <ErrorBox error={this.state.error} onRetry={() => this.setState({ error: null })} /> : this.props.children; }
}

export function useElapsed(running: boolean): number {
  const [ms, setMs] = useState(0);
  useEffect(() => {
    if (!running) return;
    const t0 = performance.now();
    setMs(0);
    const id = setInterval(() => setMs(performance.now() - t0), 100);
    return () => clearInterval(id);
  }, [running]);
  return ms;
}
