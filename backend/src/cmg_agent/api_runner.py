"""Run the agent directly on the Anthropic Messages API, as a second runtime next to headless Claude Code.

Everything the study measures is held fixed so a difference can only come from the runtime:
  * the same system prompt and answer schema (claude_runner.SYSTEM_PROMPT, ANSWER_SCHEMA),
  * the same six tools, taken from the MCP server's own registry (mcp_server.server) and called in-process,
  * the same Agent Skills text (agent/workspace/.claude/skills), loaded on demand through a load_skill tool the way
    Claude Code's Skill tool works: the model sees each skill's name and description, and reads the body when needed,
  * the same per-run evidence log, verifier and grader.

The loop is a plain tool-use loop on the official SDK: prompt caching on every request (top-level cache_control, so
the system prompt, tools and growing transcript are cached), adaptive thinking at the study's effort level, thinking
blocks passed back unchanged, refusal and max_tokens stop reasons handled, and a hard USD cap that admits each call
against its worst case before it is sent.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

from cmg_agent import evidence
from cmg_agent.claude_runner import ANSWER_SCHEMA, CLOSED_BOOK_PROMPT, ROOT, SYSTEM_PROMPT, RunResult
from cmg_agent.spend import SpendCap

SKILLS_DIR = ROOT / "agent" / "workspace" / ".claude" / "skills"
MCP_PREFIX = "mcp__cmg__"  # Claude Code's name for these tools; the grader counts tool calls by this prefix

# USD per 1M tokens (Anthropic list prices). Cache reads bill at 0.1x input, 5-minute cache writes at 1.25x.
PRICES = {"claude-haiku-5-5": (0.10, 0.50), "claude-sonnet-5-5": (2.00, 10.00), "claude-opus-5-5": (4.00, 20.00)}
CACHE_READ, CACHE_WRITE = 0.1, 1.25


@dataclass
class ApiConfig:
    name: str = "C_api_tools_skills"
    model: str = "claude-haiku-5-5"
    use_tools: bool = True
    use_skills: bool = True
    effort: str = "medium"  # the study's Claude Code runs used --effort medium
    max_turns: int = 16
    max_tokens: int = 8000


def load_skills(directory: Path = SKILLS_DIR) -> dict[str, dict[str, str]]:
    """{name: {description, body}} parsed from each SKILL.md's front matter."""
    out = {}
    for path in sorted(directory.glob("*/SKILL.md")):
        text = path.read_text(encoding="utf-8")
        m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
        meta = dict(line.split(":", 1) for line in m.group(1).splitlines() if ":" in line) if m else {}
        name = meta.get("name", path.parent.name).strip()
        out[name] = {"description": meta.get("description", "").strip(), "body": (m.group(2) if m else text).strip()}
    return out


def _submit_tool() -> dict:
    schema = json.loads(json.dumps(ANSWER_SCHEMA))
    schema["additionalProperties"] = False
    schema["properties"]["claims"]["items"]["additionalProperties"] = False
    return {"name": "submit_answer", "description": "Submit the final answer. Call exactly once, as your last action.",
            "input_schema": schema, "strict": True}


async def _mcp_tools() -> list[dict]:
    from cmg_agent.mcp_server import server

    return [{"name": t.name, "description": t.description or "", "input_schema": _clean(t.input_schema)}
            for t in await server.list_tools()]


def _clean(schema: dict) -> dict:
    """Drop pydantic titles; the model sees the MCP server's descriptions and types."""
    if isinstance(schema, dict):
        return {k: _clean(v) for k, v in schema.items() if k != "title"}
    return schema


async def _call_mcp(name: str, args: dict) -> tuple[str, bool]:
    from cmg_agent.mcp_server import server

    result = await server.call_tool(name, args)
    text = "\n".join(getattr(c, "text", "") for c in getattr(result, "content", []) or [])
    return text, bool(getattr(result, "is_error", False))


def cost_usd(model: str, usage: dict[str, int]) -> float | None:
    if model not in PRICES:
        return None
    p_in, p_out = PRICES[model]
    return round((usage["input_tokens"] * p_in + usage["cache_read_input_tokens"] * p_in * CACHE_READ
                  + usage["cache_creation_input_tokens"] * p_in * CACHE_WRITE + usage["output_tokens"] * p_out) / 1e6, 6)


def _system(cfg: ApiConfig, skills: dict) -> str:
    if not cfg.use_tools:
        return CLOSED_BOOK_PROMPT + "\nWhen you are done, call submit_answer exactly once."
    text = SYSTEM_PROMPT
    if cfg.use_skills:
        index = "\n".join(f"- {n}: {s['description']}" for n, s in skills.items())
        text += f"\n\nSkills available (read one with load_skill before relying on it):\n{index}"
    return text + "\nWhen you are done, call submit_answer exactly once."


