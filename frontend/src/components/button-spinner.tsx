export function ButtonSpinner({
  className = "h-4 w-4",
  borderClassName = "border-current border-t-transparent",
}: {
  className?: string;
  borderClassName?: string;
}) {
  return (
    <span
      className={`inline-block shrink-0 animate-spin rounded-full border-2 ${borderClassName} ${className}`}
      aria-hidden="true"
    />
  );
}
