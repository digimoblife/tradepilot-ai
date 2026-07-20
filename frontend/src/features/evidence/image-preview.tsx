interface Props {
  file: File | null;
  alt?: string;
}

export function ImagePreview({ file, alt = "Pratinjau gambar" }: Props) {
  if (!file) return null;

  return (
    <div className="mt-2 overflow-hidden rounded-lg border border-zinc-200">
      <img
        src={URL.createObjectURL(file)}
        alt={alt}
        className="max-h-64 w-full object-contain"
      />
    </div>
  );
}