def run(
    query: str,
    cfg: ApiConfig,
    runs_dir: Path | str = ROOT / "runs",
    client=None,
    cap: SpendCap | None = None,
    on_event: Callable[[dict], None] | None = None,
) -> RunResult:
    import anthropic

    client = client or anthropic.Anthropic(max_retries=3)
    run_id = f"{cfg.name}-{uuid.uuid4().hex[:8]}"
    run_dir = Path(runs_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = run_dir / "evidence.jsonl"
    evidence_path.touch()
    result = RunResult(run_id=run_id, config={**asdict(cfg), "runtime": "anthropic_api"}, query=query, answer=None,
                       run_dir=str(run_dir))
    emit = on_event or (lambda e: None)
    skills = load_skills() if cfg.use_skills else {}
    tools = (asyncio.run(_mcp_tools()) if cfg.use_tools else []) + [_submit_tool()]
    if skills:
        tools.append({"name": "load_skill", "description": "Read the full instructions of one skill.",
                      "input_schema": {"type": "object", "properties": {"name": {"type": "string", "enum": list(skills)}},
                                       "required": ["name"], "additionalProperties": False}})
    system = _system(cfg, skills)
    messages: list[dict] = [{"role": "user", "content": query}]
    usage = {"input_tokens": 0, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0, "output_tokens": 0}
    start, nudged = time.perf_counter(), False
    with evidence.bound_to(evidence_path):
        for turn in range(1, cfg.max_turns + 1):
            if cap:
                est_in = (len(system) + len(json.dumps(tools)) + len(json.dumps(messages, default=str))) // 3
                cap.admit(cfg.model, est_in, cfg.max_tokens)
            t0 = time.perf_counter()
            try:
                resp = client.messages.create(
                    model=cfg.model, max_tokens=cfg.max_tokens, system=system, tools=tools, messages=messages,
                    output_config={"effort": cfg.effort}, cache_control={"type": "ephemeral"},
                )
            except anthropic.APIStatusError as exc:
                result.error = f"api_error {exc.status_code}: {str(exc.message)[:300]}"
                break
            except anthropic.APIConnectionError as exc:
                result.error = f"connection_error: {exc}"
                break
            u = resp.usage
            step_usage = {"input_tokens": u.input_tokens or 0, "cache_read_input_tokens": u.cache_read_input_tokens or 0,
                          "cache_creation_input_tokens": u.cache_creation_input_tokens or 0,
                          "output_tokens": u.output_tokens or 0}
            for k, v in step_usage.items():
                usage[k] += v
            if cap:
                cap.record(cfg.model, step_usage, cost_usd(cfg.model, step_usage))
            result.num_turns = turn
            calls = [b for b in resp.content if b.type == "tool_use"]
            emit({"type": "turn", "turn": turn, "ms": round(1000 * (time.perf_counter() - t0)),
                  "stop_reason": resp.stop_reason, "tool_calls": [c.name for c in calls], "usage": step_usage})
            messages.append({"role": "assistant", "content": [b.model_dump(exclude_none=True) for b in resp.content]})
            if resp.stop_reason == "refusal":
                result.error = "refusal: the model declined the request"
                break
            if resp.stop_reason == "max_tokens":
                result.error = f"max_tokens reached at turn {turn}"
                break
            if not calls:
                if nudged:
                    result.error = "no submit_answer"
                    break
                nudged = True
                messages.append({"role": "user", "content": "Call submit_answer now with your final answer."})
                continue
            results = []
            for c in calls:
                t1, ok, text = time.perf_counter(), True, ""
                if c.name == "submit_answer":
                    result.answer, text = dict(c.input), "received"
                elif c.name == "load_skill":
                    name = str(c.input.get("name", ""))
                    ok = name in skills
                    text = skills[name]["body"] if ok else f"unknown skill {name!r}"
                    if ok:
                        result.skills_loaded.append(name)
                else:
                    try:
                        text, is_error = asyncio.run(_call_mcp(c.name, dict(c.input)))
                        ok = not is_error
                    except Exception as exc:  # noqa: BLE001  (tool failures go back to the model as tool errors)
                        ok, text = False, f"{type(exc).__name__}: {exc}"[:500]
                    result.tool_calls.append({"tool": MCP_PREFIX + c.name, "input": dict(c.input), "ok": ok})
                if c.name != "submit_answer":
                    emit({"type": "tool", "tool": c.name, "input": dict(c.input), "ok": ok,
                          "ms": round(1000 * (time.perf_counter() - t1))})
                results.append({"type": "tool_result", "tool_use_id": c.id, "content": text, "is_error": not ok})
            messages.append({"role": "user", "content": results})
            if result.answer is not None:
                break
        else:
            result.error = result.error or f"no answer within {cfg.max_turns} turns"
    result.latency_s = round(time.perf_counter() - start, 2)
    result.usage = usage
    result.cost_usd_list_price = cost_usd(cfg.model, usage)
    (run_dir / "transcript.json").write_text(json.dumps({"system": system, "messages": messages}, indent=2, default=str))
    (run_dir / "result.json").write_text(json.dumps(asdict(result), indent=2, default=str))
    return result
