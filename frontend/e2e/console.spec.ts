import { readFileSync } from "node:fs";
import AxeBuilder from "@axe-core/playwright";
import { type Page, expect, test } from "@playwright/test";

const fixture = (name: string) => JSON.parse(readFileSync(new URL(`./fixtures/${name}.json`, import.meta.url), "utf8"));
const [check_bad, check_ok, health, runs, search, section, tools] =
  ["check_bad", "check_ok", "health", "runs", "search", "section", "tools"].map(fixture);

async function mockApi(page: Page) {
  await page.route("**/api/health", (r) => r.fulfill({ json: health }));
  await page.route("**/api/tools", (r) => r.fulfill({ json: tools }));
  await page.route("**/api/runs", (r) => r.fulfill({ json: runs }));
  await page.route("**/api/tools/fda_search_labels", (r) => r.fulfill({ json: search }));
  await page.route("**/api/tools/fda_get_label_section", (r) => r.fulfill({ json: section }));
  await page.route("**/api/check", async (r) => {
    const body = r.request().postDataJSON() as { quote: string };
    await r.fulfill({ json: body.quote.includes("activating") ? check_bad : check_ok });
  });
}

test.beforeEach(async ({ page }) => { await mockApi(page); });

test("overview shows the measured headline and the tab bar is keyboard navigable @mobile", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("cannot cite a document");
  await expect(page.getByRole("region", { name: "Headline results" })).toContainText("95%");
  await page.getByRole("tab", { name: "Overview" }).focus();
  await page.keyboard.press("ArrowRight");
  await expect(page.getByRole("tab", { name: "Ask the agent" })).toHaveAttribute("aria-selected", "true");
  await expect(page).toHaveURL(/#ask/);
});

test("replaying a recorded run streams the trace and ends in a graded answer with verified claims", async ({ page }) => {
  await page.goto("/#ask");
  await page.getByRole("button", { name: /Compare two boxed warnings/ }).click();
  await expect(page.getByRole("heading", { name: "Graded answer" })).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText(/claims verified/).first()).toBeVisible();
  await expect(page.getByText("0 invented trial IDs")).toBeVisible();
  await expect(page.locator(".claim.ok").first()).toBeVisible();
  await expect(page).toHaveURL(/#ask\?run=C01/);
});

test("a citation in an answer opens the checker pre-filled and verifies it", async ({ page }) => {
  await page.goto("/#ask?run=C01");
  await expect(page.getByRole("heading", { name: "Graded answer" })).toBeVisible({ timeout: 15_000 });
  await page.locator(".claim header a").first().click();
  await expect(page).toHaveURL(/#check\?source_id=/);
  await expect(page.locator(".stamp")).toBeVisible();
});

test("evidence explorer runs the starter search and opens a label section from a result", async ({ page }) => {
  await page.goto("/#explorer");
  await expect(page.locator(".cand").first()).toContainText("KEYTRUDA");
  await page.locator(".cand").filter({ hasText: /^KEYTRUDA PEMBROLIZUMAB/ }).getByRole("button", { name: "indications and usage" }).click();
  await expect(page.locator("pre.doc").first()).toContainText("INDICATIONS AND USAGE");
  await expect(page.locator(".evid a").first()).toHaveText(/^fda:.*:indications_and_usage$/);
});

test("citation check rejects a one-word change and shows where it diverges", async ({ page }) => {
  await page.goto("/#check");
  await page.getByRole("button", { name: "Change one word" }).click();
  await expect(page.locator(".stamp")).toHaveText("REJECTED");
  await expect(page.locator(".diff .x")).toContainText("activating");
});

test("study shows the cross-runtime check and the red-team suite", async ({ page }) => {
  await page.goto("/#study");
  await expect(page.getByRole("heading", { name: /Cross-runtime check/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: /Red-team suite/ })).toBeVisible();
});

test("theme toggle switches and persists across reloads", async ({ page }) => {
  await page.goto("/");
  const before = await page.locator("html").getAttribute("data-theme");
  await page.getByRole("button", { name: /Switch to/ }).click();
  const after = await page.locator("html").getAttribute("data-theme");
  expect(after).not.toBe(before);
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", after as string);
});

for (const path of ["/", "/#ask", "/#explorer", "/#check", "/#study", "/#runs"]) {
  for (const theme of ["dark", "light"]) {
    test(`no serious accessibility violations on ${path} (${theme})`, async ({ page }) => {
      await page.addInitScript((t) => localStorage.setItem("hea.theme", t), theme);
      await page.goto(path);
      await page.waitForLoadState("networkidle");
      const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
      const serious = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
      expect(serious.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).slice(0, 3).join(", ")}`)).toEqual([]);
    });
  }
}
