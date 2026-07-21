const STATUS_MAP: Record<string, string> = {
  DRAFT: "Draf",
  READY_FOR_ANALYSIS: "Siap Dianalisis",
  ANALYZING: "Sedang Dianalisis",
  WATCHING: "Dipantau",
  OPEN_POSITION: "Posisi Terbuka",
  PARTIALLY_CLOSED: "Ditutup Sebagian",
  CLOSED_TAKE_PROFIT: "Selesai",
  CLOSED_STOP_LOSS: "Selesai",
  CLOSED_MANUAL: "Selesai",
  CANCELLED: "Dibatalkan",
  ARCHIVED: "Diarsipkan",
};

export function statusLabel(status: string): string {
  return STATUS_MAP[status] ?? status;
}

const ACTION_MAP: Record<string, string> = {
  MARK_READY: "Tandai Siap",
  OPEN_POSITION: "Buka Posisi",
  CONFIRM_STOP: "Konfirmasi Stop Loss",
  CHANGE_STOP: "Ubah Stop Loss",
  CONFIRM_TARGET: "Konfirmasi Target",
  CHANGE_TARGET: "Ubah Target",
  PARTIAL_EXIT: "Partial Exit",
  FULL_EXIT: "Tutup Posisi",
  CANCEL: "Batalkan",
  ARCHIVE: "Arsipkan",
};

export function actionLabel(action: string): string {
  return ACTION_MAP[action] ?? action;
}

export function formatTimestamp(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return "—";
    return d.toLocaleDateString("id-ID", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "—";
  }
}

export function displayValue(value: string | null | undefined): string {
  if (value === null || value === undefined) return "Belum tersedia";
  return value;
}
