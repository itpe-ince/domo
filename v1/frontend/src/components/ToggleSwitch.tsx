"use client";

/**
 * ToggleSwitch — Phase 9 L-E
 *
 * WCAG AAA 준수 토글 스위치.
 * role="switch", aria-checked, aria-labelledby 포함.
 * focus-visible ring 2px solid primary + offset 2px.
 */

interface ToggleSwitchProps {
  id: string;
  checked: boolean;
  onChange: (next: boolean) => void;
  label: string;
  description?: string;
  disabled?: boolean;
}

export function ToggleSwitch({
  id,
  checked,
  onChange,
  label,
  description,
  disabled = false,
}: ToggleSwitchProps) {
  const labelId = `${id}-label`;
  const descId = description ? `${id}-desc` : undefined;

  return (
    <div className="flex items-start gap-4">
      {/* Toggle button */}
      <button
        id={id}
        role="switch"
        type="button"
        aria-checked={checked}
        aria-labelledby={labelId}
        aria-describedby={descId}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={[
          "relative inline-flex h-7 w-12 flex-shrink-0 rounded-full border-2 transition-colors",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background",
          checked
            ? "bg-primary border-primary"
            : "bg-surface border-border",
          disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer",
        ].join(" ")}
      >
        <span
          aria-hidden="true"
          className={[
            "pointer-events-none inline-block h-5 w-5 rounded-full bg-background shadow-sm",
            "transform transition-transform duration-150",
            checked ? "translate-x-5" : "translate-x-0.5",
            "mt-0.5",
          ].join(" ")}
        />
      </button>

      {/* Label + description */}
      <div className="flex flex-col gap-0.5">
        <label
          id={labelId}
          htmlFor={id}
          className="text-text-primary font-medium cursor-pointer select-none"
        >
          {label}
        </label>
        {description && (
          <p id={descId} className="text-sm text-text-subtle">
            {description}
          </p>
        )}
      </div>
    </div>
  );
}
