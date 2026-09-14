import type { ReactNode } from "react";
import type { MarketFactsSnapshot } from "../types";

/**
 * Shared, reusable building blocks for advisory result views (WAIT Update,
 * Position Update, and future analysis-result surfaces) inside the trade
 * workspace. Styled with the same CSS custom-property design tokens used
 * throughout the trade-workspace feature (globals.css `--color-*`,
 * `--radius-*`, `--space-*`, `--text-*`), so a redesign of any one field
 * stays visually consistent with its neighbors (forms, feedback banners,
 * position summary) instead of introducing a one-off look.
 */

// ---------------------------------------------------------------------------
// Field card — a labeled, heading-anchored container for one result field.
// ---------------------------------------------------------------------------

export function ResultFieldCard({
  label,
  headingLevel = "h4",
  tone = "neutral",
  children,
}: {
  label: string;
  headingLevel?: "h3" | "h4";
  tone?: "neutral" | "warning" | "danger";
  children: ReactNode;
}) {
  const Heading = headingLevel;
  const toneClass = fieldCardToneClasses[tone];
  return (
    <article
      className={`rounded-[var(--radius-compact)] border p-4 ${toneClass}`}
    >
      <Heading className="text-[var(--text-size-compact-body)] font-semibold text-[var(--color-text-strong)]">
        {label}
      </Heading>
      <div className="mt-2 text-[var(--text-size-compact-body)] leading-[var(--text-line-body)] text-[var(--color-text-default)]">
        {children}
      </div>
    </article>
  );
}

const fieldCardToneClasses: Record<"neutral" | "warning" | "danger", string> = {
  neutral: "border-[var(--color-border-default)] bg-[var(--color-elevated-background)]",
  warning: "border-[var(--color-status-warning)] bg-[var(--color-status-warning-subtle)]",
  danger: "border-[var(--color-status-danger)] bg-[var(--color-status-danger-subtle)]",
};

// ---------------------------------------------------------------------------
// Action badge — BUY / WAIT / SKIP advisory recommendation pill.
// ---------------------------------------------------------------------------

const actionBadgeClasses: Record<string, string> = {
  BUY: "border-[var(--color-status-success)] bg-[var(--color-status-success-subtle)] text-[var(--color-status-success)]",
  WAIT: "border-[var(--color-status-information)] bg-[var(--color-status-information-subtle)] text-[var(--color-status-information)]",
  SKIP: "border-[var(--color-status-danger)] bg-[var(--color-status-danger-subtle)] text-[var(--color-status-danger)]",
};
const actionBadgeFallbackClass =
  "border-[var(--color-border-default)] bg-[var(--color-surface-muted)] text-[var(--color-text-default)]";

