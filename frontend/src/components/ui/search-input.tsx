import type { ChangeEventHandler } from "react";

export interface SearchInputProps {
  value: string;
  onChange: ChangeEventHandler<HTMLInputElement>;
  placeholder?: string;
  className?: string;
}

/**
 * Reusable search input with a magnifying-glass icon prefix.
 * Used in SessionsListSurface and ArchivedSessionsListSurface.
 */
export function SearchInput({
  value,
  onChange,
  placeholder = "Cari kode saham...",
  className = "",
}: SearchInputProps) {
  return (
    <div className={`relative flex-1 ${className}`}>
      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
          />
        </svg>
      </div>
      <input
        type="text"
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        className="block w-full pl-9 pr-4 py-2 border border-slate-200 rounded-lg text-sm placeholder-slate-400 bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition"
      />
    </div>
  );
}
