import { get, post, upload, download } from "./client";
import type { EvidenceItem, ListEvidenceResponse } from "@/types/evidence";

export function uploadEvidence(
  sessionId: string,
  file: File,
  evidenceType: string,
  marketTimestamp?: string,
): Promise<EvidenceItem> {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("evidence_type", evidenceType);
  if (marketTimestamp) {
    fd.append("market_timestamp", marketTimestamp);
  }
  return upload<EvidenceItem>(`/api/trade-sessions/${sessionId}/evidence`, fd);
}

export function listEvidence(
  sessionId: string,
  query?: Record<string, string | number | undefined>,
): Promise<ListEvidenceResponse> {
  return get<ListEvidenceResponse>(`/api/trade-sessions/${sessionId}/evidence`, query);
}

export function getEvidence(evidenceId: string): Promise<EvidenceItem> {
  return get<EvidenceItem>(`/api/evidence/${evidenceId}`);
}

export function downloadEvidenceFile(evidenceId: string): Promise<Blob> {
  return download(`/api/evidence/${evidenceId}/file`).then((res) => res.blob());
}

export function replaceEvidence(
  evidenceId: string,
  file: File,
  evidenceType: string,
  marketTimestamp?: string,
): Promise<EvidenceItem> {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("evidence_type", evidenceType);
  if (marketTimestamp) {
    fd.append("market_timestamp", marketTimestamp);
  }
  return upload<EvidenceItem>(`/api/evidence/${evidenceId}/replace`, fd);
}

export function deactivateEvidence(evidenceId: string): Promise<EvidenceItem> {
  return post<EvidenceItem>(`/api/evidence/${evidenceId}/deactivate`);
}
