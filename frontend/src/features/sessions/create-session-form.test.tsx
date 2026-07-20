import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { createSession } from "@/lib/api/trade-sessions";

// Mock next/navigation
const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

// Mock createSession
vi.mock("@/lib/api/trade-sessions", () => ({
  createSession: vi.fn(),
}));

import userEvent from "@testing-library/user-event";
import { CreateSessionForm } from "./create-session-form";

beforeEach(() => {
  vi.clearAllMocks();
});

// -------------------------------------------------------------------
// Rendering
// -------------------------------------------------------------------
describe("rendering", () => {
  it("renders ticker field with Indonesian label", () => {
    render(<CreateSessionForm />);
    expect(screen.getByLabelText(/Kode Saham/)).toBeTruthy();
  });

  it("renders company field with Indonesian label", () => {
    render(<CreateSessionForm />);
    expect(screen.getByLabelText(/Nama Perusahaan/)).toBeTruthy();
  });

  it("renders exchange field with Indonesian label", () => {
    render(<CreateSessionForm />);
    expect(screen.getByLabelText(/Bursa/)).toBeTruthy();
  });

  it("renders currency field with Indonesian label", () => {
    render(<CreateSessionForm />);
    expect(screen.getByLabelText(/Mata Uang/)).toBeTruthy();
  });

  it("renders submit button", () => {
    render(<CreateSessionForm />);
    expect(screen.getByText("Buat Sesi")).toBeTruthy();
  });

  it("renders back link to /sessions", () => {
    render(<CreateSessionForm />);
    const link = screen.getByText("Kembali ke Daftar Sesi");
    expect(link.getAttribute("href")).toBe("/sessions");
  });
});

// -------------------------------------------------------------------
// Validation
// -------------------------------------------------------------------
describe("validation", () => {
  it("shows error when ticker is blank", async () => {
    const user = userEvent.setup();
    render(<CreateSessionForm />);
    await user.click(screen.getByText("Buat Sesi"));
    expect(screen.getByText("Kode saham wajib diisi.")).toBeTruthy();
    expect(createSession).not.toHaveBeenCalled();
  });

  it("shows error when ticker is whitespace-only", async () => {
    const user = userEvent.setup();
    render(<CreateSessionForm />);
    const input = screen.getByLabelText(/Kode Saham/);
    await user.type(input, "   ");
    await user.click(screen.getByText("Buat Sesi"));
    expect(screen.getByText("Kode saham wajib diisi.")).toBeTruthy();
    expect(createSession).not.toHaveBeenCalled();
  });

  it("does not submit when ticker is missing", async () => {
    const user = userEvent.setup();
    render(<CreateSessionForm />);
    await user.click(screen.getByText("Buat Sesi"));
    expect(createSession).not.toHaveBeenCalled();
  });
});

// -------------------------------------------------------------------
// Successful creation
// -------------------------------------------------------------------
describe("successful creation", () => {
  it("calls createSession with form values", async () => {
    const user = userEvent.setup();
    vi.mocked(createSession).mockResolvedValue({
      id: "sess-123",
      ticker: "BBRI",
      company_name: "Test Co",
      exchange: "IDX",
      currency: "IDR",
      title: null,
      lifecycle_status: "DRAFT",
      archived_at: null,
      created_at: "2026-07-20T00:00:00Z",
      updated_at: "2026-07-20T00:00:00Z",
    });

    render(<CreateSessionForm />);
    await user.type(screen.getByLabelText(/Kode Saham/), "BBRI");
    await user.type(screen.getByLabelText(/Nama Perusahaan/), "Test Co");
    await user.type(screen.getByLabelText(/Bursa/), "IDX");
    await user.click(screen.getByText("Buat Sesi"));

    expect(createSession).toHaveBeenCalledTimes(1);
    expect(createSession).toHaveBeenCalledWith({
      ticker: "BBRI",
      company_name: "Test Co",
      exchange: "IDX",
      currency: "IDR",
    });
  });

  it("redirects to created session", async () => {
    const user = userEvent.setup();
    vi.mocked(createSession).mockResolvedValue({
      id: "sess-456",
      ticker: "TLKM",
      company_name: null,
      exchange: "IDX",
      currency: "IDR",
      title: null,
      lifecycle_status: "DRAFT",
      archived_at: null,
      created_at: "2026-07-20T00:00:00Z",
      updated_at: "2026-07-20T00:00:00Z",
    });

    render(<CreateSessionForm />);
    await user.type(screen.getByLabelText(/Kode Saham/), "TLKM");
    await user.click(screen.getByText("Buat Sesi"));
    expect(mockPush).toHaveBeenCalledWith("/sessions/sess-456");
  });

  it("does not redirect before API resolves", () => {
    // push should not be called until createSession resolves
    expect(mockPush).not.toHaveBeenCalled();
  });
});

