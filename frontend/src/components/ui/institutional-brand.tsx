/**
 * InstitutionalBrand — the TradePilot ⚡ logo lockup.
 *
 * Used in:
 *  - ModernSessionWorkspace sticky header
 *  - Login page
 *
 * Props allow customising size for different placements.
 */
export interface InstitutionalBrandProps {
  /** Icon container size class, e.g. "w-8 h-8" (header) or "w-12 h-12" (login) */
  iconSizeClass?: string;
  /** Text size class for "TradePilot", e.g. "text-sm" (header) or "text-2xl" (login) */
  textSizeClass?: string;
  /** Whether to show the engine tagline row ("GEMINI ENGINE PRO") — defaults to false */
  showEngineTag?: boolean;
  /** Extra wrapper class, e.g. "shrink-0" */
  className?: string;
}

export function InstitutionalBrand({
  iconSizeClass = "w-9 h-9",
  textSizeClass = "text-base",
  showEngineTag = false,
  className = "",
}: InstitutionalBrandProps) {
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div
        className={`${iconSizeClass} rounded-lg bg-blue-600 text-white flex items-center justify-center shadow-xs font-bold`}
      >
        ⚡
      </div>
      <div className="flex flex-col">
        <div className="flex items-center gap-1">
          <span className={`font-bold tracking-tight text-slate-900 ${textSizeClass}`}>
            TradePilot
          </span>
          <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 font-bold uppercase border border-blue-200">
            AI
          </span>
        </div>
        {showEngineTag && (
          <div className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="font-mono text-[10px] text-slate-500 font-medium">
              GEMINI ENGINE PRO
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
