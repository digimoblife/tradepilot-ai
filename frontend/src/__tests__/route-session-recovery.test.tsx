import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import SessionAnalysisPage from "@/app/sessions/[sessionId]/analysis/page";
import SessionHistoryPage from "@/app/sessions/[sessionId]/history/page";
import SessionDetailPage from "@/app/sessions/[sessionId]/page";
import { getSession, getSessionDetail } from "@/features/trade-workspace/api";
import type { SessionDetailAggregate, TradeSession } from "@/features/trade-workspace/types";
import { ApiError, AuthenticationError } from "@/lib/api/errors";

vi.mock("next/navigation", () => ({
  usePathname: () => "/sessions/11111111-1111-4111-8111-111111111111",
}));

vi.mock("@/features/trade-workspace/api", () => ({
  getSession: vi.fn(),
  getSessionDetail: vi.fn(),
}));

const sessionId = "11111111-1111-4111-8111-111111111111";
const routeSession: TradeSession = {
  id: sessionId,
  ticker: "BBRI",
  company_name: "Bank Rakyat Indonesia",
  status: "DRAFT",
  note: "Route-owned context",
  created_at: "2026-08-04T00:00:00Z",
  updated_at: "2026-08-04T00:00:00Z",
  closed_at: null,
  archived_at: null,
};
const detail: SessionDetailAggregate = {
  session: {
    id: sessionId, ticker: "BBRI", company_name: "Bank Rakyat Indonesia",
    status: "DRAFT", initial_note: "Route-owned context",
    created_at: "2026-08-04T00:00:00Z", updated_at: "2026-08-04T00:00:00Z", closed_at: null,
  },
  initial_evidence: [], initial_analysis: null, decisions: [], wait_updates: [],
  position: null, position_updates: [], closure: null,
  latest_analysis: null, recent_activity: [],
  current_step: {
    code: "INITIAL_EVIDENCE", mode: "ACTIONABLE",
    workflow_actions: ["SUBMIT_INITIAL_EVIDENCE"],
    active_request: null, failed_request: null, read_only: false,
  },
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(getSession).mockResolvedValue(routeSession);
  vi.mocked(getSessionDetail).mockResolvedValue(detail);
});

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((res) => { resolve = res; });
  return { promise, resolve };
}

