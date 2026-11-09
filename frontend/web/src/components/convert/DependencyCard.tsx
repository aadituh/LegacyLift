"use client";
import { useState } from "react";
import type { AnalyzeResponse } from "@/types/api";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { GitBranch } from "lucide-react";
import { DependencyMap } from "./DependencyMap";
import { dependencyKinds, groupConnections } from "@/lib/dependencies";
import { ConnectionInspector } from "./ConnectionInspector";
import { useCompactScreen } from "@/hooks/useCompactScreen";
export function DependencyCard({
  fileName,
  analysis,
  onJumpLine,
}: {
  fileName: string;
  analysis: AnalyzeResponse | null;
  onJumpLine: (line: number) => void;
}) {
  const [filter, setFilter] = useState("all");
  const [selectedId, setSelectedId] = useState<string>();
  const [display, setDisplay] = useState<"graph" | "list" | null>(null);
  const compact = useCompactScreen();
  if (!analysis || !fileName) return null;
  const belongs = (source: string) =>
    source === fileName || source.startsWith(fileName + ":");
  const links = (analysis.dependencies ?? []).filter((l) => belongs(l.source));
  const unresolved = (analysis.unresolved ?? []).filter((l) =>
    belongs(l.source),
  );
  const program = analysis.programs?.find((p) => p.source_name === fileName);
  const allConnections = groupConnections(links, unresolved);
  const connections = allConnections.filter(
    (item) => filter === "all" || item.kind === filter,
  );
  const selected = connections.find((item) => item.id === selectedId) ?? null;
  const displayMode = display ?? (compact ? "list" : "graph");
  return (
    <Card
      title={`Dependencies for ${fileName}`}
      actions={<GitBranch size={21} aria-hidden="true" />}
    >
      <p className="hint">
        Start at the program, then follow a branch to its shared definitions,
        other programs, or local routines. Items in a branch are grouped by
        type; they do not call each other.
      </p>
      <div className="dependency-legend">
        {dependencyKinds.map((item) => (
          <div key={item.kind} className={`legend-${item.kind}`}>
            <strong>
              {item.title}{" "}
              <span className="count-pill">
                {
                  allConnections.filter(
                    (connection) => connection.kind === item.kind,
                  ).length
                }
              </span>
            </strong>
            <p>{item.explanation}</p>
          </div>
        ))}
      </div>
      {links.length || unresolved.length ? (
        <>
          <div className="map-toolbar">
            <SegmentedControl
              label="Dependency map filter"
              value={filter}
              onChange={setFilter}
              options={[
                { value: "all", label: "All connections" },
                ...dependencyKinds.map((item) => ({
                  value: item.kind,
                  label: item.kind.toUpperCase(),
                })),
              ]}
            />
            <SegmentedControl
              label="Dependency display"
              value={displayMode}
              onChange={setDisplay}
              options={[
                { value: "graph", label: "Map" },
                { value: "list", label: "List" },
              ]}
            />
          </div>
          {!connections.length ? (
            <p className="graph-instruction">
              No connections of this type were found.
            </p>
          ) : displayMode === "graph" ? (
            <DependencyMap
              key={filter}
              fileName={fileName}
              connections={connections}
              selectedId={selectedId}
              onSelect={(item) => setSelectedId(item.id)}
            />
          ) : (
            <ul
              className="connection-browser"
              aria-label="Dependency references"
            >
              {connections.map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    aria-pressed={selectedId === item.id}
                    onClick={() => setSelectedId(item.id)}
                  >
                    <span className={`kind-label legend-${item.kind}`}>
                      {item.kind.toUpperCase()}
                    </span>
                    <strong>{item.target}</strong>
                    <span className={item.missing ? "missing-label" : "hint"}>
                      {item.missing
                        ? "Missing"
                        : `${item.lines.length} reference${item.lines.length === 1 ? "" : "s"}`}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
          <ConnectionInspector connection={selected} onJumpLine={onJumpLine} />
        </>
      ) : (
        <p className="resolved-note">
          No external links or local routine references were found.
        </p>
      )}
      <div
        className={`dependency-health ${unresolved.length ? "notice warning" : ""}`}
      >
        {unresolved.length ? (
          <div>
            <strong>{unresolved.length} references need attention</strong>
            <p className="hint">
              Add a missing program or copybook using Project files. For a local
              routine, check its name in the source.
            </p>
            <ul>
              {unresolved.map((item, i) => (
                <li key={i}>
                  <code>
                    {item.kind.toUpperCase()} {item.name}
                  </code>{" "}
                  <Button size="sm" onClick={() => onJumpLine(item.line)}>
                    View source line {item.line}
                  </Button>
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <p className="resolved-note">
            All detected references are resolved. This checks names and links;
            review the behavior separately.
          </p>
        )}
      </div>
      <details>
        <summary>Connection list ({links.length})</summary>
        <ul className="connection-list">
          {links.map((item, i) => (
            <li key={i}>
              <span className={`kind-label legend-${item.kind.toLowerCase()}`}>
                {item.kind.toUpperCase()}
              </span>
              <code>{item.target}</code>
              <Button size="sm" onClick={() => onJumpLine(item.line)}>
                Line {item.line}
              </Button>
            </li>
          ))}
        </ul>
      </details>
      <details>
        <summary>
          Data fields ({program?.fields?.length ?? 0}) · values this program
          stores
        </summary>
        <ul className="inventory" tabIndex={0} aria-label="Data fields">
          {program?.fields?.map((f, i) => (
            <li key={i}>
              <code>
                {f.name}
                {f.picture ? ` · PIC ${f.picture}` : ""}
                {f.occurs ? ` · repeats ${f.occurs} times` : ""}
              </code>
              <Button size="sm" onClick={() => onJumpLine(f.line)}>
                Line {f.line}
              </Button>
            </li>
          ))}
        </ul>
      </details>
      <details>
        <summary>
          Local routines ({program?.paragraphs?.length ?? 0}) · named blocks of
          work
        </summary>
        <ul className="inventory" tabIndex={0} aria-label="Local routines">
          {program?.paragraphs?.map((p, i) => (
            <li key={i}>
              <code>{p.name}</code>
              <Button size="sm" onClick={() => onJumpLine(p.start_line)}>
                Lines {p.start_line}–{p.end_line}
              </Button>
            </li>
          ))}
        </ul>
      </details>
    </Card>
  );
}
