"use client";
import { Upload } from "lucide-react";
import { Spinner } from "./Spinner";
export function FileInputButton({
  label,
  accept,
  multiple = true,
  disabled,
  isPending,
  onFiles,
}: {
  label: string;
  accept: string;
  multiple?: boolean;
  disabled?: boolean;
  isPending?: boolean;
  onFiles: (files: File[]) => void;
}) {
  return (
    <label
      className={`button button-secondary file-input ${disabled || isPending ? "is-disabled" : ""}`}
    >
      {isPending ? <Spinner /> : <Upload size={17} aria-hidden="true" />}
      {label}
      <input
        className="sr-only"
        type="file"
        accept={accept}
        multiple={multiple}
        disabled={disabled || isPending}
        onChange={(event) => {
          const files = Array.from(event.target.files ?? []);
          event.target.value = "";
          if (files.length) onFiles(files);
        }}
      />
    </label>
  );
}
