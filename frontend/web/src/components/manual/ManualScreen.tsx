import Link from "next/link";
import { AuthLayout } from "@/components/auth/AuthLayout";
import { WikiBody } from "@/components/manual/WikiBody";
import { manualHref, wikiCatalog, type WikiPage } from "@/lib/wiki";

export function ManualScreen({ page }: { page: WikiPage }) {
  const { sections } = wikiCatalog();
  return (
    <AuthLayout variant="manual">
      <div className="manual-shell">
        <nav className="manual-nav" aria-label="User manual">
          {sections.map((section) => (
            <section key={section.title || "overview"}>
              {section.title ? <h2>{section.title}</h2> : null}
              <ul>
                {section.links.map((link) => (
                  <li key={link.slug}>
                    <Link
                      href={manualHref(link.slug)}
                      aria-current={
                        link.slug === page.slug ? "page" : undefined
                      }
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </nav>
        <div className="manual-reading">
          <p className="manual-kicker">User manual</p>
          <article className="manual-article">
            <WikiBody markdown={page.markdown} />
          </article>
        </div>
      </div>
    </AuthLayout>
  );
}
