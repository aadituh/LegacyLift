import { createAuthClient } from "@neon/auth";
import { BetterAuthReactAdapter } from "@neon/auth/react/adapters";
import { readStored, writeStored } from "@/lib/storage";
import type { LoginResponse, UserResponse } from "@/types/api";
import { request } from "./client";
const authUrl = process.env.NEXT_PUBLIC_NEON_AUTH_URL?.trim();
export const authClient = authUrl
  ? createAuthClient(authUrl, {
      adapter: BetterAuthReactAdapter({
        fetchOptions: { credentials: "include" },
      }),
    })
  : null;
let memoryToken = "";
let neonSignedIn = false;
let authRevision = 0;
export const getAuthRevision = () => authRevision;
export function syncStoredToken(value: string) {
  memoryToken = value;
  authRevision++;
}
export function setNeonSignedIn(value: boolean) {
  if (neonSignedIn !== value) authRevision++;
  neonSignedIn = value;
}
export function clearToken() {
  authRevision++;
  memoryToken = "";
  writeStored("legacylift-token", "");
}
export function setToken(token: string) {
  authRevision++;
  memoryToken = token;
  writeStored("legacylift-token", token);
}
const isJwt = (value: unknown): value is string =>
  typeof value === "string" && value.split(".").length === 3;
export async function getAccessToken(): Promise<string> {
  const saved = memoryToken || readStored("legacylift-token");
  if (saved) return saved;
  if (!authClient || !neonSignedIn) return "";
  let headerToken = "";
  const session = await authClient.getSession({
    fetchOptions: {
      headers: { "X-Force-Fetch": "1" },
      onSuccess(ctx) {
        const value = ctx.response.headers.get("set-auth-jwt");
        if (isJwt(value)) headerToken = value;
      },
    },
  });
  if (headerToken) return headerToken;
  if (isJwt(session.data?.session?.token)) return session.data.session.token;
  const response = await fetch(`${authUrl}/token`, { credentials: "include" });
  const body = await response.json().catch(() => null);
  if (response.ok && isJwt(body?.token)) return body.token;
  throw new Error("Sign in again so this project is saved to your account.");
}
export async function login(email: string, password: string) {
  const result = await request<LoginResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  setToken(result.token);
  return result;
}
export const register = (
  email: string,
  password: string,
  display_name: string,
) =>
  request<UserResponse>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password, display_name }),
  });
export const getMe = () => request<UserResponse>("/api/auth/me");
export async function logout() {
  clearToken();
  setNeonSignedIn(false);
  if (authClient) {
    writeStored("legacylift-neon-signed-out", "1");
    const result = await authClient.signOut();
    if (result.error)
      throw new Error(
        result.error.message || "Could not reach the identity service.",
      );
  }
}
