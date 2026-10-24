import { expect, test } from "@playwright/test";

const RUN = "20261023-164113";

test("home page shows the latest run's leaderboard", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Round robin from/ })).toBeVisible();
  const leaderboard = page.getByRole("region", { name: "Leaderboard" });
  await expect(leaderboard.getByRole("list", { name: "Models ranked by overall score" }).getByRole("listitem")).toHaveCount(3);
  await expect(page.getByRole("heading", { name: "Head to head" })).toBeVisible();
});

test("filters narrow the game list", async ({ page }) => {
  await page.goto(`/runs/${RUN}`);
  const games = page.getByRole("region", { name: "Games" });
  await expect(games.getByText("12 games")).toBeVisible();
  await games.getByText("DeepSeek V4.1 Flash", { exact: true }).first().click();
  await expect(games.getByText("8 games")).toBeVisible();
  await games.getByText("No deal", { exact: true }).first().click();
  await expect(games.getByText("No games match these filters yet.")).toBeVisible();
});

test("a game opens with its chart and transcript in sync", async ({ page }) => {
  await page.goto(`/runs/${RUN}`);
  await page.locator('a[href*="/games/used-car--"]').first().click();
  await expect(page.getByRole("heading", { name: "Used car", level: 1 })).toBeVisible();
  const transcript = page.getByRole("list", { name: "Transcript" });
  await expect(transcript.getByRole("listitem").first()).toBeVisible();

  const chart = page.getByRole("group", { name: /Offers over/ });
  await chart.focus();
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("ArrowRight");
  await expect(page.locator("#turn-2")).toHaveClass(/ring-2/);
});

test("the page never scrolls sideways", async ({ page }) => {
  for (const url of ["/", `/runs/${RUN}`]) {
    await page.goto(url);
    await expect(page.getByRole("heading", { name: "Leaderboard" })).toBeVisible();
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(overflow).toBe(0);
  }
});

test("unknown runs and games show the not-found page", async ({ page }) => {
  await page.goto("/runs/nope");
  await expect(page.getByRole("heading", { name: "Nothing here" })).toBeVisible();
  await page.goto(`/runs/${RUN}/games/..%2F..%2Fetc`);
  await expect(page.getByRole("heading", { name: "Nothing here" })).toBeVisible();
});
