import { href, navigate } from "../route";
import { money, study } from "../study";

export function Runs({ params }: { params: URLSearchParams }) {
  const trace = study.traces.find((t) => t.id === params.get("id")) ?? study.traces[0];
  return (
    <>
      <header className="page-head">
        <p className="kicker">Checked into the repository</p>
        <h1>Saved runs</h1>
        <p className="lede">Five Claude Code runs. Each claim is re-checked against that run's evidence log: green means the quote is a verbatim span of a source retrieved in that run.</p>
      </header>
      <div className="chips" role="radiogroup" aria-label="Saved run">{study.traces.map((t) => (
        <button key={t.id} type="button" role="radio" aria-checked={t.id === trace.id} className={t.id === trace.id ? "on" : ""}
          onClick={() => navigate("runs", { id: t.id }, true)}>{t.id} · {t.title}</button>
      ))}</div>
      <section className="panel" aria-labelledby="run-q">
        <p className="kicker">{trace.config} · {trace.model}</p>
        <h2 id="run-q">{trace.query}</h2>
        <p className="status-line"><b>{trace.status}</b>{trace.needs_human_review ? " · human review" : " · no review flag"} · {trace.n_sources} sources · {trace.latency_s}s · {money(trace.cost_usd)}</p>
        <p>{trace.summary}</p>
        {trace.review_reasons.length > 0 && <p className="banner">{trace.review_reasons.join(" · ")}</p>}
        {trace.claims.map((claim, i) => (
          <article key={`${claim.source_id}-${i}`} className={claim.verified ? "claim ok" : "claim bad"}>
            <header><b>{claim.verified ? "✓ verified" : `✗ ${claim.reason}`}</b>
              <a className="mono" href={href("check", { source_id: claim.source_id, quote: claim.quote ?? "" })} title="Re-check against today's live document">{claim.source_id} ↗</a></header>
            <p>{claim.statement}</p><blockquote>{claim.quote}</blockquote>
            <small>{[claim.kind, claim.brand_name, claim.section].filter(Boolean).join(" · ")}</small>
          </article>
        ))}
      </section>
    </>
  );
}
