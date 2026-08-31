// The single place the frontend talks to the backend.
// No component calls `fetch` directly — routing every request through here
// means the base URL, the cookie behaviour, and error handling are defined once.

import type { ApiErrorBody } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** An error carrying the HTTP status, so callers can branch on 401 vs 409. */
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** Turn FastAPI's `detail` field into a single readable string. */
function messageFrom(body: ApiErrorBody | null, status: number): string {
  const detail = body?.detail;

  if (typeof detail === "string") return detail;

  // Pydantic validation errors (422) arrive as a list of objects.
  if (Array.isArray(detail) && detail.length > 0) return detail[0].msg;

  return `Request failed with status ${status}`;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init.headers },

    // Without this the browser silently drops the session cookie on every
    // cross-origin request and each call comes back 401. It pairs with
    // `allow_credentials=True` in the backend's CORS middleware.
    credentials: "include",
  });

  if (!response.ok) {
    // An error body is not guaranteed (a 500 may return HTML), so parsing is
    // allowed to fail without masking the real status.
    const body = await response.json().catch(() => null);
    throw new ApiError(response.status, messageFrom(body, response.status));
  }

  // 204 No Content (logout) has an empty body — parsing it would throw.
  if (response.status === 204) return undefined as T;

  return response.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path, { method: "GET" }),

  post: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "POST",
      body: body === undefined ? undefined : JSON.stringify(body),
    }),
};
