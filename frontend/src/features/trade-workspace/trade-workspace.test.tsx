import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CreateTradeSession } from "./create-session";
import { InitialAnalysisResultView } from "./result";
import { TradeWorkspaceSessionList } from "./session-list";
import { createSession } from "./api";
import type { TradeSession } from "./types";
vi.mock("./api", () => ({ createSession: vi.fn() }));
const session: TradeSession = { id: "s1", ticker: "BBRI", company_name: "Bank Rakyat", status: "DRAFT", note: "catatan", created_at: "2026-01-01", updated_at: "2026-01-01", closed_at: null };
beforeEach(() => vi.clearAllMocks());
describe("rebuild trade workspace primitives", () => {
  it("validates required session fields and trims submitted values", async () => { const user = userEvent.setup(); render(<CreateTradeSession onCreated={vi.fn()} />); await user.click(screen.getByText("Buat Sesi")); expect(screen.getByRole("alert")).toHaveTextContent("wajib"); await user.type(screen.getByLabelText("Kode Saham"), " BBRI "); await user.type(screen.getByLabelText("Nama Perusahaan"), " Bank Rakyat "); vi.mocked(createSession).mockResolvedValue(session); await user.click(screen.getByText("Buat Sesi")); expect(createSession).toHaveBeenCalledWith({ ticker: "BBRI", company_name: "Bank Rakyat", note: null }); });
  it("keeps sessions selectable independently and touch-safe", async () => { const user = userEvent.setup(); const onSelect = vi.fn(); render(<TradeWorkspaceSessionList sessions={[session, { ...session, id: "s2", ticker: "TLKM" }]} selectedId="s1" onSelect={onSelect} />); const selectedButton = screen.getByRole("button", { name: /BBRIBank RakyatDRAFT/ }); expect(selectedButton).toHaveClass("min-h-11"); expect(selectedButton).toHaveAttribute("aria-pressed", "true"); await user.click(screen.getByText("TLKM")); expect(onSelect).toHaveBeenCalledWith("s2"); });
  it("renders the new Foreign Flow section in order without decision controls", () => { const { container } = render(<InitialAnalysisResultView result={{ summary: "ringkas", orderbook_analysis: "book", three_month_chart_analysis: "3m", six_month_chart_analysis: "6m", foreign_flow_analysis: { assessment: "ACCUMULATION", analysis: "Akumulasi konsisten." }, support: { low: 1, high: 2, note: "s" }, resistance: { low: 3, high: 4, note: "r" }, entry_area: { low: 2, high: 3, note: "e" }, stop_recommendation: { level: 1, note: "stop" }, target_recommendation: { level: 5, note: "target" }, probabilities: { upside: 60, downside: 40 }, risks: ["risiko"], trading_plan: "plan", conclusion: "akhir" }} />); expect(screen.getByText("Analisa Foreign Flow")).toBeTruthy(); expect(screen.getByText(/assessment: ACCUMULATION/)).toBeTruthy(); expect(screen.getByText(/analysis: Akumulasi konsisten/)).toBeTruthy(); const headings = [...container.querySelectorAll("h3")].map((item) => item.textContent); expect(headings.indexOf("Analisis Grafik 6 Bulan")).toBeLessThan(headings.indexOf("Analisa Foreign Flow")); expect(headings.indexOf("Analisa Foreign Flow")).toBeLessThan(headings.indexOf("Support")); expect(screen.queryByRole("button")).toBeNull(); });
  it("omits Foreign Flow gracefully for historical Initial results", () => { render(<InitialAnalysisResultView result={{ summary: "ringkas", orderbook_analysis: "book", three_month_chart_analysis: "3m", six_month_chart_analysis: "6m", support: { low: 1, high: 2, note: "s" }, resistance: { low: 3, high: 4, note: "r" }, entry_area: { low: 2, high: 3, note: "e" }, stop_recommendation: { level: 1, note: "stop" }, target_recommendation: { level: 5, note: "target" }, probabilities: { upside: 60, downside: 40 }, risks: ["risiko"], trading_plan: "plan", conclusion: "akhir" }} />); expect(screen.queryByText("Analisa Foreign Flow")).toBeNull(); expect(screen.getByText("Kesimpulan")).toBeTruthy(); });
  it("renders market facts valuation and technical metrics when provided", () => {
    render(
      <InitialAnalysisResultView
        result={{
          summary: "ringkas",
          orderbook_analysis: "book",
          three_month_chart_analysis: "3m",
          six_month_chart_analysis: "6m",
          support: { low: 2850, high: 2810, note: "s" },
          resistance: { low: 3200, high: 3220, note: "r" },
          entry_area: { low: 2950, high: 3020, note: "e" },
          stop_recommendation: { level: 2840, note: "stop" },
          target_recommendation: { level: 3220, note: "target" },
          probabilities: { upside: 65, downside: 35 },
          risks: ["risiko komoditas"],
          trading_plan: "plan",
          conclusion: "akhir",
        }}
        marketFacts={{
          sector: "Energi",
          sub_sector: "Batu Bara",
          pe_ratio: 7.53,
          eps_ttm: 411.7,
          dividend_yield_percent: 3.69,
          dividend_per_share: 114.51,
          beta: -0.33,
          one_year_return_percent: 29.17,
          next_earnings_date: "2026-11-04",
          ma_alignment: "BULLISH_ALIGNMENT",
          ma20: 2622.5,
          rsi14: 86.66,
          system_bid_ask_ratio: 2.5,
          key_supports: [2850, 2810],
        }}
      />
    );
    expect(screen.getByText("Profil & Valuasi Emiten")).toBeTruthy();
    expect(screen.getByText("Energi")).toBeTruthy();
    expect(screen.getByText("Batu Bara")).toBeTruthy();
    expect(screen.getByText("7.53x")).toBeTruthy();
    expect(screen.getByText("Rp 411.70")).toBeTruthy();
    expect(screen.getByText("3.69%")).toBeTruthy();
    expect(screen.getByText("+29.17%")).toBeTruthy();
    expect(screen.getByText("2026-11-04")).toBeTruthy();
    expect(screen.getByText(/BULLISH ALIGNMENT/)).toBeTruthy();
  });
});

