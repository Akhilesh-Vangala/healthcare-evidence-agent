import { useEffect, useState } from "react";

/** Hash routing with query state: `#check?source_id=...&quote=...`. Every page and input is a shareable URL, and the
 * browser's back button walks through them. */
export type Page = "overview" | "ask" | "explorer" | "check" | "study" | "runs";
export const PAGES: Page[] = ["overview", "ask", "explorer", "check", "study", "runs"];

export type Route = { page: Page; params: URLSearchParams };

export function parse(hash: string = location.hash): Route {
  const [path, query = ""] = hash.replace(/^#/, "").split("?");
  const page = (PAGES as string[]).includes(path) ? (path as Page) : "overview";
  return { page, params: new URLSearchParams(query) };
}

export function href(page: Page, params?: Record<string, string>): string {
  const q = params ? new URLSearchParams(params).toString() : "";
  return `#${page}${q ? `?${q}` : ""}`;
}

export function navigate(page: Page, params?: Record<string, string>, replace = false): void {
  const next = href(page, params);
  if (replace) history.replaceState(null, "", next);
  else location.hash = next.slice(1);
  if (replace) window.dispatchEvent(new HashChangeEvent("hashchange"));
}

export function useRoute(): Route {
  const [route, setRoute] = useState<Route>(() => parse());
  useEffect(() => {
    const on = () => setRoute(parse());
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return route;
}
