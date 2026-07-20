import { get } from "./client";
import type { ListTimelineResponse } from "@/types/timeline";

export function getTimeline(
  sessionId: string,
  query?: {
    event_type?: string;
    from_timestamp?: string;
    to_timestamp?: string;
    limit?: number;
    offset?: number;
  },
): Promise<ListTimelineResponse> {
  return get<ListTimelineResponse>(`/api/trade-sessions/${sessionId}/timeline`, query);
}
