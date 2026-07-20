import { statusLabel } from "./helpers";

interface Props {
  status: string;
}

export function LifecycleStatus({ status }: Props) {
  return (
    <section className="rounded-lg border border-zinc-200 bg-white p-4">
      <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-zinc-500">
        Status Lifecycle
      </h3>
      <p className="text-lg font-medium text-zinc-800">
        {statusLabel(status)}
      </p>
      <p className="mt-0.5 text-xs text-zinc-400">{status}</p>
    </section>
  );
}
