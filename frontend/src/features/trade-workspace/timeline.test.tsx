import { describe, expect, it } from "vitest";
import { buildTimelineEvents } from "./timeline";
import type { SessionDetailAggregate } from "./types";

const aggregate: SessionDetailAggregate = {
  latest_analysis: null,
  recent_activity: [],
  current_step: {
    code: "TERMINAL_CLOSED",
    mode: "READ_ONLY",
    workflow_actions: [],
    active_request: null,
    failed_request: null,
    read_only: true,
  },
  session: { id: "s1", ticker: "BBRI", company_name: "Bank BRI", status: "CLOSED", initial_note: null, created_at: "2026-07-30T00:00:00Z", updated_at: "2026-07-31T00:00:00Z", closed_at: "2026-07-31T10:00:00Z" },
  initial_evidence: [
    { id: "e2", evidence_type: "CHART_3_MONTH", original_filename: "chart.png", uploaded_at: "2026-07-30T00:02:00Z", path: "/unsafe/secret" },
    { id: "e1", evidence_type: "ORDERBOOK", original_filename: "book.png", uploaded_at: "2026-07-30T00:01:00Z" },
    { id: "e3", evidence_type: "CHART_6_MONTH", original_filename: "chart6.png", uploaded_at: "2026-07-30T00:03:00Z" },
  ],
  initial_analysis: { request_id: "a1", status: "COMPLETED", created_at: "2026-07-30T00:04:00Z", completed_at: "2026-07-30T00:05:00Z", processed_response: { summary: "Ringkasan awal" } },
  decisions: [
    { decision_id: "w1", decision: "WAIT", created_at: "2026-07-30T00:06:00Z", note: "Tunggu" },
    { decision_id: "w2", decision: "WAIT", created_at: "2026-07-30T00:07:00Z", note: "Masih tunggu" },
    { decision_id: "b1", decision: "BUY", created_at: "2026-07-30T00:10:00Z" },
  ],
  wait_updates: [
    { request_id: "wu1", status: "COMPLETED", observation_timestamp: "2026-07-30T00:08:00Z", created_at: "2026-07-30T00:09:00Z", current_price: "100", processed_response: { update_summary: "Perubahan" }, evidence: { original_filename: "wait.png", path: "/unsafe" } },
    { request_id: "wu2", status: "FAILED", observation_timestamp: "2026-07-30T00:09:00Z", created_at: "2026-07-30T00:09:30Z", error_message: "internal secret" },
  ],
  position: { entry_price: "100", quantity: "10", stop_loss: "90", target_price: "120", entry_timestamp: "2026-07-30T00:10:00Z" },
  position_updates: [
    { request_id: "pu1", status: "COMPLETED", observation_timestamp: "2026-07-30T00:11:00Z", created_at: "2026-07-30T00:12:00Z", current_price: "105" },
    { request_id: "pu2", status: "COMPLETED", observation_timestamp: "2026-07-30T00:13:00Z", created_at: "2026-07-30T00:14:00Z", current_price: "110" },
  ],
  closure: { closure_id: "c1", close_price: "115", close_timestamp: "2026-07-31T10:00:00Z", close_reason: "Target tercapai", realized_result: "150" },
};

describe("P10.3 chronological timeline", () => {
  it("preserves every approved event in chronological order", () => {
    const events = buildTimelineEvents(aggregate);
    expect(events.map((event) => event.type)).toEqual([
      "INITIAL_EVIDENCE", "INITIAL_ANALYSIS", "WAIT_DECISION", "WAIT_DECISION", "WAIT_UPDATE", "WAIT_UPDATE", "BUY_DECISION", "POSITION_UPDATE", "POSITION_UPDATE", "CLOSE",
    ]);
    expect(events.filter((event) => event.type === "INITIAL_EVIDENCE")[0].details).toHaveLength(3);
    expect(events.filter((event) => event.type === "WAIT_DECISION")).toHaveLength(2);
    expect(events.filter((event) => event.type === "WAIT_UPDATE")).toHaveLength(2);
    expect(events.filter((event) => event.type === "POSITION_UPDATE")).toHaveLength(2);
    expect(events.find((event) => event.type === "BUY_DECISION")?.details.join(" ")).toContain("100");
    expect(events.flatMap((event) => event.details).join(" ")).not.toContain("/unsafe");
    expect(events.flatMap((event) => event.details).join(" ")).not.toContain("internal secret");
    expect(events.find((event) => event.type === "WAIT_UPDATE")?.timestamp).toBe("2026-07-30T00:08:00Z");
  });

  it("keeps equal timestamps and skip sessions deterministic without CLOSE", () => {
    const skip = { ...aggregate, session: { ...aggregate.session, status: "CLOSED_SKIPPED" as const }, decisions: [{ decision_id: "s2", decision: "SKIP" as const, created_at: "2026-07-30T00:06:00Z", reason: "USER_DECISION", note: "Tidak jadi" }], wait_updates: [], position: null, position_updates: [], closure: null };
    const events = buildTimelineEvents(skip);
    expect(events.map((event) => event.type)).not.toContain("CLOSE");
    expect(events.map((event) => event.type)).toContain("SKIP_DECISION");
    expect(buildTimelineEvents({ ...skip, initial_evidence: [], initial_analysis: null }).map((event) => event.id)).toEqual(buildTimelineEvents({ ...skip, initial_evidence: [], initial_analysis: null }).map((event) => event.id));
  });
});
