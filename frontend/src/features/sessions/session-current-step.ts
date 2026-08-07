import type {
  CurrentStep,
  CurrentStepCode,
  CurrentStepWorkflowAction,
} from "@/features/trade-workspace/types";

export type SessionCurrentStepPresentation = {
  key: CurrentStepCode | "UNAVAILABLE";
  eyebrow: "Langkah Saat Ini";
  title: string;
  description: string;
  supportingText: string | null;
  state: "actionable" | "processing" | "failed" | "read-only" | "inconsistent";
  navigationAction: { label: string } | null;
};

const ALLOWED_ACTIONS: Record<CurrentStepCode, ReadonlySet<CurrentStepWorkflowAction>> = {
  INITIAL_EVIDENCE: new Set(["SUBMIT_INITIAL_EVIDENCE"]),
  INITIAL_ANALYSIS: new Set(["REQUEST_INITIAL_ANALYSIS"]),
  PROCESSING: new Set(),
  DECISION: new Set(["BUY", "WAIT", "SKIP"]),
  WAIT_UPDATE: new Set(["BUY", "WAIT", "SKIP", "SUBMIT_WAIT_UPDATE"]),
  POSITION_MONITORING: new Set(["SUBMIT_POSITION_UPDATE", "CLOSE"]),
  FAILED_REQUEST: new Set(["RETRY_INITIAL_ANALYSIS", "RETRY_WAIT_UPDATE"]),
  TERMINAL_CLOSED: new Set(),
  TERMINAL_SKIPPED: new Set(),
  ARCHIVED_CLOSED: new Set(),
  ARCHIVED_SKIPPED: new Set(),
  INCONSISTENT: new Set(),
};

const ACTIONABLE_CODES = new Set<CurrentStepCode>([
  "INITIAL_EVIDENCE",
  "INITIAL_ANALYSIS",
  "DECISION",
  "WAIT_UPDATE",
  "POSITION_MONITORING",
]);
const READ_ONLY_CODES = new Set<CurrentStepCode>([
  "TERMINAL_CLOSED",
  "TERMINAL_SKIPPED",
  "ARCHIVED_CLOSED",
  "ARCHIVED_SKIPPED",
]);

export function unavailableCurrentStepPresentation(): SessionCurrentStepPresentation {
  return {
    key: "UNAVAILABLE",
    eyebrow: "Langkah Saat Ini",
    title: "Langkah Saat Ini Belum Tersedia",
    description: "Kondisi sesi belum dapat dimuat. Tidak ada tindakan yang ditawarkan.",
    supportingText: "Status langkah tidak dapat digunakan dengan aman.",
    state: "inconsistent",
    navigationAction: null,
  };
}

export function loadingCurrentStepPresentation(): SessionCurrentStepPresentation {
  return {
    key: "UNAVAILABLE",
    eyebrow: "Langkah Saat Ini",
    title: "Memuat Langkah Saat Ini",
    description: "Memeriksa kondisi sesi terbaru dari backend.",
    supportingText: "Belum ada tindakan yang ditawarkan selama pemuatan.",
    state: "processing",
    navigationAction: null,
  };
}

function isContractConsistent(step: CurrentStep): boolean {
  if (step.workflow_actions.some((action) => !ALLOWED_ACTIONS[step.code].has(action))) {
    return false;
  }
  if (step.read_only && step.workflow_actions.length > 0) return false;

  if (ACTIONABLE_CODES.has(step.code)) {
    return (
      step.mode === "ACTIONABLE" &&
      !step.read_only &&
      step.active_request === null &&
      step.failed_request === null
    );
  }
  if (step.code === "PROCESSING") {
    return (
      step.mode === "PROCESSING" &&
      !step.read_only &&
      step.workflow_actions.length === 0 &&
      step.active_request !== null &&
      ["PENDING", "PROCESSING"].includes(step.active_request.status) &&
      step.failed_request === null
    );
  }
  if (step.code === "FAILED_REQUEST") {
    if (
      step.mode !== "FAILED" ||
      step.read_only ||
      step.active_request !== null ||
      step.failed_request === null ||
      step.failed_request.status !== "FAILED"
    ) {
      return false;
    }
    const expectedRetry =
      step.failed_request.analysis_type === "INITIAL_ANALYSIS"
        ? "RETRY_INITIAL_ANALYSIS"
        : step.failed_request.analysis_type === "WAIT_UPDATE"
          ? "RETRY_WAIT_UPDATE"
          : null;
    if (!step.failed_request.retry_allowed) return step.workflow_actions.length === 0;
    return expectedRetry !== null &&
      step.workflow_actions.length === 1 &&
      step.workflow_actions[0] === expectedRetry;
  }
  if (READ_ONLY_CODES.has(step.code)) {
    return (
      step.mode === "READ_ONLY" &&
      step.read_only &&
      step.workflow_actions.length === 0 &&
      step.active_request === null &&
      step.failed_request === null
    );
  }
  return (
    step.code === "INCONSISTENT" &&
    step.mode === "INCONSISTENT" &&
    step.workflow_actions.length === 0 &&
    step.active_request === null &&
    step.failed_request === null
  );
}

