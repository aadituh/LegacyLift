"use client";
import { useId } from "react";
import { LayoutGroup, m } from "motion/react";
export function SegmentedControl<T extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: { value: T; label: string }[];
  value: T;
  onChange: (value: T) => void;
}) {
  const id = useId();
  return (
    <LayoutGroup id={id}>
      <div className="segmented" role="group" aria-label={label}>
        {options.map((option) => (
          <button
            type="button"
            key={option.value}
            aria-pressed={value === option.value}
            onClick={() => onChange(option.value)}
          >
            {value === option.value && (
              <m.span
                className="segment-indicator"
                layoutId="active"
                aria-hidden="true"
                transition={{ type: "spring", stiffness: 480, damping: 38 }}
              />
            )}
            <span>{option.label}</span>
          </button>
        ))}
      </div>
    </LayoutGroup>
  );
}
