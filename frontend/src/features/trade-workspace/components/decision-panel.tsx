import type { DecisionAction, SkipReason } from "../types";
import type { BuyFormState } from "./buy-decision-form";
import { BuyDecisionForm } from "./buy-decision-form";
import { SkipDecisionForm } from "./skip-decision-form";

export function DecisionPanel({
  actions,
  decisionSubmitting,
  decisionError,
  decisionSuccess,
  buyForm,
  skipReasons,
  skipReason,
  skipNote,
  onBuyChange,
  onBuySubmit,
  onWait,
  onSkipReasonChange,
  onSkipNoteChange,
  onSkipSubmit,
}: {
  actions: DecisionAction[];
  decisionSubmitting: "WAIT" | "SKIP" | "BUY" | null;
  decisionError: string | null;
  decisionSuccess: string | null;
  buyForm: BuyFormState;
  skipReasons: Array<{ value: SkipReason; label: string }>;
  skipReason: SkipReason | "";
  skipNote: string;
  onBuyChange: (field: keyof BuyFormState, value: string) => void;
  onBuySubmit: (event: React.FormEvent<HTMLFormElement>) => void;
  onWait: () => void;
  onSkipReasonChange: (reason: SkipReason | "") => void;
  onSkipNoteChange: (note: string) => void;
  onSkipSubmit: (event: React.FormEvent<HTMLFormElement>) => void;
}) {
  return <section aria-label="Keputusan sesi" className="min-w-0 overflow-hidden rounded-[var(--radius-standard)] border border-[var(--color-border-strong)] bg-[var(--color-surface-standard)] shadow-[var(--elevation-low)]">
    <div className="min-w-0 space-y-[var(--space-2)] p-[var(--space-card)]">
      <h3 className="text-[var(--text-size-section-title)] font-semibold leading-[var(--text-line-heading)] text-[var(--color-text-strong)]">Keputusan Anda</h3>
      {decisionError && <p role="alert" className="break-words rounded-[var(--radius-compact)] border border-[var(--color-status-danger)] bg-[var(--color-status-danger-subtle)] p-[var(--space-3)] text-[var(--text-size-compact-body)] leading-[var(--text-line-body)] text-[var(--color-text-default)]">{decisionError}</p>}
      {decisionSuccess && <p role="status" aria-live="polite" className="break-words rounded-[var(--radius-compact)] border border-[var(--color-status-success)] bg-[var(--color-surface-feedback)] p-[var(--space-3)] text-[var(--text-size-compact-body)] leading-[var(--text-line-body)] text-[var(--color-text-default)]">{decisionSuccess}</p>}
      <div className="flex min-w-0 flex-col gap-[var(--space-action)] sm:flex-row sm:flex-wrap" aria-label="Pilihan keputusan">
        {actions.includes("WAIT") && <button type="button" disabled={decisionSubmitting !== null} aria-busy={decisionSubmitting === "WAIT"} onClick={onWait} className="min-h-11 rounded-[var(--radius-compact)] border border-[var(--color-status-warning)] bg-[var(--color-status-warning-subtle)] px-[var(--space-4)] py-[var(--space-2)] text-[var(--text-size-compact-body)] font-semibold text-[var(--color-text-strong)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-status-warning)] disabled:cursor-not-allowed disabled:border-[var(--color-border-default)] disabled:bg-[var(--color-surface-muted)] disabled:text-[var(--color-text-muted)]">{decisionSubmitting === "WAIT" ? "Menyimpan…" : "WAIT"}</button>}
      </div>
    </div>
    {actions.includes("SKIP") && <SkipDecisionForm skipReasons={skipReasons} skipReason={skipReason} skipNote={skipNote} busy={decisionSubmitting !== null} submitting={decisionSubmitting === "SKIP"} onReasonChange={onSkipReasonChange} onNoteChange={onSkipNoteChange} onSubmit={onSkipSubmit} />}
    {actions.includes("BUY") && <BuyDecisionForm buyForm={buyForm} busy={decisionSubmitting !== null} submitting={decisionSubmitting === "BUY"} onChange={onBuyChange} onSubmit={onBuySubmit} />}
  </section>;
}
