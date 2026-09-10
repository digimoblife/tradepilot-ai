import { ButtonSpinner } from "@/components/button-spinner";

export default function SessionsLoading() {
  return (
    <div
      role="status"
      aria-live="polite"
      className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12 space-y-8 animate-pulse"
    >
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              Sesi Perdagangan
            </h1>
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold bg-blue-50 text-blue-700 border border-blue-200">
              <ButtonSpinner className="h-3 w-3 text-blue-600" />
              <span>Sinkronisasi Data…</span>
            </span>
          </div>
          <p className="mt-2 text-sm text-slate-500">
            Memuat sesi perdagangan…
          </p>
        </div>
      </div>

      {/* Quick Metrics Skeleton Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
            <div className="space-y-2">
              <div className="h-3 w-24 bg-slate-200 rounded"></div>
              <div className="h-6 w-16 bg-slate-200 rounded"></div>
            </div>
            <div className="w-10 h-10 rounded-lg bg-slate-100 flex items-center justify-center">
              <div className="w-5 h-5 bg-slate-200 rounded"></div>
            </div>
          </div>
        ))}
      </div>

      {/* Filter Toolbar Skeleton */}
      <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-2xs flex items-center justify-between gap-3">
        <div className="h-9 w-64 bg-slate-100 rounded-lg"></div>
        <div className="h-9 w-48 bg-slate-100 rounded-lg"></div>
      </div>

      {/* Session Cards Skeleton */}
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="bg-white rounded-2xl border border-slate-200 p-5 sm:p-6 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-11 h-11 rounded-xl bg-slate-100 border border-slate-200"></div>
                <div className="space-y-1.5">
                  <div className="h-5 w-24 bg-slate-200 rounded"></div>
                  <div className="h-3.5 w-40 bg-slate-100 rounded"></div>
                </div>
              </div>
              <div className="h-9 w-28 bg-slate-100 rounded-lg"></div>
            </div>
            <div className="h-16 w-full bg-slate-50 rounded-xl border border-slate-100"></div>
          </div>
        ))}
      </div>
    </div>
  );
}