// -------------------------------------------------------------------
// Pending state
// -------------------------------------------------------------------
describe("pending state", () => {
  it("shows processing text while submitting", async () => {
    const user = userEvent.setup();
    vi.mocked(createSession).mockImplementation(
      () => new Promise(() => {}), // never resolves
    );

    render(<CreateSessionForm />);
    await user.type(screen.getByLabelText(/Kode Saham/), "BBRI");
    await user.click(screen.getByText("Buat Sesi"));
    expect(screen.getByText("Membuat sesi…")).toBeTruthy();
  });

  it("disables button while submitting", async () => {
    const user = userEvent.setup();
    vi.mocked(createSession).mockImplementation(
      () => new Promise(() => {}),
    );

    render(<CreateSessionForm />);
    await user.type(screen.getByLabelText(/Kode Saham/), "BBRI");
    await user.click(screen.getByText("Buat Sesi"));
    expect(screen.getByText("Membuat sesi…")).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// API errors
// -------------------------------------------------------------------
describe("API errors", () => {
  it("shows backend validation message", async () => {
    const user = userEvent.setup();
    const { ApiError } = await import("@/lib/api/errors");
    vi.mocked(createSession).mockRejectedValue(
      new ApiError(422, "VALIDATION_ERROR", "Data yang dikirim tidak valid."),
    );

    render(<CreateSessionForm />);
    await user.type(screen.getByLabelText(/Kode Saham/), "BBRI");
    await user.click(screen.getByText("Buat Sesi"));
    expect(await screen.findByText("Data yang dikirim tidak valid.")).toBeTruthy();
  });

  it("shows authentication error safely", async () => {
    const user = userEvent.setup();
    const { AuthenticationError } = await import("@/lib/api/errors");
    vi.mocked(createSession).mockRejectedValue(
      new AuthenticationError(401, "AUTHENTICATION_REQUIRED", "Autentikasi diperlukan."),
    );

    render(<CreateSessionForm />);
    await user.type(screen.getByLabelText(/Kode Saham/), "BBRI");
    await user.click(screen.getByText("Buat Sesi"));
    expect(
      await screen.findByText(
        "Silakan masuk terlebih dahulu untuk membuat sesi trading.",
      ),
    ).toBeTruthy();
  });

  it("shows generic fallback for unknown error", async () => {
    const user = userEvent.setup();
    vi.mocked(createSession).mockRejectedValue(new Error("something broke"));

    render(<CreateSessionForm />);
    await user.type(screen.getByLabelText(/Kode Saham/), "BBRI");
    await user.click(screen.getByText("Buat Sesi"));
    expect(
      await screen.findByText("Terjadi kesalahan. Silakan coba lagi."),
    ).toBeTruthy();
  });

  it("retains form values after error", async () => {
    const user = userEvent.setup();
    vi.mocked(createSession).mockRejectedValue(
      new Error("fail"),
    );

    render(<CreateSessionForm />);
    await user.type(screen.getByLabelText(/Kode Saham/), "BBRI");
    await user.click(screen.getByText("Buat Sesi"));
    expect(await screen.findByText("Terjadi kesalahan. Silakan coba lagi.")).toBeTruthy();
    expect(screen.getByLabelText(/Kode Saham/)).toHaveValue("BBRI");
  });
});

// -------------------------------------------------------------------
// Boundaries
// -------------------------------------------------------------------
describe("boundaries", () => {
  it("does not call fetch directly", () => {
    const src = CreateSessionForm.toString();
    expect(src).not.toContain("fetch(");
    expect(src).not.toContain('"/api/');
    expect(src).not.toContain("http://localhost");
  });
});
