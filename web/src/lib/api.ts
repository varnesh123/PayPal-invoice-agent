// Backend API client for the frontend.
//
// Phase 1: provides a typed helper to call the FastAPI backend from the
// Next.js frontend, starting with the /health check used to verify
// frontend-to-backend communication.

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export interface HealthResponse {
  status: string;
  service: string;
  environment: string;
  database_configured: boolean;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BACKEND_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    ...init,
  });
  if (!res.ok) {
    throw new Error(`Backend request failed: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}

/** Fetch backend health status. */
export async function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}
