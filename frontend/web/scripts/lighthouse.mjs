// Run against the isolated QA API (8011) and production web server (3011).
import lighthouse from "lighthouse";
import { launch } from "chrome-launcher";
import { chromium } from "@playwright/test";
import fs from "node:fs/promises";
const origin = process.env.QA_ORIGIN || "http://127.0.0.1:3011";
const api = process.env.QA_API || "http://127.0.0.1:8011";
const email = `lighthouse-${Date.now()}@example.com`;
async function post(path, body, token) {
  const response = await fetch(api + path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  if (!response.ok)
    throw new Error(`QA setup failed: ${path} (${response.status})`);
  return response.json();
}
await post("/api/auth/register", {
  email,
  password: "LighthouseTest123",
  display_name: "Accessibility Reviewer",
});
const { token } = await post("/api/auth/login", {
  email,
  password: "LighthouseTest123",
});
const project = await post("/api/projects/demo", undefined, token);
await post(`/api/projects/${project.id}/analyze`, undefined, token);
await post(`/api/projects/${project.id}/convert`, undefined, token);
await post(`/api/projects/${project.id}/verify`, undefined, token);
const chrome = await launch({
  chromeFlags: ["--headless=new", "--no-sandbox", "--disable-dev-shm-usage"],
});
try {
  const browser = await chromium.connectOverCDP(
    `http://127.0.0.1:${chrome.port}`,
  );
  const page = await browser.contexts()[0].newPage();
  await page.goto(origin + "/sign-in");
  await page.evaluate(
    (value) => localStorage.setItem("legacylift-token", value),
    token,
  );
  const screens = [
    ["upload", "/upload"],
    ["convert", `/projects/${project.id}/convert`],
    ["export", `/projects/${project.id}/export`],
  ];
  const scores = {};
  await fs.mkdir("test-results/lighthouse", { recursive: true });
  for (const [name, pathname] of screens) {
    const auditPage = await browser.contexts()[0].newPage();
    await auditPage.goto(origin + pathname);
    await auditPage
      .locator("main h1")
      .waitFor()
      .catch(async (error) => {
        console.log(
          "Audit navigation failed:",
          name,
          auditPage.url(),
          await auditPage.locator("body").innerText(),
        );
        throw error;
      });
    const result = await lighthouse(origin + pathname, {
      port: chrome.port,
      onlyCategories: ["accessibility"],
      disableStorageReset: true,
      formFactor: "desktop",
      screenEmulation: { disabled: true },
      logLevel: "error",
    });
    if (!result) throw new Error("Lighthouse returned no report.");
    scores[name] = Math.round(result.lhr.categories.accessibility.score * 100);
    if (!result.lhr.finalDisplayedUrl.includes(pathname))
      throw new Error("Audit was redirected away from " + pathname);
    await fs.writeFile(`test-results/lighthouse/${name}.html`, result.report);
    const failed = Object.values(result.lhr.audits)
      .filter((a) => a.score === 0)
      .map((a) => a.title);
    if (failed.length) console.log(name, failed);
  }
  await fs.writeFile(
    "test-results/lighthouse/scores.json",
    JSON.stringify(scores, null, 2),
  );
  console.log("Lighthouse accessibility:", JSON.stringify(scores));
  await browser.close();
  if (Object.values(scores).some((score) => score < 90)) process.exitCode = 1;
} finally {
  await chrome.kill();
}
