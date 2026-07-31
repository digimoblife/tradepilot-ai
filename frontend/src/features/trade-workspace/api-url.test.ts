import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/env", () => ({
  publicEnv: {
    apiBaseUrl: "https://tradepilotai.deployroom.my.id/api",
  },
}));

import { getSession, listSessions } from "./api";

describe("Trade Workspace API Base URL composition", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("resolves requests to /api/v2/trade-sessions without duplicating /api prefix when API base URL ends with /api", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ id: "session-1", ticker: "BBRI" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await getSession("session-1");

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const requestedUrl = fetchMock.mock.calls[0][0] as string;

    // Should resolve to https://tradepilotai.deployroom.my.id/api/v2/trade-sessions/session-1
    expect(requestedUrl).toBe("https://tradepilotai.deployroom.my.id/api/v2/trade-sessions/session-1");
    // Must NEVER produce /api/api/
    expect(requestedUrl).not.toContain("/api/api/");
  });

  it("resolves listSessions to /api/v2/trade-sessions without duplicate prefix", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ sessions: [] }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await listSessions();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const requestedUrl = fetchMock.mock.calls[0][0] as string;

    expect(requestedUrl).toBe("https://tradepilotai.deployroom.my.id/api/v2/trade-sessions");
    expect(requestedUrl).not.toContain("/api/api/");
  });
});
