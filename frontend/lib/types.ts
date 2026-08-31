// TypeScript mirrors of the backend's Pydantic schemas (backend/app/schemas.py).
// Hand-maintained: when a schema changes on the backend, change it here too and
// TypeScript will point at every place that needs updating.

/** Mirrors `UserOut`. Never contains the password hash. */
export interface User {
  id: string; // UUID, serialized as a string over JSON
  email: string;
  display_name: string | null;
  created_at: string; // ISO 8601 timestamp
}

/** Mirrors `SignupIn`. */
export interface SignupPayload {
  email: string;
  password: string;
}

/** Mirrors `LoginIn`. */
export interface LoginPayload {
  email: string;
  password: string;
}

/** Shape of FastAPI's error responses: `{"detail": "..."}`. */
export interface ApiErrorBody {
  detail?: string | { msg: string }[];
}
