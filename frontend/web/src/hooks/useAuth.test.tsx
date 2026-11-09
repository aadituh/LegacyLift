import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
const router = vi.hoisted(() => ({ replace: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => router }));
vi.mock("@/lib/api/auth", () => ({
  authClient: null,
  clearToken: vi.fn(),
  getMe: vi.fn(),
  login: vi.fn(),
  logout: vi.fn(),
  register: vi.fn(),
  setNeonSignedIn: vi.fn(),
  syncStoredToken: vi.fn(),
}));
import { AuthProvider, useAuth } from "./useAuth";
import * as auth from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";
const user = {
  id: "user-1",
  email: "a@example.com",
  display_name: "Reviewer",
  created_at: "2026-11-08T12:00:00Z",
};
const wrapper = ({ children }: { children: React.ReactNode }) => (
  <AuthProvider>{children}</AuthProvider>
);
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(auth.getMe).mockResolvedValue(user);
});
it("restores an API account from its saved token", async () => {
  localStorage.setItem("legacylift-token", "saved-token");
  const { result } = renderHook(() => useAuth(), { wrapper });
  await waitFor(() => expect(result.current.isPending).toBe(false));
  expect(result.current.user?.id).toBe("user-1");
});
it("signs in, signs up without claiming a session, and signs out", async () => {
  const { result } = renderHook(() => useAuth(), { wrapper });
  await waitFor(() => expect(result.current.isPending).toBe(false));
  await act(() => result.current.signIn("a@example.com", "Password123"));
  expect(auth.login).toHaveBeenCalledWith("a@example.com", "Password123");
  await act(async () => {
    expect(
      await result.current.signUp("Reviewer", "a@example.com", "Password123"),
    ).toBe(false);
  });
  expect(auth.register).toHaveBeenCalledWith(
    "a@example.com",
    "Password123",
    "Reviewer",
  );
  await act(() => result.current.signOut());
  expect(result.current.user).toBeNull();
  expect(router.replace).toHaveBeenCalledWith("/sign-in");
});
it("keeps a valid token during outages and restores it on retry", async () => {
  localStorage.setItem("legacylift-token", "saved-token");
  vi.mocked(auth.getMe).mockRejectedValueOnce(
    new ApiError("Cannot reach the backend.", 0),
  );
  const { result } = renderHook(() => useAuth(), { wrapper });
  await waitFor(() => expect(result.current.isPending).toBe(false));
  expect(auth.clearToken).not.toHaveBeenCalled();
  expect(localStorage.getItem("legacylift-token")).toBe("saved-token");
  expect(result.current.sessionUnavailable).toBe(true);
  await act(async () => result.current.retrySession());
  await waitFor(() => expect(result.current.user?.id).toBe("user-1"));
  expect(result.current.sessionUnavailable).toBe(false);
});
it("does not restore a late account response after sign-out", async () => {
  localStorage.setItem("legacylift-token", "saved-token");
  let resolve!: (value: typeof user) => void;
  vi.mocked(auth.getMe).mockReturnValueOnce(
    new Promise((r) => {
      resolve = r;
    }),
  );
  const { result } = renderHook(() => useAuth(), { wrapper });
  await waitFor(() => expect(auth.getMe).toHaveBeenCalledTimes(1));
  await act(() => result.current.signOut());
  await act(async () => {
    resolve(user);
  });
  expect(result.current.user).toBeNull();
});
it("synchronizes account changes from another browser tab", async () => {
  const { result } = renderHook(() => useAuth(), { wrapper });
  await waitFor(() => expect(result.current.isPending).toBe(false));
  localStorage.setItem("legacylift-token", "other-tab-token");
  const storageEvent = new Event("storage");
  Object.defineProperty(storageEvent, "key", {
    value: "legacylift-token",
  });
  Object.defineProperty(storageEvent, "newValue", {
    value: "other-tab-token",
  });
  await act(async () => window.dispatchEvent(storageEvent));
  await waitFor(() => expect(result.current.user?.id).toBe("user-1"));
  expect(auth.syncStoredToken).toHaveBeenCalledWith("other-tab-token");
});
