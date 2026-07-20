interface SectionPlaceholderProps {
  title: string;
  message?: string;
}

export function SectionPlaceholder({
  title,
  message = "Fitur ini akan tersedia pada tahap berikutnya.",
}: SectionPlaceholderProps) {
  return (
    <section className="rounded-lg border border-zinc-200 bg-white p-4">
      <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-zinc-500">
        {title}
      </h3>
      <p className="text-sm text-zinc-400">{message}</p>
    </section>
  );
}
