import { publicEnv } from "@/lib/env";
import type { RequestOptions } from "@/types/api";
import { parseErrorResponse } from "./errors";

async function request<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { method = "GET", body, query, formData, raw } = options;
  const url = new URL(path, publicEnv.apiBaseUrl);

  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined) {
        url.searchParams.set(key, String(value));
      }
    }
  }

  const headers: Record<string, string> = {};
  let reqBody: BodyInit | undefined;

  if (formData) {
    reqBody = formData;
    // Do not set Content-Type — browser sets multipart boundary
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    reqBody = JSON.stringify(body);
  }

  const response = await fetch(url.toString(), {
    method,
    headers,
    body: reqBody,
    credentials: "include",
  });

  if (!response.ok) {
    throw await parseErrorResponse(response);
  }

  if (raw) {
    return response as unknown as T;
  }

  // Handle empty responses (204)
  const text = await response.text();
  if (!text) {
    return undefined as T;
  }

  return JSON.parse(text) as T;
}

export function get<T>(path: string, query?: Record<string, string | number | undefined>): Promise<T> {
  return request<T>(path, { method: "GET", query });
}

export function post<T>(path: string, body?: unknown, options?: Partial<RequestOptions>): Promise<T> {
  return request<T>(path, { ...options, method: "POST", body });
}

export function patch<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, { method: "PATCH", body });
}

export function upload<T>(path: string, formData: FormData): Promise<T> {
  return request<T>(path, { method: "POST", formData });
}

export function download(path: string): Promise<Response> {
  return request<Response>(path, { method: "GET", raw: true });
}
