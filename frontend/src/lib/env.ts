export function resolveApiBaseUrl(): string {
  const raw = process.env.NEXT_PUBLIC_API_BASE_URL;
  const val = raw?.trim() ?? "";

  if (val) {
    return val;
  }

  if (process.env.NODE_ENV === "production") {
    throw new Error(
      "NEXT_PUBLIC_API_BASE_URL is required in production.",
    );
  }

  return "http://localhost:8000";
}

export const publicEnv = {
  apiBaseUrl: resolveApiBaseUrl(),
} as const;
