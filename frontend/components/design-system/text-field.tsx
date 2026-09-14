import { useId, type InputHTMLAttributes } from "react";

// CDD-079 (WOW-I1) §8/§12: the systemic fix for the two known bare-input
// occurrences (frontend/app/context/_components/context-lookup.tsx,
// frontend/app/quality/evidence-fitness/page.tsx). Tailwind's Preflight
// import in globals.css strips all default browser input chrome -- a
// bare <input> with no className is visually imperceptible against a
// panel. This component provides its own explicit, always-visible
// boundary (.obs-text-field-input in globals.css) so no consumer can
// regress back into the defect by omitting a className.
export function TextField({
  label,
  error,
  id,
  ...inputProps
}: {
  label: string;
  error?: string;
  id?: string;
} & Omit<InputHTMLAttributes<HTMLInputElement>, "id">) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const errorId = error ? `${inputId}-error` : undefined;

  return (
    <div className={`obs-text-field${error ? " obs-text-field--error" : ""}`}>
      <label className="obs-text-field-label" htmlFor={inputId}>
        {label}
      </label>
      <input
        {...inputProps}
        id={inputId}
        className="obs-text-field-input"
        aria-invalid={error ? true : undefined}
        aria-describedby={errorId}
      />
      {error ? (
        <span className="obs-text-field-error" id={errorId} role="alert">
          {error}
        </span>
      ) : null}
    </div>
  );
}
