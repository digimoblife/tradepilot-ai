import { describe, it, expect, vi, beforeEach } from "vitest";
import { publicEnv } from "@/lib/env";

// Mock fetch globally
const mockFetch = vi.fn();
globalThis.fetch = mockFetch;

beforeEach(() => {
  vi.resetAllMocks();
});

// -------------------------------------------------------------------
// Environment
// -------------------------------------------------------------------
describe("environment", () => {
  it("reads API base URL from env with fallback", () => {
    expect(publicEnv.apiBaseUrl).toBe("http://localhost:8000");
  });

  it("has no hardcoded production URL", () => {
    // The default is localhost:8000 — not a production URL
    expect(publicEnv.apiBaseUrl).not.toContain("tradepilot");
    expect(publicEnv.apiBaseUrl).not.toContain(".com");
    expect(publicEnv.apiBaseUrl).not.toContain(".app");
  });
});

// -------------------------------------------------------------------
// URL joining
// -------------------------------------------------------------------
describe("URL joining", () => {
  it("joins path with base URL", async () => {
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ id: "1" }), { status: 200 }),
    );
    const { get } = await import("./client");
    await get("/api/trade-sessions");
    const calledUrl = mockFetch.mock.calls[0][0];
    expect(calledUrl).toBe("http://localhost:8000/api/trade-sessions");
  });
});

// -------------------------------------------------------------------
// JSON request/response
// -------------------------------------------------------------------
describe("JSON request/response", () => {
  it("sends JSON body with correct content-type", async () => {
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ id: "abc" }), { status: 200 }),
    );
    const { post } = await import("./client");
    await post("/api/trade-sessions", { ticker: "BBRI" });
    const [url, opts] = mockFetch.mock.calls[0];
    expect(url).toBe("http://localhost:8000/api/trade-sessions");
    expect(opts.method).toBe("POST");
    expect(opts.headers["Content-Type"]).toBe("application/json");
    expect(JSON.parse(opts.body)).toEqual({ ticker: "BBRI" });
  });

  it("parses JSON response", async () => {
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ id: "abc", ticker: "BBRI" }), { status: 200 }),
    );
    const { post } = await import("./client");
    const result = await post("/api/trade-sessions", { ticker: "BBRI" });
    expect(result).toEqual({ id: "abc", ticker: "BBRI" });
  });
});

// -------------------------------------------------------------------
// Authentication cookies
// -------------------------------------------------------------------
describe("authentication cookies", () => {
  it("sends credentials include", async () => {
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({}), { status: 200 }),
    );
    const { get } = await import("./client");
    await get("/api/auth/me");
    const [, opts] = mockFetch.mock.calls[0];
    expect(opts.credentials).toBe("include");
  });
});

// -------------------------------------------------------------------
// Empty response (204)
// -------------------------------------------------------------------
describe("empty response", () => {
  it("handles 204 with no body", async () => {
    mockFetch.mockResolvedValueOnce(
      new Response(null, { status: 204 }),
    );
    const { post } = await import("./client");
    const result = await post("/api/auth/logout");
    expect(result).toBeUndefined();
  });
});

// -------------------------------------------------------------------
// Query parameters
// -------------------------------------------------------------------
describe("query parameters", () => {
  it("appends query params to URL", async () => {
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ sessions: [], total: 0 }), { status: 200 }),
    );
    const { get } = await import("./client");
    await get("/api/trade-sessions", { status: "DRAFT", limit: 10 });
    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain("status=DRAFT");
    expect(url).toContain("limit=10");
  });

  it("skips undefined query params", async () => {
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ sessions: [], total: 0 }), { status: 200 }),
    );
    const { get } = await import("./client");
    await get("/api/trade-sessions", { status: undefined, limit: 5 });
    const [url] = mockFetch.mock.calls[0];
    expect(url).not.toContain("status");
    expect(url).toContain("limit=5");
  });
});

