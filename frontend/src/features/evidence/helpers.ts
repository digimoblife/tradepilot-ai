import type { EvidenceItem } from "@/types/evidence";

const REQUIRED_TYPES_BY_ANALYSIS: Record<string, readonly string[]> = {
  INITIAL_ANALYSIS: ["ORDERBOOK_SCREENSHOT", "CHART_THREE_MONTH", "CHART_SIX_MONTH"],
  WATCHING_UPDATE: ["ORDERBOOK_SCREENSHOT"],
  OPEN_POSITION_UPDATE: ["ORDERBOOK_SCREENSHOT"],
  CLOSING_ANALYSIS: [],
};

export const EVIDENCE_TYPE_LABELS: Record<string, string> = {
  ORDERBOOK_SCREENSHOT: "Screenshot Orderbook",
  CHART_THREE_MONTH: "Chart 3 Bulan",
  CHART_SIX_MONTH: "Chart 6 Bulan",
  CHART_DAILY: "Chart Harian",
  CHART_INTRADAY: "Chart Intraday",
  BROKER_SUMMARY: "Ringkasan Broker",
  FOREIGN_FLOW: "Arus Asing",
  NEWS_SCREENSHOT: "Screenshot Berita",
  CUSTOM_IMAGE: "Gambar Lainnya",
  USER_NOTE: "Catatan Pengguna",
  MARKET_DATA_SNAPSHOT: "Data Pasar",
};

const STATUS_LABELS: Record<string, string> = {
  AVAILABLE: "Aktif",
  SUPERSEDED: "Digantikan",
  EXCLUDED: "Tidak Digunakan",
  PENDING: "Menunggu",
  PROCESSING: "Diproses",
  UNREADABLE: "Tidak Terbaca",
  DUPLICATE: "Duplikat",
  FAILED: "Gagal",
  DELETED: "Dihapus",
};

export function evidenceTypeLabel(type: string): string {
  return EVIDENCE_TYPE_LABELS[type] ?? type;
}

export function evidenceStatusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status;
}

export interface RequiredTypeStatus {
  type: string;
  label: string;
  active: boolean;
}

export function getRequiredTypesStatus(
  items: EvidenceItem[],
  analysisType = "INITIAL_ANALYSIS",
): RequiredTypeStatus[] {
  const requiredTypes = REQUIRED_TYPES_BY_ANALYSIS[analysisType] ?? [];
  return requiredTypes.map((t) => ({
    type: t,
    label: evidenceTypeLabel(t),
    active: items.some((e) => e.evidence_type === t && e.status === "AVAILABLE"),
  }));
}

export function formatTimestamp(iso: string | null | undefined): string {
  if (!iso) return "-";
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return "-";
    return d.toLocaleDateString("id-ID", {
      year: "numeric", month: "short", day: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
  } catch {
    return "-";
  }
}

export const SUPPORTED_MIME_TYPES = "image/png,image/jpeg,image/webp";
