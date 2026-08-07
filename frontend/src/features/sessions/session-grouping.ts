import type {
  SessionStatus,
  TradeSessionListItem,
} from "@/features/trade-workspace/types";

export type SessionGroupKey = "needs-attention" | "in-progress" | "completed";

export type SessionGroup = {
  key: SessionGroupKey;
  label: "Needs Attention" | "In Progress" | "Completed";
  sessions: TradeSessionListItem[];
};

export const SESSION_GROUP_DEFINITIONS = [
  { key: "needs-attention", label: "Needs Attention" },
  { key: "in-progress", label: "In Progress" },
  { key: "completed", label: "Completed" },
] as const satisfies ReadonlyArray<Pick<SessionGroup, "key" | "label">>;

export const SESSION_GROUP_BY_STATUS = {
  DRAFT: "needs-attention",
  ANALYZED: "needs-attention",
  ANALYZING: "in-progress",
  WAITING: "in-progress",
  OPEN_POSITION: "in-progress",
  CLOSED: "completed",
  CLOSED_SKIPPED: "completed",
} satisfies Record<SessionStatus, SessionGroupKey>;

export type SessionGroupingResult = {
  groups: SessionGroup[];
  invalidSessions: TradeSessionListItem[];
};

export function groupSessions(sessions: TradeSessionListItem[]): SessionGroupingResult {
  const grouped: Record<SessionGroupKey, TradeSessionListItem[]> = {
    "needs-attention": [],
    "in-progress": [],
    completed: [],
  };
  const invalidSessions: TradeSessionListItem[] = [];

  for (const session of sessions) {
    const groupKey = SESSION_GROUP_BY_STATUS[session.status as SessionStatus];
    if (groupKey === undefined) {
      invalidSessions.push(session);
      continue;
    }
    grouped[groupKey].push(session);
  }

  return {
    groups: SESSION_GROUP_DEFINITIONS.map((definition) => ({
      ...definition,
      sessions: grouped[definition.key],
    })),
    invalidSessions,
  };
}
