import { getAccessToken, clearToken, getAuthRevision } from "./auth";
import { saveBlob } from "@/lib/download";
const base = (process.env.NEXT_PUBLIC_API_URL ?? "").trim().replace(/\/+$/, "");
export const apiConfigured = true; // Next.js proxies the API when no public origin is set.
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}
let unauthorized: ((message: string) => void) | undefined;
export function setUnauthorizedHandler(handler?: (message: string) => void) {
  unauthorized = handler;
}
export async function responseError(
  response: Response,
  revision = getAuthRevision(),
) {
  const body = await response.json().catch(() => null);
  const detail: unknown = body?.detail;
  const validation = Array.isArray(detail)
    ? detail
        .flatMap((d) => (d && typeof d.msg === "string" ? [d.msg] : []))
        .join(" ")
    : "";
  const message =
    response.status === 413
      ? "That upload is too large. The API accepts up to 24 MB per request."
      : typeof detail === "string"
        ? detail
        : validation
          ? validation
          : response.status === 401
            ? "Please log in again."
            : `Request failed (${response.status}).`;
  if (response.status === 401 && revision === getAuthRevision()) {
    clearToken();
    unauthorized?.(message);
  }
  return new ApiError(message, response.status);
}
async function fetchResponse(path: string, options: RequestInit = {}) {
  const revision = getAuthRevision();
  const headers = new Headers(options.headers);
  const token = await getAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options.body && !(options.body instanceof FormData))
    headers.set("Content-Type", "application/json");
  let response: Response;
  try {
    response = await fetch(`${base}${path}`, {
      ...options,
      headers,
      cache: "no-store",
      signal: options.signal
        ? AbortSignal.any([options.signal, AbortSignal.timeout(120_000)])
        : AbortSignal.timeout(120_000),
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "TimeoutError")
      throw new ApiError(
        "The request timed out. Check the API connection and try again.",
        0,
      );
    if (error instanceof DOMException && error.name === "AbortError")
      throw error;
    throw new ApiError(
      "Cannot reach the LegacyLift backend. Check the API connection and try again.",
      0,
    );
  }
  if (!response.ok) throw await responseError(response, revision);
  return response;
}
export async function request<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetchResponse(path, options);
  return response.status === 204 ? (null as T) : response.json();
}
export async function checkBackend() {
  try {
    const response = await fetch(`${base}/health`, {
      cache: "no-store",
      signal: AbortSignal.timeout(8000),
    });
    return response.ok && (await response.json()).status === "ok";
  } catch {
    return false;
  }
}
export async function downloadFile(path: string, name: string) {
  saveBlob(await (await fetchResponse(path)).blob(), name);
}
