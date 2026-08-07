import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import HomePage from "@/app/page";
import LoginPage from "@/app/login/page";
import SessionsPage from "@/app/sessions/page";
import SessionDetailPage from "@/app/sessions/[sessionId]/page";
import TradeWorkspacePage from "@/app/trade-workspace/page";
import { Header } from "@/components/header";
import { listSessions } from "@/features/trade-workspace/api";

const mockReplace = vi.fn();
const mockPush = vi.fn();
const mockRedirect = vi.fn();
const mockLogout = vi.fn();
let mockUser: { id: string; email: string } | null = null;
let mockLoading = false;

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mockReplace, push: mockPush }),
  useSearchParams: () => ({ get: () => null }),
  usePathname: () => "/sessions",
  redirect: (url: string) => mockRedirect(url),
}));

vi.mock("@/lib/auth-context", () => ({
  useAuth: () => ({
    user: mockUser,
    loading: mockLoading,
    logout: mockLogout,
    login: vi.fn().mockResolvedValue(undefined),
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("@/features/trade-workspace/api", () => ({
  getSession: vi.fn(),
  listSessions: vi.fn(),
}));

beforeEach(() => {
  vi.clearAllMocks();
  mockUser = null;
  mockLoading = false;
  vi.mocked(listSessions).mockResolvedValue({ sessions: [] });
});

describe("Reversible Frontend Cutover", () => {
  it("authenticated / resolves to /sessions", async () => {
    mockUser = { id: "user-1", email: "test@example.com" };
    render(<HomePage />);

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith("/sessions");
    });
  });

  it("unauthenticated / renders landing page without redirecting", async () => {
    mockUser = null;
    render(<HomePage />);

    expect(screen.getByText("TradePilot AI")).toBeTruthy();
    expect(mockReplace).not.toHaveBeenCalled();
  });

  it("/trade-workspace route redirects directly to /sessions", () => {
    TradeWorkspacePage();
    expect(mockRedirect).toHaveBeenCalledWith("/sessions");
  });

  it("login success resolves to /sessions", async () => {
    render(await LoginPage());

    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = screen.getByLabelText(/kata sandi/i);

    await userEvent.type(emailInput, "user@example.com");
    await userEvent.type(passwordInput, "secret123");
    await userEvent.click(screen.getByRole("button", { name: /masuk/i }));

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/sessions");
    });
  });

  it("primary Header navigation points to Sessions and Archive when authenticated", () => {
    mockUser = { id: "user-1", email: "test@example.com" };
    render(<Header />);

    const brandLink = screen.getByRole("link", { name: "TradePilot AI" });
    expect(brandLink.getAttribute("href")).toBe("/sessions");

    const sessionsLink = screen.getByRole("link", { name: "Sessions" });
    expect(sessionsLink.getAttribute("href")).toBe("/sessions");
    expect(screen.getByRole("link", { name: "Archive" }).getAttribute("href")).toBe(
      "/sessions/archived",
    );
    expect(screen.queryByRole("link", { name: /trade workspace/i })).toBeNull();
  });

  it("/sessions renders its own route shell", () => {
    render(<SessionsPage />);
    expect(screen.getByRole("heading", { name: "Sesi Perdagangan" })).toBeTruthy();
  });

  it("/sessions/{session_id} renders its own route shell", async () => {
    render(
      await SessionDetailPage({
        params: Promise.resolve({ sessionId: "session-1" }),
      }),
    );
    expect(screen.getByRole("heading", { name: "Ringkasan Sesi" })).toBeTruthy();
  });

  it("logout behavior remains unchanged and pushes to /login", async () => {
    mockUser = { id: "user-1", email: "test@example.com" };
    mockLogout.mockResolvedValue(undefined);

    render(<Header />);
    const logoutBtn = screen.getByRole("button", { name: "Keluar" });
    await userEvent.click(logoutBtn);

    await waitFor(() => {
      expect(mockLogout).toHaveBeenCalled();
      expect(mockPush).toHaveBeenCalledWith("/login");
    });
  });
});
