import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/env", () => ({
  publicEnv: {
    apiBaseUrl: "https://tradepilotai.deployroom.my.id/api",
  },
}));

import { createSession, getSession, getSessionDetail, listSessions, submitInitialAnalysis, uploadInitialEvidence } from "./api";

describe("Trade Workspace API Base URL composition", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("resolves requests to /api/v2/trade-sessions without duplicating /api prefix when API base URL ends with /api", async () => {
    const response = {
      id: "11111111-1111-4111-8111-111111111111",
      ticker: "BBRI",
      company_name: "Bank Rakyat Indonesia",
      status: "DRAFT",
      note: null,
      created_at: "2026-08-04T00:00:00Z",
      updated_at: "2026-08-04T00:00:00Z",
      closed_at: null,
      archived_at: null,
    };
    const controller = new AbortController();
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(response), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await getSession(response.id, controller.signal);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [requestedUrl, options] = fetchMock.mock.calls[0] as [string, RequestInit];

    // Should resolve to https://tradepilotai.deployroom.my.id/api/v2/trade-sessions/session-1
    expect(requestedUrl).toBe(
      `https://tradepilotai.deployroom.my.id/api/v2/trade-sessions/${response.id}`,
    );
    // Must NEVER produce /api/api/
    expect(requestedUrl).not.toContain("/api/api/");
    expect(options.credentials).toBe("include");
    expect(options.signal).toBe(controller.signal);
    expect(result).toEqual(response);
  });

  it("resolves listSessions to /api/v2/trade-sessions without duplicate prefix", async () => {
    const response = {
      sessions: [
        {
          id: "22222222-2222-4222-8222-222222222222",
          ticker: "TLKM",
          company_name: "Telkom Indonesia",
          status: "CLOSED",
          note: null,
          created_at: "2026-08-04T01:00:00Z",
          updated_at: "2026-08-04T01:00:00Z",
          closed_at: "2026-08-04T02:00:00Z",
          archived_at: null,
        },
        {
          id: "11111111-1111-4111-8111-111111111111",
          ticker: "BBRI",
          company_name: "Bank Rakyat Indonesia",
          status: "DRAFT",
          note: null,
          created_at: "2026-08-04T00:00:00Z",
          updated_at: "2026-08-04T00:00:00Z",
          closed_at: null,
          archived_at: null,
        },
      ],
    };
    const controller = new AbortController();
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(response), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await listSessions(controller.signal);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [requestedUrl, options] = fetchMock.mock.calls[0] as [string, RequestInit];

    expect(requestedUrl).toBe("https://tradepilotai.deployroom.my.id/api/v2/trade-sessions");
    expect(requestedUrl).not.toContain("/api/api/");
    expect(options.method).toBe("GET");
    expect(options.credentials).toBe("include");
    expect(options.signal).toBe(controller.signal);
    expect(result).toEqual(response);
    expect(result.sessions.map((session) => session.id)).toEqual([
      response.sessions[0].id,
      response.sessions[1].id,
    ]);
  });

  it("loads the canonical detail aggregate with credentials and AbortSignal", async () => {
    const response = {
      session: {}, initial_evidence: [], initial_analysis: null, decisions: [],
      wait_updates: [], position: null, position_updates: [], closure: null,
      latest_analysis: null, recent_activity: [],
      current_step: {
        code: "INITIAL_EVIDENCE", mode: "ACTIONABLE",
        workflow_actions: ["SUBMIT_INITIAL_EVIDENCE"], active_request: null,
        failed_request: null, read_only: false,
      },
    };
    const controller = new AbortController();
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(response), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    expect(await getSessionDetail("session-1", controller.signal)).toEqual(response);
    const [requestedUrl, options] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(requestedUrl).toBe(
      "https://tradepilotai.deployroom.my.id/api/v2/trade-sessions/session-1/detail",
    );
    expect(options.method).toBe("GET");
    expect(options.credentials).toBe("include");
    expect(options.signal).toBe(controller.signal);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("posts the exact V2 create payload through the credentialed shared client", async () => {
    const response = {
      id: "33333333-3333-4333-8333-333333333333",
      ticker: "BBRI",
      company_name: "Bank Rakyat Indonesia",
      status: "DRAFT" as const,
      note: null,
      created_at: "2026-08-04T03:00:00Z",
      updated_at: "2026-08-04T03:00:00Z",
      closed_at: null,
      archived_at: null,
    };
    const payload = { ticker: "BBRI", company_name: "Bank Rakyat Indonesia", note: null };
    const controller = new AbortController();
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(response), { status: 201 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    expect(await createSession(payload, controller.signal)).toEqual(response);
    const [requestedUrl, options] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(requestedUrl).toBe("https://tradepilotai.deployroom.my.id/api/v2/trade-sessions");
    expect(options.method).toBe("POST");
    expect(options.credentials).toBe("include");
    expect(options.signal).toBe(controller.signal);
    expect(options.headers).toEqual({ "Content-Type": "application/json" });
    expect(JSON.parse(String(options.body))).toEqual(payload);
  });

  it("uploads the one exact initial-evidence multipart set with credentials", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ evidence: [] }), { status: 201 }));
    vi.stubGlobal("fetch", fetchMock);
    const files = {
      orderbook: new File(["orderbook"], "orderbook.png", { type: "image/png" }),
      chart_3_month: new File(["chart-3"], "three.png", { type: "image/png" }),
      chart_6_month: new File(["chart-6"], "six.png", { type: "image/png" }),
    };

    await uploadInitialEvidence("session-1", files);

    const [url, options] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("https://tradepilotai.deployroom.my.id/api/v2/trade-sessions/session-1/initial-evidence");
    expect(options.method).toBe("POST");
    expect(options.credentials).toBe("include");
    expect([...((options.body as FormData).keys())]).toEqual(["orderbook", "chart_3_month", "chart_6_month"]);
  });

  it("submits Initial Analysis through its separate credentialed endpoint without a body", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: "request-1" }), { status: 201 }));
    vi.stubGlobal("fetch", fetchMock);

    await submitInitialAnalysis("session-1");

    const [url, options] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("https://tradepilotai.deployroom.my.id/api/v2/trade-sessions/session-1/initial-analysis");
    expect(options.method).toBe("POST");
    expect(options.credentials).toBe("include");
    expect(options.body).toBeUndefined();
  });
});
