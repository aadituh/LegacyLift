import { test, expect, type Page, type Locator } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import fs from "node:fs/promises";
const unique = () =>
  `reviewer-${Date.now()}-${Math.random().toString(36).slice(2, 7)}@example.com`;
async function copyCode(page: Page, button?: Locator) {
  await page.context().grantPermissions(["clipboard-read", "clipboard-write"]);
  await (
    button ?? page.getByRole("button", { name: "Copy Python", exact: true })
  ).click();
  return page.evaluate(async () =>
    (await navigator.clipboard.readText()).replace(/\r\n/g, "\n"),
  );
}
async function replaceCode(page: Page, editor: Locator, text: string) {
  await page.context().grantPermissions(["clipboard-read", "clipboard-write"]);
  await page.evaluate((value) => navigator.clipboard.writeText(value), text);
  await editor.click();
  await editor.press("Control+A");
  await editor.press("Control+V");
}
async function signUp(page: Page) {
  const email = unique();
  await page.goto("/sign-up");
  await page.getByLabel("Full name").fill("Frontend Reviewer");
  await page.getByLabel("Email address").fill(email);
  await page.getByLabel("Password", { exact: true }).fill("ReviewTest123");
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await expect(page).toHaveURL(/sign-in\?created=1/);
  await page.getByLabel("Email address").fill(email);
  await page.getByLabel("Password", { exact: true }).fill("ReviewTest123");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "A new chapter for your code." }),
  ).toBeVisible();
  await expect(page.getByText("API connected", { exact: true })).toBeVisible();
}
async function demo(page: Page) {
  await page
    .getByRole("button", { name: "Load demo project", exact: true })
    .click();
  await expect(
    page.getByRole("link", { name: "Continue to Convert" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Continue to Convert" }).click();
  await expect(
    page.getByRole("heading", { name: "From legacy to possibility." }),
  ).toBeVisible();
}
async function screenshot(page: Page, name: string) {
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
  await fs.mkdir("test-results/screenshots", { recursive: true });
  await page.screenshot({
    path: `test-results/screenshots/${name}.png`,
    fullPage: true,
  });
}
async function accessible(page: Page) {
  // Theme changes fade button colours for 150 ms; scan the settled colours.
  await page.waitForFunction(() =>
    document
      .getAnimations()
      .every((a) => !(a instanceof CSSTransition) || a.playState !== "running"),
  );
  const result = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  expect(
    result.violations.map((v) => ({
      id: v.id,
      targets: v.nodes.map((n) => n.target),
    })),
  ).toEqual([]);
}
test("account, demo, conversion, local edits, export, restore, sign out", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/sign-in");
  await screenshot(page, "sign-in");
  await accessible(page);
  await signUp(page);
  await screenshot(page, "upload-empty");
  await accessible(page);
  await demo(page);
  await page
    .getByRole("button", { name: "Convert project", exact: true })
    .click();
  await expect(page.getByLabel("Edit BANKMAIN.py")).toBeVisible();
  await expect(
    page.getByText("Not compared", { exact: true }).first(),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: /Dependencies for BANKMAIN/ }),
  ).toBeVisible();
  await screenshot(page, "convert");
  await accessible(page);
  const editor = page.getByLabel("Edit BANKMAIN.py");
  const original = await copyCode(page);
  await replaceCode(page, editor, original + "\n# local review edit\n");
  await expect(page.getByText("Edited", { exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Go to Export" }).click();
  await expect(
    page.getByRole("heading", { name: "Downloads", exact: true }),
  ).toBeVisible();
  const downloadPromise = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "Download .py BANKMAIN.py", exact: true })
    .click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe("BANKMAIN.py");
  expect(await fs.readFile((await download.path())!, "utf8")).toContain(
    "# local review edit",
  );
  const csvPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download .csv" }).click();
  const csv = await csvPromise;
  expect(await fs.readFile((await csv.path())!, "utf8")).toContain(
    "not_verified",
  );
  await screenshot(page, "export");
  await accessible(page);
  await page.getByRole("link", { name: "Back to Convert" }).click();
  await expect
    .poll(() => copyCode(page))
    .toBe(original + "\n# local review edit\n");
  page.once("dialog", (dialog) => dialog.accept());
  await page.reload();
  await expect(page.getByLabel("Edit BANKMAIN.py")).toBeVisible();
  await expect.poll(() => copyCode(page)).toBe(original);
  await expect(
    page.getByText("Not compared", { exact: true }).first(),
  ).toBeVisible();
  await page.getByRole("button", { name: "Review with AI" }).click();
  await expect(page.locator(".notice[role=alert]")).toContainText(
    /Gemini|API key|GEMINI/i,
  );
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page).toHaveURL(/sign-in/);
  expect(errors).toEqual([]);
});
test("create, upload, analyze, delete file, project not found, and project removal", async ({
  page,
}) => {
  await signUp(page);
  await page.getByLabel("Project name").fill("Payroll");
  await page
    .getByRole("button", { name: "Create project", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Payroll", exact: true, level: 2 }),
  ).toBeVisible();
  await page.locator('input[type="file"]').setInputFiles({
    name: "payroll.cbl",
    mimeType: "text/plain",
    buffer: Buffer.from(
      '       IDENTIFICATION DIVISION.\n       PROGRAM-ID. PAYROLL.\n       PROCEDURE DIVISION.\n           DISPLAY "PAYROLL"\n           STOP RUN.\n',
    ),
  });
  await expect(
    page.getByRole("link", { name: "Continue to Convert" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Continue to Convert" }).click();
  await page
    .getByRole("button", { name: "Convert project", exact: true })
    .click();
  await expect(page.getByLabel("Edit payroll.py")).toBeVisible();
  await page
    .getByRole("navigation", { name: "Main", exact: true })
    .getByRole("link", { name: "Upload", exact: true })
    .click();
  page.once("dialog", (dialog) => dialog.accept());
  await page
    .getByRole("button", { name: "Remove payroll.cbl", exact: true })
    .click();
  await expect(
    page.getByRole("link", { name: "Continue to Convert" }),
  ).toHaveCount(0);
  await page.goto("/convert?project=999999");
  await expect(
    page.getByRole("heading", { name: "Project not found" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Back to Upload" }).click();
  page.once("dialog", (dialog) => dialog.accept());
  await page
    .getByRole("button", { name: "Remove project Payroll", exact: true })
    .click();
  await expect(
    page.getByText("No saved projects yet. Create your first project above."),
  ).toBeVisible();
});
test("batch conversion, edited download, and upload validation", async ({
  page,
}) => {
  await signUp(page);
  await page
    .getByRole("link", { name: "Batch conversion", exact: true })
    .click();
  await page.getByRole("button", { name: "Load small sample" }).click();
  await expect(
    page.getByRole("button", { name: "Convert files", exact: true }),
  ).toBeEnabled();
  await page
    .getByRole("button", { name: "Convert files", exact: true })
    .click();
  const editor = page.getByLabel(/Edit hello_team.py/i);
  await expect(editor).toBeVisible();
  await replaceCode(page, editor, "# edited batch file\n");
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: /Download .py/ }).click();
  expect(await fs.readFile((await (await download).path())!, "utf8")).toBe(
    "# edited batch file\n",
  );
  await screenshot(page, "batch");
  await accessible(page);
  await page.locator('input[type="file"]').setInputFiles({
    name: "wrong.cpy",
    mimeType: "text/plain",
    buffer: Buffer.from("COPY TEST."),
  });
  await expect(page.locator(".notice[role=alert]")).toContainText(
    ".cbl or .cob",
  );
});
test("mobile and projector widths fit, and reduced motion stays usable", async ({
  page,
}) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await signUp(page);
  await screenshot(page, "mobile-upload");
  await accessible(page);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await demo(page);
  await page
    .getByRole("button", { name: "Convert project", exact: true })
    .click();
  await expect(page.getByLabel("Edit BANKMAIN.py")).toBeVisible();
  await expect(
    page.getByText("Not compared", { exact: true }).first(),
  ).toBeVisible();
  await screenshot(page, "mobile-convert");
  await accessible(page);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("link", { name: "Go to Export" }).click();
  await screenshot(page, "mobile-export");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  for (const size of [
    { width: 1280, height: 720 },
    { width: 1920, height: 1080 },
  ]) {
    await page.setViewportSize(size);
    await screenshot(page, `export-${size.width}`);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
  }
});
test("verification matches, mismatches, AI findings, and report stay in sync", async ({
  page,
}) => {
  await signUp(page);
  await demo(page);
  await page.route("**/api/projects/*/verify", async (route) =>
    route.fulfill({
      json: {
        project_id: "1",
        run_id: "99",
        status: "mismatch",
        passed: false,
        note: "Outputs differed.",
        files: [
          {
            source_name: "BANKMAIN.cbl",
            python_name: "BANKMAIN.py",
            equivalent: false,
            cobol_stdout: "EXPECTED\n",
            python_stdout: "ACTUAL\n",
            diff: "-EXPECTED\n+ACTUAL",
            error: null,
          },
        ],
      },
    }),
  );
  await page
    .getByRole("button", { name: "Convert project", exact: true })
    .click();
  await expect(
    page.getByText("Mismatch", { exact: true }).first(),
  ).toBeVisible();
  await expect(page.getByText("1 of 1 output lines differ")).toBeVisible();
  await page.getByRole("button", { name: "Audit report", exact: true }).click();
  await expect(page.getByText("EXPECTED", { exact: true })).toBeVisible();
  await expect(page.getByText("Differs", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Side by side", exact: true }).click();
  await page.route("**/api/projects/*/ai-review", async (route) =>
    route.fulfill({
      json: {
        project_id: "1",
        run_id: "100",
        status: "concerns",
        model: "Test review fixture",
        files: [
          {
            source_name: "BANKMAIN.cbl",
            python_name: "BANKMAIN.py",
            concerns: [
              {
                cobol_lines: [3],
                python_lines: [4],
                detail: "Check the rounding rule.",
              },
            ],
            matches: [],
          },
        ],
      },
    }),
  );
  await page.getByRole("button", { name: "Review with AI" }).click();
  await expect(page.getByText("Check the rounding rule.")).toBeVisible();
  await accessible(page);
  await page.route("**/api/projects/*/verify", async (route) =>
    route.fulfill({
      json: {
        project_id: "1",
        run_id: "101",
        status: "verified",
        passed: true,
        note: "Outputs match.",
        files: [
          {
            source_name: "BANKMAIN.cbl",
            python_name: "BANKMAIN.py",
            equivalent: true,
            cobol_stdout: "SAME\n",
            python_stdout: "SAME\n",
            diff: "",
            error: null,
          },
        ],
      },
    }),
  );
  await page.getByRole("button", { name: "Run verification again" }).click();
  await expect(
    page.getByText("Verified", { exact: true }).first(),
  ).toBeVisible();
  await expect(page.getByText("0 of 1 output lines differ")).toBeVisible();
});
test("offline connection, recovery, invalid credentials, auth guard, and unknown route", async ({
  page,
}) => {
  await page.goto("/upload");
  await expect(page).toHaveURL(/sign-in/);
  await page.getByLabel("Email address").fill("missing@example.com");
  await page.getByLabel("Password", { exact: true }).fill("WrongPassword1");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.locator(".notice[role=alert]")).toHaveText(
    "Invalid email or password.",
  );
  await page.route("**/health", (route) => route.abort());
  await signUpWithoutReady(page);
  await expect(page.getByText("API offline", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Create project", exact: true }),
  ).toBeDisabled();
  await screenshot(page, "offline");
  await page.unroute("**/health");
  await page.getByRole("button", { name: "Retry API connection" }).click();
  await expect(page.getByText("API connected", { exact: true })).toBeVisible();
  await page.goto("/page-does-not-exist");
  await expect(
    page.getByRole("heading", { name: "This page isn’t here." }),
  ).toBeVisible();
});
async function signUpWithoutReady(page: Page) {
  const email = unique();
  await page.goto("/sign-up");
  await page.getByLabel("Full name").fill("Offline Reviewer");
  await page.getByLabel("Email address").fill(email);
  await page.getByLabel("Password", { exact: true }).fill("ReviewTest123");
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await expect(page).toHaveURL(/sign-in\?created=1/);
  await page.getByLabel("Email address").fill(email);
  await page.getByLabel("Password", { exact: true }).fill("ReviewTest123");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "A new chapter for your code." }),
  ).toBeVisible();
}

test("empty project supports upload, source previews, conversion and exact export previews", async ({
  page,
}) => {
  await signUp(page);
  await page.getByLabel("Project name").fill("Direct upload");
  await page
    .getByRole("button", { name: "Create project", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Direct upload", exact: true, level: 2 }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Convert", exact: true }).click();
  await expect(
    page.getByText("Add COBOL files to begin", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("region", { name: "COBOL source code", exact: true }),
  ).toHaveCount(0);
  const source =
    "       IDENTIFICATION DIVISION.\n       PROGRAM-ID. PAYROLL.\n       DATA DIVISION.\n       WORKING-STORAGE SECTION.\n       COPY SHARED.\n       PROCEDURE DIVISION.\n           PERFORM SHOW-TOTAL\n           STOP RUN.\n       SHOW-TOTAL.\n           DISPLAY WS-TOTAL.\n";
  await page.getByLabel("Add files").setInputFiles([
    {
      name: "payroll.cbl",
      mimeType: "text/plain",
      buffer: Buffer.from(source),
    },
    {
      name: "SHARED.cpy",
      mimeType: "text/plain",
      buffer: Buffer.from("       01 WS-TOTAL PIC ZZ9.\n"),
    },
    {
      name: "input.dat",
      mimeType: "text/plain",
      buffer: Buffer.from("00100\n"),
    },
  ]);
  await page
    .getByText("Browse, preview & manage 3 files", { exact: true })
    .click();
  await expect(page.getByText("3 files", { exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: "Preview SHARED.cpy", exact: true })
    .click();
  await expect(
    page.getByRole("dialog", { name: "Source file preview" }),
  ).toBeVisible();
  await expect(
    page.getByLabel("Preview of SHARED.cpy", { exact: true }),
  ).toContainText("WS-TOTAL");
  await page.keyboard.press("Escape");
  await expect(
    page.getByRole("dialog", { name: "Source file preview" }),
  ).not.toBeVisible();
  await page
    .getByRole("button", { name: "Preview input.dat", exact: true })
    .click();
  await expect(
    page.getByLabel("Preview of input.dat", { exact: true }),
  ).toHaveText("00100\n");
  await page
    .getByRole("button", { name: "Close preview", exact: true })
    .click();
  await expect(
    page.getByText("Shared definitions", { exact: false }).first(),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Convert project", exact: true })
    .click();
  await expect(page.getByLabel("Edit payroll.py")).toBeVisible();
  await page
    .getByText("Numbers & display formatting", { exact: false })
    .first()
    .click();
  await page
    .getByRole("button", { name: "View SHARED.cpy, line 1", exact: true })
    .click();
  await expect(
    page.getByRole("dialog", { name: "Review source preview", exact: true }),
  ).toBeVisible();
  await expect(
    page
      .getByRole("dialog", { name: "Review source preview", exact: true })
      .locator(".focused-line"),
  ).toContainText("WS-TOTAL PIC ZZ9");
  await page
    .getByRole("button", { name: "Close preview", exact: true })
    .click();
  const original = await copyCode(page);
  const edited = original + "\n# preview and download agree\n";
  await replaceCode(page, page.getByLabel("Edit payroll.py"), edited);
  await page.getByRole("link", { name: "Go to Export", exact: true }).click();
  await expect(
    page.getByLabel("Preview of payroll.py", { exact: true }),
  ).toBeVisible();
  expect(
    await copyCode(
      page,
      page
        .locator(".export-preview")
        .getByRole("button", { name: "Copy", exact: true }),
    ),
  ).toBe(edited);
  const event = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "Download .py payroll.py", exact: true })
    .click();
  expect(await fs.readFile((await (await event).path())!, "utf8")).toBe(edited);
  await page
    .getByRole("group", { name: "Export preview", exact: true })
    .getByRole("button", { name: "Original COBOL", exact: true })
    .click();
  await expect(
    page.getByLabel("Preview of payroll.cbl", { exact: true }),
  ).toBeVisible();
  expect(
    await copyCode(
      page,
      page
        .locator(".export-preview")
        .getByRole("button", { name: "Copy", exact: true }),
    ),
  ).toBe(source);
  await page
    .getByRole("group", { name: "Export preview", exact: true })
    .getByRole("button", { name: "Audit report", exact: true })
    .click();
  await page.getByText("Preview audit-report.csv", { exact: true }).click();
  await expect(
    page.getByLabel("Preview of audit-report.csv", { exact: true }),
  ).toContainText("not_verified");
  await accessible(page);
});

test("visual dependencies, review guidance, persistent dark mode and mobile previews", async ({
  page,
}) => {
  await page.goto("/sign-in");
  await page.getByLabel("Color theme", { exact: true }).click();
  await page.getByRole("button", { name: "Dark mode", exact: true }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await accessible(page);
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await signUp(page);
  await accessible(page);
  await demo(page);
  await expect(page.locator(".dependency-map")).toBeVisible();
  await page
    .getByRole("group", { name: "Dependency map filter", exact: true })
    .getByRole("button", { name: "COPY", exact: true })
    .click();
  const node = page.getByRole("button", {
    name: "Inspect COPY ACCTDEF.cpy",
  });
  await expect(node).toBeVisible();
  await node.focus();
  await page.keyboard.press("Enter");
  await expect(page.locator(".connection-inspector")).toContainText(
    "includes a copybook",
  );
  await page
    .locator(".connection-inspector")
    .getByRole("button", { name: "View source line 41", exact: true })
    .click();
  await expect(page.locator(".focused-line")).toContainText("COPY ACCTDEF");
  await page
    .getByRole("button", { name: "Convert project", exact: true })
    .click();
  await expect(page.getByLabel("Edit BANKMAIN.py")).toBeVisible();
  await page
    .getByText("Numbers & display formatting", { exact: false })
    .first()
    .click();
  const review = page.locator(".review-group[open]");
  await expect(review).toContainText("decimal precision");
  await review
    .getByRole("button", { name: /View source line/ })
    .first()
    .click();
  await expect(page.locator(".focused-line")).toContainText("PIC");
  await accessible(page);
  await screenshot(page, "convert-dark");
  await page.getByRole("link", { name: "Go to Export", exact: true }).click();
  await page
    .getByRole("button", { name: "Preview TXNPOST.py", exact: true })
    .click();
  await expect(
    page.getByLabel("Preview of TXNPOST.py", { exact: true }),
  ).toBeVisible();
  await accessible(page);
  await screenshot(page, "export-dark");
  await page.setViewportSize({ width: 375, height: 812 });
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(375);
  await expect(page.getByLabel("Color theme", { exact: true })).toBeVisible();
  await accessible(page);
  await screenshot(page, "mobile-export-dark");
  await page.getByLabel("Color theme", { exact: true }).click();
  await page.getByRole("button", { name: "Light mode", exact: true }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await accessible(page);
  await page.getByLabel("Color theme", { exact: true }).click();
  await page.getByRole("button", { name: "Use system", exact: true }).click();
  await page.emulateMedia({ colorScheme: "dark" });
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.emulateMedia({ colorScheme: "light" });
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
});

test("wide syntax editors support search, wrapping, focus mode and keyboard escape", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await page.setViewportSize({ width: 1920, height: 1080 });
  await signUp(page);
  await demo(page);
  await page
    .getByRole("button", { name: "Convert project", exact: true })
    .click();
  const editor = page.getByLabel("Edit BANKMAIN.py", { exact: true });
  await expect(editor).toBeVisible();
  const code = page.locator(".code-workbench");
  expect((await code.boundingBox())!.width).toBeGreaterThan(1700);
  expect(
    (await page.locator(".python-panel").boundingBox())!.width,
  ).toBeGreaterThan(800);
  await expect(
    page.locator(".source-code-region .tok-keyword").first(),
  ).toBeVisible();
  await expect(
    page.locator(".python-panel .tok-keyword").first(),
  ).toBeVisible();
  await expect(
    page.getByLabel("Read original COBOL", { exact: true }),
  ).toHaveAttribute("aria-readonly", "true");
  await expect(editor).toHaveAttribute("aria-readonly", "false");
  const animationFrames = page.evaluate(
    () =>
      new Promise<string[]>((resolve) => {
        const group = document.querySelector('[aria-label="Code view"]')!;
        const target = [...group.querySelectorAll("button")].find(
          (button) => button.textContent === "Python",
        )!;
        target.addEventListener(
          "click",
          () => {
            const transforms: string[] = [];
            const sample = () => {
              const indicator = group.querySelector(".segment-indicator")!;
              transforms.push(getComputedStyle(indicator).transform);
              if (transforms.length < 25) requestAnimationFrame(sample);
              else resolve(transforms);
            };
            requestAnimationFrame(sample);
          },
          { once: true },
        );
      }),
  );
  await page
    .getByRole("group", { name: "Code view", exact: true })
    .getByRole("button", { name: "Python", exact: true })
    .click();
  expect(
    (await animationFrames).some((transform) => transform !== "none"),
  ).toBe(true);
  await page
    .getByRole("group", { name: "Code view", exact: true })
    .getByRole("button", { name: "Side by side", exact: true })
    .click();

  await page
    .getByRole("button", { name: "Find in Python", exact: true })
    .click();
  const search = page
    .locator(".python-panel")
    .getByLabel("Find", { exact: true });
  await expect(search).toBeFocused();
  await search.pressSequentially("cobol_number");
  await expect(
    page.locator(".python-panel .cm-searchMatch").first(),
  ).toBeVisible();
  await accessible(page);
  await page.keyboard.press("Escape");
  await expect(search).not.toBeVisible();
  await page.getByRole("button", { name: "Wrap lines", exact: true }).click();
  await expect(page.locator(".python-panel .cm-content")).toHaveClass(
    /cm-lineWrapping/,
  );
  await page.getByRole("button", { name: "Focus code", exact: true }).click();
  await expect
    .poll(() => page.evaluate(() => Boolean(document.fullscreenElement)))
    .toBe(true);
  await expect(
    page.getByRole("button", { name: "Exit focus mode", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Exit focus mode", exact: true })
    .click();
  await expect
    .poll(() => page.evaluate(() => Boolean(document.fullscreenElement)))
    .toBe(false);
  await editor.focus();
  await page.keyboard.press("Tab");
  await expect(editor).not.toBeFocused();
  await screenshot(page, "wide-code-workspace");
  await page.getByLabel("Color theme", { exact: true }).click();
  await page.getByRole("button", { name: "Dark mode", exact: true }).click();
  await accessible(page);
  await screenshot(page, "wide-code-workspace-dark");
});

test("reading guide teaches both languages and restores keyboard focus in both themes", async ({
  page,
}) => {
  await signUp(page);
  const trigger = page.getByRole("button", {
    name: "Reading guide",
    exact: true,
  });
  await trigger.click();
  const guide = page.getByRole("dialog", {
    name: "Read the code. Follow the behavior.",
    exact: true,
  });
  await expect(guide).toBeVisible();
  await expect(
    guide.getByLabel("Guide COBOL example", { exact: true }),
  ).toBeVisible();
  await expect(
    guide.getByLabel("Guide Python example", { exact: true }),
  ).toBeVisible();
  const topics = guide.getByRole("group", {
    name: "Reading guide topics",
    exact: true,
  });
  await topics.getByRole("button", { name: "Read COBOL", exact: true }).click();
  await expect(guide).toContainText("PROCEDURE DIVISION");
  await expect(guide).toContainText("Columns matter");
  await topics
    .getByRole("button", { name: "Read Python", exact: true })
    .click();
  await expect(guide).toContainText(/indentation/i);
  await topics
    .getByRole("button", { name: "Compare & verify", exact: true })
    .click();
  await expect(guide).toContainText("local Python edits");
  await accessible(page);
  await page.keyboard.press("Escape");
  await expect(guide).not.toBeVisible();
  await expect(trigger).toBeFocused();
  await page.getByLabel("Color theme", { exact: true }).click();
  await page.getByRole("button", { name: "Dark mode", exact: true }).click();
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setViewportSize({ width: 375, height: 812 });
  await trigger.click();
  expect((await guide.boundingBox())!.width).toBeLessThanOrEqual(375);
  await topics.getByRole("button", { name: "Start here", exact: true }).click();
  await accessible(page);
  await screenshot(page, "reading-guide-dark");
  await guide
    .getByRole("button", { name: "Close reading guide", exact: true })
    .click();
  await expect(trigger).toBeFocused();
});

test("Upload has searchable file types and source previews beside compact project controls", async ({
  page,
}) => {
  await signUp(page);
  await page
    .getByRole("button", { name: "Load demo project", exact: true })
    .click();
  await expect(
    page.getByRole("link", { name: "Continue to Convert", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".compact-create")).toBeVisible();
  const search = page.getByLabel("Find project files", { exact: true });
  await search.fill("acctdef");
  await expect(page.locator(".file-list li")).toHaveCount(1);
  await page
    .getByRole("button", { name: "Preview ACCTDEF.cpy", exact: true })
    .click();
  const dialog = page.getByRole("dialog", {
    name: "Source file preview",
    exact: true,
  });
  await expect(
    dialog.getByLabel("Preview of ACCTDEF.cpy", { exact: true }),
  ).toContainText("ACCT");
  await page.keyboard.press("Escape");
  await search.fill("");
  await page.getByLabel("File type", { exact: true }).selectOption("data");
  await expect(page.locator(".file-list li")).toHaveCount(2);
  await page
    .getByRole("button", { name: "Preview accounts.dat", exact: true })
    .click();
  await expect(
    dialog.getByLabel("Preview of accounts.dat", { exact: true }),
  ).not.toBeEmpty();
  await dialog
    .getByRole("button", { name: "Close preview", exact: true })
    .click();
  await accessible(page);
  await screenshot(page, "upload-refined");
});

test("grouped dependency branches paginate references and explain missing items with a mobile list", async ({
  page,
}) => {
  await signUp(page);
  await page.route("**/api/projects/*/analyze", (route) =>
    route.fulfill({
      json: {
        project_id: "1",
        run_id: "analysis",
        status: "analyzed",
        program_count: 5,
        copybook_count: 3,
        data_file_count: 2,
        dependencies: [
          ...Array.from({ length: 7 }, (_, index) => ({
            source: "BANKMAIN.cbl",
            target: `BOOK-${index}.cpy`,
            kind: "copy",
            line: 41,
          })),
          {
            source: "BANKMAIN.cbl",
            target: "INTCALC.cbl",
            kind: "call",
            line: 156,
          },
          {
            source: "BANKMAIN.cbl",
            target: "LOAD-ACCOUNTS",
            kind: "perform",
            line: 74,
          },
        ],
        unresolved: [
          { source: "BANKMAIN.cbl", name: "ABSENT", kind: "call", line: 116 },
        ],
        programs: [],
      },
    }),
  );
  await demo(page);
  await expect(page.locator(".connection-group")).toHaveCount(3);
  await expect(page.locator(".react-flow__edge")).toHaveCount(3);
  await page
    .getByRole("button", { name: "Next COPY references", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Inspect COPY BOOK-6.cpy" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Inspect CALL ABSENT" }).click();
  await expect(page.locator(".connection-inspector")).toContainText(
    "Add the missing program or copybook",
  );
  await expect(
    page
      .locator(".connection-inspector")
      .getByRole("button", { name: "View source line 116", exact: true }),
  ).toBeVisible();
  await accessible(page);
  await page.setViewportSize({ width: 375, height: 812 });
  await expect(
    page
      .getByRole("group", { name: "Dependency display", exact: true })
      .getByRole("button", { name: "List", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await expect(
    page.getByRole("list", { name: "Dependency references", exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(375);
  await accessible(page);
});
