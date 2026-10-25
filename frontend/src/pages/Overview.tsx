import { href } from "../route";
import { pct, study } from "../study";

const STAGES: Array<[string, string, string]> = [
  ["Question", "commercial · medical · gov affairs", "s-q"],
  ["Claude", "plans, loads Agent Skills", "s-model"],
  ["MCP tools", "openFDA · ClinicalTrials.gov · CMS", "s-tools"],
  ["Evidence log", "every document, per run", "s-log"],
  ["Verifier", "verbatim quotes · no unseen NCT", "s-verify"],
  ["Review flag", "off-label · comparative · coverage", "s-review"],
];

export function Overview() {
  const c = study.configs.find((x) => x.id === "C_tools_skills");
  const head = study.runtime?.headline;
  return (
    <>
      <section className="hero">
        <p className="kicker">Agentic GenAI · evaluation · governance</p>
        <h1>A tool-using agent that cannot cite a document it did not retrieve.</h1>
        <p className="lede">Questions about FDA labels, clinical trials and Medicare coverage. Six MCP tools fetch the evidence, four Agent Skills
          carry the procedure, and a grader that is not the model checks every quote word for word against what the tools returned in that run.
          Measured on two runtimes: headless Claude Code and the Anthropic Messages API.</p>
        <div className="row">
          <a className="btn primary" href={href("ask")}>Ask the agent</a>
          <a className="btn" href={href("explorer")}>Explore the evidence tools</a>
          <a className="btn" href={href("study")}>Read the study</a>
        </div>
      </section>
      <section className="metrics" aria-label="Headline results">
        <article><b className="teal">{c ? pct(c.pass_rate) : "—"}</b><span>golden-set pass, tools + skills</span><small>Claude Code · 60 runs · CI {c ? `${pct(c.ci[0])}–${pct(c.ci[1])}` : ""}</small></article>
        <article><b className="sky">{head ? pct(head.api_c_28) : "—"}</b><span>same config, Anthropic API</span><small>{head ? `vs ${pct(head.claude_code_c_28)}, 28 tasks unaffected by data drift` : ""}</small></article>
        <article><b className="amber">0</b><span>invented trial IDs with tools</span><small>closed book invented them in 4 runs</small></article>
        <article><b className="violet">{study.redteam ? pct(study.redteam.pass_rate) : "—"}</b><span>red-team suite</span><small>{study.redteam ? `${study.redteam.runs} adversarial runs` : ""}</small></article>
      </section>
      <ol className="pipeline" aria-label="How a question is answered">
        {STAGES.map(([a, b, cls]) => <li key={a} className={cls}><b>{a}</b><small>{b}</small></li>)}
      </ol>
      <section className="split">
        <div className="panel"><h2>What is reusable</h2><ul>
          <li>An MCP server over three public APIs; every document written to a per-run evidence log.</li>
          <li>Agent Skills for product disambiguation, citation discipline, trial landscapes and escalation.</li>
          <li>A grader that is not the model: a paraphrase fails, an NCT id the tools never returned fails the task.</li>
          <li>Two runtimes behind one grader, so a result can be checked outside the harness that produced it.</li>
        </ul></div>
        <div className="panel"><h2>What it will not do</h2><ul>
          <li>Give medical advice, dosing for a patient, or promotional claims; those are refused or escalated.</li>
          <li>Average the 90% pilot of config C into the 95%; those 30 runs sit outside the 240.</li>
          <li>Call a model from this site unless live answering is enabled with rate and spend limits.</li>
        </ul></div>
      </section>
    </>
  );
}
