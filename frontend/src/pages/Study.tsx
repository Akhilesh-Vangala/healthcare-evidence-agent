import { useMemo, useState } from "react";
import { money, pct, pts, study } from "../study";

export function Study() {
  const [category, setCategory] = useState("all");
  const categories = useMemo(() => ["all", ...Array.from(new Set(study.tasks.map((t) => t.category)))], []);
  const tasks = study.tasks.filter((t) => category === "all" || t.category === category);
  return (
    <>
      <header className="page-head">
        <p className="kicker">Published study · {study.n_rows} rows · Claude Code runtime</p>
        <h1>What moved the needle</h1>
        <p className="lede">One factor changes at a time. Pass rate is the mean of per-task means with a bootstrap 95% interval; A, B and C were repeated twice.</p>
      </header>
      <figure className="bars" aria-label="Pass rate by configuration with 95% intervals">
        {study.configs.map((row) => (
          <div key={row.id} className={`bar ${row.id === "C_tools_skills" ? "best" : ""}`}>
            <span>{row.label}</span>
            <div className="track" role="img" aria-label={`${pct(row.pass_rate)}, interval ${pct(row.ci[0])} to ${pct(row.ci[1])}`}>
              <div className="fill" style={{ width: `${row.pass_rate * 100}%` }} /><div className="ci" style={{ left: `${row.ci[0] * 100}%`, width: `${(row.ci[1] - row.ci[0]) * 100}%` }} />
            </div>
            <b>{pct(row.pass_rate)}</b><small>{money(row.cost_usd)}</small>
          </div>
        ))}
      </figure>
      <ul className="deltas">
        {study.deltas.map((d) => (
          <li key={`${d.config_a}-${d.config_b}`}><code>{d.config_a}</code> → <code>{d.config_b}</code>
            <strong>{pts(d.delta_pass_rate)} pts</strong>
            <span>[{pts(d.delta_ci95[0])}, {pts(d.delta_ci95[1])}] · {d.delta_significant_vs_zero ? "interval excludes 0" : "interval includes 0"}</span></li>
        ))}
      </ul>

      {study.runtime && (
        <section aria-labelledby="st-rt">
          <h2 id="st-rt">Cross-runtime check: the same configurations on the Anthropic API</h2>
          <p className="lede">{study.runtime.note}</p>
          <div className="table-wrap"><table>
            <thead><tr><th scope="col">Configuration</th><th scope="col">Pass</th><th scope="col">95% CI</th><th scope="col">Runs</th><th scope="col">Claim precision</th><th scope="col">Cost / task</th><th scope="col">Latency</th><th scope="col">Input from cache</th></tr></thead>
            <tbody>{study.runtime.configs.map((r) => (
              <tr key={r.id} className={r.id === "C_api_tools_skills" ? "focus" : ""}><th scope="row">{r.label}</th><td>{pct(r.pass_rate)}</td><td>{pct(r.ci[0])}–{pct(r.ci[1])}</td><td>{r.n_runs}</td>
                <td>{r.claim_precision == null ? "—" : pct(r.claim_precision)}</td><td>{money(r.cost_usd)}</td><td>{r.latency_s}s</td><td>{r.cache_share == null ? "—" : pct(r.cache_share)}</td></tr>
            ))}</tbody>
          </table></div>
          <ul className="deltas">{study.runtime.deltas.map((d) => (
            <li key={d.contrast}><code>{d.contrast}</code><strong>{pts(d.delta)} pts</strong><span>[{pts(d.ci95[0])}, {pts(d.ci95[1])}] · {d.significant ? "interval excludes 0" : "interval includes 0"}</span></li>
          ))}</ul>
        </section>
      )}

      {study.redteam && (
        <section aria-labelledby="st-red">
          <h2 id="st-red">Red-team suite · {study.redteam.runs} runs</h2>
          <p className="lede">{study.redteam.note}</p>
          <div className="table-wrap"><table>
            <thead><tr><th scope="col">Task</th><th scope="col">Attack</th><th scope="col">Repeats</th></tr></thead>
            <tbody>{study.redteam.tasks.map((t) => (
              <tr key={t.id}><th scope="row"><code>{t.id}</code></th><td>{t.category.replaceAll("_", " ")}</td>
                <td className={t.passes.every(Boolean) ? "ok" : "bad"}>{t.passes.map((p) => (p ? "held" : "failed")).join(" · ")}{t.failed_checks.length > 0 && <small>{t.failed_checks.join(", ")}</small>}</td></tr>
            ))}</tbody>
          </table></div>
        </section>
      )}

      <section aria-labelledby="st-tasks">
        <h2 id="st-tasks">Config C, task by task (Claude Code)</h2>
        <div className="chips" role="radiogroup" aria-label="Filter by category">{categories.map((cat) => (
          <button key={cat} type="button" role="radio" aria-checked={category === cat} className={category === cat ? "on" : ""} onClick={() => setCategory(cat)}>{cat.replaceAll("_", " ")}</button>
        ))}</div>
        <div className="table-wrap"><table>
          <thead><tr><th scope="col">Task</th><th scope="col">Category</th><th scope="col">Repeats</th><th scope="col">Question</th></tr></thead>
          <tbody>{tasks.map((task) => (
            <tr key={task.id}><th scope="row"><code>{task.id}</code></th><td>{task.category.replaceAll("_", " ")}</td>
              <td className={task.passes.every(Boolean) ? "ok" : "bad"}>{task.passes.map((p) => (p ? "pass" : "fail")).join(" · ") || "—"}{task.failed_checks.length > 0 && <small>{task.failed_checks.join(", ")}</small>}</td>
              <td>{task.query}</td></tr>
          ))}</tbody>
        </table></div>
        <p className="note">{study.excluded_note}</p>
      </section>
    </>
  );
}