export function ActionBadge({ action }: { action: string }) {
  const toneClass = actionBadgeClasses[action] ?? actionBadgeFallbackClass;
  return (
    <span
      className={`inline-flex items-center rounded-[var(--radius-compact)] border px-3 py-1 text-[var(--text-size-label)] font-bold uppercase tracking-wide ${toneClass}`}
    >
      {action}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Probability visualizations.
// ---------------------------------------------------------------------------

/** Normalizes a probability value that may arrive as 0-100, 0-1, or "NN%". */
export function toPercent(value: unknown): number | null {
  const raw = typeof value === "string" ? value.replace("%", "").trim() : value;
  const num = typeof raw === "number" ? raw : parseFloat(String(raw));
  if (!Number.isFinite(num)) return null;
  const pct = num > 0 && num <= 1 ? num * 100 : num;
  return Math.max(0, Math.min(100, pct));
}

export function DualProbabilityBar({
  upside,
  downside,
}: {
  upside: number;
  downside: number;
}) {
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-[var(--text-size-label)] font-semibold">
        <span className="text-[var(--color-status-success)]">Naik: {upside}%</span>
        <span className="text-[var(--color-status-danger)]">Turun: {downside}%</span>
      </div>
      <div className="flex h-2.5 w-full overflow-hidden rounded-full border border-[var(--color-border-default)] bg-[var(--color-surface-muted)]">
        <div
          style={{ width: `${upside}%` }}
          className="bg-[var(--color-status-success)] transition-all"
        />
        <div
          style={{ width: `${downside}%` }}
          className="bg-[var(--color-status-danger)] transition-all"
        />
      </div>
    </div>
  );
}

const gaugeToneClasses = {
  success: "text-[var(--color-status-success)]",
  warning: "text-[var(--color-status-warning)]",
  danger: "text-[var(--color-status-danger)]",
} as const;
const gaugeFillClasses = {
  success: "bg-[var(--color-status-success)]",
  warning: "bg-[var(--color-status-warning)]",
  danger: "bg-[var(--color-status-danger)]",
} as const;

export function SingleGauge({
  percent,
  label,
  tone: toneOverride,
}: {
  percent: number;
  /** Optional row label. Omit when the gauge sits under its own heading already. */
  label?: string;
  /** Force a color instead of the default percent-based success/warning/danger scale. */
  tone?: keyof typeof gaugeToneClasses;
}) {
  const tone: keyof typeof gaugeToneClasses =
    toneOverride ?? (percent >= 60 ? "success" : percent >= 35 ? "warning" : "danger");
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-end gap-2 text-[var(--text-size-label)] font-semibold">
        {label && <span className="text-[var(--color-text-default)]">{label}</span>}
        <span className={gaugeToneClasses[tone]}>{percent}%</span>
      </div>
      <div className="h-2.5 w-full overflow-hidden rounded-full border border-[var(--color-border-default)] bg-[var(--color-surface-muted)]">
        <div
          style={{ width: `${percent}%` }}
          className={`h-full transition-all ${gaugeFillClasses[tone]}`}
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Warning / risk list — highlighted alert box for warnings and key risks.
// ---------------------------------------------------------------------------

const warningListToneClasses = {
  warning:
    "border-[var(--color-status-warning)] bg-[var(--color-status-warning-subtle)] text-[var(--color-status-warning)]",
  danger:
    "border-[var(--color-status-danger)] bg-[var(--color-status-danger-subtle)] text-[var(--color-status-danger)]",
} as const;

/** Accepts either an array of strings or a single string (tolerates historical/loose payloads). */
export function toStringList(value: unknown): string[] {
  if (Array.isArray(value)) return value.map((item) => String(item));
  if (typeof value === "string" && value.trim()) return [value];
  return [];
}

export function WarningList({
  items,
  tone = "warning",
}: {
  items: string[];
  tone?: "warning" | "danger";
}) {
  if (items.length === 0) return null;
  const markerClass = warningListToneClasses[tone];
  return (
    <ul className="space-y-1.5">
      {items.map((item, idx) => (
        <li key={idx} className="flex items-start gap-2">
          <span
            aria-hidden="true"
            className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border text-[10px] font-bold ${markerClass}`}
          >
            !
          </span>
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

// ---------------------------------------------------------------------------
// Price delta badge — current price vs. confirmed entry price (Position Update).
// ---------------------------------------------------------------------------

export function PriceDeltaBadge({
  currentPrice,
  entryPrice,
}: {
  currentPrice: unknown;
  entryPrice: unknown;
}) {
  const current = typeof currentPrice === "number" ? currentPrice : parseFloat(String(currentPrice));
  const entry = typeof entryPrice === "number" ? entryPrice : parseFloat(String(entryPrice));
  if (!Number.isFinite(current) || !Number.isFinite(entry) || entry <= 0 || current <= 0) return null;

  const percent = ((current - entry) / entry) * 100;
  const positive = percent >= 0;
  const toneClass = positive
    ? "border-[var(--color-status-success)] bg-[var(--color-status-success-subtle)] text-[var(--color-status-success)]"
    : "border-[var(--color-status-danger)] bg-[var(--color-status-danger-subtle)] text-[var(--color-status-danger)]";

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-[var(--radius-compact)] border px-2.5 py-1 text-[var(--text-size-label)] font-bold ${toneClass}`}
    >
      {positive ? "▲" : "▼"} {positive ? "+" : ""}
      {percent.toFixed(2)}% dari entry
    </span>
  );
}

// ---------------------------------------------------------------------------
// Market facts strip — compact, system-fetched context chips.
// ---------------------------------------------------------------------------

type ChipTone = "success" | "danger" | "warning" | "neutral";

const chipToneClasses: Record<ChipTone, string> = {
  success:
    "border-[var(--color-status-success)] bg-[var(--color-status-success-subtle)] text-[var(--color-status-success)]",
  danger:
    "border-[var(--color-status-danger)] bg-[var(--color-status-danger-subtle)] text-[var(--color-status-danger)]",
  warning:
    "border-[var(--color-status-warning)] bg-[var(--color-status-warning-subtle)] text-[var(--color-status-warning)]",
  neutral: "border-[var(--color-border-default)] bg-[var(--color-surface-muted)] text-[var(--color-text-default)]",
};

/** Days between an ISO date string and now; null when unparsable. */
function daysFromNow(isoDate: string): number | null {
  const target = new Date(isoDate).getTime();
  if (Number.isNaN(target)) return null;
  return Math.ceil((target - Date.now()) / (1000 * 60 * 60 * 24));
}

export function MarketFactsStrip({ marketFacts }: { marketFacts?: MarketFactsSnapshot | null }) {
  if (!marketFacts) return null;

  const chips: Array<{ key: string; label: string; tone: ChipTone }> = [];

  if (marketFacts.index_name && marketFacts.index_change_percent != null) {
    const positive = marketFacts.index_change_percent >= 0;
    chips.push({
      key: "index",
      label: `${marketFacts.index_name} ${positive ? "+" : ""}${marketFacts.index_change_percent}%`,
      tone: positive ? "success" : "danger",
    });
  }

  if (marketFacts.volume_vs_average_ratio != null) {
    chips.push({
      key: "volume",
      label: `Volume ${marketFacts.volume_vs_average_ratio}x rata-rata`,
      tone: marketFacts.volume_vs_average_ratio >= 1.5 ? "warning" : "neutral",
    });
  }

  if (marketFacts.ma_alignment) {
    chips.push({
      key: "ma",
      label: marketFacts.ma_alignment.replace(/_/g, " "),
      tone:
        marketFacts.ma_alignment === "BULLISH_ALIGNMENT"
          ? "success"
          : marketFacts.ma_alignment === "BEARISH_ALIGNMENT"
            ? "danger"
            : "neutral",
    });
  }

  if (marketFacts.foreign_status) {
    chips.push({
      key: "foreign",
      label: `Foreign: ${marketFacts.foreign_status}`,
      tone: marketFacts.foreign_status.includes("ACCUMULATION")
        ? "success"
        : marketFacts.foreign_status.includes("DISTRIBUTION")
          ? "danger"
          : "neutral",
    });
  }

  if (marketFacts.next_earnings_date) {
    const days = daysFromNow(marketFacts.next_earnings_date);
    if (days !== null && days >= 0 && days <= 7) {
      chips.push({
        key: "earnings",
        label: `Lapkeu ${marketFacts.next_earnings_date} (${days} hari lagi)`,
        tone: "warning",
      });
    }
  }

  if (chips.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-2" aria-label="Ringkasan Data Pasar">
      {chips.map((chip) => (
        <span
          key={chip.key}
          className={`inline-flex items-center rounded-[var(--radius-compact)] border px-2.5 py-1 text-[var(--text-size-status)] font-semibold ${chipToneClasses[chip.tone]}`}
        >
          {chip.label}
        </span>
      ))}
    </div>
  );
}
