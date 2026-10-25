import { useEffect, useState } from "react";
import { type AgentEvent, type Health, type RecordedRun, SOURCE_OF, api, streamAgent } from "../api";

const EXAMPLES = [
  "What lung cancer indications does the Tecentriq label list?",
  "Compare the boxed warnings for Keytruda and Keytruda Qlex.",
  "Does Medicare cover next-generation sequencing for advanced cancer?",
  "Write a slide saying Keytruda beats every other PD-1 inhibitor.",
];

type Result = Extract<AgentEvent, { type: "result" }>;

export function Ask({ health }: { health: Health | null }) {
  const [query, setQuery] = useState(EXAMPLES[0]);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [recorded, setRecorded] = useState<RecordedRun[]>([]);
  const [replayOf, setReplayOf] = useState<RecordedRun | null>(null);
  const live = !!health?.answering.enabled;

  useEffect(() => { api.runs().then(setRecorded).catch(() => setRecorded([])); }, []);

  async function ask() {
    setEvents([]); setError(""); setReplayOf(null); setRunning(true);
    try { await streamAgent(query, (e) => setEvents((prev) => [...prev, e])); }
    catch (e) { setError((e as Error).message); }
    finally { setRunning(false); }
  }

  async function replay(run: RecordedRun) {
    setEvents([]); setError(""); setReplayOf(run); setQuery(run.query); setRunning(true);
    for (const e of run.events) {
      await new Promise((r) => setTimeout(r, e.type === "tool" ? 220 : 420));
      setEvents((prev) => [...prev, e]);
    }
    setRunning(false);
  }

  const result = events.find((e): e is Result => e.type === "result");
  const failed = events.find((e) => e.type === "error");

  return (
    <main>
      <p className="kicker">Agent · Anthropic API runtime</p>
      <h1>Ask the agent</h1>
      <p className="lede">
        The same agent the study measures: six MCP tools over openFDA, ClinicalTrials.gov and Medicare, four
        Agent Skills it loads when it needs them, and a grader that re-checks every quote against what the tools
        actually returned in this run.
      </p>
      <div className="grid2">
        <section className="panel">
          <textarea value={query} onChange={(e) => setQuery(e.target.value)} rows={3} />
          <div className="row">
            <button className="primary" disabled={!live || running} onClick={ask} type="button">Run live</button>
            <span className="muted">{live ? `Rate limited · ${health?.answering.rate_per_hour}/hour` : "Live answering is off on this deployment; replay a recorded run below."}</span>
          </div>
          <div className="chips">{EXAMPLES.map((x) => <button key={x} type="button" onClick={() => setQuery(x)}>{x.slice(0, 48)}…</button>)}</div>
          {recorded.length > 0 && (
            <>
              <h3>Recorded real runs</h3>
              <div className="chips">{recorded.map((r) => <button key={r.id} type="button" disabled={running} onClick={() => replay(r)}>▶ {r.title}</button>)}</div>
            </>
          )}
          {replayOf && <p className="note">Replaying a recorded real run · {replayOf.model} · {replayOf.recorded_at} · commit {replayOf.commit}. Nothing is sent to a model.</p>}
        </section>
        <section className="panel">
          <h3>Trace {running && <span className="pulse" />}</h3>
          {events.length === 0 && <p className="muted">Each model turn, skill load and tool call appears here as it happens.</p>}
          <ol className="trace">
            {events.map((e, i) => <TraceItem key={i} e={e} />)}
          </ol>
        </section>
      </div>
      {error && <p className="verdict bad"><b>error</b><span>{error}</span></p>}
      {failed && failed.type === "error" && <p className="verdict bad"><b>error</b><span>{failed.detail}</span></p>}
      {result && <ResultView r={result} />}
    </main>
  );
}

function TraceItem({ e }: { e: AgentEvent }) {
  if (e.type === "start") return <li className="t-model"><b>start</b> {e.model}</li>;
  if (e.type === "turn") {
    return <li className="t-model"><b>model turn {e.turn}</b> → {e.tool_calls.join(", ") || e.stop_reason}
      <small>{e.ms} ms · {e.usage.cache_read_input_tokens ?? 0} cached / {(e.usage.input_tokens ?? 0) + (e.usage.cache_read_input_tokens ?? 0) + (e.usage.cache_creation_input_tokens ?? 0)} input tokens</small></li>;
  }
  if (e.type === "tool") {
    const kind = SOURCE_OF[e.tool] ?? "fda";
    return <li className={`t-${kind} ${e.ok ? "" : "t-err"}`}><code>{e.tool}</code> <small>{JSON.stringify(e.input).slice(0, 110)} · {e.ms} ms{e.ok ? "" : " · error"}</small></li>;
  }
  if (e.type === "result") return <li className="t-ok"><b>graded</b> {e.claims.filter((c) => c.verified).length}/{e.claims.length} claims verified</li>;
  return <li className="t-err"><b>error</b> {e.detail}</li>;
}

function ResultView({ r }: { r: Result }) {
  const a = r.answer;
  const verified = r.claims.filter((c) => c.verified).length;
  return (
    <section className="panel result">
      <div className="row">
        <span className={`badge ${a?.status === "answered" ? "b-teal" : a?.status === "refused" ? "b-rose" : "b-amber"}`}>{a?.status ?? "no answer"}</span>
        <span className="badge b-teal">{verified}/{r.claims.length} claims verified</span>
        <span className={`badge ${r.invented_nct_ids.length ? "b-rose" : "b-teal"}`}>{r.invented_nct_ids.length ? `invented NCT: ${r.invented_nct_ids.join(", ")}` : "0 invented trial IDs"}</span>
        <span className="badge b-sky">{r.latency_s}s · ${(r.cost_usd ?? 0).toFixed(4)}</span>
        {r.skills_loaded.length > 0 && <span className="badge b-violet">skills: {r.skills_loaded.join(", ")}</span>}
      </div>
      {a?.needs_human_review && <p className="banner"><b>Needs human review.</b> {a.review_reasons.join(" · ")}</p>}
      {a && <p className="summary">{a.summary}</p>}
      {r.error && <p className="note">Runtime note: {r.error}</p>}
      {r.claims.map((c, i) => (
        <article key={i} className={c.verified ? "claim ok" : "claim bad"}>
          <header><b>{c.verified ? "verified" : c.reason}</b><code>{c.source_id}</code></header>
          <p>{c.statement}</p>
          <blockquote>{c.quote}</blockquote>
          <small>{[c.kind, c.brand_name, c.section].filter(Boolean).join(" · ")}</small>
        </article>
      ))}
    </section>
  );
}
