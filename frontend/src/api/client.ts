const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

let authToken = "";

export function setAuthToken(token: string): void {
  authToken = token;
}

export function hasAuthToken(): boolean {
  return authToken !== "";
}

async function fetchWithTimeout(url: string, init: RequestInit, timeoutMs: number): Promise<Response> {
  const controller = new AbortController();
  const abort = () => controller.abort();
  init.signal?.addEventListener("abort", abort, { once: true });
  const timer = window.setTimeout(abort, timeoutMs);
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } catch (error) {
    if (controller.signal.aborted && !init.signal?.aborted) {
      throw new Error("Request timed out. Please try again.");
    }
    throw error;
  } finally {
    window.clearTimeout(timer);
    init.signal?.removeEventListener("abort", abort);
  }
}

async function responseError(response: Response): Promise<Error> {
  const payload = await response.json().catch(() => null) as { detail?: unknown } | null;
  const detail = typeof payload?.detail === "string" ? payload.detail : null;
  return new Error(detail || `Request failed (${response.status})`);
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetchWithTimeout(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
      ...init?.headers,
    },
  }, 20_000);
  if (!response.ok) throw await responseError(response);
  return response.json() as Promise<T>;
}

export async function apiUpload<T>(path: string, body: FormData): Promise<T> {
  const response = await fetchWithTimeout(`${API_BASE}${path}`, {
    method: "POST",
    headers: authToken ? { Authorization: `Bearer ${authToken}` } : undefined,
    body,
  }, 60_000);
  if (!response.ok) throw await responseError(response);
  return response.json() as Promise<T>;
}
