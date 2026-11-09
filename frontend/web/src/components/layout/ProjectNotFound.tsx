import Link from "next/link";
import { EmptyState } from "@/components/ui/EmptyState";
export function ProjectNotFound() {
  return (
    <div className="card">
      <h1>Project not found</h1>
      <EmptyState
        action={
          <Link className="button button-primary" href="/upload">
            Back to Upload
          </Link>
        }
      >
        This project may have been removed, or it belongs to another account.
      </EmptyState>
    </div>
  );
}
