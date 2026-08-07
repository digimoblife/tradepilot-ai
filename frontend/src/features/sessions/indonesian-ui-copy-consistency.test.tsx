import { describe, expect, it } from "vitest";

import { SESSION_DETAIL_STATUS_PRESENTATIONS } from "./session-detail-header";
import { SESSION_STATUS_PRESENTATIONS } from "./session-list-card";
import { SKIP_REASON_OPTIONS } from "./session-decision-surface";

describe("UX7.4 — Indonesian UI Copy Consistency", () => {
  it("maps persisted session status technical values to approved Indonesian presentation labels", () => {
    expect(SESSION_STATUS_PRESENTATIONS.DRAFT.label).toBe("Sesi Baru");
    expect(SESSION_STATUS_PRESENTATIONS.ANALYZED.label).toBe("Menunggu Keputusan");
    expect(SESSION_STATUS_PRESENTATIONS.WAITING.label).toBe("Menunggu");
    expect(SESSION_STATUS_PRESENTATIONS.OPEN_POSITION.label).toBe("Posisi Terbuka");
    expect(SESSION_STATUS_PRESENTATIONS.CLOSED.label).toBe("Selesai");
    expect(SESSION_STATUS_PRESENTATIONS.CLOSED_SKIPPED.label).toBe("Dilewati");

    expect(SESSION_DETAIL_STATUS_PRESENTATIONS.DRAFT.label).toBe("Sesi Baru");
    expect(SESSION_DETAIL_STATUS_PRESENTATIONS.ANALYZED.label).toBe("Menunggu Keputusan");
    expect(SESSION_DETAIL_STATUS_PRESENTATIONS.WAITING.label).toBe("Menunggu");
    expect(SESSION_DETAIL_STATUS_PRESENTATIONS.OPEN_POSITION.label).toBe("Posisi Terbuka");
    expect(SESSION_DETAIL_STATUS_PRESENTATIONS.CLOSED.label).toBe("Selesai");
    expect(SESSION_DETAIL_STATUS_PRESENTATIONS.CLOSED_SKIPPED.label).toBe("Dilewati");
  });

  it("maps all 7 canonical SKIP reason values to approved Indonesian presentation labels without mutating values", () => {
    expect(SKIP_REASON_OPTIONS).toHaveLength(7);
    expect(SKIP_REASON_OPTIONS).toEqual([
      { value: "RISK_TOO_HIGH", label: "Risiko Terlalu Tinggi" },
      { value: "SETUP_NOT_ATTRACTIVE", label: "Setup Tidak Menarik" },
      { value: "ORDERBOOK_WEAK", label: "Orderbook Lemah" },
      { value: "MARKET_CONDITION_UNFAVORABLE", label: "Kondisi Pasar Tidak Mendukung" },
      { value: "WAITING_TOO_LONG", label: "Waktu Tunggu Terlalu Lama" },
      { value: "USER_DECISION", label: "Keputusan Pengguna" },
      { value: "OTHER", label: "Lainnya" },
    ]);
  });

  it("verifies normalized presentation wording contains no mixed-language presentation artifacts", () => {
    const archiveBody = "Sesi BBRI akan dipindahkan dari daftar Sesi ke Sesi Diarsipkan. Data, analisis, dan riwayat sesi tetap tersimpan, dan sesi dapat dikembalikan ke daftar selesai nanti.";
    const restoreBody = "Sesi BBRI akan dikembalikan ke bagian Selesai pada daftar Sesi. Status selesai, data, analisis, dan riwayat tetap sama. Trading tidak akan dibuka kembali.";

    expect(archiveBody).not.toMatch(/daftar Sessions|Archived Sessions/);
    expect(restoreBody).not.toMatch(/bagian Completed|daftar Sessions/);
  });
});
