import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { Header } from "./header";

const mockLogout = vi.fn().mockResolvedValue(undefined);
const mockPush = vi.fn();
let mockUser: { id: string; email: string } | null = null;
let mockLoading = false;

vi.mock("@/lib/auth-context", () => ({
  useAuth: () => ({ user: mockUser, loading: mockLoading, logout: mockLogout }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

describe("global header", () => {
  it("preserves unauthenticated brand and login navigation", () => {
    mockUser = null;
    mockLoading = false;
    render(<Header />);

    expect(screen.getByRole("link", { name: "TradePilot AI" })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: "Masuk" })).toHaveAttribute("href", "/login");
    expect(screen.queryByRole("button", { name: "Keluar" })).toBeNull();
  });

  it("keeps authenticated navigation, identity, and logout as separate controls", () => {
    const email = "very-long-trading-identity@example.test";
    mockUser = { id: "user-a", email };
    mockLoading = false;
    render(<Header />);

    expect(screen.getByRole("link", { name: "TradePilot AI" })).toHaveAttribute("href", "/trade-workspace");
    expect(screen.getByRole("link", { name: "Sesi" })).toHaveAttribute("href", "/trade-workspace");
    expect(screen.getByText(email)).toHaveAttribute("title", email);
    expect(screen.getByRole("button", { name: "Keluar" })).toBeInTheDocument();
  });
});