describe("UX2.4 route session recovery", () => {
  it.each([
    {
      renderPage: () => SessionDetailPage({ params: Promise.resolve({ sessionId }) }),
      heading: "Ringkasan Sesi",
      backHref: "/sessions",
    },
    {
      renderPage: () => SessionAnalysisPage({ params: Promise.resolve({ sessionId }) }),
      heading: "Analisis Sesi",
      backHref: `/sessions/${sessionId}`,
    },
    {
      renderPage: () => SessionHistoryPage({ params: Promise.resolve({ sessionId }) }),
      heading: "Riwayat Sesi",
      backHref: `/sessions/${sessionId}`,
    },
  ])("loads $heading independently from its route ID", async ({ renderPage, heading, backHref }) => {
    render(await renderPage());

    expect(screen.getByRole("heading", { level: 1, name: heading })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Memuat konteks sesi");
    expect(screen.getByRole("link", { name: /kembali/i })).toHaveAttribute(
      "href",
      backHref,
    );

    await waitFor(() => {
      expect(getSession).toHaveBeenCalledWith(sessionId, expect.any(AbortSignal));
      expect(screen.getByText("BBRI")).toBeInTheDocument();
    });
    expect(screen.queryByRole("status")).toBeNull();
    if (heading === "Ringkasan Sesi") {
      expect(screen.getByRole("heading", { level: 1, name: "BBRI" })).toBeInTheDocument();
      expect(screen.queryByRole("heading", { name: "Ringkasan Sesi" })).toBeNull();
      expect(getSession).toHaveBeenCalledTimes(1);
      expect(await screen.findByRole("heading", { level: 2, name: "Lengkapi Bukti Awal" })).toBeInTheDocument();
      expect(getSessionDetail).toHaveBeenCalledWith(sessionId, expect.any(AbortSignal));
    }
  });

  it("reloads route context on a remount representing refresh", async () => {
    const first = render(
      await SessionDetailPage({ params: Promise.resolve({ sessionId }) }),
    );
    await screen.findByText("BBRI");
    first.unmount();

    render(await SessionDetailPage({ params: Promise.resolve({ sessionId }) }));
    await screen.findByText("BBRI");

    expect(getSession).toHaveBeenCalledTimes(2);
    expect(getSessionDetail).toHaveBeenCalledTimes(2);
    expect(getSession).toHaveBeenNthCalledWith(1, sessionId, expect.any(AbortSignal));
    expect(getSession).toHaveBeenNthCalledWith(2, sessionId, expect.any(AbortSignal));
  });

  it("preserves the UX4.1 header while Current Step loads independently", async () => {
    const pending = deferred<SessionDetailAggregate>();
    vi.mocked(getSessionDetail).mockReturnValue(pending.promise);
    render(await SessionDetailPage({ params: Promise.resolve({ sessionId }) }));

    expect(await screen.findByRole("heading", { level: 1, name: "BBRI" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "Memuat Langkah Saat Ini" })).toBeInTheDocument();
    expect(screen.queryByRole("button")).toBeNull();
    expect(screen.queryByRole("link", { name: /BUY|WAIT|SKIP|analisis awal/i })).toBeNull();

    pending.resolve(detail);
    expect(await screen.findByRole("heading", { level: 2, name: "Lengkapi Bukti Awal" })).toBeInTheDocument();
  });

  it.each([
    new ApiError(500, "INTERNAL_ERROR", "provider-secret"),
    new AuthenticationError(401, "AUTHENTICATION_EXPIRED", "auth-secret"),
  ])("preserves the header and fails closed when aggregate loading fails", async (error) => {
    vi.mocked(getSessionDetail).mockRejectedValue(error);
    render(await SessionDetailPage({ params: Promise.resolve({ sessionId }) }));

    expect(await screen.findByRole("heading", { level: 1, name: "BBRI" })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { level: 2, name: "Langkah Saat Ini Belum Tersedia" })).toBeInTheDocument();
    expect(screen.getByText(/Tidak ada tindakan yang ditawarkan/)).toBeInTheDocument();
    expect(screen.queryByText(/provider-secret|auth-secret/)).toBeNull();
    expect(screen.queryByRole("button")).toBeNull();
  });

  it.each(["missing", "cross-owner"])(
    "uses the same controlled not-found presentation for %s 404",
    async () => {
      vi.mocked(getSession).mockRejectedValue(
        new ApiError(404, "SESSION_NOT_FOUND", "internal ownership detail"),
      );
      render(await SessionDetailPage({ params: Promise.resolve({ sessionId }) }));

      const alert = await screen.findByRole("alert");
      expect(alert).toHaveTextContent("Sesi tidak ditemukan atau tidak dapat diakses");
      expect(alert).not.toHaveTextContent("ownership");
      expect(screen.queryByRole("heading", { name: "BBRI" })).toBeNull();
      expect(screen.queryByText("Langkah Saat Ini")).toBeNull();
      expect(screen.getByRole("link", { name: "Kembali ke Sesi" })).toHaveAttribute(
        "href",
        "/sessions",
      );
    },
  );

  it("renders controlled authentication handling without exposing protected data", async () => {
    vi.mocked(getSession).mockRejectedValue(
      new AuthenticationError(401, "AUTHENTICATION_EXPIRED", "raw auth detail"),
    );
    render(await SessionDetailPage({ params: Promise.resolve({ sessionId }) }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Sesi Anda telah berakhir");
    expect(alert).not.toHaveTextContent("raw auth detail");
    expect(screen.queryByText("BBRI")).toBeNull();
    expect(screen.queryByText("Langkah Saat Ini")).toBeNull();
    expect(screen.getByRole("link", { name: "Masuk kembali" })).toHaveAttribute(
      "href",
      `/login?next=${encodeURIComponent(`/sessions/${sessionId}`)}`,
    );
  });

  it("handles invalid identifiers without a request or crash", async () => {
    render(
      await SessionDetailPage({
        params: Promise.resolve({ sessionId: "invalid-session-id" }),
      }),
    );

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Sesi tidak ditemukan atau tidak dapat diakses",
    );
    expect(getSession).not.toHaveBeenCalled();
    expect(getSessionDetail).not.toHaveBeenCalled();
  });

  it("uses safe generic copy for server and network failures", async () => {
    vi.mocked(getSession).mockRejectedValue(
      new ApiError(500, "INTERNAL_ERROR", "database host secret.internal"),
    );
    render(await SessionDetailPage({ params: Promise.resolve({ sessionId }) }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Konteks sesi tidak dapat dimuat");
    expect(alert).not.toHaveTextContent("database host");
    expect(alert).not.toHaveTextContent("secret.internal");
    expect(screen.queryByRole("heading", { name: "BBRI" })).toBeNull();
    expect(screen.queryByText("Langkah Saat Ini")).toBeNull();
  });
});
