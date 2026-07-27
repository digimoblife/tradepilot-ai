import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { OpenPositionPanel } from "./open-position-panel";
import type { TradeState, EvidenceBatchSummary } from "@/types/trade-session";
import * as tradeSessionApi from "@/lib/api/trade-sessions";

vi.mock("@/lib/api/trade-sessions", () => ({
  updateOpenPositionBatchSlot: vi.fn().mockResolvedValue({}),
  confirmStop: vi.fn().mockResolvedValue({ session_id: "s1", action_type: "STOP_LOSS_CONFIRMED", active_stop_loss: 4800 }),
  confirmTarget: vi.fn().mockResolvedValue({ session_id: "s1", action_type: "TARGET_CONFIRMED", active_target: 5500 }),
}));

describe("OpenPositionPanel", () => {
  const mockTradeState: TradeState = {
    position_status: "OPEN",
    thesis_status: "INTACT",
    entry_price: "5000",
    entry_at: "2026-07-27T10:00:00Z",
    original_quantity: "100",
    remaining_quantity: "100",
    active_stop_loss: null,
    active_target: null,
    average_exit_price: null,
    realized_pnl: null,
    realized_return: null,
    state_version: 1,
  };

  const mockDraftBatch: EvidenceBatchSummary = {
    id: "b1",
    session_id: "s1",
    analysis_type: "OPEN_POSITION_UPDATE",
    status: "DRAFT",
    sequence_number: 1,
    label: "Open Position Update Batch 1",
    monitoring_slot: "UNSPECIFIED",
    created_at: "2026-07-27T10:00:00Z",
    ready_at: null,
    processing_at: null,
    frozen_at: null,
    failed_at: null,
  };

  const defaultProps = {
    sessionId: "s1",
    tradeState: mockTradeState,
    currentBatch: mockDraftBatch,
    allowedActions: [
      "REQUEST_OPEN_POSITION_UPDATE",
      "CONFIRM_STOP",
      "CONFIRM_TARGET",
      "FULL_EXIT",
    ],
    onRequestUpdate: vi.fn(),
    onFullExit: vi.fn(),
    onSuccess: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders position facts and default UNSPECIFIED slot", () => {
    render(<OpenPositionPanel {...defaultProps} />);
    expect(screen.getByText("Posisi Terbuka")).toBeInTheDocument();
    expect(screen.getByText("Rp 5.000")).toBeInTheDocument();
    expect(screen.getByText("Tidak Ditentukan")).toBeInTheDocument();
  });

  it("renders safe missing-data text when values are null", () => {
    const emptyState: TradeState = {
      ...mockTradeState,
      entry_price: null,
      remaining_quantity: null,
      active_stop_loss: null,
      active_target: null,
    };
    render(<OpenPositionPanel {...defaultProps} tradeState={emptyState} />);
    expect(screen.getAllByText("Tidak tersedia")).toHaveLength(2);
    expect(screen.getAllByText("Belum ditentukan")).toHaveLength(2);
  });

  it("allows selecting a monitoring slot", async () => {
    render(<OpenPositionPanel {...defaultProps} />);
    const morningBtn = screen.getByText("Pagi / Pembukaan");
    fireEvent.click(morningBtn);

    await waitFor(() => {
      expect(tradeSessionApi.updateOpenPositionBatchSlot).toHaveBeenCalledWith(
        "s1",
        "b1",
        "MORNING",
      );
      expect(defaultProps.onSuccess).toHaveBeenCalled();
    });
  });

  it("triggers onRequestUpdate when clicking Minta Update Posisi", () => {
    render(<OpenPositionPanel {...defaultProps} />);
    const btn = screen.getByText("Minta Update Posisi");
    fireEvent.click(btn);
    expect(defaultProps.onRequestUpdate).toHaveBeenCalled();
  });

  it("triggers onFullExit when clicking Jual (sell remains explicit)", () => {
    render(<OpenPositionPanel {...defaultProps} />);
    const btn = screen.getByText("Jual");
    fireEvent.click(btn);
    expect(defaultProps.onFullExit).toHaveBeenCalled();
  });

  it("opens stop loss modal and submits stop loss confirmation", async () => {
    render(<OpenPositionPanel {...defaultProps} />);
    const openBtn = screen.getByText("Ubah Stop Loss");
    fireEvent.click(openBtn);

    expect(screen.getByText("Konfirmasi Stop Loss")).toBeInTheDocument();
    const input = screen.getByRole("spinbutton");
    fireEvent.change(input, { target: { value: "4800" } });

    const submitBtn = screen.getByText("Simpan");
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(tradeSessionApi.confirmStop).toHaveBeenCalledWith(
        "s1",
        expect.objectContaining({ price: 4800 }),
      );
      expect(defaultProps.onSuccess).toHaveBeenCalled();
    });
  });

  it("opens target modal and submits target confirmation", async () => {
    render(<OpenPositionPanel {...defaultProps} />);
    const openBtn = screen.getByText("Ubah Target");
    fireEvent.click(openBtn);

    expect(screen.getByText("Konfirmasi Target")).toBeInTheDocument();
    const input = screen.getByRole("spinbutton");
    fireEvent.change(input, { target: { value: "5500" } });

    const submitBtn = screen.getByText("Simpan");
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(tradeSessionApi.confirmTarget).toHaveBeenCalledWith(
        "s1",
        expect.objectContaining({ price: 5500 }),
      );
      expect(defaultProps.onSuccess).toHaveBeenCalled();
    });
  });
});
