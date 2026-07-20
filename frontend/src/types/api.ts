/** TP-1007 unified error contract */
export interface ApiErrorDetail {
  code: string;
  message: string;
  details: Record<string, unknown>[] | null;
  request_id: string | null;
}

export interface ApiErrorResponse {
  error: ApiErrorDetail;
}

export type HttpMethod = "GET" | "POST" | "PATCH" | "DELETE";

export interface RequestOptions {
  method?: HttpMethod;
  body?: unknown;
  query?: Record<string, string | number | undefined>;
  formData?: FormData;
  /** When true, returns raw Response instead of parsing JSON */
  raw?: boolean;
}
