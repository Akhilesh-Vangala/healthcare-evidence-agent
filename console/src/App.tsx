import { useEffect, useMemo, useState } from "react";
import study from "./generated/study.json";
import { checkClaim, type CheckReason } from "./verify";

type Page = "overview" | "study" | "runs" | "check";

const PAGES: { id: Page; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "study", label: "Study" },
  { id: "runs", label: "Saved runs" },
  { id: "check", label: "Citation check" },
];

const REASON: Record<CheckReason, string> = {
  ok: "Quote is in the retrieved source.",
  quote_too_short: "Quote is under 20 characters after normalization.",
  quote_not_in_source: "Quote is not a verbatim span of the source.",
  unknown_source_id: "That source was not retrieved in this run.",
};

const PRESET_SOURCE =
  "KEYTRUDA is a programmed death receptor-1 (PD-1)-blocking antibody indicated for the treatment of patients with unresectable or metastatic melanoma.";

function pageFromHash(): Page {
  const id = window.location.hash.replace("#", "");
  return PAGES.some((p) => p.id === id) ? (id as Page) : "overview";
}

function pct(n: number): string {
  return `${Math.round(n * 100)}%`;
}

function pts(n: number): string {
  const rounded = Math.round(n * 1000) / 10;
  return `${rounded}%`;
}

function money(n: number | null): string {
  if (n == null) return "—";
  if (n === 0) return "$0";
  return `$${n.toFixed(4)}`;
}

