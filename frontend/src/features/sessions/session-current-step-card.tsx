import type { SessionCurrentStepPresentation } from "@/features/sessions/session-current-step";

const STATE_STYLES: Record<SessionCurrentStepPresentation["state"], string> = {
  actionable: "border-[var(--color-border-default)] bg-[var(--color-surface-standard)]",
  processing: "border-[var(--color-status-processing)] bg-[var(--color-status-processing-subtle)]",
  failed: "border-[var(--color-status-danger)] bg-[var(--color-status-danger-subtle)]",
  "read-only": "border-[var(--color-border-strong)] bg-[var(--color-surface-factual)]",
  inconsistent: "border-[var(--color-status-warning)] bg-[var(--color-status-warning-subtle)]",
};

export function SessionCurrentStepCard({
  presentation,
  sessionId,
}: {
  presentation: SessionCurrentStepPresentation;
  sessionId?: string;
}) {
  return (
    <article
      aria-labelledby="session-current-step-title"
      data-current-step={presentation.key}
      className={`min-w-0 rounded-[var(--radius-large)] border p-[var(--space-card)] shadow-[var(--elevation-low)] sm:p-6 ${STATE_STYLES[presentation.state]}`}
    >
      <p className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">
        {presentation.eyebrow}
      </p>
      <h2
        id="session-current-step-title"
        className="mt-2 break-words text-xl font-bold leading-[var(--text-line-heading)] text-[var(--color-text-strong)] sm:text-2xl"
      >
        {presentation.title}
      </h2>
      <p className="mt-3 break-words text-sm leading-[var(--text-line-body)] text-[var(--color-text-default)] sm:text-base">
        {presentation.description}
      </p>
      {presentation.supportingText ? (
        <p className="mt-3 break-words text-sm font-medium text-[var(--color-text-muted)]">
          {presentation.supportingText}
        </p>
      ) : null}
      {presentation.navigationAction && sessionId ? <Link href={`/sessions/${encodeURIComponent(sessionId)}/initial-evidence`} className="mt-4 inline-flex min-h-11 items-center font-semibold text-[var(--color-action-primary)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]">{presentation.navigationAction.label}</Link> : null}
    </article>
  );
}
import Link from "next/link";
