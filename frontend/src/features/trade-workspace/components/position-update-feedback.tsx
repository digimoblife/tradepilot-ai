import type { ReactNode } from "react";

export function PositionUpdateFeedback({ kind, children }: { kind: "error" | "success" | "processing"; children: ReactNode }) {
  const styles = {
    error: "border-[var(--color-status-danger)] bg-[var(--color-status-danger-subtle)] text-[var(--color-text-default)]",
    success: "border-[var(--color-status-success)] bg-[var(--color-surface-feedback)] text-[var(--color-text-default)]",
    processing: "border-[var(--color-border-default)] bg-[var(--color-elevated-background)] text-[var(--color-text-default)]",
  }[kind];
  return <div role={kind === "error" ? "alert" : "status"} aria-live="polite" className={`rounded-[var(--radius-compact)] border px-4 py-3 text-[var(--text-size-compact-body)] leading-[var(--text-line-body)] ${styles}`}>{children}</div>;
}
