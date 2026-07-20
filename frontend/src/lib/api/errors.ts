import type { ApiErrorResponse } from "@/types/api";

export class ApiError extends Error {
  status: number;
  code: string;
  details: Record<string, unknown>[] | null;
  requestId: string | null;

  constructor(
    status: number,
    code: string,
    message: string,
    details: Record<string, unknown>[] | null = null,
    requestId: string | null = null,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
    this.requestId = requestId;
  }
}

export class AuthenticationError extends ApiError {
  constructor(
    status: number,
    code: string,
    message: string,
    details: Record<string, unknown>[] | null = null,
    requestId: string | null = null,
  ) {
    super(status, code, message, details, requestId);
    this.name = "AuthenticationError";
  }
}

const AUTH_CODES = new Set([
  "AUTHENTICATION_REQUIRED",
  "AUTHENTICATION_INVALID",
  "AUTHENTICATION_EXPIRED",
]);

export async function parseErrorResponse(
  response: Response,
): Promise<ApiError> {
  const status = response.status;
  let code = "INTERNAL_ERROR";
  let message = "Terjadi kesalahan internal. Silakan coba lagi nanti.";
  let details: Record<string, unknown>[] | null = null;
  let requestId: string | null = null;

  try {
    const body = (await response.json()) as ApiErrorResponse;
    if (body.error) {
      code = body.error.code ?? code;
      message = body.error.message ?? message;
      details = body.error.details ?? null;
      requestId = body.error.request_id ?? null;
    }
  } catch {
    // Non-JSON response — use fallback message
  }

  if (AUTH_CODES.has(code)) {
    return new AuthenticationError(status, code, message, details, requestId);
  }

  return new ApiError(status, code, message, details, requestId);
}