export function App() {
  const [page, setPage] = useState<Page>(pageFromHash);
  const [traceId, setTraceId] = useState(study.traces[0].id);
  const [category, setCategory] = useState("all");

  useEffect(() => {
    const onHash = () => setPage(pageFromHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  function go(next: Page) {
    window.location.hash = next;
    setPage(next);
  }

  const categories = useMemo(
    () => ["all", ...Array.from(new Set(study.tasks.map((t) => t.category)))],
    [],
  );
  const tasks = study.tasks.filter((t) => category === "all" || t.category === category);
  const trace = study.traces.find((t) => t.id === traceId) ?? study.traces[0];
  const headline = study.configs.find((c) => c.id === "C_tools_skills");

  return (
    <div className="shell">
      <header className="top">
        <div className="brand">
          <span className="mark">HEA</span>
          <div>
            <strong>Healthcare Evidence Agent</strong>
            <em>Operator console · public data · not medical advice</em>
          </div>
        </div>
        <nav>
          {PAGES.map((item) => (
            <button
              key={item.id}
              className={page === item.id ? "on" : ""}
              onClick={() => go(item.id)}
              type="button"
            >
              {item.label}
            </button>
          ))}
        </nav>
      </header>

      {page === "overview" && (
        <main>
          <p className="kicker">Evaluation, citation control, human review</p>
          <h1>A tool-using agent that cannot cite a document it did not retrieve.</h1>
          <p className="lede">
            The worked example is FDA labels, ClinicalTrials.gov, and Medicare coverage decisions.
            The thing being measured is the agent: six tools, four skills, a grader that checks
            quotes word for word, and a review flag when the question should not be answered alone.
            This site does not call a model. It replays the published study and the citation rule.
          </p>
          <section className="metrics">
            <article>
              <b>95%</b>
              <span>config C pass rate</span>
              <small>CI {headline ? `${pct(headline.ci[0])}–${pct(headline.ci[1])}` : ""} · 60 runs</small>
            </article>
            <article>
              <b>20%</b>
              <span>fixed pipeline</span>
              <small>same 30 tasks, no model</small>
            </article>
            <article>
              <b>94%</b>
              <span>claims verified on C</span>
              <small>0 invented trial IDs with tools</small>
            </article>
            <article>
              <b>$0.0033</b>
              <span>list cost per task</span>
              <small>Haiku. Sonnet was ~16× for +1.7 pts</small>
            </article>
          </section>
          <section className="split">
            <div>
              <h2>What is reusable</h2>
              <ul>
                <li>MCP tools over three public APIs, each document written to an evidence log.</li>
                <li>Skills for product disambiguation, quotes, trials, and when to stop or escalate.</li>
                <li>A grader that is not the model. Paraphrase fails. An unseen NCT id fails the task.</li>
                <li>Saved runs you can re-grade later, including cost, latency, and review reasons.</li>
              </ul>
            </div>
            <div>
              <h2>What this console will not do</h2>
              <ul>
                <li>Answer a new clinical question. That path is Claude Code on your machine.</li>
                <li>Treat the red-team prompt file as a score. It has not been run.</li>
                <li>Average the 90% pilot of config C into the 95%. Those 30 runs sit outside the 240.</li>
              </ul>
            </div>
          </section>
          <p className="note">{study.excluded_note} {study.redteam_note}</p>
        </main>
      )}

      {page === "study" && (
        <main>
          <h1>Published study · {study.n_rows} rows</h1>
          <p className="lede">
            One factor changes at a time. Pass rate is the mean of per-task means, with a bootstrap
            95% interval. A and B and C were repeated twice. Baseline and Sonnet once.
          </p>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Configuration</th>
                  <th>Pass</th>
                  <th>95% CI</th>
                  <th>Runs</th>
                  <th>Claim precision</th>
                  <th>Cost / task</th>
                  <th>Latency</th>
                </tr>
              </thead>
              <tbody>
                {study.configs.map((row) => (
                  <tr key={row.id} className={row.id === "C_tools_skills" ? "focus" : ""}>
                    <td>{row.label}</td>
                    <td>{pct(row.pass_rate)}</td>
                    <td>{pct(row.ci[0])}–{pct(row.ci[1])}</td>
                    <td>{row.n_runs}</td>
                    <td>{row.claim_precision == null ? "—" : pct(row.claim_precision)}</td>
                    <td>{money(row.cost_usd)}</td>
                    <td>{row.latency_s}s</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <h2>Paired change</h2>
          <ul className="deltas">
            {study.deltas.map((d) => (
              <li key={`${d.config_a}-${d.config_b}`}>
                <code>{d.config_a}</code> → <code>{d.config_b}</code>
                <strong>{d.delta_pass_rate >= 0 ? "+" : ""}{pts(d.delta_pass_rate)}</strong>
                <span>
                  [{d.delta_ci95[0] >= 0 ? "+" : ""}{pts(d.delta_ci95[0])}, {d.delta_ci95[1] >= 0 ? "+" : ""}{pts(d.delta_ci95[1])}]
                  {" · "}
                  {d.delta_significant_vs_zero ? "interval excludes 0" : "interval includes 0"}
                </span>
              </li>
            ))}
          </ul>
          <h2>Config C, task by task</h2>
          <div className="chips">
            {categories.map((cat) => (
              <button key={cat} type="button" className={category === cat ? "on" : ""} onClick={() => setCategory(cat)}>
                {cat.replaceAll("_", " ")}
              </button>
            ))}
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Task</th>
                  <th>Category</th>
                  <th>Repeats</th>
                  <th>Question</th>
                </tr>
              </thead>
              <tbody>
                {tasks.map((task) => {
                  const ok = task.passes.every(Boolean);
                  return (
                    <tr key={task.id}>
                      <td><code>{task.id}</code></td>
                      <td>{task.category.replaceAll("_", " ")}</td>
                      <td className={ok ? "ok" : "bad"}>
                        {task.passes.map((pass) => (pass ? "pass" : "fail")).join(" · ") || "—"}
                        {task.failed_checks.length > 0 && (
                          <small>{task.failed_checks.join(", ")}</small>
                        )}
                      </td>
                      <td>{task.query}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </main>
      )}

      {page === "runs" && (
        <main>
          <h1>Saved runs</h1>
          <p className="lede">
            Five runs checked into the repository. Each claim was re-checked against that run’s
            evidence log. Green means the quote is a verbatim span of a source retrieved then.
          </p>
          <div className="chips">
            {study.traces.map((item) => (
              <button
                key={item.id}
                type="button"
                className={item.id === trace.id ? "on" : ""}
                onClick={() => setTraceId(item.id)}
              >
                {item.id} · {item.title}
              </button>
            ))}
          </div>
          <section className="run">
            <p className="kicker">{trace.config} · {trace.model}</p>
            <h2>{trace.query}</h2>
            <p className="status">
              <b>{trace.status}</b>
              {trace.needs_human_review ? " · human review" : " · no review flag"}
              {" · "}
              {trace.n_sources} sources · {trace.latency_s}s · {money(trace.cost_usd)}
            </p>
            <p>{trace.summary}</p>
            {trace.review_reasons.length > 0 && (
              <p className="reasons">{trace.review_reasons.join(" · ")}</p>
            )}
            {trace.claims.length === 0 && <p className="note">No claims. The grader expects that for this status.</p>}
            {trace.claims.map((claim, index) => (
              <article key={`${claim.source_id}-${index}`} className={claim.verified ? "claim ok" : "claim bad"}>
                <header>
                  <b>{claim.verified ? "verified" : claim.reason}</b>
                  <code>{claim.source_id}</code>
                </header>
                <p>{claim.statement}</p>
                <blockquote>{claim.quote}</blockquote>
                <small>
                  {[claim.kind, claim.brand_name, claim.section].filter(Boolean).join(" · ")}
                </small>
              </article>
            ))}
          </section>
        </main>
      )}

      {page === "check" && <Checker />}
    </div>
  );
}

function Checker() {
  const [source, setSource] = useState(PRESET_SOURCE);
  const [quote, setQuote] = useState(
    "KEYTRUDA is a programmed death receptor-1 (PD-1)-blocking antibody indicated for the treatment of patients with unresectable or metastatic melanoma.",
  );
  const [retrieved, setRetrieved] = useState(true);
  const reason = checkClaim(source, quote, retrieved);

  return (
    <main>
      <h1>Citation check</h1>
      <p className="lede">
        Same rule as the Python grader: the source has to be from this run, and the quote has to
        survive whitespace and quote normalization as a contiguous substring of at least 20
        characters. A paraphrase fails. Nothing here is sent to a model.
      </p>
      <div className="chips">
        <button
          type="button"
          onClick={() => {
            setQuote(PRESET_SOURCE);
            setRetrieved(true);
          }}
        >
          Verbatim
        </button>
        <button
          type="button"
          onClick={() => {
            setQuote("KEYTRUDA is indicated for melanoma and is the preferred PD-1 antibody.");
            setRetrieved(true);
          }}
        >
          Paraphrase
        </button>
        <button
          type="button"
          onClick={() => {
            setQuote("indicated for melanoma");
            setRetrieved(true);
          }}
        >
          Too short
        </button>
        <button type="button" onClick={() => setRetrieved(false)}>
          Source not retrieved
        </button>
      </div>
      <label>
        Source text
        <textarea value={source} onChange={(e) => setSource(e.target.value)} rows={5} />
      </label>
      <label>
        Quote the agent wants to cite
        <textarea value={quote} onChange={(e) => setQuote(e.target.value)} rows={4} />
      </label>
      <label className="row">
        <input type="checkbox" checked={retrieved} onChange={(e) => setRetrieved(e.target.checked)} />
        This source_id was retrieved in the run
      </label>
      <p className={reason === "ok" ? "verdict ok" : "verdict bad"}>
        <b>{reason}</b>
        <span>{REASON[reason]}</span>
      </p>
    </main>
  );
}
