import {
  Activity,
  ArrowRightLeft,
  GitBranch,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import type { RunSummary } from "@/types/api";
import { Card } from "@/components/ui/Card";
import { Badge, statusTone } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatRunLabel, formatRunStatus, formatRunTime } from "@/lib/format";
export function RunHistory({ runs }: { runs: RunSummary[] }) {
  return (
    <Card
      title="Run history"
      actions={<Activity size={21} aria-hidden="true" />}
    >
      {!runs.length ? (
        <EmptyState>No runs yet. Convert the project to add one.</EmptyState>
      ) : (
        <ul className="run-list" tabIndex={0} aria-label="Project run history">
          {runs.map((run) => {
            const Icon =
              run.kind === "convert"
                ? ArrowRightLeft
                : run.kind === "verify"
                  ? ShieldCheck
                  : run.kind === "ai_review"
                    ? Sparkles
                    : GitBranch;
            return (
              <li key={run.id}>
                <span className="run-icon">
                  <Icon size={18} aria-hidden="true" />
                </span>
                <strong>{formatRunLabel(run.kind)}</strong>
                <Badge tone={statusTone(run.status)}>
                  {formatRunStatus(run.status)}
                </Badge>
                <time dateTime={run.created_at}>
                  {formatRunTime(run.created_at)}
                </time>
                <span className="hint">#{run.id}</span>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}
