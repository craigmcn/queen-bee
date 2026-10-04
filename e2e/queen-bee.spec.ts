import { test, expect, type Page } from "@playwright/test";

// The word list starts hidden (hints only), so tests of the list reveal it.
async function showWordList(page: Page) {
  await page.getByLabel(/hints only/i).uncheck();
}

test("finds words, pangrams, and hints for a puzzle", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Center letter").fill("t");
  await page.getByLabel("Outer letters").fill("acreln");
  await showWordList(page);

  const results = page.getByRole("region", { name: /words?$/ });
  await expect(results.getByText("tract", { exact: true })).toBeVisible();
  await expect(results.locator(".word--pangram")).toContainText(["central"]);

  await expect(page.getByRole("table")).toBeVisible();
  await expect(
    page.getByRole("region", { name: "Two-letter list" }).getByText(/^TR-\d+$/),
  ).toBeVisible();
});

test("types straight through from Center to Outer letters", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByLabel("Center letter").click();
  await page.keyboard.type("pkncaedx");

  await expect(page.getByLabel("Center letter")).toHaveValue("p");
  await expect(page.getByLabel("Outer letters")).toHaveValue("kncaed");
  await showWordList(page);
  await expect(page.locator(".word--pangram")).toContainText([
    "kneecapped",
    "pancaked",
  ]);
});

for (const colorScheme of ["light", "dark"] as const) {
  test(`keeps pangrams highlighted in ${colorScheme} mode`, async ({
    page,
  }) => {
    await page.emulateMedia({ colorScheme });
    await page.goto("/");
    await page.getByLabel("Center letter").fill("t");
    await page.getByLabel("Outer letters").fill("acreln");
    await showWordList(page);

    await expect(page.locator(".word--pangram").first()).toHaveCSS(
      "background-color",
      "rgb(247, 218, 33)",
    );
  });
}

test("hides the word list until Hints only is unchecked", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Center letter").fill("t");
  await page.getByLabel("Outer letters").fill("acreln");

  await expect(page.getByRole("table")).toBeVisible();
  await expect(page.getByText("tract", { exact: true })).toHaveCount(0);
  await showWordList(page);
  await expect(page.getByText("tract", { exact: true })).toBeVisible();
});
