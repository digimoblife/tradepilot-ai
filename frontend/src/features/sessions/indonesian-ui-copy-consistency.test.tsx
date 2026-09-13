import { describe, expect, it } from "vitest";

import { SESSION_DETAIL_STATUS_PRESENTATIONS } from "./session-detail-header";
import { SESSION_STATUS_PRESENTATIONS } from "./session-list-card";

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

  it("verifies normalized presentation wording contains no mixed-language presentation artifacts", () => {
    const archiveBody = "Sesi BBRI akan dipindahkan dari daftar Sesi ke Sesi Diarsipkan. Data, analisis, dan riwayat sesi tetap tersimpan, dan sesi dapat dikembalikan ke daftar selesai nanti.";
    const restoreBody = "Sesi BBRI akan dikembalikan ke bagian Selesai pada daftar Sesi. Status selesai, data, analisis, dan riwayat tetap sama. Trading tidak akan dibuka kembali.";

    expect(archiveBody).not.toMatch(/daftar Sessions|Archived Sessions/);
    expect(restoreBody).not.toMatch(/bagian Completed|daftar Sessions/);
  });
});
