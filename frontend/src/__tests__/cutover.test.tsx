import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import HomePage from "@/app/page";
import LoginPage from "@/app/login/page";
import SessionsPage from "@/app/sessions/page";
import SessionDetailPage from "@/app/sessions/[sessionId]/page";
import { Header } from "@/components/header";

const mockReplace = vi.fn();
const mockPush = vi.fn();
const mockRedirect = vi.fn();
const mockLogout = vi.fn();
let mockUser: { id: string; email: string } | null = null;
let mockLoading = false;

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mockReplace, push: mockPush }),
  useSearchParams: () => ({ get: () => null }),
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

beforeEach(() => {
  vi.clearAllMocks();
  mockUser = null;
  mockLoading = false;
});

describe("Reversible Frontend Cutover", () => {
  it("authenticated / resolves to /trade-workspace", async () => {
    mockUser = { id: "user-1", email: "test@example.com" };
    render(<HomePage />);

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith("/trade-workspace");
    });
  });

  it("unauthenticated / renders landing page without redirecting", async () => {
    mockUser = null;
    render(<HomePage />);

    expect(screen.getByText("TradePilot AI")).toBeTruthy();
    expect(mockReplace).not.toHaveBeenCalled();
  });

  it("login success resolves to /trade-workspace", async () => {
    render(await LoginPage());

    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = screen.getByLabelText(/kata sandi/i);

    await userEvent.type(emailInput, "user@example.com");
    await userEvent.type(passwordInput, "secret123");
    await userEvent.click(screen.getByRole("button", { name: /masuk/i }));

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/trade-workspace");
    });
  });

  it("primary sessions navigation in Header points to /trade-workspace when authenticated", () => {
    mockUser = { id: "user-1", email: "test@example.com" };
    render(<Header />);

    const brandLink = screen.getByRole("link", { name: "TradePilot AI" });
    expect(brandLink.getAttribute("href")).toBe("/trade-workspace");

    const sessionsLink = screen.getByRole("link", { name: "Sesi" });
    expect(sessionsLink.getAttribute("href")).toBe("/trade-workspace");
  });

  it("legacy /sessions route invokes redirect('/trade-workspace')", () => {
    SessionsPage();
    expect(mockRedirect).toHaveBeenCalledWith("/trade-workspace");
  });

  it("legacy /sessions/{session_id} route invokes redirect('/trade-workspace')", () => {
    SessionDetailPage();
    expect(mockRedirect).toHaveBeenCalledWith("/trade-workspace");
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
