import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { EvaluationDashboard } from "./evaluation-dashboard";
import * as evaluationsApi from "@/lib/api/evaluations";

vi.mock("@/lib/api/evaluations", () => ({
  listEvaluationRecords: vi.fn(),
}));

describe("EvaluationDashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders evaluation metrics and data table", async () => {
    vi.mocked(evaluationsApi.listEvaluationRecords).mockResolvedValueOnce({
      items: [
        {
          id: "rec1",
          owner_id: "u1",
          session_id: "s1",
          ticker: "BBRI",
          analysis_type: "INITIAL_ANALYSIS",
          prediction_data: { recommendation: "BUY" },
          user_decision_data: { user_action: "BUY" },
          outcome_data: { realized_return: "10.0" },
          completeness_status: "COMPLETE",
          legacy_source: false,
          validation_warning_count: 0,
          quality_notes: [],
          created_at: "2026-07-27T10:00:00Z",
          updated_at: "2026-07-27T10:00:00Z",
        },
      ],
      total: 1,
      page: 1,
      limit: 50,
    });

    render(<EvaluationDashboard />);

    await waitFor(() => {
      expect(screen.getByText("Evaluation Records & Dataset")).toBeInTheDocument();
    });

    expect(screen.getByText("BBRI")).toBeInTheDocument();
    expect(screen.getByText("INITIAL_ANALYSIS")).toBeInTheDocument();
    expect(screen.getByText("COMPLETE")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Export JSON" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Export CSV" })).toBeInTheDocument();
  });
});
