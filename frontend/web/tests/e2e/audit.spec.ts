import { test, expect, type Page } from "@playwright/test";
async function openWorkspace(page: Page) {
  const email = `audit-${Date.now()}-${Math.random().toString(36).slice(2, 6)}@example.com`;
  await page.goto("/sign-up");
  await page.getByLabel("Full name").fill("Audit Reviewer");
  await page.getByLabel("Email address").fill(email);
  await page.getByLabel("Password", { exact: true }).fill("AuditReview123");
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await expect(page).toHaveURL(/sign-in\?created=1/);
  await page.getByLabel("Email address").fill(email);
  await page.getByLabel("Password", { exact: true }).fill("AuditReview123");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "A new chapter for your code." }),
  ).toBeVisible();
  await expect(page.getByText("API connected", { exact: true })).toBeVisible();
}
test("project URL and workspace agree after browser back navigation", async ({
  page,
}) => {
  await openWorkspace(page);
  await page.getByLabel("Project name").fill("Project A");
  await page
    .getByRole("button", { name: "Create project", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Project A", exact: true, level: 2 }),
  ).toBeVisible();
  await page.getByLabel("Project name").fill("Project B");
  await page
    .getByRole("button", { name: "Create project", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Project B", exact: true, level: 2 }),
  ).toBeVisible();
  const secondUrl = page.url();
  await page
    .locator(".project-list > li")
    .filter({
      has: page.getByRole("heading", {
        name: "Project A",
        exact: true,
        level: 3,
      }),
    })
    .getByRole("button", { name: "Open", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "From legacy to possibility." }),
  ).toBeVisible();
  await page
    .getByRole("navigation", { name: "Main", exact: true })
    .getByRole("link", { name: "Upload", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Project A", exact: true, level: 2 }),
  ).toBeVisible();
  await page.goBack();
  await expect(
    page.getByRole("heading", { name: "From legacy to possibility." }),
  ).toBeVisible();
  await page.goBack();
  await expect(page).toHaveURL(secondUrl);
  await expect(
    page.getByRole("heading", { name: "Project B", exact: true, level: 2 }),
  ).toBeVisible();
});
test("offline refresh preserves login, retry restores it, and sign-out syncs between tabs", async ({
  page,
  context,
}) => {
  await openWorkspace(page);
  const token = await page.evaluate(() =>
    localStorage.getItem("legacylift-token"),
  );
  await page.route("**/api/auth/me", (route) => route.abort());
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Reconnect saved session" }),
  ).toBeVisible();
  expect(
    await page.evaluate(() => localStorage.getItem("legacylift-token")),
  ).toBe(token);
  await page.unroute("**/api/auth/me");
  await page.getByRole("button", { name: "Reconnect saved session" }).click();
  await expect(
    page.getByRole("heading", { name: "A new chapter for your code." }),
  ).toBeVisible();
  const other = await context.newPage();
  await other.goto("/upload");
  await expect(
    other.getByRole("heading", { name: "A new chapter for your code." }),
  ).toBeVisible();
  await other.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page).toHaveURL(/sign-in/);
  expect(
    await page.evaluate(() => localStorage.getItem("legacylift-token")),
  ).toBeNull();
  await other.close();
});
test("COBOL line numbers scroll with the source and keyboard scrolling works", async ({
  page,
}) => {
  await openWorkspace(page);
  await page
    .getByRole("button", { name: "Load demo project", exact: true })
    .click();
  await page.getByRole("link", { name: "Continue to Convert" }).click();
  const source = page.getByRole("region", {
    name: "COBOL source code",
    exact: true,
  });
  await expect(source).toBeVisible();
  const scroller = source.locator(".cm-scroller");
  const before = await scroller.evaluate((element) => ({
    number: element
      .querySelector(".cm-lineNumbers .cm-gutterElement:not(:first-child)")!
      .getBoundingClientRect().top,
    code: element.querySelector(".cm-content .cm-line")!.getBoundingClientRect()
      .top,
  }));
  await scroller.evaluate((element) => {
    element.scrollTop = 250;
  });
  const after = await scroller.evaluate((element) => ({
    number: element
      .querySelector(".cm-lineNumbers .cm-gutterElement:not(:first-child)")!
      .getBoundingClientRect().top,
    code: element.querySelector(".cm-content .cm-line")!.getBoundingClientRect()
      .top,
    scroll: element.scrollTop,
  }));
  expect(after.scroll).toBe(250);
  expect(
    Math.abs(before.number - after.number - (before.code - after.code)),
  ).toBeLessThan(1);
  // PageDown moves the caret one page from where it is (line 1) and scrolls to
  // follow it, so start from the top of the file.
  await scroller.evaluate((element) => {
    element.scrollTop = 0;
  });
  await page.getByLabel("Read original COBOL", { exact: true }).focus();
  await page.keyboard.press("PageDown");
  await expect
    .poll(() => scroller.evaluate((element) => element.scrollTop))
    .toBeGreaterThan(0);
});
test("a full 100-file upload passes through the real Next proxy and rejects file 101", async ({
  page,
}) => {
  test.setTimeout(120000);
  await openWorkspace(page);
  await page.getByLabel("Project name").fill("100-file audit");
  await page
    .getByRole("button", { name: "Create project", exact: true })
    .click();
  await expect(
    page.getByRole("heading", {
      name: "100-file audit",
      exact: true,
      level: 2,
    }),
  ).toBeVisible();
  const source = Buffer.from(
    '       IDENTIFICATION DIVISION.\n       PROGRAM-ID. AUDIT.\n       PROCEDURE DIVISION.\n           DISPLAY "AUDIT"\n           STOP RUN.\n',
  );
  const files = [
    { name: "audit.cbl", mimeType: "text/plain", buffer: source },
    ...Array.from({ length: 99 }, (_, i) => ({
      name: `data-${i}.dat`,
      mimeType: "text/plain",
      buffer: Buffer.alloc(200000, "0"),
    })),
  ];
  await page.locator('input[type="file"]').setInputFiles(files);
  await expect(page.locator(".file-list-summary")).toContainText("100 files", {
    timeout: 60000,
  });
  await expect(page.locator('input[type="file"]')).toBeEnabled();
  await page.locator('input[type="file"]').setInputFiles({
    name: "extra.dat",
    mimeType: "text/plain",
    buffer: Buffer.from("extra"),
  });
  await expect(page.locator(".notice[role=alert]")).toContainText(
    "already has 100",
  );
  await expect(page.locator(".file-list li")).toHaveCount(100);
});
