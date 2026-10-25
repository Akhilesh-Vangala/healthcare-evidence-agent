import { useEffect, useMemo, useState } from "react";
import { type Health, api } from "./api";
import study from "./generated/study.json";
import { Ask } from "./pages/Ask";
import { Check } from "./pages/Check";
import { Explorer } from "./pages/Explorer";

type Page = "overview" | "ask" | "explorer" | "check" | "study" | "runs";

const PAGES: { id: Page; label: string; dot: string }[] = [
  { id: "overview", label: "Overview", dot: "var(--teal)" },
  { id: "ask", label: "Ask the agent", dot: "var(--violet)" },
  { id: "explorer", label: "Evidence explorer", dot: "var(--sky)" },
  { id: "check", label: "Citation check", dot: "var(--teal)" },
  { id: "study", label: "Study", dot: "var(--amber)" },
  { id: "runs", label: "Saved runs", dot: "var(--muted)" },
];

type RuntimeRow = { id: string; label: string; pass_rate: number; ci: number[]; n_runs: number; claim_precision: number | null;
  cost_usd: number | null; latency_s: number; cache_share?: number | null };
type Extras = {
  runtime?: { configs: RuntimeRow[]; deltas: Array<{ contrast: string; delta: number; ci95: number[]; significant: boolean }>; note: string;
    headline: { api_c_28: number; claude_code_c_28: number } };
  redteam?: { runs: number; pass_rate: number; tasks: Array<{ id: string; category: string; passes: boolean[]; failed_checks: string[] }>; note: string };
};
const extra = study as typeof study & Extras;

const pct = (n: number) => `${Math.round(n * 1000) / 10}%`;
const pts = (n: number) => `${Math.round(n * 1000) / 10}`;
const money = (n: number | null) => (n == null ? "—" : n === 0 ? "$0" : `$${n.toFixed(4)}`);
const pageFromHash = (): Page => (PAGES.some((p) => p.id === location.hash.slice(1)) ? (location.hash.slice(1) as Page) : "overview");

