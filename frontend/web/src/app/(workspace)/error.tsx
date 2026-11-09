"use client";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
export default function AppError({
  retry,
}: {
  error: unknown;
  retry: () => void;
}) {
  return (
    <div className="error-page">
      <h1>Something interrupted this page.</h1>
      <p>
        Your saved projects are still available. Try opening the page again.
      </p>
      <div className="actions">
        <Button variant="primary" onClick={retry}>
          Try again
        </Button>
        <Link className="button button-secondary" href="/upload">
          Back to Upload
        </Link>
      </div>
    </div>
  );
}
