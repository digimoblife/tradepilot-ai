import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SessionNavigation } from "./session-navigation";

let pathname = "/sessions/11111111-1111-4111-8111-111111111111";

vi.mock("next/navigation", () => ({ usePathname: () => pathname }));

const sessionId = "11111111-1111-4111-8111-111111111111";

describe("SessionNavigation", () => {
  beforeEach(() => { pathname = `/sessions/${sessionId}`; });

  it.each([
    ["", "Ringkasan"],
    ["/analysis", "Analisis"],
    ["/history", "Riwayat"],
  ])("maps the exact %s route to %s only", (suffix, activeLabel) => {
    pathname = `/sessions/${sessionId}${suffix}`;
    render(<SessionNavigation sessionId={sessionId} />);

    const links = screen.getAllByRole("link");
    expect(links.map((link) => link.textContent)).toEqual(["Ringkasan", "Analisis", "Riwayat"]);
    expect(links).toHaveLength(3);
    expect(screen.getByRole("navigation", { name: "Navigasi sesi" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: activeLabel })).toHaveAttribute("aria-current", "page");
    expect(links.filter((link) => link.getAttribute("aria-current") === "page")).toHaveLength(1);
    expect(screen.getByRole("link", { name: "Ringkasan" })).toHaveAttribute("href", `/sessions/${sessionId}`);
    expect(screen.getByRole("link", { name: "Analisis" })).toHaveAttribute("href", `/sessions/${sessionId}/analysis`);
    expect(screen.getByRole("link", { name: "Riwayat" })).toHaveAttribute("href", `/sessions/${sessionId}/history`);
  });

  it("fails closed on an unknown nested route", () => {
    pathname = `/sessions/${sessionId}/analysis-extra`;
    render(<SessionNavigation sessionId={sessionId} />);
    expect(screen.queryByLabelText("Navigasi sesi")).toBeInTheDocument();
    expect(screen.queryByRole("link", { current: "page" })).toBeNull();
  });

  it("contains no route state, storage, mutations, or extra destination", async () => {
    const source = await import("node:fs").then(({ readFileSync }) => readFileSync(
      "src/features/sessions/session-navigation.tsx", "utf8",
    ));
    expect(source).not.toMatch(/useState|localStorage|sessionStorage|available-actions|POST|PATCH|DELETE|trade-workspace|timeline|overview/);
  });
});
