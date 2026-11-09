import Link from "next/link";
import { Code2, GitBranch, ShieldCheck } from "lucide-react";
import { Logo } from "@/components/brand/Logo";
import { Backdrop } from "@/components/brand/Backdrop";
import { ThemeMenu } from "@/components/ui/ThemeMenu";
export function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="auth-layout">
      <Backdrop />
      <header className="site-header">
        <div className="site-header-inner">
          <Link href="/">
            <Logo size={46} />
          </Link>
          <nav aria-label="Account" className="account-nav">
            <ThemeMenu />
            <a href="#workflow" className="auth-workflow-link">
              How it works
            </a>
            <Link href="/sign-in" className="auth-signin-link">
              Sign in
            </Link>
            <Link href="/sign-up" className="button button-secondary">
              Create account
            </Link>
          </nav>
        </div>
      </header>
      <main className="auth-content">
        <section className="auth-card">{children}</section>
        <section
          id="workflow"
          className="auth-benefits"
          aria-label="How LegacyLift works"
        >
          <div>
            <GitBranch size={20} aria-hidden="true" />
            <h2>Understand your source</h2>
            <p>See how your programs connect.</p>
          </div>
          <div>
            <Code2 size={20} aria-hidden="true" />
            <h2>Review the next chapter</h2>
            <p>Shape clear, editable Python drafts.</p>
          </div>
          <div>
            <ShieldCheck size={20} aria-hidden="true" />
            <h2>Verify the behavior</h2>
            <p>Compare outputs before moving forward.</p>
          </div>
        </section>
      </main>
      <footer className="auth-footer">
        <p>© {new Date().getFullYear()} LegacyLift · ODU CS 411W</p>
        <p>Legacy code. Lasting possibilities.</p>
      </footer>
    </div>
  );
}
