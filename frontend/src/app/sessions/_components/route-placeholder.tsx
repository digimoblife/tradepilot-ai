import Link from "next/link";

type RoutePlaceholderProps = {
  title: string;
  description: string;
  backHref?: string;
  backLabel?: string;
  children?: React.ReactNode;
};

export function RoutePlaceholder({
  title,
  description,
  backHref,
  backLabel,
  children,
}: RoutePlaceholderProps) {
  return (
    <section className="mx-auto flex w-full max-w-3xl flex-1 flex-col px-4 py-6 sm:px-6 sm:py-10 lg:px-8">
      <h1 className="text-2xl font-bold tracking-tight text-[var(--color-text-strong)]">
        {title}
      </h1>
      <p className="mt-3 text-[var(--color-text-muted)]">{description}</p>
      {children}
      {backHref && backLabel ? (
        <Link
          href={backHref}
          className="mt-8 w-fit text-sm font-semibold text-[var(--color-action-primary)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
        >
          {backLabel}
        </Link>
      ) : null}
    </section>
  );
}
