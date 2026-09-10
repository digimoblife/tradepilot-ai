import type { ReactNode } from "react";

export interface MetricCardProps {
  /** Short uppercase label */
  label: string;
  /** The main value to display (string or number) */
  value: ReactNode;
  /** Tailwind text-color class for the value, e.g. "text-amber-600" */
  valueColorClass: string;
  /** Optional small suffix after value, e.g. "Emiten" or "T" */
  unit?: ReactNode;
  /** Icon element rendered on the right side of the card */
  icon: ReactNode;
  /** Tailwind classes for the icon wrapper background/border/text */
  iconWrapperClass: string;
}

/**
 * Institutional metric summary card used in the sessions list summary strip.
 * Shows a label, a large monospaced value, an optional unit, and a tinted icon.
 */
export function MetricCard({
  label,
  value,
  valueColorClass,
  unit,
  icon,
  iconWrapperClass,
}: MetricCardProps) {
  return (
    <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
      <div>
        <p className="text-xs font-bold uppercase tracking-wider text-slate-400">
          {label}
        </p>
        <p className={`text-2xl font-bold font-mono mt-1 ${valueColorClass}`}>
          {value}
          {unit && (
            <span className="text-xs font-medium text-slate-400 font-sans ml-1">
              {unit}
            </span>
          )}
        </p>
      </div>
      <div
        className={`w-10 h-10 rounded-lg flex items-center justify-center ${iconWrapperClass}`}
      >
        {icon}
      </div>
    </div>
  );
}
