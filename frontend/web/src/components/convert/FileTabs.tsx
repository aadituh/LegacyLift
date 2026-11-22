import { FileCode2 } from "lucide-react";
export function FileTabs({
  labels,
  selectedIndex,
  onSelect,
}: {
  labels: { name: string; status?: string }[];
  selectedIndex: number;
  onSelect: (index: number) => void;
}) {
  if (!labels.length) return null;
  return (
    <nav className="file-sidebar" aria-label="Programs">
      {labels.map((f, i) => (
        <button
          key={f.name}
          type="button"
          aria-pressed={selectedIndex === i}
          onClick={() => onSelect(i)}
          title={f.name}
        >
          <FileCode2 size={16} aria-hidden="true" />
          <span>{f.name}</span>
        </button>
      ))}
    </nav>
  );
}
