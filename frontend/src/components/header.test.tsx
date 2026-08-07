import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Header } from "./header";

const mockLogout = vi.fn().mockResolvedValue(undefined);
const mockPush = vi.fn();
let mockPathname = "/sessions";
let mockUser: { id: string; email: string } | null = null;
let mockLoading = false;

vi.mock("@/lib/auth-context", () => ({
  useAuth: () => ({ user: mockUser, loading: mockLoading, logout: mockLogout }),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => mockPathname,
  useRouter: () => ({ push: mockPush }),
}));

beforeEach(() => {
  vi.clearAllMocks();
  mockPathname = "/sessions";
  mockUser = null;
  mockLoading = false;
});

describe("global header", () => {
  it("preserves reduced unauthenticated brand and login navigation", () => {
    render(<Header />);

    expect(screen.getByRole("link", { name: "TradePilot AI" })).toHaveAttribute(
      "href",
      "/",
    );
    expect(screen.getByRole("link", { name: "Masuk" })).toHaveAttribute("href", "/login");
    expect(screen.queryByRole("navigation", { name: "Navigasi utama" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Keluar" })).toBeNull();
  });

  it("does not expose authenticated navigation while auth is loading", () => {
    mockLoading = true;
    render(<Header />);

    expect(screen.getByRole("link", { name: "TradePilot AI" })).toHaveAttribute(
      "href",
      "/",
    );
    expect(screen.queryByRole("navigation", { name: "Navigasi utama" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Masuk" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Keluar" })).toBeNull();
  });

  it("renders only the approved authenticated primary navigation and account controls", () => {
    const email = "very-long-trading-identity@example.test";
    mockUser = { id: "user-a", email };
    render(<Header />);

    expect(screen.getByRole("link", { name: "TradePilot AI" })).toHaveAttribute(
      "href",
      "/sessions",
    );
    const navigation = screen.getByRole("navigation", { name: "Navigasi utama" });
    expect(navigation).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sessions" })).toHaveAttribute(
      "href",
      "/sessions",
    );
    expect(screen.getByRole("link", { name: "Archive" })).toHaveAttribute(
      "href",
      "/sessions/archived",
    );
    expect(screen.getByText(email)).toHaveAttribute("title", email);
    expect(screen.getAllByRole("button", { name: "Keluar" })).toHaveLength(1);
    expect(screen.queryByRole("link", { name: /trade workspace/i })).toBeNull();

    for (const unapprovedLabel of [
      "Dashboard",
      "Analytics",
      "Portfolio",
      "Evaluations",
      "Settings",
      "Notifications",
      "Watchlist",
      "Reports",
      "Help",
    ]) {
      expect(screen.queryByRole("link", { name: unapprovedLabel })).toBeNull();
    }
  });

  it.each([
    ["/sessions", "Sessions"],
    ["/sessions/new", "Sessions"],
    ["/sessions/session-123", "Sessions"],
    ["/sessions/session-123/analysis", "Sessions"],
    ["/sessions/session-123/history", "Sessions"],
    ["/sessions/archived", "Archive"],
  ])("marks %s active as %s", (pathname, activeLabel) => {
    mockUser = { id: "user-a", email: "user@example.test" };
    mockPathname = pathname;
    render(<Header />);

    const activeLink = screen.getByRole("link", { name: activeLabel });
    const inactiveLabel = activeLabel === "Sessions" ? "Archive" : "Sessions";
    expect(activeLink).toHaveAttribute("aria-current", "page");
    expect(activeLink).toHaveClass("font-semibold");
    expect(screen.getByRole("link", { name: inactiveLabel })).not.toHaveAttribute(
      "aria-current",
    );
  });

  it("does not mark primary navigation active on the legacy workspace", () => {
    mockUser = { id: "user-a", email: "user@example.test" };
    mockPathname = "/trade-workspace";
    render(<Header />);

    expect(screen.getByRole("link", { name: "Sessions" })).not.toHaveAttribute(
      "aria-current",
    );
    expect(screen.getByRole("link", { name: "Archive" })).not.toHaveAttribute(
      "aria-current",
    );
  });

  it("uses a compact two-row mobile structure without fixed shell widths", () => {
    mockUser = { id: "user-a", email: "very-long-trading-identity@example.test" };
    const { container } = render(<Header />);

    const shell = container.querySelector("header > div");
    const navigation = screen.getByRole("navigation", { name: "Navigasi utama" });
    const email = screen.getByText("very-long-trading-identity@example.test");

    expect(shell).toHaveClass("grid", "grid-cols-[minmax(0,1fr)_auto]");
    expect(shell).toHaveClass("sm:grid-cols-[auto_minmax(0,1fr)_auto]");
    expect(navigation).toHaveClass("row-start-2", "sm:row-start-1", "min-w-0");
    expect(email).toHaveClass("sr-only", "sm:not-sr-only", "sm:truncate");
    expect(screen.getByRole("link", { name: "Sessions" })).toHaveClass("min-h-11");
    expect(screen.getByRole("link", { name: "Archive" })).toHaveClass("min-h-11");
    expect(screen.getByRole("button", { name: "Keluar" })).toHaveClass("min-h-11");
    expect(shell?.className).not.toMatch(/\bw-(?:screen|\[)/);
  });

  it("keeps keyboard order logical and logout behavior unchanged", async () => {
    const user = userEvent.setup();
    mockUser = { id: "user-a", email: "user@example.test" };
    render(<Header />);

    await user.tab();
    expect(screen.getByRole("link", { name: "TradePilot AI" })).toHaveFocus();
    await user.tab();
    expect(screen.getByRole("link", { name: "Sessions" })).toHaveFocus();
    await user.tab();
    expect(screen.getByRole("link", { name: "Archive" })).toHaveFocus();
    await user.tab();
    const logoutButton = screen.getByRole("button", { name: "Keluar" });
    expect(logoutButton).toHaveFocus();

    await user.keyboard("{Enter}");
    await waitFor(() => {
      expect(mockLogout).toHaveBeenCalledTimes(1);
      expect(mockPush).toHaveBeenCalledWith("/login");
    });
  });
});
