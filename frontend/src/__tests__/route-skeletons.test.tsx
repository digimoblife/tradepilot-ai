import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

import { render, screen, waitFor } from "@testing-library/react";
import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ArchivedSessionsPage from "@/app/sessions/archived/page";
import SessionAnalysisPage from "@/app/sessions/[sessionId]/analysis/page";
import SessionHistoryPage from "@/app/sessions/[sessionId]/history/page";
import SessionDetailPage from "@/app/sessions/[sessionId]/page";
import NewSessionPage from "@/app/sessions/new/page";
import SessionsPage from "@/app/sessions/page";
import { getSession, getSessionDetail, listArchivedSessions, listSessions } from "@/features/trade-workspace/api";
import type { SessionDetailAggregate, TradeSession } from "@/features/trade-workspace/types";
import { middleware } from "@/middleware";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/sessions/11111111-1111-4111-8111-111111111111",
}));

vi.mock("@/features/trade-workspace/api", () => ({
  getSession: vi.fn(),
  getSessionDetail: vi.fn(),
  listSessions: vi.fn(),
  listArchivedSessions: vi.fn(),
}));

const sessionId = "11111111-1111-4111-8111-111111111111";
const routeSession: TradeSession = {
  id: sessionId,
  ticker: "BBRI",
  company_name: "Bank Rakyat Indonesia",
  status: "DRAFT",
  note: null,
  created_at: "2026-08-04T00:00:00Z",
  updated_at: "2026-08-04T00:00:00Z",
  closed_at: null,
  archived_at: null,
};
const detail: SessionDetailAggregate = {
  session: {
    id: sessionId, ticker: "BBRI", company_name: "Bank Rakyat Indonesia", status: "DRAFT",
    initial_note: null, created_at: "2026-08-04T00:00:00Z",
    updated_at: "2026-08-04T00:00:00Z", closed_at: null,
  },
  initial_evidence: [], initial_analysis: null, decisions: [], wait_updates: [],
  position: null, position_updates: [], closure: null,
  latest_analysis: null, recent_activity: [],
  current_step: {
    code: "INITIAL_EVIDENCE", mode: "ACTIONABLE",
    workflow_actions: ["SUBMIT_INITIAL_EVIDENCE"], active_request: null,
    failed_request: null, read_only: false,
  },
};
const protectedRoutes = [
  "/sessions",
  "/sessions/new",
  "/sessions/archived",
  `/sessions/${sessionId}`,
  `/sessions/${sessionId}/analysis`,
  `/sessions/${sessionId}/history`,
];

afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

