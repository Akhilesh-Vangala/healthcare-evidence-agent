#!/usr/bin/env python3
"""Build a static HTML provenance viewer from a checked-in example run."""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from cmg_agent.evidence import load  # noqa: E402
from cmg_agent.provenance import build_provenance  # noqa: E402

RUN = ROOT / "examples/agent_runs/A01_keytruda_vs_keytruda_qlex"
OUT = ROOT / "examples/trace_viewer/index.html"


def main() -> int:
    result = json.loads((RUN / "result.json").read_text())
    evidence = load(RUN / "evidence.jsonl")
    answer = result.get("answer") or {}
    prov = build_provenance(answer, evidence)

    claim_cards = []
    for node in prov["nodes"]:
        if node.get("type") != "claim":
            continue
        sid = node.get("source_id") or ""
        src = evidence.get(sid, {})
        ok = bool(node.get("verified"))
        badge = "VERIFIED" if ok else node.get("reason", "FAIL")
        color = "#0f766e" if ok else "#b45309"
        quote = ""
        for c in answer.get("claims") or []:
            if c.get("source_id") == sid and c.get("statement") == node.get("statement"):
                quote = c.get("quote") or ""
                break
        claim_cards.append(
            f"""
            <article class="card">
              <div class="row"><span class="badge" style="background:{color}">{html.escape(badge)}</span>
              <code>{html.escape(sid)}</code></div>
              <p class="stmt">{html.escape(node.get("statement") or "")}</p>
              <blockquote>{html.escape(quote[:400])}</blockquote>
              <p class="meta">{html.escape(str(src.get("kind") or ""))}
 · {html.escape(str(src.get("brand_name") or ""))}
 · {html.escape(str(src.get("section") or ""))}</p>
            </article>
            """
        )

    sources = [
        f"<li><code>{html.escape(n['id'])}</code> — {html.escape(str(n.get('kind')))} ({n.get('chars', 0)} chars)</li>"
        for n in prov["nodes"]
        if n.get("type") == "source"
    ]

    page = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>HEA trace — KEYTRUDA vs KEYTRUDA QLEX</title>
  <style>
    :root {{ --ink:#0b1620; --teal:#0f766e; --muted:#5b6b75; --bg:#f4f7f8; }}
    body {{ margin:0; font-family: ui-sans-serif, system-ui, Helvetica, Arial, sans-serif; background:var(--bg); color:var(--ink); }}
    header {{ background:linear-gradient(120deg,#071018,#0f2f2a); color:#e8eef4; padding:2rem 1.5rem; }}
    header h1 {{ margin:0 0 .4rem; font-size:1.6rem; }}
    header p {{ margin:0; opacity:.85; max-width:52rem; }}
    main {{ max-width:960px; margin:0 auto; padding:1.5rem; }}
    .stats {{ display:flex; gap:1rem; flex-wrap:wrap; margin:1rem 0 1.5rem; }}
    .stat {{ background:#fff; border:1px solid #dbe4ea; border-radius:12px; padding:1rem 1.2rem; min-width:140px; }}
    .stat b {{ display:block; font-size:1.4rem; color:var(--teal); }}
    .card {{ background:#fff; border:1px solid #dbe4ea; border-radius:12px; padding:1rem 1.1rem; margin:0 0 1rem; }}
    .badge {{ color:#fff; font-size:.7rem; font-weight:700; letter-spacing:.06em; padding:.25rem .5rem; border-radius:999px; }}
    .row {{ display:flex; gap:.75rem; align-items:center; flex-wrap:wrap; margin-bottom:.6rem; }}
    blockquote {{ margin:.6rem 0; padding:.75rem 1rem; background:#ecfeff; border-left:3px solid var(--teal); font-size:.92rem; }}
    .stmt {{ font-weight:600; margin:.2rem 0; }}
    .meta {{ color:var(--muted); font-size:.85rem; margin:0; }}
    code {{ font-size:.8rem; background:#eef3f6; padding:.1rem .35rem; border-radius:4px; }}
    ul {{ line-height:1.6; }}
  </style>
</head>
<body>
  <header>
    <h1>Provenance trace · KEYTRUDA vs KEYTRUDA QLEX</h1>
    <p>{html.escape(result.get("query") or "")}</p>
  </header>
  <main>
    <div class="stats">
      <div class="stat"><b>{prov["verified_claims"]}</b>verified claims</div>
      <div class="stat"><b>{prov["unverified_claims"]}</b>unverified</div>
      <div class="stat"><b>{prov["n_sources"]}</b>sources retrieved</div>
      <div class="stat"><b>{html.escape(str((result.get("config") or {}).get("name") or "C"))}</b>config</div>
    </div>
    <h2>Answer summary</h2>
    <p>{html.escape(answer.get("summary") or "")}</p>
    <h2>Claims</h2>
    {''.join(claim_cards)}
    <h2>Evidence log</h2>
    <ul>{''.join(sources)}</ul>
    <p class="meta">Generated from <code>examples/agent_runs/A01_keytruda_vs_keytruda_qlex</code> via <code>scripts/build_trace_viewer.py</code>. No model call.</p>
  </main>
</body>
</html>
"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page)
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
