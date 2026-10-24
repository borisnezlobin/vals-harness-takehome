"use client";

import { useId } from "react";

type Option<T extends string> = { value: T; label: string };

export function SegmentedControl<T extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: Option<T>[];
  value: T;
  onChange: (value: T) => void;
}) {
  const name = useId();
  return (
    <fieldset className="inline-flex flex-wrap gap-1 rounded-md bg-sunken p-1">
      <legend className="sr-only">{label}</legend>
      {options.map((option) => (
        <label
          key={option.value}
          className="relative inline-flex h-8 cursor-pointer items-center rounded-sm px-3 type-small text-ink-secondary transition-[color,background-color] duration-150 hover:text-ink has-checked:bg-surface has-checked:text-ink has-checked:shadow-raised has-focus-visible:outline-2 has-focus-visible:outline-offset-2 has-focus-visible:outline-ink"
        >
          <input
            type="radio"
            name={name}
            value={option.value}
            checked={option.value === value}
            onChange={() => onChange(option.value)}
            className="sr-only"
          />
          {option.label}
        </label>
      ))}
    </fieldset>
  );
}
