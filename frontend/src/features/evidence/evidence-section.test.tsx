import { describe, it, expect, vi, beforeEach, beforeAll } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { listEvidence, uploadEvidence, replaceEvidence } from "@/lib/api/evidence";

beforeAll(() => {
  globalThis.URL.createObjectURL = vi.fn(() => "blob:test");
  globalThis.URL.revokeObjectURL = vi.fn();
});

vi.mock("@/lib/api/evidence", () => ({
  listEvidence: vi.fn(),
  uploadEvidence: vi.fn(),
  replaceEvidence: vi.fn(),
  downloadEvidenceFile: vi.fn().mockResolvedValue(new Blob(["test"], { type: "image/png" })),
}));

import { EvidenceSection } from "./evidence-section";

function makeItem(overrides: Record<string, unknown> = {}) {
  return {
    id: "ev-1",
    session_id: "sess-1",
    evidence_type: "ORDERBOOK_SCREENSHOT",
    status: "AVAILABLE",
    original_filename: "screenshot.png",
    mime_type: "image/png",
    file_size_bytes: 1024,
    checksum_sha256: "abc123",
    market_timestamp: "2026-07-15T09:30:00Z",
    uploaded_at: "2026-07-15T10:00:00Z",
    caption: null,
    supersedes_evidence_id: null,
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

// -------------------------------------------------------------------
// Initial requirements
// -------------------------------------------------------------------
describe("initial requirements", () => {
  it("shows all three required types", async () => {
    vi.mocked(listEvidence).mockResolvedValue({ evidence: [], total: 0 });
    render(<EvidenceSection sessionId="sess-1" />);
    const charts3 = await screen.findAllByText("Chart 3 Bulan");
    expect(charts3.length).toBeGreaterThanOrEqual(1);
    const charts6 = await screen.findAllByText("Chart 6 Bulan");
    expect(charts6.length).toBeGreaterThanOrEqual(1);
    const orderbook = screen.getAllByText("Screenshot Orderbook");
    expect(orderbook.length).toBeGreaterThanOrEqual(1);
  });

  it("shows missing state as unchecked", async () => {
    vi.mocked(listEvidence).mockResolvedValue({ evidence: [], total: 0 });
    render(<EvidenceSection sessionId="sess-1" />);
    const circles = await screen.findAllByText("○");
    expect(circles.length).toBe(3);
  });

  it("shows active state as checked", async () => {
    vi.mocked(listEvidence).mockResolvedValue({
      evidence: [
        makeItem({ evidence_type: "ORDERBOOK_SCREENSHOT" }),
        makeItem({ id: "ev-2", evidence_type: "CHART_THREE_MONTH" }),
        makeItem({ id: "ev-3", evidence_type: "CHART_SIX_MONTH" }),
      ],
      total: 3,
    });
    render(<EvidenceSection sessionId="sess-1" />);
    const checks = await screen.findAllByText("✓");
    expect(checks.length).toBe(3);
  });
});

// -------------------------------------------------------------------
// Upload form
// -------------------------------------------------------------------
describe("upload form", () => {
  it("has evidence type selector", async () => {
    vi.mocked(listEvidence).mockResolvedValue({ evidence: [], total: 0 });
    render(<EvidenceSection sessionId="sess-1" />);
    expect(await screen.findByLabelText("Tipe Bukti")).toBeTruthy();
  });

  it("has file input accepting images", async () => {
    vi.mocked(listEvidence).mockResolvedValue({ evidence: [], total: 0 });
    render(<EvidenceSection sessionId="sess-1" />);
    const input = screen.getByLabelText("File Gambar");
    expect(input).toBeTruthy();
    expect(input.getAttribute("accept")).toContain("image/png");
    expect(input.getAttribute("accept")).toContain("image/jpeg");
    expect(input.getAttribute("accept")).toContain("image/webp");
  });

  it("calls uploadEvidence on initial upload", async () => {
    const user = userEvent.setup();
    vi.mocked(listEvidence).mockResolvedValue({ evidence: [], total: 0 });
    vi.mocked(uploadEvidence).mockResolvedValue(makeItem());
    render(<EvidenceSection sessionId="sess-1" />);

    await user.selectOptions(screen.getByLabelText("Tipe Bukti"), "CHART_THREE_MONTH");
    const file = new File(["test"], "chart.png", { type: "image/png" });
    const fileInput = screen.getByLabelText("File Gambar");
    await user.upload(fileInput, file);
    await user.click(screen.getAllByText("Unggah")[0]);

    expect(uploadEvidence).toHaveBeenCalledWith("sess-1", file, "CHART_THREE_MONTH", undefined);
  });

  it("shows error when type not selected", async () => {
    const user = userEvent.setup();
    vi.mocked(listEvidence).mockResolvedValue({ evidence: [], total: 0 });
    render(<EvidenceSection sessionId="sess-1" />);
    await user.click(screen.getAllByText("Unggah")[0]);
    expect(screen.getByText("Pilih tipe bukti terlebih dahulu.")).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Orderbook update
// -------------------------------------------------------------------
describe("orderbook update", () => {
  it("calls replaceEvidence when active orderbook exists", async () => {
    const user = userEvent.setup();
    vi.mocked(listEvidence).mockResolvedValue({
      evidence: [makeItem({ evidence_type: "ORDERBOOK_SCREENSHOT" })],
      total: 1,
    });
    vi.mocked(replaceEvidence).mockResolvedValue(makeItem());
    render(<EvidenceSection sessionId="sess-1" />);

    await user.selectOptions(screen.getByLabelText("Tipe Bukti"), "ORDERBOOK_SCREENSHOT");
    const file = new File(["test"], "new.png", { type: "image/png" });
    await user.upload(screen.getAllByLabelText("File Gambar")[0], file);
    await user.click(screen.getAllByText("Unggah")[0]);

    expect(replaceEvidence).toHaveBeenCalledWith("ev-1", file, "ORDERBOOK_SCREENSHOT", undefined);
  });

  it("shows replacement notice when orderbook active", async () => {
    const user = userEvent.setup();
    vi.mocked(listEvidence).mockResolvedValue({
      evidence: [makeItem({ evidence_type: "ORDERBOOK_SCREENSHOT" })],
      total: 1,
    });
    render(<EvidenceSection sessionId="sess-1" />);
    // Wait for content to appear
    await screen.findByText("Evidence");
    // Select orderbook type to trigger the notice
    const selects = screen.getAllByLabelText("Tipe Bukti");
    await user.selectOptions(selects[0], "ORDERBOOK_SCREENSHOT");
    expect(await screen.findByText(/akan digantikan/)).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Loading and error
// -------------------------------------------------------------------
describe("loading and error", () => {
  it("shows loading state", () => {
    vi.mocked(listEvidence).mockImplementation(() => new Promise(() => {}));
    render(<EvidenceSection sessionId="sess-1" />);
    expect(screen.getByText("Memuat bukti…")).toBeTruthy();
  });

  it("shows empty state", async () => {
    vi.mocked(listEvidence).mockResolvedValue({ evidence: [], total: 0 });
    render(<EvidenceSection sessionId="sess-1" />);
    expect(await screen.findByText("Belum ada bukti yang diunggah.")).toBeTruthy();
  });

  it("shows API error safely", async () => {
    const { ApiError } = await import("@/lib/api/errors");
    vi.mocked(listEvidence).mockRejectedValue(
      new ApiError(422, "EVIDENCE_FILE_UNSUPPORTED", "Format file tidak didukung."),
    );
    render(<EvidenceSection sessionId="sess-1" />);
    expect(await screen.findByText("Format file tidak didukung.")).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Evidence list
// -------------------------------------------------------------------
describe("evidence list", () => {
  it("shows evidence type label", async () => {
    vi.mocked(listEvidence).mockResolvedValue({
      evidence: [makeItem()],
      total: 1,
    });
    render(<EvidenceSection sessionId="sess-1" />);
    const items = await screen.findAllByText("Screenshot Orderbook");
    expect(items.length).toBeGreaterThanOrEqual(1);
  });

  it("shows active status label", async () => {
    vi.mocked(listEvidence).mockResolvedValue({
      evidence: [makeItem({ status: "SUPERSEDED" })],
      total: 1,
    });
    render(<EvidenceSection sessionId="sess-1" />);
    expect(await screen.findByText("Digantikan")).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Session isolation
// -------------------------------------------------------------------
describe("session isolation", () => {
  it("loads evidence for the session", async () => {
    vi.mocked(listEvidence).mockResolvedValue({ evidence: [], total: 0 });
    render(<EvidenceSection sessionId="sess-a" />);
    await screen.findByText("Evidence");
    expect(listEvidence).toHaveBeenCalledWith("sess-a");
  });
});

// -------------------------------------------------------------------
// Boundaries
// -------------------------------------------------------------------
describe("boundaries", () => {
  it("does not use direct fetch", () => {
    const src = EvidenceSection.toString();
    expect(src).not.toContain("fetch(");
  });
});
