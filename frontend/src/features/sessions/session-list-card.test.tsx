import { readFileSync } from "node:fs";
import path from "node:path";

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type {
  SessionStatus,
  TradeSessionListItem,
} from "@/features/trade-workspace/types";
import {
  SESSION_STATUS_PRESENTATIONS,
  SessionListCard,
  formatSessionUpdatedAt,
} from "./session-list-card";

function session(overrides: Partial<TradeSessionListItem> = {}): TradeSessionListItem {
  return {
    id: "session-123",
    ticker: "BBRI",
    company_name: "PT Bank Rakyat Indonesia Tbk",
    status: "DRAFT",
    note: null,
    created_at: "2020-01-02T03:04:00Z",
    updated_at: "2026-08-04T05:06:00Z",
    closed_at: null,
    archived_at: null,
    ...overrides,
  };
}

const STATUS_CASES: Array<{
  status: SessionStatus;
  label: string;
  summary: RegExp;
}> = [
  { status: "DRAFT", label: "Sesi Baru", summary: /Bukti Awal/ },
  { status: "ANALYZING", label: "Sedang Diproses", summary: /sedang diproses.*Tunggu/i },
  { status: "ANALYZED", label: "Menunggu Keputusan", summary: /Analisis Awal.*BUY, WAIT, atau SKIP/ },
  { status: "WAITING", label: "Menunggu", summary: /hasil terbaru.*Pembaruan WAIT/ },
  { status: "OPEN_POSITION", label: "Posisi Terbuka", summary: /Pantau posisi.*Pembaruan Posisi.*tutup sesi/ },
  { status: "CLOSED", label: "Selesai", summary: /telah selesai/ },
  { status: "CLOSED_SKIPPED", label: "Dilewati", summary: /dilewati tanpa membuka posisi/ },
];

describe("SessionListCard", () => {
  it.each(STATUS_CASES)(
    "presents $status with visible Indonesian meaning and a status-specific next stage",
    ({ status, label, summary }) => {
      const { container } = render(<SessionListCard session={session({ status })} />);

      expect(screen.getByText(label)).toBeVisible();
      expect(screen.getByText(summary)).toBeVisible();
      expect(container.querySelector(`[data-canonical-status="${status}"]`)).toHaveTextContent(label);
      expect(screen.getAllByRole("link", { name: "Buka Sesi" })).toHaveLength(1);
      expect(screen.queryByRole("button")).toBeNull();
    },
  );

  it("defines exactly the seven canonical statuses and keeps terminal meanings distinct", () => {
    expect(Object.keys(SESSION_STATUS_PRESENTATIONS)).toEqual([
      "DRAFT",
      "ANALYZING",
      "ANALYZED",
      "WAITING",
      "OPEN_POSITION",
      "CLOSED",
      "CLOSED_SKIPPED",
    ]);
    expect(SESSION_STATUS_PRESENTATIONS.CLOSED.label).not.toBe(
      SESSION_STATUS_PRESENTATIONS.CLOSED_SKIPPED.label,
    );
    expect(SESSION_STATUS_PRESENTATIONS.CLOSED_SKIPPED.nextStage).toContain(
      "tanpa membuka posisi",
    );
  });

  it("shows identity and one touch-safe navigation action without exposing the session ID", () => {
    const { container } = render(<SessionListCard session={session()} />);

    expect(screen.getByRole("heading", { level: 3, name: "BBRI" })).toBeVisible();
    expect(screen.getByText("PT Bank Rakyat Indonesia Tbk")).toBeVisible();
    expect(screen.queryByText("session-123")).toBeNull();

    const links = screen.getAllByRole("link");
    expect(links).toHaveLength(1);
    expect(links[0]).toHaveAccessibleName("Buka Sesi");
    expect(links[0]).toHaveAttribute("href", "/sessions/session-123");
    expect(links[0]).toHaveClass("min-h-11", "w-full", "sm:w-auto");
    expect(container.querySelector("article")?.closest("a")).toBeNull();
  });

  it("uses updated_at in semantic local-time markup and handles invalid timestamps safely", () => {
    const valid = session();
    const view = render(<SessionListCard session={valid} />);
    const time = view.container.querySelector("time");

    expect(time).toHaveAttribute("datetime", valid.updated_at);
    expect(time).toHaveTextContent(formatSessionUpdatedAt(valid.updated_at) ?? "");
    expect(time).not.toHaveAttribute("datetime", valid.created_at);

    view.rerender(<SessionListCard session={session({ updated_at: "not-a-timestamp" })} />);
    expect(screen.getByText(/Diperbarui:/)).toHaveTextContent("waktu tidak tersedia");
    expect(view.container.querySelector("time")).toBeNull();
    expect(screen.queryByText(/Invalid Date/i)).toBeNull();
  });

  it("keeps long content present in a min-width-safe mobile-first stack", () => {
    const longTicker = "VERY-LONG-TICKER-WITHIN-LIMIT";
    const longCompany =
      "PT Perusahaan Perdagangan dan Teknologi Indonesia dengan Nama Sangat Panjang Tbk";
    const { container } = render(
      <SessionListCard
        session={session({ ticker: longTicker, company_name: longCompany, status: "ANALYZING" })}
      />,
    );

    expect(screen.getByText(longTicker)).toHaveClass("break-all");
    expect(screen.getByText(longCompany)).toHaveClass("[overflow-wrap:anywhere]");
    expect(screen.getByText(/Analisis Awal sedang diproses/)).toHaveClass("break-words");

    const layout = container.querySelector("article > div");
    expect(layout).toHaveClass("grid", "min-w-0", "sm:grid-cols-[minmax(0,1fr)_auto]");
    expect(container.querySelector("article")).toHaveClass("min-w-0");
    expect(screen.getByText(/Diperbarui:/)).toHaveClass("break-words");
    expect(container.innerHTML).not.toMatch(/\bw-(?:screen|\[[0-9]+(?:px|rem))/);
  });

  it("does not present an unexpected runtime value as an approved status", () => {
    render(
      <SessionListCard
        session={session({ status: "UNEXPECTED_RUNTIME_STATUS" as SessionStatus })}
      />,
    );

    expect(screen.getByText("Status tidak dikenali")).toBeVisible();
    expect(screen.queryByText("UNEXPECTED_RUNTIME_STATUS")).toBeNull();
    expect(screen.getByText(/meninjau status terbaru/)).toBeVisible();
  });

  it("does not translate archive metadata into lifecycle presentation", () => {
    render(
      <SessionListCard
        session={session({
          status: "CLOSED",
          archived_at: "2026-08-04T07:08:00Z",
        })}
      />,
    );

    expect(screen.getByText("Selesai")).toBeVisible();
    expect(screen.queryByText(/arsip/i)).toBeNull();
    expect(screen.queryByText("2026-08-04T07:08:00Z")).toBeNull();
  });

  it("contains no request, lifecycle mutation, grouping, Archive, or Restore implementation", () => {
    const source = readFileSync(
      path.join(process.cwd(), "src/features/sessions/session-list-card.tsx"),
      "utf8",
    );

    expect(source).not.toMatch(/fetch\(|available-actions|getAvailableActions|archiveSession|restoreSession/);
    expect(source).not.toMatch(/onClick=|<button|Needs Attention|In Progress|Completed/);
    expect(source).not.toMatch(/evidence|analysis|position-updates|closePosition/);
  });
});
