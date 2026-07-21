const SETUP_STATUS_LABEL: Record<string, string> = {
  WAITING_FOR_CONFIRMATION: "Menunggu Konfirmasi",
  CONFIRMED: "Terkonfirmasi",
  NOT_PRESENT: "Tidak Ada",
  CANCELLED: "Dibatalkan",
};

const ACTION_LABEL: Record<string, string> = {
  WAIT: "Tunggu",
  ENTER_IF_CONFIRMED: "Entry Jika Terkonfirmasi",
  DO_NOT_ENTER: "Jangan Entry",
  HOLD: "Tahan",
  HOLD_WITH_CAUTION: "Tahan dengan Hati-hati",
  DO_NOT_ADD: "Jangan Tambah",
  ADD_ONLY_IF_CONFIRMED: "Tambah Jika Terkonfirmasi",
  REDUCE_RISK: "Kurangi Risiko",
  CONSIDER_PARTIAL_EXIT: "Pertimbangkan Partial Exit",
  REVIEW_EXIT: "Review Exit",
  EXIT: "Exit",
  CANCEL_SETUP: "Batalkan Setup",
  NO_ACTION: "Tidak Ada Tindakan",
};

const STRENGTH_LABEL: Record<string, string> = {
  STRONG: "Kuat",
  MODERATE: "Sedang",
  LOW: "Rendah",
  WEAK: "Lemah",
  HIGH: "Tinggi",
  NORMAL: "Normal",
  IMPROVING: "Membaik",
  INTACT: "Utuh",
  WEAKENING: "Melemah",
  BROKEN: "Rusak",
  RECOVERING: "Memulihkan",
  MIXED: "Campuran",
  UNKNOWN: "Tidak Diketahui",
};

const TREND_LABEL: Record<string, string> = {
  STRONGLY_UP: "Naik Kuat",
  UP: "Naik",
  SIDEWAYS: "Sideways",
  DOWN: "Turun",
  STRONGLY_DOWN: "Turun Kuat",
};

const ALIGNMENT_LABEL: Record<string, string> = {
  STRONGLY_ALIGNED: "Sangat Selaras",
  ALIGNED: "Selaras",
  PARTIALLY_ALIGNED: "Sebagian Selaras",
  CONFLICTING: "Bertentangan",
  INSUFFICIENT_DATA: "Data Tidak Mencukupi",
};

const RISK_LEVEL_LABEL: Record<string, string> = {
  LOW: "Rendah",
  MODERATE: "Sedang",
  HIGH: "Tinggi",
  VERY_HIGH: "Sangat Tinggi",
};

const BIAS_LABEL: Record<string, string> = {
  BULLISH: "Bullish",
  BEARISH: "Bearish",
  NEUTRAL: "Netral",
};

const HOLDING_PERIOD_LABEL: Record<string, string> = {
  SHORT_TERM: "Jangka Pendek",
  MEDIUM_TERM: "Jangka Menengah",
  LONG_TERM: "Jangka Panjang",
};

const ENUM_LABELS: Record<string, Record<string, string>> = {
  setup_status: SETUP_STATUS_LABEL,
  recommended_action: ACTION_LABEL,
  buyer_strength: STRENGTH_LABEL,
  seller_pressure: STRENGTH_LABEL,
  momentum: STRENGTH_LABEL,
  volume_condition: STRENGTH_LABEL,
  trend: TREND_LABEL,
  structure_status: STRENGTH_LABEL,
  multi_timeframe_alignment: ALIGNMENT_LABEL,
  short_term_trend: TREND_LABEL,
  medium_term_trend: TREND_LABEL,
  dominant_structure: STRENGTH_LABEL,
  main_confirmation: { BREAKOUT: "Breakout", BOUNCE: "Bounce", BREAKDOWN: "Breakdown", REVERSAL: "Reversal" },
  main_conflict: {
    OVERBOUGHT: "Overbought",
    OVERSOLD: "Oversold",
    DIVERGENCE: "Divergence",
    WEAK_VOLUME: "Volume Lemah",
    RESISTANCE: "Resistance",
    NONE: "Tidak Ada",
  },
  chase_risk: STRENGTH_LABEL,
  entry_type: {
    PRICE_ZONE: "Zona Harga",
    EXACT_PRICE: "Harga Pasti",
    BREAKOUT_CONFIRMATION: "Konfirmasi Breakout",
    PULLBACK_CONFIRMATION: "Konfirmasi Pullback",
    WAIT: "Tunggu",
    NO_ENTRY: "Tidak Entry",
  },
  risk_level: RISK_LEVEL_LABEL,
  bias: BIAS_LABEL,
  expected_holding_period: HOLDING_PERIOD_LABEL,
  setup_quality: STRENGTH_LABEL,
};

export function enumLabel(category: string, value: string | null | undefined): string {
  if (!value) return "—";
  const map = ENUM_LABELS[category];
  if (map && map[value]) return map[value];
  return value;
}

export function percentage(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `${value}%`;
}

export function currency(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return value.toLocaleString("id-ID");
}

export function displayBool(value: boolean | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return value ? "Ya" : "Tidak";
}
