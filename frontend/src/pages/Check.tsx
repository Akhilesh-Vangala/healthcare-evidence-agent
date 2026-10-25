import { useEffect, useState } from "react";
import { type CheckResult, api } from "../api";
import { href } from "../route";
import { ErrorBox, Skeleton } from "../ui";
import { type CheckReason, checkClaim } from "../verify";

const KEYTRUDA = "fda:9333c79b-d487-4538-a9f0-71b91a02b287:indications_and_usage";
const PRESETS: Array<[string, string, string]> = [
  ["Verbatim", KEYTRUDA, "KEYTRUDA is a programmed death receptor-1 (PD-1)-blocking antibody indicated"],
  ["Change one word", KEYTRUDA, "KEYTRUDA is a programmed death receptor-1 (PD-1)-activating antibody indicated"],
  ["Too short", KEYTRUDA, "KEYTRUDA is a PD-1"],
  ["Invented source id", "fda:00000000-0000-0000-0000-000000000000:boxed_warning", "KEYTRUDA causes spontaneous remission in all patients."],
];

const REASON: Record<string, string> = {
  ok: "The quote is a verbatim span of the document this source_id names.",
  quote_too_short: "Under 20 characters after normalization: too short to carry a claim.",
  quote_not_in_source: "Not a verbatim span of the document. A paraphrase or one changed word fails.",
  unknown_source_id: "No document exists behind this source_id, so nothing can be cited from it.",
};

/** Live: fetch the document behind a source_id from the public API and run the Python verifier on it. */
export function Check({ params }: { params: URLSearchParams }) {
  const [sourceId, setSourceId] = useState(params.get("source_id") ?? PRESETS[0][1]);
  const [quote, setQuote] = useState(params.get("quote") ?? PRESETS[0][2]);
  const [res, setRes] = useState<CheckResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function run(sid = sourceId, q = quote) {
    if (!sid) return;
    setBusy(true); setError("");
    history.replaceState(null, "", href("check", { source_id: sid, quote: q }));
    try { setRes(await api.check(sid, q)); } catch (e) { setError((e as Error).message); setRes(null); } finally { setBusy(false); }
  }
  useEffect(() => { if (params.get("source_id") && params.get("quote")) run(); /* deep link: check on arrival */ // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <>
      <header className="page-head">
        <p className="kicker">Verifier · same code as the grader</p>
        <h1>Citation check</h1>
        <p className="lede">Give a <code>source_id</code> and a quote. The server fetches that document live, through the same tool the agent
          uses, and applies the grader's rule: the quote must survive whitespace and quote-mark normalization as a contiguous span of at least 20 characters.</p>
      </header>
      <div className="chips" aria-label="Presets">{PRESETS.map(([label, sid, q]) => <button key={label} type="button" onClick={() => { setSourceId(sid); setQuote(q); run(sid, q); }}>{label}</button>)}</div>
      <div className="grid2">
        <form className="panel" onSubmit={(e) => { e.preventDefault(); run(); }} aria-labelledby="ck-in">
          <h2 id="ck-in" className="h3">Claim</h2>
          <label>source_id<input value={sourceId} onChange={(e) => setSourceId(e.target.value)} spellCheck={false} /></label>
          <label>Quote<textarea rows={4} value={quote} onChange={(e) => setQuote(e.target.value)} /></label>
          <button className="primary" type="submit" disabled={busy || !sourceId}>{busy ? "Fetching…" : "Fetch and check"}</button>
          {error && <ErrorBox error={error} onRetry={() => run()} />}
        </form>
        <section className="panel" aria-labelledby="ck-out" aria-busy={busy} aria-live="polite">
          <h2 id="ck-out" className="h3">Verdict</h2>
          {busy && <Skeleton lines={4} />}
          {!busy && !res && !error && <p className="muted">Pick a preset, or follow a source_id link from the evidence explorer or an agent answer.</p>}
          {!busy && res && (
            <>
              <div className={`stamp ${res.verified ? "ok" : "bad"}`}>{res.verified ? "VERIFIED" : "REJECTED"}</div>
              <p><code>{res.reason}</code> — {REASON[res.reason]}</p>
              {res.reason === "quote_not_in_source" && (
                <div className="diff" aria-label="Where the quote diverges from the document">
                  <span className="m">{res.normalized_quote.slice(0, res.matched_prefix)}</span><span className="x">{res.normalized_quote.slice(res.matched_prefix)}</span>
                  <small>Green: the longest opening stretch found in the document ({res.matched_prefix} of {res.normalized_quote.length} characters). Red: from the first character that is not.</small>
                </div>
              )}
              {res.document_found && <pre className="doc" tabIndex={0}>{res.excerpt}{res.document_chars > res.excerpt.length ? "…" : ""}</pre>}
              {res.url && <p className="note"><a href={res.url} target="_blank" rel="noreferrer">Open the source on DailyMed ↗</a></p>}
            </>
          )}
        </section>
      </div>
      <OfflineCheck />
    </>
  );
}

function OfflineCheck() {
  const [source, setSource] = useState("KEYTRUDA is a programmed death receptor-1 (PD-1)-blocking antibody indicated for the treatment of patients with unresectable or metastatic melanoma.");
  const [quote, setQuote] = useState("KEYTRUDA is indicated for melanoma and is the preferred PD-1 antibody.");
  const reason: CheckReason = checkClaim(source, quote, true);
  return (
    <details className="panel offline">
      <summary>Offline variant: paste any text (runs in your browser, same rule)</summary>
      <label>Source text<textarea rows={3} value={source} onChange={(e) => setSource(e.target.value)} /></label>
      <label>Quote<textarea rows={2} value={quote} onChange={(e) => setQuote(e.target.value)} /></label>
      <p className={reason === "ok" ? "verdict ok" : "verdict bad"}><b>{reason}</b><span>{REASON[reason]}</span></p>
    </details>
  );
}
