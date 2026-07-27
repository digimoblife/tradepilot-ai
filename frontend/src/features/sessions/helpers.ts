const STATUS_MAP: Record<string, string> = {
  DRAFT: "Draf",
  READY_FOR_INITIAL_ANALYSIS: "Siap Dianalisis",
  READY_FOR_ANALYSIS: "Siap Dianalisis",
  ANALYZING: "Sedang Dianalisis",
  INITIAL_ANALYZED: "Analisis Awal Selesai",
  WATCHING: "Dipantau",
  OPEN_POSITION: "Posisi Terbuka",
  PARTIALLY_CLOSED: "Ditutup Sebagian",
  CLOSED: "Selesai",
  CLOSED_SKIPPED: "Dilewatkan",
  CLOSED_TAKE_PROFIT: "Selesai",
  CLOSED_STOP_LOSS: "Selesai",
  CLOSED_MANUAL: "Selesai",
  CANCELLED: "Dibatalkan",
  ARCHIVED: "Diarsipkan",
};

export function statusLabel(status: string): string {
  return STATUS_MAP[status] ?? status;
}

export function formatTimestamp(iso: string): string {
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return "";
    return d.toLocaleDateString("id-ID", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
}
