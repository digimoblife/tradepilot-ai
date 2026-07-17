export default function Home() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-4">
      <main className="mx-auto max-w-xl py-20 text-center">
        <h1 className="text-4xl font-bold tracking-tight">
          TradePilot AI
        </h1>
        <p className="mt-3 text-lg font-medium text-zinc-500">
          One Trade, One Story
        </p>
        <div className="mt-10 space-y-4 text-left text-zinc-600">
          <p>
            Workspace analisis trading dari tahap watching hingga closing.
          </p>
          <p>
            Setiap sesi perdagangan memiliki halaman khusus yang berisi
            riwayat lengkap: tesis awal, evidence, analisis AI, posisi,
            dan jurnal akhir.
          </p>
          <p className="text-sm text-zinc-400">
            Fondasi aplikasi sedang disiapkan.
          </p>
        </div>
      </main>
    </div>
  );
}
