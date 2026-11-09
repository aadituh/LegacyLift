import type { DependencyLink, UnresolvedDependency } from "@/types/api";
export const dependencyKinds = [
  {
    kind: "copy",
    title: "Shared definitions",
    explanation: "COPY includes a copybook's definitions in this program.",
    action: "Review the shared fields and their formats.",
  },
  {
    kind: "call",
    title: "Other programs",
    explanation: "CALL invokes another program, often passing values to it.",
    action: "Check inputs, returned values, and changes to shared records.",
  },
  {
    kind: "perform",
    title: "Local routines",
    explanation: "PERFORM runs a named section or paragraph in this program.",
    action: "Follow the routine and check its loop or exit conditions.",
  },
];
export type Connection = {
  id: string;
  kind: string;
  target: string;
  lines: number[];
  missing: boolean;
};
export function groupConnections(
  links: DependencyLink[],
  unresolved: UnresolvedDependency[],
): Connection[] {
  const groups = new Map<string, Connection>();
  for (const item of [
    ...links.map((link) => ({
      kind: link.kind.toLowerCase(),
      target: link.target,
      line: link.line,
      missing: false,
    })),
    ...unresolved.map((link) => ({
      kind: link.kind.toLowerCase(),
      target: link.name,
      line: link.line,
      missing: true,
    })),
  ]) {
    const id = JSON.stringify([item.kind, item.target, item.missing]);
    const existing = groups.get(id);
    if (existing) {
      if (!existing.lines.includes(item.line)) existing.lines.push(item.line);
    } else
      groups.set(id, {
        id,
        kind: item.kind,
        target: item.target,
        lines: [item.line],
        missing: item.missing,
      });
  }
  return [...groups.values()]
    .map((group) => ({ ...group, lines: group.lines.sort((a, b) => a - b) }))
    .sort(
      (a, b) =>
        a.kind.localeCompare(b.kind) ||
        Number(b.missing) - Number(a.missing) ||
        a.target.localeCompare(b.target),
    );
}
