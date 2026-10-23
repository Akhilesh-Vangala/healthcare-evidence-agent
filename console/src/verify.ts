/** Same quote rule as src/cmg_agent/verify.py and evidence.normalize. */

const QUOTE_MAP: Record<string, string> = {
  "\u2018": "'",
  "\u2019": "'",
  "\u201c": '"',
  "\u201d": '"',
  "\u2013": "-",
  "\u2014": "-",
};

export function normalize(text: string): string {
  let out = "";
  for (const ch of text) out += QUOTE_MAP[ch] ?? ch;
  return out.replace(/\s+/g, " ").trim().toLowerCase();
}

export type CheckReason = "ok" | "quote_too_short" | "quote_not_in_source" | "unknown_source_id";

export function checkClaim(source: string, quote: string, retrieved: boolean): CheckReason {
  if (!retrieved) return "unknown_source_id";
  const normalized = normalize(quote);
  if (normalized.length < 20) return "quote_too_short";
  if (!normalize(source).includes(normalized)) return "quote_not_in_source";
  return "ok";
}
