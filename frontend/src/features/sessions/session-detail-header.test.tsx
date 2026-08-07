import { readFileSync } from "node:fs";
import path from "node:path";

import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  formatSessionDetailTimestamp,
  SessionDetailHeader,
} from "@/features/sessions/session-detail-header";
import type { SessionStatus, TradeSession } from "@/features/trade-workspace/types";

const sessionId = "11111111-1111-4111-8111-111111111111";

function session(overrides: Partial<TradeSession> = {}): TradeSession {
  return {
    id: sessionId,
    ticker: "BBRI",
    company_name: "Bank Rakyat Indonesia",
    status: "DRAFT",
    note: "Pantau pembukaan\nJangan mengejar harga.",
    created_at: "2026-08-04T00:00:00Z",
    updated_at: "2026-08-04T01:30:00Z",
    closed_at: null,
    archived_at: null,
    ...overrides,
  };
}

const statusCases: Array<[SessionStatus, string]> = [
  ["DRAFT", "Sesi Baru"],
  ["ANALYZING", "Sedang Diproses"],
  ["ANALYZED", "Menunggu Keputusan"],
  ["WAITING", "Menunggu"],
  ["OPEN_POSITION", "Posisi Terbuka"],
  ["CLOSED", "Selesai"],
  ["CLOSED_SKIPPED", "Dilewati"],
];

