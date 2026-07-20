import Link from "next/link";
import { SessionList } from "@/features/sessions/session-list";

export default function SessionsPage() {
  return (
    <div className="mx-auto w-full max-w-2xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight text-zinc-900">
          Sesi Trading
        </h1>
        <Link
          href="/sessions/new"
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          Buat Sesi Baru
        </Link>
      </div>
      <SessionList />
    </div>
  );
}
