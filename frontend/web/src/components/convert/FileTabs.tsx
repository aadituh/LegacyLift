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
  return labels.length > 8 ? (
    <div className="field">
      <label htmlFor="selected-file">Selected program</label>
      <select
        id="selected-file"
        value={selectedIndex}
        onChange={(e) => onSelect(Number(e.target.value))}
      >
        {labels.map((f, i) => (
          <option key={f.name} value={i}>
            {f.name}
          </option>
        ))}
      </select>
    </div>
  ) : (
    <div className="file-tabs" role="group" aria-label="Select a program">
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
    </div>
  );
}