function processingLabel(step: CurrentStep): string | null {
  const analysisType = step.active_request?.analysis_type;
  if (analysisType === "INITIAL_ANALYSIS") return "Analisis Awal sedang diproses.";
  if (analysisType === "WAIT_UPDATE") return "Pembaruan WAIT sedang diproses.";
  if (analysisType === "POSITION_UPDATE") return "Pembaruan posisi sedang diproses.";
  return null;
}

function waitDescription(actions: CurrentStepWorkflowAction[]): string {
  return actions.includes("SUBMIT_WAIT_UPDATE")
    ? "Pembaruan WAIT tersedia berdasarkan kondisi backend saat ini."
    : "Tinjau hasil terbaru dan keputusan yang masih tersedia.";
}

function positionDescription(actions: CurrentStepWorkflowAction[]): string {
  const canUpdate = actions.includes("SUBMIT_POSITION_UPDATE");
  const canClose = actions.includes("CLOSE");
  if (canUpdate && canClose) {
    return "Anda dapat memperbarui kondisi posisi atau menutup sesi melalui langkah lanjutan yang tersedia.";
  }
  if (canClose) return "Penutupan sesi tersedia berdasarkan kondisi backend saat ini.";
  if (canUpdate) return "Pembaruan posisi tersedia berdasarkan kondisi backend saat ini.";
  return "Tidak ada langkah lanjutan yang tersedia untuk posisi saat ini.";
}

export function mapSessionCurrentStep(step: CurrentStep): SessionCurrentStepPresentation {
  if (!isContractConsistent(step)) return unavailableCurrentStepPresentation();

  const base = {
    key: step.code,
    eyebrow: "Langkah Saat Ini" as const,
    navigationAction: null,
  };
  switch (step.code) {
    case "INITIAL_EVIDENCE":
      return { ...base, title: "Lengkapi Bukti Awal", description: "Siapkan satu orderbook, chart 3 bulan, dan chart 6 bulan untuk memulai sesi.", supportingText: null, state: "actionable", navigationAction: { label: "Lanjutkan Bukti Awal" } };
    case "INITIAL_ANALYSIS":
      return { ...base, title: "Minta Analisis Awal", description: "Bukti Awal sudah lengkap dan sesi siap masuk ke Analisis Awal.", supportingText: null, state: "actionable", navigationAction: { label: "Lanjutkan Analisis Awal" } };
    case "PROCESSING":
      return { ...base, title: "Sedang Diproses", description: "Permintaan terbaru sedang diproses. Tunggu hingga proses selesai sebelum melanjutkan.", supportingText: processingLabel(step), state: "processing" };
    case "DECISION":
      return { ...base, title: "Tinjau Analisis dan Tentukan Keputusan", description: ["BUY", "WAIT", "SKIP"].every((action) => step.workflow_actions.includes(action as CurrentStepWorkflowAction)) ? "Tinjau hasil Analisis Awal sebelum memilih BUY, WAIT, atau SKIP." : "Tinjau hasil Analisis Awal dan keputusan yang tersedia berdasarkan kondisi backend saat ini.", supportingText: null, state: "actionable" };
    case "WAIT_UPDATE":
      return { ...base, title: "Pantau dan Perbarui Sesi", description: waitDescription(step.workflow_actions), supportingText: null, state: "actionable" };
    case "POSITION_MONITORING":
      return { ...base, title: "Pantau Posisi Terbuka", description: positionDescription(step.workflow_actions), supportingText: null, state: "actionable" };
    case "FAILED_REQUEST":
      return { ...base, title: "Permintaan Terakhir Gagal", description: "Permintaan terakhir tidak berhasil diselesaikan.", supportingText: step.failed_request?.retry_allowed ? "Percobaan ulang tersedia berdasarkan kondisi backend saat ini." : "Tidak ada percobaan ulang yang tersedia saat ini.", state: "failed" };
    case "TERMINAL_CLOSED":
      return { ...base, title: "Sesi Telah Selesai", description: "Sesi ini sudah ditutup dan hanya dapat ditinjau.", supportingText: "Sesi bersifat hanya-baca.", state: "read-only" };
    case "TERMINAL_SKIPPED":
      return { ...base, title: "Sesi Dilewati", description: "Sesi selesai tanpa membuka posisi dan hanya dapat ditinjau.", supportingText: "Sesi bersifat hanya-baca.", state: "read-only" };
    case "ARCHIVED_CLOSED":
      return { ...base, title: "Sesi Selesai dan Diarsipkan", description: "Sesi historis ini bersifat hanya-baca.", supportingText: "Tidak ada tindakan sesi yang tersedia.", state: "read-only" };
    case "ARCHIVED_SKIPPED":
      return { ...base, title: "Sesi Dilewati dan Diarsipkan", description: "Sesi historis ini selesai tanpa membuka posisi dan bersifat hanya-baca.", supportingText: "Tidak ada tindakan sesi yang tersedia.", state: "read-only" };
    case "INCONSISTENT":
      return { ...base, title: "Status Langkah Tidak Tersedia", description: "Kondisi sesi tidak dapat dipetakan secara aman. Tidak ada tindakan yang ditawarkan.", supportingText: "Status langkah perlu ditinjau kembali.", state: "inconsistent" };
  }
}
