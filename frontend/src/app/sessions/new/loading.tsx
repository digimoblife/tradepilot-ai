import { ButtonSpinner } from "@/components/button-spinner";

export default function NewSessionLoading() {
  return (
    <main
      role="status"
      aria-live="polite"
      className="mx-auto w-full max-w-4xl min-w-0 px-4 py-8 sm:px-6 lg:px-8 space-y-6 flex-1 animate-pulse"
    >
      <div className="pb-4 border-b border-slate-200">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Buat Sesi Baru
          </h1>
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold bg-blue-50 text-blue-700 border border-blue-200">
            <ButtonSpinner className="h-3 w-3 text-blue-600" />
            <span>Mempersiapkan Form…</span>
          </span>
        </div>
        <p className="mt-1 text-sm text-slate-500">
          Inisialisasi sesi analisis saham berbasis AI Gemini Pro dengan integrasi data pasar IDX.
        </p>
      </div>

      <div className="h-14 w-full bg-white rounded-xl border border-slate-200"></div>

      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-6">
        <div className="space-y-2">
          <div className="h-4 w-28 bg-slate-200 rounded"></div>
          <div className="h-10 w-full bg-slate-50 rounded-lg border border-slate-200"></div>
        </div>
        <div className="space-y-2">
          <div className="h-4 w-36 bg-slate-200 rounded"></div>
          <div className="h-10 w-full bg-slate-50 rounded-lg border border-slate-200"></div>
        </div>
        <div className="space-y-2">
          <div className="h-4 w-32 bg-slate-200 rounded"></div>
          <div className="h-24 w-full bg-slate-50 rounded-lg border border-slate-200"></div>
        </div>
        <div className="pt-4 border-t border-slate-200 flex justify-between">
          <div className="h-10 w-36 bg-slate-200 rounded-lg"></div>
          <div className="h-10 w-24 bg-slate-100 rounded-lg"></div>
        </div>
      </div>
    </main>
  );
}
