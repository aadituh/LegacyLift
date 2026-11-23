import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { WikiBody } from "@/components/manual/WikiBody";
import { linkWikiPages, manualHref, wikiCatalog, wikiPage } from "./wiki";

it("loads the GitHub wiki sidebar and pages for the manual", () => {
  const wiki = wikiCatalog();
  expect(wiki.pages.has("README")).toBe(false);
  expect(wiki.pages.has("_Sidebar")).toBe(false);
  expect(wiki.pages.get("Home")?.markdown).toContain("What is LegacyLift?");
  expect(wiki.sections.map((section) => section.title)).toEqual([
    "",
    "Processes",
    "Interfaces",
    "Tasks",
  ]);
  expect(wiki.sections[3]?.links.map((link) => link.slug)).toContain(
    "Create-an-Account-and-Sign-In",
  );
  expect(wikiPage("Home")?.title).toBe("Welcome to LegacyLift");
  expect(wikiPage("../Home")).toBeUndefined();
  expect(wikiPage("Not-A-Page")).toBeUndefined();
  expect(manualHref("Home")).toBe("/manual");
  expect(manualHref("Run-LegacyLift-Locally")).toBe(
    "/manual/Run-LegacyLift-Locally",
  );
});

it("turns wiki links into manual links and leaves fenced code unchanged", () => {
  const linked = linkWikiPages(
    "See [[Home]] and [[Run LegacyLift Locally|Run-LegacyLift-Locally]].\n```\n[[Home]]\n```\n",
    (slug) => `/manual/${slug}`,
  );
  expect(linked).toContain("[Home](/manual/Home)");
  expect(linked).toContain(
    "[Run LegacyLift Locally](/manual/Run-LegacyLift-Locally)",
  );
  expect(linked).toContain("```\n[[Home]]\n```");
});

it("shows a wiki figure from the manual image folder", () => {
  render(<WikiBody markdown={wikiPage("Analyze-Page")!.markdown} />);
  expect(
    screen
      .getByRole("img", {
        name: "Dependencies for BANKMAIN on the Convert page",
      })
      .getAttribute("src"),
  ).toBe("/manual-images/analyze-dependencies.png");
});

it("renders every wiki page without dropping its text", () => {
  for (const page of wikiCatalog().pages.values()) {
    const view = render(<WikiBody markdown={page.markdown} />);
    expect(view.container.textContent?.length).toBeGreaterThan(40);
    if (/^# +/m.test(page.markdown)) {
      expect(view.container.textContent).toContain(page.title);
    }
    view.unmount();
  }
});

it("renders wiki headings, lists, code, tables, and cross-links", () => {
  const run = render(
    <WikiBody markdown={wikiPage("Run-LegacyLift-Locally")!.markdown} />,
  );
  expect(
    screen.getByRole("heading", { name: "Run LegacyLift Locally" }),
  ).toBeTruthy();
  expect(
    screen
      .getByRole("link", { name: "Create an Account and Sign In" })
      .getAttribute("href"),
  ).toBe("/manual/Create-an-Account-and-Sign-In");
  expect(screen.getByText("docker compose up --build")).toBeTruthy();
  expect(
    screen.getByText(/Wait until the terminal stops printing/),
  ).toBeTruthy();
  expect(
    screen
      .getByRole("link", { name: /^Docker \(opens a new tab\)$/ })
      .getAttribute("href"),
  ).toBe("https://docs.docker.com/get-docker/");
  run.unmount();

  const verification = render(
    <WikiBody markdown={wikiPage("Verification-Against-GnuCOBOL")!.markdown} />,
  );
  expect(
    screen.getByRole("columnheader", { name: "Status on the page" }),
  ).toBeTruthy();
  expect(
    screen.getAllByRole("cell", { name: "Verified" }).length,
  ).toBeGreaterThan(0);
  verification.unmount();

  const contents = render(
    <WikiBody markdown={wikiPage("Table-of-Contents")!.markdown} />,
  );
  expect(screen.getByRole("link", { name: "Home" }).getAttribute("href")).toBe(
    "/manual",
  );
  expect(contents.container.querySelectorAll("ol ol").length).toBeGreaterThan(
    0,
  );
  contents.unmount();

  render(<WikiBody markdown={wikiPage("Upload-Page")!.markdown} />);
  expect(screen.getAllByRole("separator").length).toBeGreaterThan(0);
  expect(screen.getByText(/Spencer Peloquin/)).toBeTruthy();
});
