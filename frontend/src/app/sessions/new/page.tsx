import Link from "next/link";
import { CreateSessionNavigation } from "@/features/sessions/create-session-navigation";

export default function NewSessionPage() {
  return (
    <div className="w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 flex-1">
      {/* Navigation / Back to Sessions */}
      <div className="mb-6 flex items-center justify-between">
        <Link
          href="/sessions"
          className="inline-flex items-center text-sm font-semibold text-slate-600 hover:text-slate-900 transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
        >
          <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path d="M10 19l-7-7m0 0l7-7m-7 7h18" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
          </svg>
          Kembali ke Daftar Sesi
        </Link>
        <div className="flex items-center space-x-2 text-xs text-slate-500 font-mono">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span>SYSTEM READY</span>
        </div>
      </div>

      {/* Page Header */}
      <div className="mb-8">
        <div className="flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-blue-600 font-mono mb-2">
          <span>Inisiasi Analisis</span>
          <span>/</span>
          <span>Protokol v2.4</span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
          Buat Sesi Baru
        </h1>
        <p className="mt-1.5 text-sm text-slate-600 max-w-2xl">
          Tentukan parameter emiten saham yang akan dianalisis. Sistem akan memvalidasi data pasar secara real-time dari BEI sebelum menghasilkan intelligence rekomendasi.
        </p>
      </div>

      <CreateSessionNavigation />
    </div>
  );
}

