import fs from "node:fs";
import path from "node:path";

const PAGE_FILE = /^[A-Za-z0-9-]+\.md$/;
const SKIPPED_PAGES = new Set(["README.md", "_Sidebar.md", "_Footer.md"]);
const WIKI_LINK = /\[\[([^\]\n|]+?)(?:\|([^\]\n]+?))?\]\]/g;

export type WikiLink = { slug: string; label: string };
export type WikiSection = { title: string; links: WikiLink[] };
export type WikiPage = { slug: string; title: string; markdown: string };
export type WikiCatalog = {
  pages: ReadonlyMap<string, WikiPage>;
  sections: readonly WikiSection[];
};

let catalog: WikiCatalog | undefined;

/** Manual address for a wiki page. Home is the manual index. */
export function manualHref(slug: string): string {
  return slug === "Home" ? "/manual" : `/manual/${slug}`;
}

/**
 * Replace GitHub wiki links with manual links.
 * Fenced code stays literal, matching the wiki source.
 */
export function linkWikiPages(
  markdown: string,
  hrefForSlug: (slug: string) => string | null,
): string {
  return markdown
    .split(/(```[\s\S]*?```)/g)
    .map((part, index) =>
      index % 2 === 1
        ? part
        : part.replace(WIKI_LINK, (match, label, slug) => {
            const target = String(slug ?? label).trim();
            const href = hrefForSlug(target);
            if (!href) return match;
            return `[${String(label).trim()}](${href})`;
          }),
    )
    .join("");
}

/** Pages and sidebar from the GitHub wiki source (`wiki/` in this repo). */
export function wikiCatalog(): WikiCatalog {
  catalog ??= loadWiki(wikiDirectory());
  return catalog;
}

export function wikiPage(slug: string): WikiPage | undefined {
  if (!/^[A-Za-z0-9-]+$/.test(slug)) return undefined;
  return wikiCatalog().pages.get(slug);
}

export function wikiDirectory(): string {
  const candidates = [
    path.resolve(process.cwd(), "../../wiki"),
    path.resolve(process.cwd(), "../wiki"),
    path.resolve(process.cwd(), "wiki"),
  ];
  for (const dir of candidates) {
    if (
      fs.existsSync(path.join(dir, "Home.md")) &&
      fs.existsSync(path.join(dir, "_Sidebar.md"))
    ) {
      return dir;
    }
  }
  throw new Error(
    "LegacyLift wiki pages were not found. The user manual reads the GitHub wiki source in the wiki folder.",
  );
}

function loadWiki(dir: string): WikiCatalog {
  const pages = new Map<string, WikiPage>();
  for (const name of fs.readdirSync(dir)) {
    if (SKIPPED_PAGES.has(name) || !PAGE_FILE.test(name)) continue;
    const slug = name.slice(0, -3);
    const markdown = fs
      .readFileSync(path.join(dir, name), "utf8")
      .replace(/^\uFEFF/, "");
    pages.set(slug, { slug, title: pageTitle(markdown, slug), markdown });
  }
  const sections = sidebar(
    fs.readFileSync(path.join(dir, "_Sidebar.md"), "utf8"),
  );
  for (const section of sections) {
    for (const link of section.links) {
      if (!pages.has(link.slug)) {
        throw new Error(`Wiki sidebar links to missing page ${link.slug}.`);
      }
    }
  }
  return { pages, sections };
}

function pageTitle(markdown: string, slug: string): string {
  const heading = markdown.match(/^# +(.+?)[ \t]*$/m);
  return heading ? heading[1].trim() : slug.replaceAll("-", " ");
}

function sidebar(source: string): WikiSection[] {
  const overview: WikiSection = { title: "", links: [] };
  const sections = [overview];
  let current = overview;
  for (const line of source.split(/\r?\n/)) {
    const summary = line.match(/<h2>([^<]+)<\/h2>/);
    if (summary) {
      current = { title: summary[1].trim(), links: [] };
      sections.push(current);
      continue;
    }
    const match = line.match(/\[\[([^\]|]+)(?:\|([^\]]+))?\]\]/);
    if (!match) continue;
    current.links.push({
      label: match[1].trim(),
      slug: (match[2] ?? match[1]).trim(),
    });
  }
  return sections;
}
