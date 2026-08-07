import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import LoginPage from "@/app/login/page";

// Mock next/navigation
const mockPush = vi.fn();
const mockGet = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
  useSearchParams: () => ({ get: mockGet }),
}));

// Mock auth context
const mockLogin = vi.fn();
vi.mock("@/lib/auth-context", () => ({
  useAuth: () => ({ login: mockLogin, user: null, loading: false }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

beforeEach(() => {
  vi.clearAllMocks();
  mockGet.mockReturnValue(null);
});

async function submitLogin(next: string | null = null) {
  mockGet.mockReturnValue(next);
  mockLogin.mockResolvedValue(undefined);
  const view = render(<LoginPage />);

  await userEvent.type(view.container.querySelector("input[type='email']")!, "user@test.com");
  await userEvent.type(view.container.querySelector("input[type='password']")!, "pass123");
  await userEvent.click(screen.getByRole("button", { name: /masuk/i }));

  return view;
}

// -------------------------------------------------------------------
// Rendering
// -------------------------------------------------------------------
describe("LoginPage", () => {
  it("renders login form", async () => {
    const { container } = render(await LoginPage());
    expect(container.querySelector("input[type='email']")).toBeTruthy();
    expect(container.querySelector("input[type='password']")).toBeTruthy();
    expect(screen.getByRole("button", { name: /masuk/i })).toBeTruthy();
  });

  it("shows error on empty submit", async () => {
    render(await LoginPage());
    const btn = screen.getByRole("button", { name: /masuk/i });
    await userEvent.click(btn);
    await waitFor(() => {
      expect(screen.getByText(/email dan password harus diisi/i)).toBeTruthy();
    });
  });

  it("keeps the login payload unchanged and uses /sessions by default", async () => {
    mockLogin.mockResolvedValue(undefined);
    const { container } = render(await LoginPage());

    const emailInput = container.querySelector("input[type='email']")!;
    const passwordInput = container.querySelector("input[type='password']")!;

    await userEvent.type(emailInput, "user@test.com");
    await userEvent.type(passwordInput, "pass123");
    await userEvent.click(screen.getByRole("button", { name: /masuk/i }));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith({
        email: "user@test.com",
        password: "pass123",
      });
      expect(mockPush).toHaveBeenCalledWith("/sessions");
      expect(mockPush).not.toHaveBeenCalledWith("/trade-workspace");
    });
  });

  it("shows Indonesian error on invalid credentials", async () => {
    mockLogin.mockRejectedValue(new Error("Invalid email or password"));
    const { container } = render(await LoginPage());

    await userEvent.type(container.querySelector("input[type='email']")!, "bad@test.com");
    await userEvent.type(container.querySelector("input[type='password']")!, "wrong");
    await userEvent.click(screen.getByRole("button", { name: /masuk/i }));

    await waitFor(() => {
      expect(screen.getByText(/email atau password salah/i)).toBeTruthy();
      expect(mockPush).not.toHaveBeenCalled();
    });
  });

  it("disables button while submitting", async () => {
    let resolveLogin: () => void;
    mockLogin.mockReturnValue(new Promise<void>((r) => { resolveLogin = r; }));

    const { container } = render(await LoginPage());
    await userEvent.type(container.querySelector("input[type='email']")!, "a@b.com");
    await userEvent.type(container.querySelector("input[type='password']")!, "pw");
    await userEvent.click(screen.getByRole("button", { name: /masuk/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /memproses/i })).toBeDisabled();
    });

    resolveLogin!();
  });

  it("follows safe next redirect and normalizes legacy /trade-workspace to /sessions", async () => {
    mockGet.mockReturnValue("/trade-workspace");
    mockLogin.mockResolvedValue(undefined);
    const { container } = render(await LoginPage());

    await userEvent.type(container.querySelector("input[type='email']")!, "a@b.com");
    await userEvent.type(container.querySelector("input[type='password']")!, "pw");
    await userEvent.click(screen.getByRole("button", { name: /masuk/i }));

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/sessions");
    });
  });

  it("preserves approved protected intended routes and safe query strings", async () => {
    const destinations = [
      "/sessions",
      "/sessions/new",
      "/sessions/archived",
      "/sessions/session-123",
      "/sessions/session-123/analysis",
      "/sessions/session-123/history?view=full",
      "/trade-workspace",
    ];

    for (const destination of destinations) {
      const expectedDestination = destination === "/trade-workspace" ? "/sessions" : destination;
      const view = await submitLogin(destination);
      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith(expectedDestination);
      });
      view.unmount();
      mockPush.mockClear();
    }
  });

  it("rejects unsafe, malformed, looping, public, and unsupported targets", async () => {
    const unsafeDestinations = [
      "https://example.com",
      "//example.com",
      "javascript:alert(1)",
      "/\\example.com",
      "/sessions/%",
      "/sessions/session-123/unsupported",
      "/login",
      "/",
      "/evaluations",
    ];

    for (const destination of unsafeDestinations) {
      const view = await submitLogin(destination);
      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith("/sessions");
      });
      view.unmount();
      mockPush.mockClear();
    }
  });
});
