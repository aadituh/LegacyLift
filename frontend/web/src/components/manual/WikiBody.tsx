import { createElement, Fragment, type ReactNode } from "react";
import Link from "next/link";
import { marked, type Token, type Tokens } from "marked";
import { linkWikiPages, manualHref, wikiCatalog } from "@/lib/wiki";

const HEADINGS = ["h1", "h2", "h3", "h4", "h5", "h6"] as const;

/** Render one GitHub wiki page. Wiki links open other manual pages. */
export function WikiBody({ markdown }: { markdown: string }) {
  const pages = wikiCatalog().pages;
  const linked = linkWikiPages(markdown, (slug) =>
    pages.has(slug) ? manualHref(slug) : null,
  );
  return <>{renderTokens(marked.lexer(linked), "wiki")}</>;
}

function renderTokens(tokens: Token[], keyPrefix: string): ReactNode[] {
  return tokens.map((token, index) =>
    renderToken(token, `${keyPrefix}-${index}`),
  );
}

function renderToken(token: Token, key: string): ReactNode {
  switch (token.type) {
    case "space":
    case "html":
    case "def":
      return null;
    case "heading":
      return createElement(
        HEADINGS[token.depth - 1] ?? "h2",
        { key },
        renderTokens(token.tokens ?? [], key),
      );
    case "paragraph":
      return <p key={key}>{renderTokens(token.tokens ?? [], key)}</p>;
    case "blockquote":
      return (
        <blockquote key={key}>
          {renderTokens(token.tokens ?? [], key)}
        </blockquote>
      );
    case "list":
      return renderList(token as Tokens.List, key);
    case "list_item":
      return <li key={key}>{renderTokens(token.tokens ?? [], key)}</li>;
    case "code":
      return (
        <pre
          key={key}
          tabIndex={0}
          aria-label={token.lang ? `${token.lang} code` : "Code"}
        >
          <code className={token.lang ? `language-${token.lang}` : undefined}>
            {token.text.replace(/\n$/, "")}
          </code>
        </pre>
      );
    case "hr":
      return <hr key={key} />;
    case "table":
      return renderTable(token as Tokens.Table, key);
    case "text":
      return token.tokens ? (
        <Fragment key={key}>{renderTokens(token.tokens ?? [], key)}</Fragment>
      ) : (
        <Fragment key={key}>{token.text}</Fragment>
      );
    case "escape":
      return <Fragment key={key}>{token.text}</Fragment>;
    case "checkbox":
      return null;
    case "strong":
      return <strong key={key}>{renderTokens(token.tokens ?? [], key)}</strong>;
    case "em":
      return <em key={key}>{renderTokens(token.tokens ?? [], key)}</em>;
    case "del":
      return <del key={key}>{renderTokens(token.tokens ?? [], key)}</del>;
    case "codespan":
      return <code key={key}>{token.text}</code>;
    case "br":
      return <br key={key} />;
    case "link":
      return renderLink(token as Tokens.Link, key);
    case "image":
      return (
        // Wiki pages are the manual text; keep their images when a page has one.
        // eslint-disable-next-line @next/next/no-img-element
        <img key={key} src={manualImageSrc(token.href)} alt={token.text} />
      );
    default:
      return null;
  }
}

function renderList(token: Tokens.List, key: string): ReactNode {
  const items = token.items.map((item, index) => (
    <li key={`${key}-${index}`}>
      {renderTokens(item.tokens, `${key}-${index}`)}
    </li>
  ));
  if (!token.ordered) return <ul key={key}>{items}</ul>;
  const start =
    typeof token.start === "number" && token.start > 1
      ? token.start
      : undefined;
  return (
    <ol key={key} start={start}>
      {items}
    </ol>
  );
}

function renderTable(token: Tokens.Table, key: string): ReactNode {
  const caption = token.header
    .map((cell) => cell.text)
    .filter(Boolean)
    .join(", ");
  return (
    <div
      key={key}
      className="manual-table"
      role="region"
      aria-label={caption}
      tabIndex={0}
    >
      <table>
        <thead>
          <tr>
            {token.header.map((cell, index) => (
              <th key={`${key}-h-${index}`} scope="col">
                {renderTokens(cell.tokens, `${key}-h-${index}`)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {token.rows.map((row, rowIndex) => (
            <tr key={`${key}-r-${rowIndex}`}>
              {row.map((cell, index) => (
                <td key={`${key}-${rowIndex}-${index}`}>
                  {renderTokens(cell.tokens, `${key}-${rowIndex}-${index}`)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Wiki pictures live in `wiki/images`. The manual serves the same files from `public/manual-images`. */
function manualImageSrc(href: string): string {
  const name = href.match(/^images\/([A-Za-z0-9._-]+)$/)?.[1];
  if (!name) return href;
  const base = process.env.NEXT_PUBLIC_BASE_PATH ?? "";
  return `${base}/manual-images/${name}`;
}

function renderLink(token: Tokens.Link, key: string): ReactNode {
  const children = renderTokens(token.tokens ?? [], key);
  if (token.href.startsWith("/")) {
    return (
      <Link key={key} href={token.href}>
        {children}
      </Link>
    );
  }
  return (
    <a key={key} href={token.href} target="_blank" rel="noreferrer">
      {children} <span className="sr-only">(opens a new tab)</span>
    </a>
  );
}