describe("UX2.1 route shells", () => {
  beforeEach(() => {
    vi.mocked(getSession).mockResolvedValue(routeSession);
    vi.mocked(getSessionDetail).mockResolvedValue(detail);
    vi.mocked(listSessions).mockResolvedValue({ sessions: [] });
    vi.mocked(listArchivedSessions).mockResolvedValue({ sessions: [] });
  });

  it("renders every approved route independently with safe navigation", async () => {
    const pages = [
      { page: <SessionsPage />, heading: "Sesi Perdagangan", backHref: null, backLinkName: null },
      { page: <NewSessionPage />, heading: "Buat Sesi Baru", backHref: "/sessions", backLinkName: "Batal" },
      {
        page: <ArchivedSessionsPage />,
        heading: "Sesi Diarsipkan",
        backHref: "/sessions",
        backLinkName: "Kembali ke Sesi",
      },
      {
        page: await SessionDetailPage({ params: Promise.resolve({ sessionId }) }),
        heading: "BBRI",
        backHref: "/sessions",
        backLinkName: "Kembali ke Sesi",
      },
      {
        page: await SessionAnalysisPage({ params: Promise.resolve({ sessionId }) }),
        heading: "Analisis",
        backHref: "/sessions",
        backLinkName: "Kembali ke Sesi",
      },
      {
        page: await SessionHistoryPage({ params: Promise.resolve({ sessionId }) }),
        heading: "Riwayat Sesi",
        backHref: "/sessions",
        backLinkName: "Kembali ke Sesi",
      },
    ];

    for (const { page, heading, backHref, backLinkName } of pages) {
      const view = render(page);
      expect(await screen.findByRole("heading", { level: 1, name: heading })).toBeTruthy();
      if (backHref && backLinkName) {
        const links = screen.getAllByRole("link", { name: backLinkName });
        expect(links.some((l) => l.getAttribute("href") === backHref)).toBe(true);
      }
      view.unmount();
    }

    expect(listSessions).toHaveBeenCalledTimes(1);
  });

  it("uses the URL session identifier structurally for route recovery", async () => {
    render(await SessionDetailPage({ params: Promise.resolve({ sessionId }) }));

    await waitFor(() => {
      expect(getSession).toHaveBeenCalledWith(sessionId, expect.any(AbortSignal));
    });
  });

  it("keeps every sessions route protected by the shared middleware", async () => {
    for (const route of protectedRoutes) {
      const response = await middleware(new NextRequest(`http://localhost${route}`));
      expect(response.status).toBe(307);
      const location = new URL(response.headers.get("location") ?? "", "http://localhost");
      expect(location.pathname).toBe("/login");
      expect(location.searchParams.get("next")).toBe(route);
    }
  });

  it("allows authenticated access through the unchanged middleware guard", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 200 })));

    for (const route of protectedRoutes) {
      const request = new NextRequest(`http://localhost${route}`, {
        headers: { cookie: "tradepilot_session=test-token" },
      });
      const response = await middleware(request);
      expect(response.status).toBe(200);
      expect(response.headers.get("x-middleware-next")).toBe("1");
    }
  });

  it("preserves static route precedence and framework not-found boundaries", () => {
    const appRoot = path.join(process.cwd(), "src/app");

    expect(existsSync(path.join(appRoot, "sessions/new/page.tsx"))).toBe(true);
    expect(existsSync(path.join(appRoot, "sessions/archived/page.tsx"))).toBe(true);
    expect(existsSync(path.join(appRoot, "sessions/[sessionId]/page.tsx"))).toBe(true);
    expect(existsSync(path.join(appRoot, "sessions/[sessionId]/unsupported/page.tsx"))).toBe(
      false,
    );
    expect(existsSync(path.join(appRoot, "unknown/page.tsx"))).toBe(false);
    expect(existsSync(path.join(appRoot, "sessions/[...sessionId]/page.tsx"))).toBe(false);
  });

  it("contains no blind workspace redirects or lifecycle imports", () => {
    const sessionRouteFiles = [
      "src/app/sessions/archived/page.tsx",
      "src/app/sessions/[sessionId]/page.tsx",
      "src/app/sessions/[sessionId]/analysis/page.tsx",
      "src/app/sessions/[sessionId]/history/page.tsx",
    ];

    for (const routeFile of ["src/app/sessions/new/page.tsx", ...sessionRouteFiles]) {
      const source = readFileSync(path.join(process.cwd(), routeFile), "utf8");
      expect(source).not.toContain("redirect(");
      expect(source).not.toContain("/trade-workspace");
      expect(source).not.toMatch(/features\/(trade-workspace|trade-session|analysis)/);
      expect(source).not.toMatch(/lib\/api|restoreSession/);
    }

    const archivedSource = readFileSync(
      path.join(process.cwd(), "src/app/sessions/archived/page.tsx"),
      "utf8",
    );
    expect(archivedSource).toContain("ArchivedSessionsListSurface");

    const sessionsSource = readFileSync(
      path.join(process.cwd(), "src/app/sessions/page.tsx"),
      "utf8",
    );
    expect(sessionsSource).toContain("SessionsListSurface");
    expect(sessionsSource).not.toMatch(
      /trade-workspace|trade-session|analysis|archiveSession|restoreSession|setInterval/,
    );

    const loaderSource = readFileSync(
      path.join(process.cwd(), "src/features/sessions/use-route-session.ts"),
      "utf8",
    );
    expect(loaderSource).toContain("getSession");
    expect(loaderSource).not.toMatch(
      /getSessionDetail|listSessions|analysis|evidence|archive|restore|poll|setInterval|localStorage|sessionStorage/,
    );
  });

  it("redirects the legacy workspace entry route to /sessions", () => {
    const source = readFileSync(
      path.join(process.cwd(), "src/app/trade-workspace/page.tsx"),
      "utf8",
    );

    expect(source).toContain('redirect("/sessions")');
  });
});
