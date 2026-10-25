/** Client for the agent service (backend/src/hea/server.py), served same-origin under /api. */

export type Health = {
  ok: boolean;
  version: string;
  tools: number;
  answering: { enabled: boolean; reason?: string; rate_per_hour?: number; daily_usd_cap?: number };
};

export type ToolSpec = { name: string; description: string; input_schema: { properties: Record<string, SchemaProp>; required?: string[] } };
export type SchemaProp = { type?: string; default?: unknown; description?: string };

export type EvidenceDoc = { source_id: string; kind: string; chars: number; brand_name?: string; section?: string; url?: string };
export type ToolCall = { tool: string; args: Record<string, unknown>; result: Record<string, unknown>; ms: number; evidence: EvidenceDoc[] };

export type CheckResult = {
  source_id: string;
  verified: boolean;
  reason: string;
  document_found: boolean;
  document_chars: number;
  excerpt: string;
  url?: string;
  normalized_quote: string;
  matched_prefix: number;
};

export type AgentEvent =
  | { type: "start"; model: string }
  | { type: "turn"; turn: number; ms: number; stop_reason: string; tool_calls: string[]; usage: Record<string, number> }
  | { type: "tool"; tool: string; input: Record<string, unknown>; ok: boolean; ms: number }
  | { type: "result"; answer: Answer | null; claims: Claim[]; error: string | null; invented_nct_ids: string[];
      usage: Record<string, number>; cost_usd: number | null; latency_s: number; skills_loaded: string[] }
  | { type: "error"; detail: string };

export type Answer = { status: string; summary: string; needs_human_review: boolean; review_reasons: string[] };
export type Claim = { statement: string; source_id: string; quote: string; verified: boolean; reason: string;
  kind?: string; brand_name?: string; section?: string; excerpt?: string };

export type RecordedRun = { id: string; title: string; query: string; model: string; recorded_at: string; commit: string; events: AgentEvent[] };

async function json<T>(url: string, body?: unknown): Promise<T> {
  const init: RequestInit = body === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
  const res = await fetch(url, init);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : res.statusText);
  return data as T;
}

export const api = {
  health: () => json<Health>("/api/health"),
  tools: () => json<{ tools: ToolSpec[] }>("/api/tools").then((d) => d.tools),
  call: (name: string, args: Record<string, unknown>) => json<ToolCall>(`/api/tools/${name}`, args),
  check: (source_id: string, quote: string) => json<CheckResult>("/api/check", { source_id, quote }),
  runs: () => json<{ runs: RecordedRun[] }>("/api/runs").then((d) => d.runs),
};

/** POST /api/agent/stream and hand each server-sent event to `onEvent` as it arrives. */
export async function streamAgent(query: string, onEvent: (e: AgentEvent) => void): Promise<void> {
  const res = await fetch("/api/agent/stream", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query }) });
  if (!res.ok || !res.body) {
    const data = await res.json().catch(() => ({}));
    throw new Error(typeof data.detail === "string" ? data.detail : res.statusText);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let cut: number;
    while ((cut = buffer.indexOf("\n\n")) >= 0) {
      const block = buffer.slice(0, cut);
      buffer = buffer.slice(cut + 2);
      const line = block.split("\n").find((l) => l.startsWith("data: "));
      if (line) onEvent(JSON.parse(line.slice(6)) as AgentEvent);
    }
  }
}

export const SOURCE_OF: Record<string, "fda" | "trials" | "cms" | "skill" | "submit"> = {
  fda_search_labels: "fda", fda_get_label_section: "fda", trials_search: "trials", trials_get: "trials",
  cms_ncd_search: "cms", cms_ncd_get: "cms", load_skill: "skill", submit_answer: "submit",
};
