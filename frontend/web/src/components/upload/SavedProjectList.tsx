import { Folder, ArrowUpRight, Trash2, RefreshCw } from "lucide-react";
import type { ProjectSummary } from "@/types/api";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge, statusTone } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Spinner";
import { formatRunStatus, formatRunTime } from "@/lib/format";
export function SavedProjectList({
  projects,
  isLoading,
  error,
  busy,
  onOpen,
  onRemove,
  onClearAll,
  onRetry,
}: {
  projects: ProjectSummary[];
  isLoading: boolean;
  error: string;
  busy: boolean;
  onOpen: (id: string) => void;
  onRemove: (id: string) => void;
  onClearAll: () => void;
  onRetry: () => void;
}) {
  return (
    <Card
      title="Saved projects"
      actions={
        <div className="actions">
          <span className="count-pill">{projects.length}</span>
          <Button
            variant="ghost"
            size="sm"
            disabled={busy || !projects.length}
            onClick={() => {
              if (
                window.confirm(
                  `Delete all ${projects.length} saved projects and their files? This cannot be undone.`,
                )
              )
                onClearAll();
            }}
          >
            Clear all
          </Button>
        </div>
      }
    >
      {isLoading ? (
        <Skeleton label="Loading saved projects…" />
      ) : error ? (
        <div className="notice danger" role="alert">
          <span>{error}</span>
          <Button onClick={onRetry}>
            <RefreshCw size={16} />
            Retry
          </Button>
        </div>
      ) : !projects.length ? (
        <EmptyState>
          No saved projects yet. Create your first project above.
        </EmptyState>
      ) : (
        <ul className="project-list">
          {projects.map((project) => (
            <li key={project.id}>
              <span className="project-icon">
                <Folder size={22} aria-hidden="true" />
              </span>
              <div className="project-info">
                <h3>{project.name}</h3>
                <p>
                  {project.program_count} programs · {project.copybook_count}{" "}
                  copybooks · {project.data_file_count} data files
                </p>
                <time dateTime={project.created_at}>
                  {formatRunTime(project.created_at)}
                </time>
              </div>
              {project.last_run && (
                <Badge tone={statusTone(project.last_run.status)}>
                  {formatRunStatus(project.last_run.status)}
                </Badge>
              )}
              <div className="actions">
                <Button
                  size="sm"
                  onClick={() => onOpen(project.id)}
                  disabled={busy}
                >
                  Open <ArrowUpRight size={16} aria-hidden="true" />
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={busy}
                  aria-label={`Remove project ${project.name}`}
                  onClick={() => {
                    if (
                      window.confirm(
                        `Delete "${project.name}" and all its files and runs? This cannot be undone.`,
                      )
                    )
                      onRemove(project.id);
                  }}
                >
                  <Trash2 size={16} aria-hidden="true" />
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
