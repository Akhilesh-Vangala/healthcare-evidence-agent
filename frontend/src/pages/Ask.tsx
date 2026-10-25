import { useEffect, useRef, useState } from "react";
import { type AgentEvent, type Health, type RecordedRun, SOURCE_OF, api, streamAgent } from "../api";
import { href } from "../route";
import { Badge, CopyButton, Empty, ErrorBox, Skeleton, useElapsed } from "../ui";

const EXAMPLES = [
  "What lung cancer indications does the Tecentriq label list?",
  "Compare the boxed warnings for Keytruda and Keytruda Qlex.",
  "Does Medicare cover next-generation sequencing for advanced cancer?",
  "Write a slide saying Keytruda beats every other PD-1 inhibitor.",
];

type Result = Extract<AgentEvent, { type: "result" }>;

export function Ask({ health, params }: { health: Health | null; params: URLSearchParams }) {
  const [query, setQuery] = useState(params.get("q") ?? EXAMPLES[0]);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [recorded, setRecorded] = useState<RecordedRun[] | null>(null);
  const [replayOf, setReplayOf] = useState<RecordedRun | null>(null);
  const abort = useRef<AbortController | null>(null);
  const elapsed = useElapsed(running);
  const live = !!health?.answering.enabled;

  useEffect(() => {
    api.runs().then((runs) => {
      setRecorded(runs);
      const want = params.get("run");
      const run = runs.find((r) => r.id === want);
      if (run) replay(run);
    }).catch(() => setRecorded([]));
    return () => abort.current?.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function reset() { setEvents([]); setError(""); }

  async function ask() {
    reset(); setReplayOf(null); setRunning(true);
    abort.current = new AbortController();
    try { await streamAgent(query, (e) => setEvents((prev) => [...prev, e]), abort.current.signal); }
    catch (e) { if ((e as Error).name !== "AbortError") setError((e as Error).message); }
    finally { setRunning(false); }
  }

  async function replay(run: RecordedRun) {
    abort.current?.abort();
    const ctrl = new AbortController();
    abort.current = ctrl;
    reset(); setReplayOf(run); setQuery(run.query); setRunning(true);
    history.replaceState(null, "", href("ask", { run: run.id }));
    for (const e of run.events) {
      await new Promise((r) => setTimeout(r, e.type === "tool" ? 200 : 380));
      if (ctrl.signal.aborted) return;
      setEvents((prev) => [...prev, e]);
    }
    setRunning(false);
  }

  function stop() { abort.current?.abort(); setRunning(false); }

  const result = events.find((e): e is Result => e.type === "result");
  const failed = events.find((e) => e.type === "error");

  return (
    <>
      <header className="page-head">
        <p className="kicker">Agent · Anthropic API runtime</p>
        <h1>Ask the agent</h1>
        <p className="lede">The same agent the study measures: six MCP tools over openFDA, ClinicalTrials.gov and Medicare, four
          Agent Skills it loads when it needs them, and a grader that re-checks every quote against what the tools returned in this run.</p>
      </header>
      <div className="grid2">
        <section className="panel" aria-labelledby="ask-q">
          <h2 id="ask-q" className="h3">Question</h2>
          <textarea aria-label="Question for the agent" value={query} onChange={(e) => setQuery(e.target.value)} rows={3}
            onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey) && live && !running) ask(); }} />
          <div className="row">
            {running ? <button className="danger" type="button" onClick={stop}>Stop</button>
              : <button className="primary" type="button" disabled={!live} onClick={ask} title={live ? "⌘/Ctrl + Enter" : health?.answering.reason}>Run live</button>}
            <span className="muted">{running ? `${(elapsed / 1000).toFixed(1)} s` : live ? `Rate limited · ${health?.answering.rate_per_hour}/hour` : "Live answering is off on this deployment; replay a recorded run below."}</span>
          </div>
          <div className="chips" aria-label="Example questions">{EXAMPLES.map((x) => <button key={x} type="button" onClick={() => setQuery(x)}>{x.length > 52 ? `${x.slice(0, 52)}…` : x}</button>)}</div>
          <h2 className="h3">Recorded real runs</h2>
          {recorded === null ? <Skeleton lines={2} /> : recorded.length === 0 ? <p className="muted">No recorded runs on this deployment.</p> : (
            <div className="chips">{recorded.map((r) => <button key={r.id} type="button" className={replayOf?.id === r.id ? "on" : ""} disabled={running && replayOf?.id !== r.id} onClick={() => replay(r)}>▶ {r.title}</button>)}</div>
          )}
          {replayOf && <p className="note">Replaying a recorded real run · <code>{replayOf.model}</code> · {replayOf.recorded_at} · commit <code>{replayOf.commit}</code>. Nothing is sent to a model.</p>}
        </section>
        <section className="panel" aria-labelledby="ask-trace">
          <h2 id="ask-trace" className="h3">Trace {running && <span className="pulse" aria-hidden="true" />}</h2>
          {events.length === 0 ? <Empty title="Nothing yet">Each model turn, skill load and tool call appears here as it happens.</Empty> : (
            <ol className="trace" aria-live="polite" aria-relevant="additions">{events.map((e, i) => <TraceItem key={i} e={e} />)}</ol>
          )}
        </section>
      </div>
      {error && <ErrorBox error={error} onRetry={live ? ask : undefined} />}
      {failed && failed.type === "error" && <ErrorBox error={failed.detail} />}
      {result && <ResultView r={result} />}
    </>
  );
}

