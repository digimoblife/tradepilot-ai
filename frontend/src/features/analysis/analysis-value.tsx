import type { ReactNode } from "react";

interface Props {
  label: string;
  value: ReactNode;
  className?: string;
}

export function AnalysisValue({ label, value, className = "" }: Props) {
  const display = value === null || value === undefined ? "—" : value;
  return (
    <div className={`text-sm ${className}`}>
      <span className="text-zinc-400">{label}</span>
      <p className="text-zinc-800">{display}</p>
    </div>
  );
}
