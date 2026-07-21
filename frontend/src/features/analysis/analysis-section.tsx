import type { ReactNode } from "react";

interface Props {
  title: string;
  children: ReactNode;
  className?: string;
}

export function AnalysisSection({ title, children, className = "" }: Props) {
  return (
    <section className={`rounded-lg border border-zinc-200 bg-white p-4 ${className}`}>
      <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-zinc-500">
        {title}
      </h3>
      {children}
    </section>
  );
}
