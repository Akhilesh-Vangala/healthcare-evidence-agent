import { useEffect, useState } from "react";
import { type ToolCall, type ToolSpec, SOURCE_OF, api } from "../api";
import { href } from "../route";
import { Empty, ErrorBox, Skeleton } from "../ui";

const STARTERS: Record<string, Record<string, unknown>> = {
  fda_search_labels: { drug: "Keytruda" },
  trials_search: { intervention: "pembrolizumab", condition: "melanoma", phase: "PHASE3" },
  cms_ncd_search: { keywords: "next generation sequencing" },
};

function argsFrom(params: URLSearchParams, tool: string): Record<string, unknown> {
  try { return params.get("args") ? JSON.parse(params.get("args") as string) : STARTERS[tool] ?? {}; } catch { return STARTERS[tool] ?? {}; }
}

/** The agent's own MCP tools, called live; every document comes back with the source_id the agent would cite. */
export function Explorer({ params }: { params: URLSearchParams }) {
  const initial = params.get("tool") ?? "fda_search_labels";
  const [tools, setTools] = useState<ToolSpec[] | null>(null);
  const [name, setName] = useState(initial);
  const [args, setArgs] = useState<Record<string, unknown>>(argsFrom(params, initial));
  const [calls, setCalls] = useState<ToolCall[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  function load() {
    setError("");
    api.tools().then((t) => { setTools(t); return run(name, args); }).catch((e) => setError((e as Error).message));
  }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(load, []);
  const spec = tools?.find((t) => t.name === name);

  function pick(next: string, preset?: Record<string, unknown>) { setName(next); setArgs(preset ?? STARTERS[next] ?? {}); }

  async function run(toolName = name, toolArgs = args) {
    setBusy(true); setError("");
    history.replaceState(null, "", href("explorer", { tool: toolName, args: JSON.stringify(toolArgs) }));
    try { const r = await api.call(toolName, toolArgs); setCalls((prev) => [r, ...prev].slice(0, 8)); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  return (
    <>
      <header className="page-head">
        <p className="kicker">MCP tools · live public data</p>
        <h1>Evidence explorer</h1>
        <p className="lede">The agent's six tools, listed from the MCP server itself. Calls go to openFDA, ClinicalTrials.gov and the CMS
          coverage API, and every document comes back with the <code>source_id</code> the agent would have to cite. No model is involved.</p>
      </header>
      <div className="grid2">
        <section className="panel" aria-labelledby="ex-tool">
          <h2 id="ex-tool" className="h3">Tool</h2>
          {tools === null && !error ? <Skeleton lines={2} /> : (
            <div className="chips" role="radiogroup" aria-label="MCP tool">
              {(tools ?? []).map((t) => <button key={t.name} type="button" role="radio" aria-checked={t.name === name}
                className={`${t.name === name ? "on" : ""} s-${SOURCE_OF[t.name]}`} onClick={() => pick(t.name)}>{t.name}</button>)}
            </div>
          )}
          {spec && <p className="muted">{spec.description}</p>}
          {spec && (
            <form onSubmit={(e) => { e.preventDefault(); run(); }}>
              {Object.entries(spec.input_schema.properties).map(([key, prop]) => (
                <label key={key}>{key}{spec.input_schema.required?.includes(key) ? <span aria-hidden="true"> *</span> : null}
                  <input name={key} required={spec.input_schema.required?.includes(key)} value={String(args[key] ?? prop.default ?? "")}
                    onChange={(e) => {
                      const raw = e.target.value;
                      setArgs({ ...args, [key]: prop.type === "integer" ? Number(raw) : prop.type === "boolean" ? raw === "true" : raw });
                    }} />
                </label>
              ))}
              <div className="row"><button className="primary" type="submit" disabled={busy}>{busy ? "Calling…" : `Call ${name}`}</button></div>
            </form>
          )}
          {error && <ErrorBox error={error} onRetry={tools ? () => run() : load} />}
        </section>
        <section className="panel" aria-labelledby="ex-res" aria-busy={busy}>
          <h2 id="ex-res" className="h3">Results</h2>
          {busy && calls.length === 0 && <Skeleton lines={4} />}
          {!busy && calls.length === 0 && !error && <Empty title="No calls yet">Search a label, then open a section from a result.</Empty>}
          {calls.map((c, i) => <CallView key={`${c.tool}-${i}`} c={c} onOpen={(n, a) => { pick(n, a); run(n, a); }} />)}
        </section>
      </div>
    </>
  );
}

function CallView({ c, onOpen }: { c: ToolCall; onOpen: (name: string, args: Record<string, unknown>) => void }) {
  const candidates = (c.result.candidates as Array<Record<string, unknown>> | undefined) ?? [];
  const results = (c.result.results as Array<Record<string, unknown>> | undefined) ?? [];
  return (
    <article className={`call s-${SOURCE_OF[c.tool]}`}>
      <header><code>{c.tool}</code><small>{c.ms} ms</small></header>
      {candidates.length === 0 && results.length === 0 && typeof c.result.text !== "string" && <p className="muted">{String(c.result.note ?? "No results.")}</p>}
      {candidates.map((x) => (
        <div key={String(x.set_id)} className="cand">
          <b>{String(x.brand_name)}</b> <small>{String(x.generic_name)} · {String(x.manufacturer || "")}{x.name_source === "spl_product_data_elements" ? " · name from label text" : ""}</small>
          <div className="chips">{(x.sections_available as string[]).slice(0, 5).map((s) => <button key={s} type="button" onClick={() => onOpen("fda_get_label_section", { set_id: x.set_id, section: s })}>{s.replaceAll("_", " ")}</button>)}</div>
        </div>
      ))}
      {results.slice(0, 6).map((t, i) => (
        <div key={i} className="cand">
          <b>{String(t.nct_id ?? t.title ?? "")}</b> <small>{String(t.title ?? t.brief_title ?? "")}</small>
          {"nct_id" in t && <div className="chips"><button type="button" onClick={() => onOpen("trials_get", { nct_id: t.nct_id })}>open record</button></div>}
          {"ncd_id" in t && <div className="chips"><button type="button" onClick={() => onOpen("cms_ncd_get", { ncd_id: t.ncd_id, version: t.version ?? 1 })}>open NCD {String(t.ncd_id)}</button></div>}
        </div>
      ))}
      {typeof c.result.text === "string" && <pre className="doc" tabIndex={0}>{(c.result.text as string).slice(0, 1400)}{(c.result.text as string).length > 1400 ? "…" : ""}</pre>}
      {c.evidence.length > 0 && (
        <p className="evid">Logged as evidence: {c.evidence.map((e) => (
          <a key={e.source_id} className="mono" href={href("check", { source_id: e.source_id, quote: "" })} title="Check a quote against this document">{e.source_id}</a>
        ))}</p>
      )}
    </article>
  );
}
