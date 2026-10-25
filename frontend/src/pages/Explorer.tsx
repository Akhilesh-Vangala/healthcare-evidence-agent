import { useEffect, useState } from "react";
import { type ToolCall, type ToolSpec, SOURCE_OF, api } from "../api";

const STARTERS: Record<string, Record<string, unknown>> = {
  fda_search_labels: { drug: "Keytruda" },
  trials_search: { intervention: "pembrolizumab", condition: "melanoma", phase: "PHASE3" },
  cms_ncd_search: { keywords: "next generation sequencing" },
};

/** Call the agent's own MCP tools live and see exactly what it would see, including the evidence it would log. */
export function Explorer() {
  const [tools, setTools] = useState<ToolSpec[]>([]);
  const [name, setName] = useState("fda_search_labels");
  const [args, setArgs] = useState<Record<string, unknown>>(STARTERS.fda_search_labels);
  const [calls, setCalls] = useState<ToolCall[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {  // open with a real result: the starter label search
    api.tools().then((t) => { setTools(t); return run(); }).catch((e) => setError((e as Error).message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const spec = tools.find((t) => t.name === name);

  function pick(next: string, preset?: Record<string, unknown>) {
    setName(next);
    setArgs(preset ?? STARTERS[next] ?? {});
  }

  async function run(toolName = name, toolArgs = args) {
    setBusy(true); setError("");
    try { const r = await api.call(toolName, toolArgs); setCalls((prev) => [r, ...prev].slice(0, 8)); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  return (
    <main>
      <p className="kicker">MCP tools · live public data</p>
      <h1>Evidence explorer</h1>
      <p className="lede">
        These are the agent's six tools, listed from the MCP server itself. Calls go to openFDA, ClinicalTrials.gov
        and the CMS coverage API, and every document returned is shown with the <code>source_id</code> the agent
        would have to cite. No model is involved.
      </p>
      <div className="grid2">
        <section className="panel">
          <div className="chips">
            {tools.map((t) => <button key={t.name} type="button" className={`${t.name === name ? "on" : ""} s-${SOURCE_OF[t.name]}`} onClick={() => pick(t.name)}>{t.name}</button>)}
          </div>
          {spec && <p className="muted">{spec.description}</p>}
          {spec && Object.entries(spec.input_schema.properties).map(([key, prop]) => (
            <label key={key}>{key}{spec.input_schema.required?.includes(key) ? " *" : ""}
              <input value={String(args[key] ?? prop.default ?? "")} onChange={(e) => {
                const raw = e.target.value;
                setArgs({ ...args, [key]: prop.type === "integer" ? Number(raw) : prop.type === "boolean" ? raw === "true" : raw });
              }} />
            </label>
          ))}
          <div className="row"><button className="primary" type="button" disabled={busy} onClick={() => run()}>Call {name}</button></div>
          {error && <p className="verdict bad"><b>error</b><span>{error}</span></p>}
        </section>
        <section className="panel">
          <h3>Results</h3>
          {calls.length === 0 && <p className="muted">Try a label search, then open a section from a result.</p>}
          {calls.map((c, i) => <CallView key={i} c={c} onOpen={(n, a) => { pick(n, a); run(n, a); }} />)}
        </section>
      </div>
    </main>
  );
}

function CallView({ c, onOpen }: { c: ToolCall; onOpen: (name: string, args: Record<string, unknown>) => void }) {
  const candidates = (c.result.candidates as Array<Record<string, unknown>> | undefined) ?? [];
  const trials = (c.result.results as Array<Record<string, unknown>> | undefined) ?? [];
  return (
    <article className={`call s-${SOURCE_OF[c.tool]}`}>
      <header><code>{c.tool}</code><small>{c.ms} ms</small></header>
      {candidates.map((x) => (
        <div key={String(x.set_id)} className="cand">
          <b>{String(x.brand_name)}</b> <small>{String(x.generic_name)} · {String(x.manufacturer || "")}{x.name_source === "spl_product_data_elements" ? " · name from label text" : ""}</small>
          <div className="chips">{(x.sections_available as string[]).slice(0, 4).map((s) => <button key={s} type="button" onClick={() => onOpen("fda_get_label_section", { set_id: x.set_id, section: s })}>{s.replaceAll("_", " ")}</button>)}</div>
        </div>
      ))}
      {trials.slice(0, 6).map((t, i) => (
        <div key={i} className="cand">
          <b>{String(t.nct_id ?? t.title ?? "")}</b> <small>{String(t.title ?? t.brief_title ?? "")}</small>
          {"nct_id" in t && <div className="chips"><button type="button" onClick={() => onOpen("trials_get", { nct_id: t.nct_id })}>open record</button></div>}
          {"ncd_id" in t && <div className="chips"><button type="button" onClick={() => onOpen("cms_ncd_get", { ncd_id: t.ncd_id, version: t.version ?? 1 })}>open NCD {String(t.ncd_id)}</button></div>}
        </div>
      ))}
      {typeof c.result.text === "string" && <pre className="doc">{(c.result.text as string).slice(0, 1400)}{(c.result.text as string).length > 1400 ? "…" : ""}</pre>}
      {c.evidence.length > 0 && <p className="evid">logged as evidence: {c.evidence.map((e) => <code key={e.source_id}>{e.source_id}</code>)}</p>}
    </article>
  );
}
