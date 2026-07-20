"use client";

import { useState } from "react";
import { uploadEvidence, replaceEvidence } from "@/lib/api/evidence";
import { ApiError, AuthenticationError } from "@/lib/api/errors";
import type { EvidenceItem } from "@/types/evidence";
import { ImagePreview } from "./image-preview";
import { EVIDENCE_TYPE_LABELS, SUPPORTED_MIME_TYPES } from "./helpers";

interface Props {
  sessionId: string;
  evidenceList: EvidenceItem[];
  onUploaded: () => void;
}

export function EvidenceUploadForm({ sessionId, evidenceList, onUploaded }: Props) {
  const [selectedType, setSelectedType] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [marketTs, setMarketTs] = useState("");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  const orderbookActive = evidenceList.find(
    (e) => e.evidence_type === "ORDERBOOK_SCREENSHOT" && e.status === "AVAILABLE",
  );

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedType) { setError("Pilih tipe bukti terlebih dahulu."); return; }
    if (!file) { setError("Pilih file gambar terlebih dahulu."); return; }

    setUploading(true);
    setError("");

    try {
      let result: EvidenceItem;
      const ts = marketTs || undefined;

      if (selectedType === "ORDERBOOK_SCREENSHOT" && orderbookActive) {
        result = await replaceEvidence(orderbookActive.id, file, selectedType, ts);
      } else {
        result = await uploadEvidence(sessionId, file, selectedType, ts);
      }

      if (result) {
        setFile(null);
        setMarketTs("");
        onUploaded();
      }
    } catch (err: unknown) {
      if (err instanceof AuthenticationError) {
        setError("Silakan masuk terlebih dahulu.");
      } else if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Terjadi kesalahan. Silakan coba lagi.");
      }
    } finally {
      setUploading(false);
    }
  }

  const isOrderbookOnly = selectedType === "ORDERBOOK_SCREENSHOT";

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div>
        <label htmlFor="ev-type" className="mb-1 block text-sm font-medium text-zinc-700">
          Tipe Bukti
        </label>
        <select
          id="ev-type"
          value={selectedType}
          onChange={(e) => setSelectedType(e.target.value)}
          disabled={uploading}
          className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
        >
          <option value="">Pilih tipe…</option>
          {Object.entries(EVIDENCE_TYPE_LABELS).map(([val, label]) => (
            <option key={val} value={val}>{label}</option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="ev-file" className="mb-1 block text-sm font-medium text-zinc-700">
          File Gambar
        </label>
        <input
          id="ev-file"
          type="file"
          accept={SUPPORTED_MIME_TYPES}
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          disabled={uploading}
          className="block w-full text-sm text-zinc-600 file:mr-3 file:rounded file:border-0 file:bg-blue-50 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-blue-700 hover:file:bg-blue-100"
        />
        {file && (
          <p className="mt-1 text-xs text-zinc-500">{file.name}</p>
        )}
        <ImagePreview file={file} />
      </div>

      {isOrderbookOnly && orderbookActive && (
        <p className="text-xs text-amber-600">
          Orderbook aktif akan digantikan dengan yang baru.
        </p>
      )}

      <div>
        <label htmlFor="ev-ts" className="mb-1 block text-sm font-medium text-zinc-700">
          Waktu Pasar <span className="text-xs text-zinc-400">(opsional)</span>
        </label>
        <input
          id="ev-ts"
          type="datetime-local"
          value={marketTs}
          onChange={(e) => setMarketTs(e.target.value)}
          disabled={uploading}
          className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
        />
      </div>

      {error && (
        <div role="alert" className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      <button
        type="submit"
        disabled={uploading}
        className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {uploading ? "Mengunggah…" : "Unggah"}
      </button>
    </form>
  );
}
