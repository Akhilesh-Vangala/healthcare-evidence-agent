import { useState } from "react";
import { type CheckResult, api } from "../api";
import { type CheckReason, checkClaim } from "../verify";

const LIVE_PRESETS: Array<[string, string, string]> = [
  ["Verbatim (Keytruda indications)", "fda:9333c79b-d487-4538-a9f0-71b91a02b287:indications_and_usage",
    "KEYTRUDA is a programmed death receptor-1 (PD-1)-blocking antibody indicated"],
  ["Change one word", "fda:9333c79b-d487-4538-a9f0-71b91a02b287:indications_and_usage",
    "KEYTRUDA is a programmed death receptor-1 (PD-1)-activating antibody indicated"],
  ["Invented source id", "fda:00000000-0000-0000-0000-000000000000:boxed_warning",
    "KEYTRUDA causes spontaneous remission in all patients."],
];

const REASON: Record<string, string> = {
  ok: "The quote is a verbatim span of the document this source_id names.",
  quote_too_short: "Under 20 characters after normalization: too short to carry a claim.",
  quote_not_in_source: "Not a verbatim span of the document. A paraphrase or one changed word fails.",
  unknown_source_id: "No document exists behind this source_id, so nothing can be cited from it.",
};

/** Live: fetch the document behind a source_id from the public API and run the Python verifier on it. */
export function Check() {
  const [sourceId, setSourceId] = useState(LIVE_PRESETS[0][1]);
  const [quote, setQuote] = useState(LIVE_PRESETS[0][2]);
  const [res, setRes] = useState<CheckResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function run(sid = sourceId, q = quote) {
    setBusy(true); setError("");
    try { setRes(await api.check(sid, q)); } catch (e) { setError((e as Error).message); setRes(null); } finally { setBusy(false); }
  }

  return (
    <main>
      <p className="kicker">Verifier · same code as the grader</p>
      <h1>Citation check</h1>
      <p className="lede">
        Give a <code>source_id</code> and a quote. The server fetches that document live, through the same tool the
        agent uses, and runs the grader's rule: the quote must survive whitespace and quote-mark normalization as a
        contiguous span of at least 20 characters.
      </p>
      <div className="chips">{LIVE_PRESETS.map(([label, sid, q]) => <button key={label} type="button" onClick={() => { setSourceId(sid); setQuote(q); run(sid, q); }}>{label}</button>)}</div>
      <div className="grid2">
        <section className="panel">
          <label>source_id<input value={sourceId} onChange={(e) => setSourceId(e.target.value)} /></label>
          <label>Quote<textarea rows={4} value={quote} onChange={(e) => setQuote(e.target.value)} /></label>
          <button className="primary" type="button" disabled={busy} onClick={() => run()}>Fetch and check</button>
          {error && <p className="verdict bad"><b>error</b><span>{error}</span></p>}
        </section>
        <section className="panel">
          {!res && <p className="muted">Pick a preset or paste a source_id from the evidence explorer.</p>}
          {res && (
            <>
              <div className={`stamp ${res.verified ? "ok" : "bad"}`}>{res.verified ? "VERIFIED" : "REJECTED"}</div>
              <p><code>{res.reason}</code> — {REASON[res.reason]}</p>
              {res.reason === "quote_not_in_source" && (
                <div className="diff"><span className="m">{res.normalized_quote.slice(0, res.matched_prefix)}</span><span className="x">{res.normalized_quote.slice(res.matched_prefix)}</span>
                  <small>green: the longest opening stretch found in the document ({res.matched_prefix} of {res.normalized_quote.length} characters)</small></div>
              )}
              {res.document_found && <pre className="doc">{res.excerpt}{res.document_chars > res.excerpt.length ? "…" : ""}</pre>}
              {res.url && <p className="note"><a href={res.url} target="_blank" rel="noreferrer">Open on DailyMed</a></p>}
            </>
          )}
        </section>
      </div>
      <OfflineCheck />
    </main>
  );
}

function OfflineCheck() {
  const [source, setSource] = useState("KEYTRUDA is a programmed death receptor-1 (PD-1)-blocking antibody indicated for the treatment of patients with unresectable or metastatic melanoma.");
  const [quote, setQuote] = useState("KEYTRUDA is indicated for melanoma and is the preferred PD-1 antibody.");
  const reason: CheckReason = checkClaim(source, quote, true);
  return (
    <details className="panel offline">
      <summary>Offline variant: paste any source text (runs in your browser, same rule)</summary>
      <label>Source text<textarea rows={3} value={source} onChange={(e) => setSource(e.target.value)} /></label>
      <label>Quote<textarea rows={2} value={quote} onChange={(e) => setQuote(e.target.value)} /></label>
      <p className={reason === "ok" ? "verdict ok" : "verdict bad"}><b>{reason}</b><span>{REASON[reason]}</span></p>
    </details>
  );
}
