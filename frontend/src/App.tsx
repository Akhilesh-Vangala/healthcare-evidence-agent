import { useEffect, useState } from "react";
import { type Health, api } from "./api";
import { Ask } from "./pages/Ask";
import { Check } from "./pages/Check";
import { Explorer } from "./pages/Explorer";
import { Overview } from "./pages/Overview";
import { Runs } from "./pages/Runs";
import { Study } from "./pages/Study";
import { type Page, navigate, useRoute } from "./route";
import { ErrorBoundary, Tabs, ThemeToggle, ToastProvider, useTheme } from "./ui";

const NAV: { id: Page; label: string; dot: string }[] = [
  { id: "overview", label: "Overview", dot: "var(--teal)" },
  { id: "ask", label: "Ask the agent", dot: "var(--violet)" },
  { id: "explorer", label: "Evidence explorer", dot: "var(--sky)" },
  { id: "check", label: "Citation check", dot: "var(--teal)" },
  { id: "study", label: "Study", dot: "var(--amber)" },
  { id: "runs", label: "Saved runs", dot: "var(--muted)" },
];

const TITLES: Record<Page, string> = {
  overview: "Overview", ask: "Ask the agent", explorer: "Evidence explorer", check: "Citation check", study: "Study", runs: "Saved runs",
};

export function App() {
  const route = useRoute();
  const [theme, toggleTheme] = useTheme();
  const [health, setHealth] = useState<Health | null | undefined>(undefined);

  useEffect(() => { api.health().then(setHealth).catch(() => setHealth(null)); }, []);
  useEffect(() => { document.title = `${TITLES[route.page]} · Healthcare Evidence Agent`; }, [route.page]);

  const status = health === undefined ? ["", "Connecting…"] : health === null ? ["", "API offline · replay only"]
    : health.answering.enabled ? ["on", "Live agent on"] : ["", "Tools live · agent replay"];

  return (
    <ToastProvider>
      {/* not href="#main": the hash is the router, so the skip link moves focus without navigating */}
      <a className="skip" href={`#${route.page}`} onClick={(e) => { e.preventDefault(); document.querySelector<HTMLElement>("main")?.focus(); }}>Skip to content</a>
      <div className="shell">
        <header className="top">
          <a className="brand" href="#overview" aria-label="Healthcare Evidence Agent, overview">
            <span className="mark" aria-hidden="true">HEA</span>
            <span><strong>Healthcare Evidence Agent</strong><em>Public data only · not medical advice · no PHI</em></span>
          </a>
          <div className="top-actions">
            <span className={`status ${status[0]}`} title={health?.answering.reason}><i aria-hidden="true" />{status[1]}</span>
            <a className="icon-btn" href="https://github.com/Akhilesh-Vangala/healthcare-evidence-agent" aria-label="Source on GitHub" target="_blank" rel="noreferrer">
              <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" /></svg>
            </a>
            <ThemeToggle theme={theme} onToggle={toggleTheme} />
          </div>
        </header>
        <Tabs items={NAV} current={route.page} onSelect={(p) => navigate(p)} label="Console sections" />
        <main id={`panel-${route.page}`} role="tabpanel" aria-labelledby={`tab-${route.page}`} tabIndex={-1}>
          <ErrorBoundary resetKey={route.page}>
            {route.page === "overview" && <Overview />}
            {route.page === "ask" && <Ask health={health ?? null} params={route.params} />}
            {route.page === "explorer" && <Explorer params={route.params} />}
            {route.page === "check" && <Check params={route.params} />}
            {route.page === "study" && <Study />}
            {route.page === "runs" && <Runs params={route.params} />}
          </ErrorBoundary>
        </main>
        <footer>
          <span>MIT · Sai Akhilesh Vangala</span>
          <span><a href="https://github.com/Akhilesh-Vangala/healthcare-evidence-agent">Source</a> · <a href="/api/docs">API reference</a> · v{health?.version ?? "1.0.0"}</span>
        </footer>
      </div>
    </ToastProvider>
  );
}
