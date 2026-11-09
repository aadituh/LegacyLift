"use client";
import { m, useReducedMotion } from "motion/react";
import { ArrowUpRight, AlertTriangle } from "lucide-react";
import type { Connection } from "@/lib/dependencies";
import { dependencyKinds } from "@/lib/dependencies";
import { Button } from "@/components/ui/Button";
export function ConnectionInspector({
  connection,
  onJumpLine,
}: {
  connection: Connection | null;
  onJumpLine: (line: number) => void;
}) {
  const reduced = useReducedMotion();
  if (!connection)
    return (
      <p className="graph-instruction">
        Select a name in the map to see what the connection means and find it in
        the source.
      </p>
    );
  const definition = dependencyKinds.find(
    (item) => item.kind === connection.kind,
  );
  return (
    <m.div
      key={connection.id}
      className={`connection-inspector ${connection.missing ? "has-missing" : ""}`}
      initial={{ opacity: reduced ? 1 : 0, y: reduced ? 0 : 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: reduced ? 0 : 0.16 }}
    >
      <div>
        <span className={`kind-label legend-${connection.kind}`}>
          {connection.kind.toUpperCase()}
        </span>
        <h3>{connection.target}</h3>
        {connection.missing && (
          <span className="missing-label">
            <AlertTriangle size={14} aria-hidden="true" />
            Missing
          </span>
        )}
      </div>
      <p>
        {definition?.explanation ?? "This program refers to this item."}{" "}
        {connection.missing
          ? "Add the missing program or copybook, or check the routine name."
          : definition?.action}
      </p>
      <div className="actions">
        {connection.lines.map((line) => (
          <Button size="sm" key={line} onClick={() => onJumpLine(line)}>
            View source line {line}
            <ArrowUpRight size={14} aria-hidden="true" />
          </Button>
        ))}
      </div>
    </m.div>
  );
}
