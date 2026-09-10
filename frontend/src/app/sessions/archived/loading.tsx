import { ButtonSpinner } from "@/components/button-spinner";

export default function ArchivedSessionsLoading() {
  return (
    <div
      role="status"
      aria-live="polite"
      className="mx-auto w-full max-w-7xl min-w-0 px-4 py-6 sm:px-6 sm:py-8 lg:px-8 space-y-6 flex-1 animate-pulse"
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Sesi Diarsipkan</h1>
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold bg-blue-50 text-blue-700 border border-blue-200">
              <ButtonSpinner className="h-3 w-3 text-blue-600" />
              <span>Memuat Riwayat…</span>
            </span>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Sesi trading yang telah selesai dan dipindahkan dari daftar Sesi aktif.
          </p>
        </div>
        <div className="h-9 w-32 bg-slate-100 rounded-lg"></div>
      </div>

      <div className="h-14 w-full bg-white rounded-xl border border-slate-200 p-3 flex items-center justify-between">
        <div className="h-8 w-64 bg-slate-100 rounded-lg"></div>
        <div className="h-8 w-48 bg-slate-100 rounded-lg"></div>
      </div>

      <div className="space-y-3.5">
        {[1, 2, 3].map((i) => (
          <div key={i} className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="space-y-2">
                <div className="h-5 w-32 bg-slate-200 rounded"></div>
                <div className="h-4 w-48 bg-slate-100 rounded"></div>
              </div>
              <div className="h-9 w-24 bg-slate-100 rounded-lg"></div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
