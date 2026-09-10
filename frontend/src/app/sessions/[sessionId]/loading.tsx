import { ButtonSpinner } from "@/components/button-spinner";

export default function SessionWorkspaceLoading() {
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex flex-col min-h-screen w-full bg-slate-50 text-slate-800"
    >
      {/* Header Skeleton */}
      <header className="sticky top-0 left-0 right-0 z-40 bg-white border-b border-slate-200">
        <div className="h-14 sm:h-16 w-full px-3 sm:px-6 flex items-center justify-between gap-3 max-w-[1600px] mx-auto">
          <div className="flex items-center gap-3 animate-pulse">
            <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-lg bg-blue-600 text-white flex items-center justify-center font-bold text-sm shadow-xs">
              ⚡
            </div>
            <div className="flex items-center gap-1.5">
              <span className="font-bold text-slate-900 text-sm sm:text-base">TradePilot</span>
              <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 font-bold border border-blue-200">
                AI
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <ButtonSpinner className="h-4 w-4 text-blue-600" />
            <span className="text-xs font-mono font-semibold text-slate-500 hidden sm:inline">
              Mempersiapkan Workspace AI…
            </span>
          </div>
        </div>
      </header>

      {/* Main Canvas Skeleton */}
      <main className="pt-4 sm:pt-6 pb-28 w-full px-3 sm:px-6 bg-slate-50 flex-1">
        <div className="flex flex-col w-full space-y-4 max-w-[1600px] mx-auto animate-pulse">
          {/* Top Banner Skeleton */}
          <div className="h-12 w-full rounded-xl bg-white border border-slate-200 p-3 flex items-center gap-3">
            <div className="w-6 h-6 rounded-full bg-slate-100"></div>
            <div className="h-4 w-48 bg-slate-100 rounded"></div>
          </div>

          {/* Emiten Primary Card Skeleton */}
          <div className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6 shadow-xs space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-xl bg-slate-100 border border-slate-200"></div>
                <div className="space-y-2">
                  <div className="h-7 w-28 bg-slate-200 rounded"></div>
                  <div className="h-4 w-48 bg-slate-100 rounded"></div>
                </div>
              </div>
              <div className="h-10 w-36 bg-slate-100 rounded-lg"></div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-20 rounded-xl bg-slate-50 border border-slate-100 p-3 space-y-2">
                  <div className="h-3 w-16 bg-slate-200 rounded"></div>
                  <div className="h-6 w-24 bg-slate-200 rounded"></div>
                </div>
              ))}
            </div>
          </div>

          {/* Content Grid Skeleton */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="lg:col-span-2 space-y-4">
              <div className="h-80 rounded-2xl bg-white border border-slate-200 p-5 space-y-3">
                <div className="h-5 w-40 bg-slate-200 rounded"></div>
                <div className="h-60 w-full bg-slate-50 rounded-xl border border-slate-100"></div>
              </div>
            </div>
            <div className="space-y-4">
              <div className="h-80 rounded-2xl bg-white border border-slate-200 p-5 space-y-3">
                <div className="h-5 w-32 bg-slate-200 rounded"></div>
                <div className="h-60 w-full bg-slate-50 rounded-xl border border-slate-100"></div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
