import { expect, test } from "@playwright/test";

test("local preview opens the settings page and persists a text-size choice", async ({ page }) => {
  await page.goto("/settings");

  const sizeGroup = page.getByRole("group", { name: /Размер текста|Розмір тексту|Text size/i });
  await expect(sizeGroup).toBeVisible();
  const large = sizeGroup.getByRole("button").last();
  await large.click();
  await expect(large).toHaveAttribute("aria-pressed", "true");

  await page.reload();
  await expect(page.getByRole("group", { name: /Размер текста|Розмір тексту|Text size/i }).getByRole("button").last()).toHaveAttribute(
    "aria-pressed",
    "true",
  );
});
