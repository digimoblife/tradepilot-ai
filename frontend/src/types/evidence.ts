/** Evidence metadata */
export interface EvidenceItem {
  id: string;
  session_id: string;
  evidence_type: string;
  status: string;
  original_filename: string | null;
  mime_type: string | null;
  file_size_bytes: number | null;
  checksum_sha256: string | null;
  market_timestamp: string | null;
  uploaded_at: string;
  caption: string | null;
  supersedes_evidence_id: string | null;
}

/** GET /api/trade-sessions/{id}/evidence */
export interface ListEvidenceResponse {
  evidence: EvidenceItem[];
  total: number;
}
