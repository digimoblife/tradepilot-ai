import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import SessionsPage from "@/app/sessions/page";
import { listSessions } from "@/features/trade-workspace/api";
import type { SessionStatus, TradeSessionListItem } from "@/features/trade-workspace/types";
import { ApiError, AuthenticationError } from "@/lib/api/errors";

vi.mock("@/features/trade-workspace/api", () => ({
  listSessions: vi.fn(),
}));

function session(
  id: string,
  ticker: string,
  status: SessionStatus,
  archivedAt: string | null = null,
): TradeSessionListItem {
  return {
    id,
    ticker,
    company_name: `${ticker} Company`,
    status,
    note: null,
    created_at: "2026-08-04T00:00:00Z",
    updated_at: "2026-08-04T00:00:00Z",
    closed_at: status === "CLOSED" || status === "CLOSED_SKIPPED"
      ? "2026-08-04T01:00:00Z"
      : null,
    archived_at: archivedAt,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("Sessions list data surface", () => {
  it("loads directly, preserves backend order, renders every non-archived status, and links to detail", async () => {
    const sessions = [
      session("s-closed", "CLOS", "CLOSED"),
      session("s-draft", "DRFT", "DRAFT"),
      session("s-analyzing", "ANLY", "ANALYZING"),
      session("s-analyzed", "DONE", "ANALYZED"),
      session("s-waiting", "WAIT", "WAITING"),
      session("s-open", "OPEN", "OPEN_POSITION"),
      session("s-skipped", "SKIP", "CLOSED_SKIPPED"),
      session("s-archived", "HIDE", "CLOSED", "2026-08-04T02:00:00Z"),
    ];
    vi.mocked(listSessions).mockResolvedValue({ sessions });

    render(<SessionsPage />);
    expect(screen.getByRole("heading", { name: "Sesi Perdagangan" })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Memuat sesi perdagangan");

    await screen.findByRole("heading", { level: 2, name: "Needs Attention" });
    const sections = Array.from(
      document.querySelectorAll<HTMLElement>('section[aria-labelledby^="sessions-group-"]'),
    );
    expect(sections.map((section) => within(section).getByRole("heading", { level: 2 }).textContent)).toEqual([
      "Needs Attention",
      "In Progress",
      "Completed",
    ]);
    expect(sections.map((section) => within(section).getAllByRole("heading", { level: 3 }).map((heading) => heading.textContent))).toEqual([
      ["DRFT", "DONE"],
      ["ANLY", "WAIT", "OPEN"],
      ["CLOS", "SKIP"],
    ]);
    expect(sections.every((section) => within(section).getAllByRole("list").length === 1)).toBe(true);
    expect(screen.getAllByRole("link", { name: "Buka Sesi" })).toHaveLength(7);
    expect(screen.queryByText("HIDE")).toBeNull();
    expect(screen.getByText("Selesai")).toBeInTheDocument();
    expect(screen.getByText("Dilewati")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Buat Sesi Baru" })).toHaveAttribute(
      "href",
      "/sessions/new",
    );
    expect(listSessions).toHaveBeenCalledTimes(1);
    expect(listSessions).toHaveBeenCalledWith(expect.any(AbortSignal));
  });

  it("renders a controlled empty state with navigation but no embedded create form", async () => {
    vi.mocked(listSessions).mockResolvedValue({ sessions: [] });
    render(<SessionsPage />);

    expect(await screen.findByText("Belum ada sesi perdagangan.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Buat Sesi Baru" })).toHaveAttribute(
      "href",
      "/sessions/new",
    );
    expect(screen.queryByRole("form")).toBeNull();
    expect(screen.queryByLabelText(/kode saham|nama perusahaan|catatan/i)).toBeNull();
  });

  it("sanitizes failures and retries with a fresh request", async () => {
    vi.mocked(listSessions)
      .mockRejectedValueOnce(
        new ApiError(500, "INTERNAL_ERROR", "database host secret.internal"),
      )
      .mockResolvedValueOnce({ sessions: [session("retry", "RTRY", "DRAFT")] });
    render(<SessionsPage />);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Daftar sesi tidak dapat dimuat");
    expect(alert).not.toHaveTextContent("database host");
    expect(alert).not.toHaveTextContent("secret.internal");

    await userEvent.click(screen.getByRole("button", { name: "Coba lagi" }));
    await screen.findByText("RTRY");
    expect(listSessions).toHaveBeenCalledTimes(2);
  });

  it("clears protected data and offers safe login recovery on authentication failure", async () => {
    vi.mocked(listSessions).mockRejectedValue(
      new AuthenticationError(401, "AUTHENTICATION_EXPIRED", "raw auth detail"),
    );
    render(<SessionsPage />);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Sesi Anda telah berakhir");
    expect(alert).not.toHaveTextContent("raw auth detail");
    expect(screen.queryByRole("list")).toBeNull();
    expect(screen.getByRole("link", { name: "Masuk kembali" })).toHaveAttribute(
      "href",
      "/login?next=%2Fsessions",
    );
  });

  it("does not create a request loop after the success state is stable", async () => {
    vi.mocked(listSessions).mockResolvedValue({ sessions: [session("stable", "STBL", "DRAFT")] });
    const view = render(<SessionsPage />);
    await screen.findByText("STBL");

    view.rerender(<SessionsPage />);
    await waitFor(() => expect(listSessions).toHaveBeenCalledTimes(1));
  });

  it.each([
    ["DRAFT" as SessionStatus, "Needs Attention", ["In Progress", "Completed"]],
    ["OPEN_POSITION" as SessionStatus, "In Progress", ["Needs Attention", "Completed"]],
    ["CLOSED" as SessionStatus, "Completed", ["Needs Attention", "In Progress"]],
  ])("hides empty groups for a list containing only %s", async (status, visible, hidden) => {
    vi.mocked(listSessions).mockResolvedValue({ sessions: [session("only", "ONLY", status)] });
    render(<SessionsPage />);

    expect(await screen.findByRole("heading", { level: 2, name: visible })).toBeVisible();
    for (const label of hidden) {
      expect(screen.queryByRole("heading", { level: 2, name: label })).toBeNull();
    }
  });

  it("excludes an unexpected runtime status, keeps valid groups, and surfaces a controlled signal", async () => {
    const invalid = session("invalid", "BAD", "DRAFT");
    invalid.status = "UNEXPECTED_RUNTIME_STATUS" as SessionStatus;
    vi.mocked(listSessions).mockResolvedValue({
      sessions: [invalid, session("valid", "GOOD", "WAITING")],
    });
    render(<SessionsPage />);

    expect(await screen.findByRole("heading", { level: 2, name: "In Progress" })).toBeVisible();
    expect(screen.getByText("GOOD")).toBeVisible();
    expect(screen.queryByText("BAD")).toBeNull();
    expect(screen.getByRole("alert")).toHaveTextContent("status tidak dikenali");
    expect(
      document.querySelectorAll('section[aria-labelledby^="sessions-group-"]'),
    ).toHaveLength(1);
  });
});
