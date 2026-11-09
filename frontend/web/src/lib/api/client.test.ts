import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
vi.mock("./auth", () => ({
  getAccessToken: vi.fn(async () => "test-token"),
  clearToken: vi.fn(),
  getAuthRevision: vi.fn(() => 0),
}));
import { request, setUnauthorizedHandler } from "./client";
import { clearToken, getAuthRevision } from "./auth";
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(getAuthRevision).mockReturnValue(0);
  vi.stubGlobal("fetch", vi.fn());
});
afterEach(() => {
  setUnauthorizedHandler();
  vi.unstubAllGlobals();
});
describe("API client", () => {
  it("attaches bearer authentication and JSON headers", async () => {
    vi.mocked(fetch).mockResolvedValue(new Response('{"ok":true}'));
    await request("/api/projects", { method: "POST", body: "{}" });
    expect(vi.mocked(fetch).mock.calls[0][1]?.headers).toBeInstanceOf(Headers);
    const headers = vi.mocked(fetch).mock.calls[0][1]?.headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer test-token");
  });
  it("retains backend detail on login 401 and clears stale sessions", async () => {
    const handler = vi.fn();
    setUnauthorizedHandler(handler);
    vi.mocked(fetch).mockResolvedValue(
      new Response('{"detail":"Invalid email or password."}', { status: 401 }),
    );
    await expect(request("/api/auth/login")).rejects.toThrow(
      "Invalid email or password.",
    );
    expect(clearToken).toHaveBeenCalled();
    expect(handler).toHaveBeenCalledWith("Invalid email or password.");
  });
  it("explains upload size and connection failures", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(new Response("", { status: 413 }))
      .mockRejectedValueOnce(new TypeError("fetch failed"));
    await expect(request("/api/projects")).rejects.toThrow("24 MB");
    await expect(request("/api/projects")).rejects.toThrow("Cannot reach");
  });
  it("accepts no-content deletes and preserves multipart boundaries", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(new Response("{}"));
    expect(await request("/api/projects/1", { method: "DELETE" })).toBeNull();
    await request("/api/projects/1/files", {
      method: "POST",
      body: new FormData(),
    });
    expect(
      (vi.mocked(fetch).mock.calls[1][1]?.headers as Headers).has(
        "Content-Type",
      ),
    ).toBe(false);
  });
  it("ignores a late unauthorized response from an older account", async () => {
    let resolve!: (response: Response) => void;
    vi.mocked(fetch).mockReturnValueOnce(
      new Promise((r) => {
        resolve = r;
      }),
    );
    const promise = request("/api/projects");
    await vi.waitFor(() => expect(fetch).toHaveBeenCalled());
    vi.mocked(getAuthRevision).mockReturnValue(1);
    resolve(new Response('{"detail":"Expired old session."}', { status: 401 }));
    await expect(promise).rejects.toThrow("Expired old session.");
    expect(clearToken).not.toHaveBeenCalled();
  });
  it("provides a plain timeout error and tolerates malformed validation details", async () => {
    vi.mocked(fetch).mockRejectedValueOnce(
      new DOMException("Timeout", "TimeoutError"),
    );
    await expect(request("/api/projects")).rejects.toThrow("timed out");
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response('{"detail":[null,{}, {"msg":"Enter a name."}]}', {
        status: 422,
      }),
    );
    await expect(request("/api/projects")).rejects.toThrow("Enter a name.");
  });
});