export function App() {
  const [page, setPage] = useState<Page>(pageFromHash);
  const [health, setHealth] = useState<Health | null>(null);

  useEffect(() => {
    const onHash = () => setPage(pageFromHash());
    window.addEventListener("hashchange", onHash);
    api.health().then(setHealth).catch(() => setHealth(null));
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  return (
    <div className="shell">
      <header className="top">
        <div className="brand">
          <span className="mark">HEA</span>
          <div><strong>Healthcare Evidence Agent</strong><em>Public data only · not medical advice · no PHI</em></div>
        </div>
        <span className={`status ${health?.answering.enabled ? "on" : ""}`}>
          <i />{health ? (health.answering.enabled ? "Live agent on" : "Tools live · agent replay") : "API offline · replay only"}
        </span>
      </header>
      <nav className="tabs">
        {PAGES.map((p) => (
          <button key={p.id} type="button" className={page === p.id ? "on" : ""} onClick={() => { location.hash = p.id; setPage(p.id); }}>
            <span className="dot" style={{ background: p.dot }} />{p.label}
          </button>
        ))}
      </nav>
      {page === "overview" && <Overview go={(p) => { location.hash = p; setPage(p); }} />}
      {page === "ask" && <Ask health={health} />}
      {page === "explorer" && <Explorer />}
      {page === "check" && <Check />}
      {page === "study" && <Study />}
      {page === "runs" && <Runs />}
      <footer>MIT · <a href="https://github.com/Akhilesh-Vangala/healthcare-evidence-agent">source</a> · <a href="/api/docs">API</a> · Sai Akhilesh Vangala</footer>
    </div>
  );
}

function Overview({ go }: { go: (p: Page) => void }) {
  const c = study.configs.find((x) => x.id === "C_tools_skills");
  const head = extra.runtime?.headline;
  return (
    <main>
      <section className="hero">
        <p className="kicker">Evaluation · citation control · human review</p>
        <h1>A tool-using agent that cannot cite a document it did not retrieve.</h1>
        <p className="lede">
          Questions about FDA labels, clinical trials and Medicare coverage. Six MCP tools fetch the evidence, four
          Agent Skills carry the procedure, and a grader that is not the model checks every quote word for word
          against what the tools returned in that run. Measured on two runtimes: headless Claude Code and the
          Anthropic Messages API.
        </p>
        <div className="row">
          <button className="primary" type="button" onClick={() => go("ask")}>Ask the agent</button>
          <button type="button" onClick={() => go("explorer")}>Explore the evidence tools</button>
          <button type="button" onClick={() => go("study")}>Read the study</button>
        </div>
      </section>
      <section className="metrics">
        <article><b>{c ? pct(c.pass_rate) : "—"}</b><span>golden-set pass, tools + skills</span><small>Claude Code · 60 runs · CI {c ? `${pct(c.ci[0])}–${pct(c.ci[1])}` : ""}</small></article>
        <article><b className="sky">{head ? pct(head.api_c_28) : "—"}</b><span>same config, Anthropic API runtime</span><small>{head ? `vs ${pct(head.claude_code_c_28)} on the 28 tasks unaffected by data drift` : "cross-runtime check"}</small></article>
        <article><b className="amber">0</b><span>invented trial IDs with tools</span><small>closed book invented them in 4 runs</small></article>
        <article><b className="violet">{extra.redteam ? pct(extra.redteam.pass_rate) : "—"}</b><span>red-team suite</span><small>{extra.redteam ? `${extra.redteam.runs} adversarial runs` : "not yet scored"}</small></article>
      </section>
      <section className="pipeline">
        {[["question", "redacted request"], ["Claude", "plans, loads skills"], ["MCP tools", "openFDA · CT.gov · CMS"], ["evidence log", "every document, per run"],
          ["verifier", "verbatim quotes · no unseen NCT"], ["review flag", "off-label, comparative, coverage"]].map(([a, b], i) => (
          <div key={a} className={`stage s${i}`}><b>{a}</b><small>{b}</small></div>
        ))}
      </section>
      <section className="split">
        <div className="panel"><h2>What is reusable</h2><ul>
          <li>An MCP server over three public APIs; every document written to a per-run evidence log.</li>
          <li>Skills for product disambiguation, citation discipline, trial landscapes and escalation.</li>
          <li>A grader that is not the model: a paraphrase fails, an NCT id the tools never returned fails the task.</li>
          <li>Two runtimes behind one grader, so a result can be checked outside the harness that produced it.</li>
        </ul></div>
        <div className="panel"><h2>What this site will not do</h2><ul>
          <li>Give medical advice, dosing for a patient, or promotional claims; those are refused or escalated.</li>
          <li>Average the 90% pilot of config C into the 95%; those 30 runs sit outside the 240.</li>
          <li>Call a model unless live answering is enabled with rate and spend limits.</li>
        </ul></div>
      </section>
    </main>
  );
}

function Study() {
  const [category, setCategory] = useState("all");
  const categories = useMemo(() => ["all", ...Array.from(new Set(study.tasks.map((t) => t.category)))], []);
  const tasks = study.tasks.filter((t) => category === "all" || t.category === category);
  return (
    <main>
      <p className="kicker">Published study · {study.n_rows} rows · Claude Code runtime</p>
      <h1>What moved the needle</h1>
      <p className="lede">One factor changes at a time. Pass rate is the mean of per-task means with a bootstrap 95% interval; A, B and C were repeated twice.</p>
      <div className="bars">
        {study.configs.map((row) => (
          <div key={row.id} className={`bar ${row.id === "C_tools_skills" ? "best" : ""}`}>
            <span>{row.label}</span>
            <div className="track"><div className="fill" style={{ width: `${row.pass_rate * 100}%` }} /><div className="ci" style={{ left: `${row.ci[0] * 100}%`, width: `${(row.ci[1] - row.ci[0]) * 100}%` }} /></div>
            <b>{pct(row.pass_rate)}</b><small>{money(row.cost_usd)}</small>
          </div>
        ))}
      </div>
      <ul className="deltas">
        {study.deltas.map((d) => (
          <li key={`${d.config_a}-${d.config_b}`}><code>{d.config_a}</code> → <code>{d.config_b}</code>
            <strong>{d.delta_pass_rate >= 0 ? "+" : ""}{pts(d.delta_pass_rate)} pts</strong>
            <span>[{pts(d.delta_ci95[0])}, {pts(d.delta_ci95[1])}] · {d.delta_significant_vs_zero ? "interval excludes 0" : "interval includes 0"}</span></li>
        ))}
      </ul>

      {extra.runtime && (
        <>
          <h2>Cross-runtime check: the same configurations on the Anthropic API</h2>
          <p className="lede">{extra.runtime.note}</p>
          <div className="table-wrap"><table>
            <thead><tr><th>Configuration</th><th>Pass</th><th>95% CI</th><th>Runs</th><th>Claim precision</th><th>Cost / task</th><th>Latency</th><th>Input from cache</th></tr></thead>
            <tbody>{extra.runtime.configs.map((r) => (
              <tr key={r.id} className={r.id === "C_api_tools_skills" ? "focus" : ""}><td>{r.label}</td><td>{pct(r.pass_rate)}</td><td>{pct(r.ci[0])}–{pct(r.ci[1])}</td><td>{r.n_runs}</td>
                <td>{r.claim_precision == null ? "—" : pct(r.claim_precision)}</td><td>{money(r.cost_usd)}</td><td>{r.latency_s}s</td><td>{r.cache_share == null ? "—" : pct(r.cache_share)}</td></tr>
            ))}</tbody>
          </table></div>
          <ul className="deltas">{extra.runtime.deltas.map((d) => (
            <li key={d.contrast}><code>{d.contrast}</code><strong>{d.delta >= 0 ? "+" : ""}{pts(d.delta)} pts</strong><span>[{pts(d.ci95[0])}, {pts(d.ci95[1])}] · {d.significant ? "interval excludes 0" : "interval includes 0"}</span></li>
          ))}</ul>
        </>
      )}

      {extra.redteam && (
        <>
          <h2>Red-team suite · {extra.redteam.runs} runs</h2>
          <p className="lede">{extra.redteam.note}</p>
          <div className="table-wrap"><table>
            <thead><tr><th>Task</th><th>Attack</th><th>Repeats</th></tr></thead>
            <tbody>{extra.redteam.tasks.map((t) => (
              <tr key={t.id}><td><code>{t.id}</code></td><td>{t.category.replaceAll("_", " ")}</td>
                <td className={t.passes.every(Boolean) ? "ok" : "bad"}>{t.passes.map((p) => (p ? "held" : "failed")).join(" · ")}{t.failed_checks.length > 0 && <small>{t.failed_checks.join(", ")}</small>}</td></tr>
            ))}</tbody>
          </table></div>
        </>
      )}

      <h2>Config C, task by task (Claude Code)</h2>
      <div className="chips">{categories.map((cat) => <button key={cat} type="button" className={category === cat ? "on" : ""} onClick={() => setCategory(cat)}>{cat.replaceAll("_", " ")}</button>)}</div>
      <div className="table-wrap"><table>
        <thead><tr><th>Task</th><th>Category</th><th>Repeats</th><th>Question</th></tr></thead>
        <tbody>{tasks.map((task) => (
          <tr key={task.id}><td><code>{task.id}</code></td><td>{task.category.replaceAll("_", " ")}</td>
            <td className={task.passes.every(Boolean) ? "ok" : "bad"}>{task.passes.map((p) => (p ? "pass" : "fail")).join(" · ") || "—"}{task.failed_checks.length > 0 && <small>{task.failed_checks.join(", ")}</small>}</td>
            <td>{task.query}</td></tr>
        ))}</tbody>
      </table></div>
      <p className="note">{study.excluded_note}</p>
    </main>
  );
}

function Runs() {
  const [traceId, setTraceId] = useState(study.traces[0].id);
  const trace = study.traces.find((t) => t.id === traceId) ?? study.traces[0];
  return (
    <main>
      <p className="kicker">Checked into the repository</p>
      <h1>Saved runs</h1>
      <p className="lede">Five Claude Code runs. Each claim is re-checked against that run's evidence log: green means the quote is a verbatim span of a source retrieved in that run.</p>
      <div className="chips">{study.traces.map((t) => <button key={t.id} type="button" className={t.id === trace.id ? "on" : ""} onClick={() => setTraceId(t.id)}>{t.id} · {t.title}</button>)}</div>
      <section className="panel">
        <p className="kicker">{trace.config} · {trace.model}</p>
        <h2>{trace.query}</h2>
        <p className="status-line"><b>{trace.status}</b>{trace.needs_human_review ? " · human review" : " · no review flag"} · {trace.n_sources} sources · {trace.latency_s}s · {money(trace.cost_usd)}</p>
        <p>{trace.summary}</p>
        {trace.review_reasons.length > 0 && <p className="banner">{trace.review_reasons.join(" · ")}</p>}
        {trace.claims.map((claim, i) => (
          <article key={`${claim.source_id}-${i}`} className={claim.verified ? "claim ok" : "claim bad"}>
            <header><b>{claim.verified ? "verified" : claim.reason}</b><code>{claim.source_id}</code></header>
            <p>{claim.statement}</p><blockquote>{claim.quote}</blockquote>
            <small>{[claim.kind, claim.brand_name, claim.section].filter(Boolean).join(" · ")}</small>
          </article>
        ))}
      </section>
    </main>
  );
}
