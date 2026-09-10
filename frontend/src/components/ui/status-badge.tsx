import type { SessionStatus } from "@/features/trade-workspace/types";

export interface StatusBadgeProps {
  status: SessionStatus;
  label: string;
  badgeClassName: string;
  dotClassName: string;
  /** Pass-through for test selectors that rely on data-canonical-status */
  "data-canonical-status"?: SessionStatus;
}

/**
 * Reusable status badge chip used in session list cards and archived sessions.
 * Renders a dot indicator + label with the provided color classes.
 */
export function StatusBadge({
  status,
  label,
  badgeClassName,
  dotClassName,
  "data-canonical-status": dataCanonicalStatus,
}: StatusBadgeProps) {
  return (
    <span
      data-canonical-status={dataCanonicalStatus ?? status}
      className={`px-2.5 py-0.5 rounded-md text-xs font-bold border flex items-center gap-1.5 ${badgeClassName}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${dotClassName}`} />
      {label}
    </span>
  );
}