// -------------------------------------------------------------------
// Multipart upload
// -------------------------------------------------------------------
describe("multipart upload", () => {
  it("sends FormData without Content-Type header", async () => {
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ id: "ev1" }), { status: 201 }),
    );
    const { upload } = await import("./client");
    const fd = new FormData();
    fd.append("file", new File(["test"], "test.png", { type: "image/png" }));
    fd.append("evidence_type", "CHART_THREE_MONTH");
    await upload("/api/trade-sessions/sid/evidence", fd);
    const [, opts] = mockFetch.mock.calls[0];
    // Content-Type should NOT be set for FormData (browser sets boundary)
    expect(opts.headers["Content-Type"]).toBeUndefined();
  });
});

// -------------------------------------------------------------------
// Binary response
// -------------------------------------------------------------------
describe("binary response", () => {
  it("download returns raw Response for blob extraction", async () => {
    const blob = new Blob(["image-data"], { type: "image/png" });
    mockFetch.mockResolvedValueOnce(
      new Response(blob, { status: 200, headers: { "Content-Type": "image/png" } }),
    );
    const { download } = await import("./client");
    const response = await download("/api/evidence/eid/file");
    const resultBlob = await response.blob();
    expect(resultBlob.type).toBe("image/png");
  });
});

// -------------------------------------------------------------------
// Error contract
// -------------------------------------------------------------------
describe("error contract", () => {
  it("parses TP-1007 error envelope", async () => {
    mockFetch.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          error: {
            code: "ANALYSIS_JOB_ALREADY_ACTIVE",
            message: "Tugas analisis untuk tipe ini sudah aktif.",
            details: null,
            request_id: null,
          },
        }),
        { status: 409 },
      ),
    );
    const { post } = await import("./client");
    try {
      await post("/api/trade-sessions/sid/analyses", { analysis_type: "WATCHING_UPDATE" });
    } catch (e: unknown) {
      const err = e as { code: string; message: string; details: unknown; requestId: unknown };
      expect(err.code).toBe("ANALYSIS_JOB_ALREADY_ACTIVE");
      expect(err.message).toContain("sudah aktif");
      expect(err.details).toBeNull();
      expect(err.requestId).toBeNull();
    }
  });

  it("returns safe fallback for non-JSON error", async () => {
    mockFetch.mockResolvedValueOnce(
      new Response("<html>Server Error</html>", { status: 500 }),
    );
    const { get } = await import("./client");
    try {
      await get("/api/trade-sessions/sid/context");
    } catch (e: unknown) {
      const err = e as { status: number; code: string };
      expect(err.status).toBe(500);
      expect(err.code).toBe("INTERNAL_ERROR");
    }
  });
});

// -------------------------------------------------------------------
// Authentication error
// -------------------------------------------------------------------
describe("authentication error", () => {
  it("returns AuthenticationError for 401", async () => {
    mockFetch.mockResolvedValueOnce(
      new Response(
        JSON.stringify({ error: { code: "AUTHENTICATION_REQUIRED", message: "Autentikasi diperlukan." } }),
        { status: 401 },
      ),
    );
    const { get } = await import("./client");
    try {
      await get("/api/trade-sessions");
    } catch (e: unknown) {
      const err = e as { name: string; status: number };
      expect(err.name).toBe("AuthenticationError");
      expect(err.status).toBe(401);
    }
  });

  it("403 is distinguishable from 401", async () => {
    mockFetch.mockResolvedValueOnce(
      new Response(
        JSON.stringify({ error: { code: "AUTHENTICATION_INACTIVE", message: "Akun tidak aktif." } }),
        { status: 403 },
      ),
    );
    const { get } = await import("./client");
    try {
      await get("/api/trade-sessions");
    } catch (e: unknown) {
      const err = e as { status: number; code: string };
      expect(err.status).toBe(403);
      expect(err.code).toBe("AUTHENTICATION_INACTIVE");
    }
  });
});
