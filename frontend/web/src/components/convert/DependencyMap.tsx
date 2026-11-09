"use client";
import { useMemo, useState } from "react";
import {
  ReactFlow,
  Controls,
  Handle,
  Position,
  type Node,
  type NodeProps,
  type Edge,
} from "@xyflow/react";
import type { Connection } from "@/lib/dependencies";
import { dependencyKinds } from "@/lib/dependencies";
type GroupData = {
  kind: string;
  items: Connection[];
  selectedId?: string;
  onSelect: (item: Connection) => void;
};
function caption(item: Connection) {
  return item.missing
    ? "Missing reference"
    : item.lines.length === 1
      ? `Source line ${item.lines[0]}`
      : `${item.lines.length} references`;
}
function ConnectionGroup({ data }: NodeProps<Node<GroupData>>) {
  const definition = dependencyKinds.find((item) => item.kind === data.kind);
  const [page, setPage] = useState(0);
  const pages = Math.ceil(data.items.length / 5);
  const currentPage = Math.min(page, pages - 1);
  return (
    <div className={`connection-group group-${data.kind}`}>
      <Handle type="target" position={Position.Top} />
      <header>
        <span>{data.kind.toUpperCase()}</span>
        <strong>{definition?.title ?? "References"}</strong>
        <small>{data.items.length}</small>
      </header>
      <div className="connection-group-items">
        {data.items.slice(currentPage * 5, currentPage * 5 + 5).map((item) => (
          <button
            key={item.id}
            type="button"
            className={`${item.missing ? "missing" : ""} ${data.selectedId === item.id ? "selected" : ""}`}
            aria-pressed={data.selectedId === item.id}
            onClick={() => data.onSelect(item)}
          >
            <span className="sr-only">Inspect {item.kind.toUpperCase()} </span>
            <strong>{item.target}</strong> <span>{caption(item)}</span>
          </button>
        ))}
      </div>
      {pages > 1 && (
        <footer>
          <button
            type="button"
            disabled={currentPage === 0}
            aria-label={`Previous ${data.kind.toUpperCase()} references`}
            onClick={() => setPage((value) => value - 1)}
          >
            Previous
          </button>
          <span>
            {currentPage * 5 + 1}-
            {Math.min((currentPage + 1) * 5, data.items.length)} of{" "}
            {data.items.length}
          </span>
          <button
            type="button"
            disabled={currentPage === pages - 1}
            aria-label={`Next ${data.kind.toUpperCase()} references`}
            onClick={() => setPage((value) => value + 1)}
          >
            Next
          </button>
        </footer>
      )}
    </div>
  );
}
const nodeTypes = { connectionGroup: ConnectionGroup };
export function DependencyMap({
  fileName,
  connections,
  selectedId,
  onSelect,
}: {
  fileName: string;
  connections: Connection[];
  selectedId?: string;
  onSelect: (item: Connection) => void;
}) {
  const { nodes, edges } = useMemo(() => {
    const kinds = [...new Set(connections.map((item) => item.kind))].sort(
      (a, b) =>
        ["copy", "call", "perform"].indexOf(a) -
        ["copy", "call", "perform"].indexOf(b),
    );
    const width = kinds.length * 300 + (kinds.length - 1) * 45;
    const nodes: Node[] = [
      {
        id: "source",
        type: "input",
        position: { x: Math.max(0, (width - 270) / 2), y: 0 },
        sourcePosition: Position.Bottom,
        data: {
          label: (
            <>
              <small>Selected program</small>
              <strong>{fileName}</strong>
            </>
          ),
        },
        className: "map-source",
        style: { width: 270 },
        ariaLabel: fileName,
      },
    ];
    const edges: Edge[] = [];
    kinds.forEach((kind, index) => {
      const id = `group-${kind}`;
      nodes.push({
        id,
        type: "connectionGroup",
        position: { x: index * 345, y: 145 },
        data: {
          kind,
          items: connections.filter((item) => item.kind === kind),
          selectedId,
          onSelect,
        },
        style: { width: 300 },
      });
      edges.push({
        id: `edge-${kind}`,
        source: "source",
        target: id,
        type: "smoothstep",
        style: {
          stroke:
            kind === "copy"
              ? "#8b6fc5"
              : kind === "call"
                ? "#418abe"
                : "#b48a32",
          strokeWidth: 2,
        },
      });
    });
    return { nodes, edges };
  }, [fileName, connections, selectedId, onSelect]);
  return (
    <div
      className="dependency-map grouped-map"
      aria-label={`Dependency map for ${fileName}`}
    >
      <ReactFlow
        key={fileName + nodes.length}
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.12, maxZoom: 1 }}
        minZoom={0.2}
        maxZoom={1.5}
        nodesDraggable={false}
        nodesConnectable={false}
        nodesFocusable={false}
        edgesFocusable={false}
        zoomOnScroll={false}
        preventScrolling={false}
      >
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