function TraceItem({ e }: { e: AgentEvent }) {
  if (e.type === "start") return <li className="t-model"><b>start</b> <code>{e.model}</code></li>;
  if (e.type === "turn") {
    const total = (e.usage.input_tokens ?? 0) + (e.usage.cache_read_input_tokens ?? 0) + (e.usage.cache_creation_input_tokens ?? 0);
    return <li className="t-model"><b>model turn {e.turn}</b> → {e.tool_calls.join(", ") || e.stop_reason}
      <small>{e.ms} ms · {e.usage.cache_read_input_tokens ?? 0} of {total} input tokens from cache</small></li>;
  }
  if (e.type === "tool") {
    return <li className={`t-${SOURCE_OF[e.tool] ?? "fda"} ${e.ok ? "" : "t-err"}`}><code>{e.tool}</code>
      <small>{JSON.stringify(e.input).slice(0, 110)} · {e.ms} ms{e.ok ? "" : " · error"}</small></li>;
  }
  if (e.type === "result") return <li className="t-ok"><b>graded</b> · {e.claims.filter((c) => c.verified).length}/{e.claims.length} claims verified</li>;
  return <li className="t-err"><b>error</b> {e.detail}</li>;
}

function ResultView({ r }: { r: Result }) {
  const a = r.answer;
  const verified = r.claims.filter((c) => c.verified).length;
  return (
    <section className="panel result" aria-labelledby="ask-result">
      <div className="result-head">
        <h2 id="ask-result" className="h3">Graded answer</h2>
        {a && <CopyButton text={`${a.summary}\n\n${r.claims.map((c) => `- ${c.statement} [${c.source_id}]`).join("\n")}`} label="Copy answer" />}
      </div>
      <div className="row">
        <Badge tone={a?.status === "answered" ? "teal" : a?.status === "refused" ? "rose" : "amber"}>{a?.status ?? "no answer"}</Badge>
        <Badge tone="teal">{verified}/{r.claims.length} claims verified</Badge>
        <Badge tone={r.invented_nct_ids.length ? "rose" : "teal"}>{r.invented_nct_ids.length ? `invented NCT: ${r.invented_nct_ids.join(", ")}` : "0 invented trial IDs"}</Badge>
        <Badge tone="sky">{r.latency_s}s · ${(r.cost_usd ?? 0).toFixed(4)}</Badge>
        {r.skills_loaded.length > 0 && <Badge tone="violet">skills: {r.skills_loaded.join(", ")}</Badge>}
      </div>
      {a?.needs_human_review && <p className="banner"><b>Needs human review.</b> {a.review_reasons.join(" · ")}</p>}
      {a && <p className="summary">{a.summary}</p>}
      {r.error && <p className="note">Runtime note: {r.error}</p>}
      {r.claims.map((c, i) => (
        <article key={i} className={c.verified ? "claim ok" : "claim bad"}>
          <header><b>{c.verified ? "✓ verified" : `✗ ${c.reason}`}</b>
            <a className="mono" href={href("check", { source_id: c.source_id, quote: c.quote })} title="Re-check this quote against the live document">{c.source_id} ↗</a></header>
          <p>{c.statement}</p>
          <blockquote>{c.quote}</blockquote>
          <small>{[c.kind, c.brand_name, c.section].filter(Boolean).join(" · ")}</small>
        </article>
      ))}
    </section>
  );
}
