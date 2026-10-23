from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from cmg_agent import __title__, __version__
from cmg_agent.agent import CMGDeepClaudeAgent
from cmg_agent.schemas import AgentRequest, WorkflowKind
from cmg_agent.skills.loader import skill_catalog

app = FastAPI(
    title=__title__,
    description=(
        "Healthcare Evidence Agent API (baseline pipeline). "
        "Primary agent path is Claude Code + MCP; see README."
    ),
    version=__version__,
)

agent = CMGDeepClaudeAgent(offline=os.getenv("CMG_OFFLINE", "").lower() in {"1", "true", "yes"})


@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "name": __title__,
        "version": __version__,
        "offline": agent.offline,
        "tools": len(agent.list_tools()),
        "skills": skill_catalog(),
    }


@app.get("/tools")
def tools() -> dict:
    return {"tools": agent.list_tools()}


@app.get("/skills")
def skills() -> dict:
    return {"skills": skill_catalog()}


@app.get("/workflows/{workflow}")
def workflow_config(workflow: WorkflowKind) -> dict:
    return agent.adapt_workflow(workflow)


@app.post("/v1/briefing")
def briefing(req: AgentRequest):
    report = agent.run(req)
    return JSONResponse(report.model_dump())
