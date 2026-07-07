const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

let authToken = "";

export function setAuthToken(token: string): void {
  authToken = token;
}

export function hasAuthToken(): boolean {
  return authToken !== "";
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.detail || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}
