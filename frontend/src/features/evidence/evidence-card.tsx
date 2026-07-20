import { useEffect, useRef, useState } from "react";
import type { EvidenceItem } from "@/types/evidence";
import { downloadEvidenceFile } from "@/lib/api/evidence";
import { evidenceTypeLabel, evidenceStatusLabel, formatTimestamp } from "./helpers";

interface Props {
  item: EvidenceItem;
}

export function EvidenceCard({ item }: Props) {
  const [imgUrl, setImgUrl] = useState<string | null>(null);
  const [loadError, setLoadError] = useState(false);
  const objUrlRef = useRef<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    downloadEvidenceFile(item.id)
      .then((blob) => {
        if (!cancelled) {
          objUrlRef.current = URL.createObjectURL(blob);
          setImgUrl(objUrlRef.current);
        }
      })
      .catch(() => {
        if (!cancelled) setLoadError(true);
      });

    return () => {
      cancelled = true;
      if (objUrlRef.current) {
        URL.revokeObjectURL(objUrlRef.current);
        objUrlRef.current = null;
      }
    };
  }, [item.id]);

  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-3">
      <div className="mb-2 flex items-start justify-between gap-2">
        <div>
          <p className="text-sm font-medium text-zinc-800">
            {evidenceTypeLabel(item.evidence_type)}
          </p>
          <p className="text-xs text-zinc-500">{item.original_filename}</p>
        </div>
        <span className="shrink-0 rounded bg-zinc-100 px-2 py-0.5 text-xs font-medium text-zinc-600">
          {evidenceStatusLabel(item.status)}
        </span>
      </div>

      {imgUrl && (
        <a href={imgUrl} target="_blank" rel="noopener noreferrer">
          <img
            src={imgUrl}
            alt={evidenceTypeLabel(item.evidence_type)}
            className="max-h-40 w-full rounded object-contain"
          />
        </a>
      )}
      {loadError && (
        <p className="text-xs text-red-500">Gagal memuat gambar.</p>
      )}

      <div className="mt-1 flex gap-3 text-xs text-zinc-400">
        {item.market_timestamp && (
          <span>Pasar: {formatTimestamp(item.market_timestamp)}</span>
        )}
        <span>Diunggah: {formatTimestamp(item.uploaded_at)}</span>
      </div>
    </div>
  );
}
