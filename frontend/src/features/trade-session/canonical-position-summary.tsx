import type { TradeState } from "@/types/trade-session";
import { displayValue, formatTimestamp } from "./helpers";

interface Props {
  tradeState: TradeState;
}

export function CanonicalPositionSummary({ tradeState }: Props) {
  return (
    <section className="rounded-lg border border-zinc-200 bg-white p-4">
      <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-zinc-500">
        Data Posisi Terkonfirmasi
      </h3>
      <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">
        <Field label="Status Posisi" value={tradeState.position_status} />
        <Field label="Harga Masuk" value={displayValue(tradeState.entry_price)} />
        <Field label="Waktu Masuk" value={formatTimestamp(tradeState.entry_at)} />
        <Field label="Jumlah Awal" value={displayValue(tradeState.original_quantity)} />
        <Field label="Sisa" value={displayValue(tradeState.remaining_quantity)} />
        <Field label="Stop Loss" value={displayValue(tradeState.active_stop_loss)} />
        <Field label="Target" value={displayValue(tradeState.active_target)} />
        <Field label="Rata-rata Keluar" value={displayValue(tradeState.average_exit_price)} />
        <Field label="Realized P&L" value={displayValue(tradeState.realized_pnl)} />
        <Field label="Return" value={displayValue(tradeState.realized_return)} />
        <Field label="Versi State" value={String(tradeState.state_version)} />
      </div>
    </section>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-zinc-400">{label}</p>
      <p className="mt-0.5 font-medium text-zinc-800">{value}</p>
    </div>
  );
}