describe("UX4.1 session detail header", () => {
  it("identifies the canonical session with one primary heading and semantic metadata", () => {
    render(<SessionDetailHeader session={session()} />);

    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("heading", { level: 1, name: "BBRI" })).toBeInTheDocument();
    expect(screen.getByText("Bank Rakyat Indonesia")).toBeInTheDocument();
    expect(screen.queryByText(sessionId)).toBeNull();
    expect(screen.getByText("Dibuat")).toBeInTheDocument();
    expect(screen.getByText("Diperbarui")).toBeInTheDocument();

    const times = screen.getAllByRole("time");
    expect(times).toHaveLength(2);
    expect(times[0]).toHaveAttribute("datetime", "2026-08-04T00:00:00Z");
    expect(times[1]).toHaveAttribute("datetime", "2026-08-04T01:30:00Z");
    expect(screen.getByRole("heading", { level: 2, name: "Catatan Awal" })).toBeInTheDocument();
    expect(screen.getByText(/Pantau pembukaan\s+Jangan mengejar harga\./)).toBeInTheDocument();
  });

  it.each(statusCases)("renders %s with approved textual status %s", (status, label) => {
    render(<SessionDetailHeader session={session({ status })} />);

    const statusElement = screen.getByText(label);
    expect(statusElement).toHaveAttribute("data-canonical-status", status);
  });

  it("keeps CLOSED and CLOSED_SKIPPED terminal meanings distinct", () => {
    const closed = render(<SessionDetailHeader session={session({ status: "CLOSED" })} />);
    expect(screen.getByText("Sesi ini telah selesai dan tidak dapat dilanjutkan.")).toBeInTheDocument();
    expect(screen.queryByText(/tanpa membuka posisi/)).toBeNull();
    closed.unmount();

    render(<SessionDetailHeader session={session({ status: "CLOSED_SKIPPED" })} />);
    expect(screen.getByText("Sesi ini dilewati tanpa membuka posisi.")).toBeInTheDocument();
    expect(screen.queryByText(/telah selesai dan tidak dapat dilanjutkan/)).toBeNull();
  });

  it("handles an unexpected runtime status without presenting it as canonical", () => {
    render(
      <SessionDetailHeader
        session={session({ status: "ARCHIVED" as SessionStatus })}
      />,
    );

    const safeStatus = screen.getByText("Status tidak dikenali");
    expect(safeStatus).not.toHaveAttribute("data-canonical-status");
    expect(screen.queryByText("ARCHIVED")).toBeNull();
  });

  it("uses deterministic absolute formatting and safe invalid timestamp fallbacks", () => {
    const value = "2026-08-04T00:00:00Z";
    const first = formatSessionDetailTimestamp(value);
    const second = formatSessionDetailTimestamp(value);
    expect(first).toBe(second);
    expect(first).not.toBeNull();

    render(
      <SessionDetailHeader
        session={session({ created_at: "not-a-date", updated_at: "also-invalid" })}
      />,
    );

    expect(screen.getAllByText("waktu tidak tersedia")).toHaveLength(2);
    expect(screen.queryByRole("time")).toBeNull();
    expect(screen.queryByText(/Invalid Date|1 Jan 1970/i)).toBeNull();
  });

  it.each([null, "", "   "])("omits the note region for %j note", (note) => {
    render(<SessionDetailHeader session={session({ note })} />);

    expect(screen.queryByRole("heading", { name: "Catatan Awal" })).toBeNull();
  });

  it("renders long identity and note as wrapping plain text without edit controls", () => {
    const longTicker = "TICKER-SANGAT-PANJANG-TETAP-TERLIHAT";
    const longCompany = "Perusahaan Dengan Nama Sangat Panjang, Tanda Baca & Identitas Lengkap (Indonesia)";
    const longNote = "<strong>teks pengguna</strong> ".repeat(12);
    const { container } = render(
      <SessionDetailHeader
        session={session({ ticker: longTicker, company_name: longCompany, note: longNote })}
      />,
    );

    expect(screen.getByRole("heading", { name: longTicker })).toHaveClass("break-all");
    expect(screen.getByText(longCompany)).toHaveClass("[overflow-wrap:anywhere]");
    const noteParagraph = container.querySelector('[aria-labelledby="initial-note-title"] p');
    expect(noteParagraph).toHaveTextContent("<strong>teks pengguna</strong>");
    expect(noteParagraph).toHaveClass(
      "whitespace-pre-wrap",
      "[overflow-wrap:anywhere]",
    );
    expect(container.querySelector("strong")).toBeNull();
    expect(container.querySelector("input, textarea, button")).toBeNull();
  });

  it.each(["CLOSED", "CLOSED_SKIPPED"] as const)(
    "shows archived read-only context while preserving %s",
    (status) => {
      const archivedAt = "2026-08-04T03:00:00Z";
      render(<SessionDetailHeader session={session({ status, archived_at: archivedAt })} />);

      const archive = screen.getByRole("complementary", { name: "Konteks arsip" });
      expect(within(archive).getByText("Sesi ini telah diarsipkan.")).toBeInTheDocument();
      expect(within(archive).getByText(/historis hanya-baca/)).toBeInTheDocument();
      expect(within(archive).getByRole("time")).toHaveAttribute("datetime", archivedAt);
      expect(screen.getByText(status === "CLOSED" ? "Selesai" : "Dilewati")).toHaveAttribute(
        "data-canonical-status",
        status,
      );
      expect(screen.queryByText("ARCHIVED")).toBeNull();
      expect(screen.getByRole("link", { name: "Kembali ke Arsip" })).toHaveAttribute("href", "/sessions/archived");
      expect(screen.queryByRole("button")).toBeNull();
      expect(screen.queryByRole("link", { name: /pulihkan|buka kembali/i })).toBeNull();
    },
  );

  it("shows no archive context for null metadata and rejects a contradictory fixture safely", () => {
    const active = render(<SessionDetailHeader session={session({ archived_at: null })} />);
    expect(screen.queryByRole("complementary", { name: "Konteks arsip" })).toBeNull();
    active.unmount();

    render(
      <SessionDetailHeader
        session={session({ status: "WAITING", archived_at: "2026-08-04T03:00:00Z" })}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Data arsip sesi tidak konsisten");
    expect(screen.queryByRole("complementary", { name: "Konteks arsip" })).toBeNull();
  });

  it("provides one touch-safe semantic back link with no mutation controls", () => {
    render(<SessionDetailHeader session={session()} />);

    const link = screen.getByRole("link", { name: "Kembali ke Sesi" });
    expect(link).toHaveAttribute("href", "/sessions");
    expect(link).toHaveClass("min-h-11");
    expect(screen.getAllByRole("link")).toHaveLength(1);
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("locks the mobile-first, min-width-safe header boundary and forbidden dependencies", () => {
    const source = readFileSync(
      path.join(process.cwd(), "src/features/sessions/session-detail-header.tsx"),
      "utf8",
    );

    expect(source).toContain("flex-col");
    expect(source).toContain("sm:grid-cols");
    expect(source).toContain("min-w-0");
    expect(source).toContain("overflow-wrap:anywhere");
    expect(source).not.toMatch(/(?:^|\s)w-(?:\d+|\[[^\]]+\])/);
    expect(source).not.toMatch(
      /localStorage|sessionStorage|TradeWorkspace|selected|available-actions|getSessionDetail|archiveSession|restoreSession|router\.back|onClick|<button/,
    );
  });
});
