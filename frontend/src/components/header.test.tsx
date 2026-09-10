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

    // Brand link goes to "/" when not logged in
    expect(
      screen.getByRole("link", { name: "TradePilot AI — Beranda" }),
    ).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: "Masuk" })).toHaveAttribute(
      "href",
      "/login",
    );
    // Nav not shown when logged out
    expect(
      screen.queryByRole("navigation", { name: "Navigasi utama" }),
    ).toBeNull();
    expect(screen.queryByRole("button", { name: "Keluar" })).toBeNull();
  });

  it("does not expose authenticated navigation while auth is loading", () => {
    mockLoading = true;
    render(<Header />);

    expect(
      screen.getByRole("link", { name: "TradePilot AI — Beranda" }),
    ).toHaveAttribute("href", "/");
    expect(
      screen.queryByRole("navigation", { name: "Navigasi utama" }),
    ).toBeNull();
    expect(screen.queryByRole("link", { name: "Masuk" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Keluar" })).toBeNull();
  });

  it("renders only the approved authenticated primary navigation and account controls", () => {
    const email = "very-long-trading-identity@example.test";
    mockUser = { id: "user-a", email };
    render(<Header />);

    // Brand link goes to /sessions when logged in
    expect(
      screen.getByRole("link", { name: "TradePilot AI — Beranda" }),
    ).toHaveAttribute("href", "/sessions");

    // Desktop nav present
    const navigation = screen.getByRole("navigation", { name: "Navigasi utama" });
    expect(navigation).toBeInTheDocument();

    // Nav links — desktop labels
    expect(
      screen.getByRole("link", { name: "Sesi Perdagangan" }),
    ).toHaveAttribute("href", "/sessions");
    expect(screen.getByRole("link", { name: "Arsip" })).toHaveAttribute(
      "href",
      "/sessions/archived",
    );

    // Email visible
    expect(screen.getByText(email)).toHaveAttribute("title", email);

    // Exactly one logout button
    expect(screen.getAllByRole("button", { name: "Keluar" })).toHaveLength(1);

    // Unapproved links absent
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
      expect(
        screen.queryByRole("link", { name: unapprovedLabel }),
      ).toBeNull();
    }
  });

  it.each([
    ["/sessions", "Sesi Perdagangan"],
    ["/sessions/new", "Sesi Perdagangan"],
    ["/sessions/session-123", "Sesi Perdagangan"],
    ["/sessions/session-123/analysis", "Sesi Perdagangan"],
    ["/sessions/session-123/history", "Sesi Perdagangan"],
    ["/sessions/archived", "Arsip"],
  ])("marks %s active as %s", (pathname, activeLabel) => {
    mockUser = { id: "user-a", email: "user@example.test" };
    mockPathname = pathname;
    render(<Header />);

    // aria-current="page" on the active desktop nav link
    const activeLink = screen.getByRole("link", { name: activeLabel });
    expect(activeLink).toHaveAttribute("aria-current", "page");

    // The inactive link has no aria-current
    const inactiveLabel =
      activeLabel === "Sesi Perdagangan" ? "Arsip" : "Sesi Perdagangan";
    expect(
      screen.getByRole("link", { name: inactiveLabel }),
    ).not.toHaveAttribute("aria-current");
  });

  it("does not mark primary navigation active on the legacy workspace", () => {
    mockUser = { id: "user-a", email: "user@example.test" };
    mockPathname = "/trade-workspace";
    render(<Header />);

    expect(
      screen.getByRole("link", { name: "Sesi Perdagangan" }),
    ).not.toHaveAttribute("aria-current");
    expect(screen.getByRole("link", { name: "Arsip" })).not.toHaveAttribute(
      "aria-current",
    );
  });

  it("has a full-width sticky header with max-w-7xl inner container", () => {
    mockUser = { id: "user-a", email: "user@example.test" };
    const { container } = render(<Header />);

    const headerEl = container.querySelector("header");
    const innerDiv = container.querySelector("header > div");

    expect(headerEl).toHaveClass("sticky", "top-0", "w-full");
    expect(innerDiv).toHaveClass("max-w-7xl", "mx-auto");
    // No fixed-width shell
    expect(innerDiv?.className).not.toMatch(/\bw-(?:screen|\[)/);
  });

  it("keeps keyboard order logical and logout behavior unchanged", async () => {
    const user = userEvent.setup();
    mockUser = { id: "user-a", email: "user@example.test" };
    render(<Header />);

    // Tab through: brand → desktop nav links → logout button
    await user.tab();
    expect(
      screen.getByRole("link", { name: "TradePilot AI — Beranda" }),
    ).toHaveFocus();
    await user.tab();
    expect(
      screen.getByRole("link", { name: "Sesi Perdagangan" }),
    ).toHaveFocus();
    await user.tab();
    expect(screen.getByRole("link", { name: "Arsip" })).toHaveFocus();
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
