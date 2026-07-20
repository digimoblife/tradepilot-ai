import { CreateSessionForm } from "@/features/sessions/create-session-form";

export default function NewSessionPage() {
  return (
    <div className="mx-auto w-full max-w-lg px-4 py-8">
      <h1 className="mb-1 text-2xl font-bold tracking-tight text-zinc-900">
        Sesi Baru
      </h1>
      <p className="mb-6 text-sm text-zinc-500">
        Buat satu sesi perdagangan untuk satu saham.
      </p>
      <CreateSessionForm />
    </div>
  );
}
