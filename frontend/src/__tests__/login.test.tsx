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
    const { container } = render(await LoginPage());
    const btn = screen.getByRole("button", { name: /masuk/i });
    await userEvent.click(btn);
    await waitFor(() => {
      expect(screen.getByText(/email dan password harus diisi/i)).toBeTruthy();
    });
  });

  it("calls login on submit and redirects", async () => {
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

  it("follows safe next redirect", async () => {
    mockGet.mockReturnValue("/sessions/new");
    mockLogin.mockResolvedValue(undefined);
    const { container } = render(await LoginPage());

    await userEvent.type(container.querySelector("input[type='email']")!, "a@b.com");
    await userEvent.type(container.querySelector("input[type='password']")!, "pw");
    await userEvent.click(screen.getByRole("button", { name: /masuk/i }));

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/sessions/new");
    });
  });

  it("rejects unsafe external redirect", async () => {
    mockGet.mockReturnValue("https://evil.com");
    mockLogin.mockResolvedValue(undefined);
    const { container } = render(await LoginPage());

    await userEvent.type(container.querySelector("input[type='email']")!, "a@b.com");
    await userEvent.type(container.querySelector("input[type='password']")!, "pw");
    await userEvent.click(screen.getByRole("button", { name: /masuk/i }));

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/sessions");
    });
  });
});
