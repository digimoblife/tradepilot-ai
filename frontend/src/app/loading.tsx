import { ButtonSpinner } from "@/components/button-spinner";

export default function GlobalLoading() {
  return (
    <div
      role="status"
      aria-live="polite"
      className="min-h-[70vh] w-full flex flex-col items-center justify-center p-6 text-center"
    >
      <div className="relative flex items-center justify-center mb-4">
        <div className="w-12 h-12 rounded-2xl bg-blue-50 border border-blue-200 flex items-center justify-center shadow-xs">
          <ButtonSpinner className="h-6 w-6 text-blue-600" />
        </div>
        <span className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-emerald-500 animate-ping" />
      </div>
      <h2 className="text-base font-bold text-slate-800 tracking-tight">Memuat Halaman…</h2>
      <p className="text-xs text-slate-500 font-mono mt-1">TradePilot AI Institutional Platform</p>
    </div>
  );
}
