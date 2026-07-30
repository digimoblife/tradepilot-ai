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
  it("keeps sessions selectable independently", async () => { const user = userEvent.setup(); const onSelect = vi.fn(); render(<TradeWorkspaceSessionList sessions={[session, { ...session, id: "s2", ticker: "TLKM" }]} selectedId="s1" onSelect={onSelect} />); await user.click(screen.getByText("TLKM")); expect(onSelect).toHaveBeenCalledWith("s2"); });
  it("renders all thirteen backend result sections without decision controls", () => { render(<InitialAnalysisResultView result={{ summary: "ringkas", orderbook_analysis: "book", three_month_chart_analysis: "3m", six_month_chart_analysis: "6m", support: { low: 1, high: 2, note: "s" }, resistance: { low: 3, high: 4, note: "r" }, entry_area: { low: 2, high: 3, note: "e" }, stop_recommendation: { level: 1, note: "stop" }, target_recommendation: { level: 5, note: "target" }, probabilities: { upside: 60, downside: 40 }, risks: ["risiko"], trading_plan: "plan", conclusion: "akhir" }} />); expect(screen.getByText("Ringkasan")).toBeTruthy(); expect(screen.getByText("Kesimpulan")).toBeTruthy(); expect(screen.queryByRole("button")).toBeNull(); });
});
