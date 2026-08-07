import { describe, expect, it } from "vitest";

import type {
  SessionStatus,
  TradeSessionListItem,
} from "@/features/trade-workspace/types";
import {
  SESSION_GROUP_BY_STATUS,
  SESSION_GROUP_DEFINITIONS,
  groupSessions,
} from "./session-grouping";

function session(id: string, status: SessionStatus): TradeSessionListItem {
  return {
    id,
    ticker: id,
    company_name: `${id} Company`,
    status,
    note: null,
    created_at: "2026-08-04T00:00:00Z",
    updated_at: "2026-08-04T00:00:00Z",
    closed_at: status === "CLOSED" || status === "CLOSED_SKIPPED"
      ? "2026-08-04T01:00:00Z"
      : null,
    archived_at: null,
  };
}

describe("groupSessions", () => {
  it("maps every canonical status exactly once into the three approved groups", () => {
    expect(SESSION_GROUP_BY_STATUS).toEqual({
      DRAFT: "needs-attention",
      ANALYZED: "needs-attention",
      ANALYZING: "in-progress",
      WAITING: "in-progress",
      OPEN_POSITION: "in-progress",
      CLOSED: "completed",
      CLOSED_SKIPPED: "completed",
    });
    expect(SESSION_GROUP_DEFINITIONS).toEqual([
      { key: "needs-attention", label: "Needs Attention" },
      { key: "in-progress", label: "In Progress" },
      { key: "completed", label: "Completed" },
    ]);
    expect(new Set(Object.values(SESSION_GROUP_BY_STATUS))).toEqual(
      new Set(["needs-attention", "in-progress", "completed"]),
    );
  });

  it("preserves relative backend order inside each approved group", () => {
    const input = [
      session("CLOSED-A", "CLOSED"),
      session("DRAFT-B", "DRAFT"),
      session("WAITING-C", "WAITING"),
      session("ANALYZED-D", "ANALYZED"),
      session("CLOSED-SKIPPED-E", "CLOSED_SKIPPED"),
      session("OPEN-POSITION-F", "OPEN_POSITION"),
      session("ANALYZING-G", "ANALYZING"),
      session("DRAFT-H", "DRAFT"),
    ];
    const result = groupSessions(input);

    expect(result.groups.map((group) => group.key)).toEqual([
      "needs-attention",
      "in-progress",
      "completed",
    ]);
    expect(result.groups.map((group) => group.sessions.map((item) => item.id))).toEqual([
      ["DRAFT-B", "ANALYZED-D", "DRAFT-H"],
      ["WAITING-C", "OPEN-POSITION-F", "ANALYZING-G"],
      ["CLOSED-A", "CLOSED-SKIPPED-E"],
    ]);
  });

  it("does not mutate the source array or records and preserves item references", () => {
    const draft = session("DRAFT-B", "DRAFT");
    const closed = session("CLOSED-A", "CLOSED");
    const input = [closed, draft];
    const inputSnapshot = structuredClone(input);
    const result = groupSessions(input);

    expect(input).toEqual(inputSnapshot);
    expect(Object.keys(draft)).not.toContain("group");
    expect(result.groups[0].sessions[0]).toBe(draft);
    expect(result.groups[2].sessions[0]).toBe(closed);
  });

  it("excludes an unexpected runtime status without creating a fourth group or crashing valid sessions", () => {
    const valid = session("DRAFT-B", "DRAFT");
    const invalid = session("BROKEN-X", "DRAFT");
    invalid.status = "UNEXPECTED_RUNTIME_STATUS" as SessionStatus;

    const result = groupSessions([invalid, valid]);

    expect(result.groups).toHaveLength(3);
    expect(result.groups.flatMap((group) => group.sessions)).toEqual([valid]);
    expect(result.invalidSessions).toEqual([invalid]);
  });
});
