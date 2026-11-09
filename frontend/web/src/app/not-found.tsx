import Link from "next/link";
import { Logo } from "@/components/brand/Logo";
export default function NotFound() {
  return (
    <main className="error-page">
      <title>Page not found · LegacyLift</title>
      <Logo />
      <p className="eyebrow">404 · A SMALL DETOUR</p>
      <h1>This page isn’t here.</h1>
      <p>Let’s get you back to your workspace.</p>
      <Link href="/upload" className="button button-primary">
        Back to Upload
      </Link>
    </main>
  );
}
