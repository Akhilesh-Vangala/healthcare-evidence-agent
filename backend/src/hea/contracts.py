"""Typed contracts for agent answers and tool results.

The Claude Code runner already constrains answers with ``ANSWER_SCHEMA``.
This module is the Python-side source of truth: Pydantic models for validation
on replay/grade paths, plus JSON Schema export for MCP clients.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

AnswerStatus = Literal["answered", "not_found", "refused"]


class Claim(BaseModel):
    statement: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    quote: str = Field(min_length=1)

    @field_validator("quote")
    @classmethod
    def quote_not_empty_after_strip(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("quote must be non-empty")
        return v


class AgentAnswer(BaseModel):
    status: AnswerStatus
    summary: str
    claims: list[Claim] = Field(default_factory=list)
    needs_human_review: bool
    review_reasons: list[str] = Field(default_factory=list)


ANSWER_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "status": {"type": "string", "enum": ["answered", "not_found", "refused"]},
        "summary": {"type": "string"},
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "statement": {"type": "string"},
                    "source_id": {"type": "string"},
                    "quote": {"type": "string"},
                },
                "required": ["statement", "source_id", "quote"],
            },
        },
        "needs_human_review": {"type": "boolean"},
        "review_reasons": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["status", "summary", "claims", "needs_human_review", "review_reasons"],
}

TOOL_CONTRACTS: dict[str, dict[str, Any]] = {
    "fda_search_labels": {
        "args": {"drug": "str", "limit": "int?"},
        "returns": "candidates[{set_id, brand_name, generic_name, manufacturer, sections_available}]",
        "cites": False,
    },
    "fda_get_label_section": {
        "args": {"set_id": "str", "section": "str", "offset": "int?"},
        "returns": "paged section text with source_id",
        "cites": True,
    },
    "trials_search": {
        "args": {"intervention": "str", "condition": "str?", "phase": "str?", "recruiting_only": "bool?"},
        "returns": "trial summaries with NCT IDs",
        "cites": True,
    },
    "trials_get": {
        "args": {"nct_id": "str"},
        "returns": "single trial record",
        "cites": True,
    },
    "cms_ncd_search": {
        "args": {"keywords": "str", "max_results": "int?"},
        "returns": "NCD list hits",
        "cites": False,
    },
    "cms_ncd_get": {
        "args": {"ncd_id": "int", "version": "int?"},
        "returns": "NCD body with source_id",
        "cites": True,
    },
}


def parse_answer(payload: dict[str, Any] | None) -> AgentAnswer | None:
    if not payload:
        return None
    return AgentAnswer.model_validate(payload)
