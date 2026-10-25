"""HTTP service behind the console.

GET  /api/health                 liveness, tool count, whether live answering is enabled
GET  /api/tools                  the MCP server's tools, exactly as the agent sees them
POST /api/tools/{name}           call one tool live (openFDA, ClinicalTrials.gov, CMS); returns the result and the
                                 documents it would add to the agent's evidence log
POST /api/check                  fetch the document behind a source_id live and run the verifier on a quote
GET  /api/runs                   recorded real agent runs (model, date, commit, every event), for replay
POST /api/agent/stream           the agent on the Anthropic API, as server-sent events (needs a key, prices and,
                                 on a public deployment, the durable rate limiter in limits.py)

Everything except /api/agent/stream calls no model. Tool calls hit public government APIs through the same cached
client the agent uses.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
import time
import uuid
from pathlib import Path

from hea import __version__, evidence
from hea.claude_runner import ROOT
from hea.limits import Limiter, LimitExceeded, client_id
from hea.verify import verify_claims
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

RECORDED = ROOT / "data" / "recorded_runs.jsonl"
log = logging.getLogger("hea.http")
if not log.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(message)s"))
    log.addHandler(_h)
    log.setLevel(logging.INFO)

app = FastAPI(title="Healthcare Evidence Agent", version=__version__, docs_url="/api/docs", redoc_url=None,
              openapi_url="/api/openapi.json")

SECURITY_HEADERS = {
    "x-content-type-options": "nosniff",
    "referrer-policy": "no-referrer",
    "x-frame-options": "DENY",
    "cache-control": "no-store",
}


@app.middleware("http")
async def observe(request: Request, call_next):
    """Request id, JSON access log (paths only, never question text) and security headers."""
    rid = request.headers.get("x-request-id", "")[:64] or uuid.uuid4().hex[:16]
    t0 = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:  # noqa: BLE001  (never leak a traceback to the client)
        log.exception(json.dumps({"rid": rid, "path": request.url.path, "event": "unhandled_error"}))
        response = JSONResponse({"detail": "internal error", "request_id": rid}, status_code=500)
    response.headers.update({"x-request-id": rid, **SECURITY_HEADERS})
    log.info(json.dumps({"rid": rid, "method": request.method, "path": request.url.path,
                         "status": response.status_code, "ms": round(1000 * (time.perf_counter() - t0), 1)}))
    return response


def _limiter() -> Limiter:
    return Limiter.from_env()


def answering_status() -> dict:
    if not os.getenv("ANTHROPIC_API_KEY"):
        return {"enabled": False, "reason": "no model key configured"}
    if not _limiter().enabled:
        return {"enabled": False, "reason": "no durable rate limiter configured for this public deployment"}
    lim = _limiter()
    return {"enabled": True, "rate_per_hour": lim.per_hour, "daily_usd_cap": lim.daily_usd}


async def _tool_specs() -> list[dict]:
    from hea.mcp_server import server

    return [{"name": t.name, "description": t.description, "input_schema": t.input_schema}
            for t in await server.list_tools()]


@app.get("/api/health")
def health():
    return {"ok": True, "version": __version__, "tools": len(asyncio.run(_tool_specs())), "answering": answering_status()}


@app.get("/api/tools")
def tools():
    return {"tools": asyncio.run(_tool_specs())}


def _run_tool(name: str, args: dict) -> tuple[dict, dict]:
    """Call one MCP tool in-process with a throwaway evidence log; return (result, documents recorded)."""
    from hea.mcp_server import server

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "evidence.jsonl"
        path.touch()
        with evidence.bound_to(path):
            result = asyncio.run(server.call_tool(name, args))
        docs = evidence.load(path)
    payload = getattr(result, "structured_content", None)
    if payload is None:
        text = "\n".join(getattr(c, "text", "") for c in result.content or [])
        payload = json.loads(text) if text.startswith("{") else {"text": text}
    return payload, docs


TOOL_NAMES = {"fda_search_labels", "fda_get_label_section", "trials_search", "trials_get", "cms_ncd_search",
              "cms_ncd_get"}


@app.post("/api/tools/{name}")
def call_tool(name: str, args: dict):
    if name not in TOOL_NAMES:
        raise HTTPException(404, f"unknown tool; one of {sorted(TOOL_NAMES)}")
    t0 = time.perf_counter()
    try:
        payload, docs = _run_tool(name, args)
    except Exception as exc:  # noqa: BLE001  (bad arguments or an upstream outage, reported to the caller)
        raise HTTPException(422, f"{type(exc).__name__}: {str(exc)[:300]}") from exc
    return {"tool": name, "args": args, "result": payload, "ms": round(1000 * (time.perf_counter() - t0)),
            "evidence": [{"source_id": k, "kind": v["kind"], "chars": len(v["text"]),
                          **{m: v.get(m) for m in ("brand_name", "section", "url") if v.get(m)}}
                         for k, v in docs.items()]}


class CheckRequest(BaseModel):
    source_id: str = Field(max_length=200)
    quote: str = Field(max_length=2000)


def _fetch_document(source_id: str) -> dict:
    """Re-fetch the document a source_id names, through the same tool the agent would have used."""
    parts = source_id.split(":")
    if parts[0] == "fda" and len(parts) == 3:
        return _run_tool("fda_get_label_section", {"set_id": parts[1], "section": parts[2]})[1]
    if parts[0] == "ctgov" and len(parts) == 2:
        return _run_tool("trials_get", {"nct_id": parts[1]})[1]
    if parts[0] == "cms" and len(parts) == 3 and parts[1] == "ncd":
        return _run_tool("cms_ncd_get", {"ncd_id": int(parts[2])})[1]
    raise HTTPException(400, "source_id must look like fda:<set_id>:<section>, ctgov:<NCT id> or cms:ncd:<id>")


@app.post("/api/check")
def check(req: CheckRequest):
    docs = _fetch_document(req.source_id)
    [result] = verify_claims({"claims": [{"source_id": req.source_id, "quote": req.quote}]}, docs)
    doc = docs.get(req.source_id)
    norm_q = evidence.normalize(req.quote)
    norm_d = evidence.normalize(doc["text"]) if doc else ""
    lo, hi = 0, len(norm_q)  # longest prefix of the quote found verbatim: substring-ness is monotone in length
    while lo < hi:
        mid = (lo + hi + 1) // 2
        lo, hi = (mid, hi) if norm_q[:mid] in norm_d else (lo, mid - 1)
    return {**result, "document_found": doc is not None, "document_chars": len(doc["text"]) if doc else 0,
            "excerpt": doc["text"][:1200] if doc else "", "url": (doc or {}).get("url"),
            "normalized_quote": norm_q, "matched_prefix": lo}


@app.get("/api/runs")
def runs():
    rows = [json.loads(x) for x in RECORDED.read_text().splitlines() if x.strip()] if RECORDED.exists() else []
    return {"runs": rows}


class AskRequest(BaseModel):
    query: str = Field(min_length=10, max_length=1500)


@app.post("/api/agent/stream")
def agent_stream(req: AskRequest, request: Request):
    from hea.api_runner import PRICES, ApiConfig, cost_usd, run

    status = answering_status()
    if not status["enabled"]:
        raise HTTPException(503, f"Live answering is disabled: {status['reason']}")
    cfg = ApiConfig()
    p_in, p_out = PRICES[cfg.model]
    worst = cfg.max_turns * (15_000 * p_in + cfg.max_tokens * p_out) / 1e6
    try:
        day = _limiter().admit(client_id(request.headers), worst)
    except LimitExceeded as exc:
        raise HTTPException(429, str(exc)) from exc

    def events():
        """The agent runs on a worker thread; its events stream from a queue as they happen."""
        import queue
        import threading

        q: queue.Queue = queue.Queue()
        box: dict = {}

        def work(tmp: str) -> None:
            try:
                box["result"] = run(req.query, cfg, tmp, on_event=q.put)
            except Exception as exc:  # noqa: BLE001
                box["error"] = exc
            finally:
                q.put(None)

        yield _sse({"type": "start", "model": cfg.model})
        result = None
        try:
            with tempfile.TemporaryDirectory() as tmp:
                threading.Thread(target=work, args=(tmp,), daemon=True).start()
                while (e := q.get()) is not None:
                    yield _sse(e)
                if "error" in box:
                    raise box["error"]
                result = box["result"]
                from hea.verify import grade

                docs = evidence.load(Path(result.run_dir) / "evidence.jsonl")
                answer = result.answer or {}
                checks = verify_claims(answer, docs)
                claims = [{**c, **chk, "excerpt": (docs.get(c.get("source_id", "")) or {}).get("text", "")[:600]}
                          for c, chk in zip(answer.get("claims", []), checks, strict=False)]
                graded = grade({"id": "live"}, result.answer, docs)
                yield _sse({"type": "result", "answer": result.answer, "claims": claims, "error": result.error,
                            "invented_nct_ids": graded["hallucinated_ncts"], "usage": result.usage,
                            "cost_usd": result.cost_usd_list_price, "latency_s": result.latency_s,
                            "skills_loaded": result.skills_loaded})
        except Exception as exc:  # noqa: BLE001  (reported to the client as a terminal event)
            log.exception(json.dumps({"event": "agent_error"}))
            yield _sse({"type": "error", "detail": f"agent failed: {type(exc).__name__}"})
        finally:
            spent = cost_usd(cfg.model, result.usage) if result and result.usage else 0.0
            _limiter().settle(day, worst, spent or 0.0)

    return StreamingResponse(events(), media_type="text/event-stream")


def _sse(event: dict) -> str:
    return f"event: {event['type']}\ndata: {json.dumps(event, default=str)}\n\n"


def main() -> None:
    import uvicorn

    uvicorn.run("hea.server:app", host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8000")))
