"use client";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { useRouter } from "next/navigation";
import {
  authClient,
  clearToken,
  getMe,
  login,
  logout,
  register,
  setNeonSignedIn,
  syncStoredToken,
} from "@/lib/api/auth";
import { readStored, writeStored } from "@/lib/storage";
import { ApiError, setUnauthorizedHandler } from "@/lib/api/client";
import type { UserResponse } from "@/types/api";
interface AuthContextValue {
  user: UserResponse | null;
  isPending: boolean;
  error: string;
  sessionUnavailable: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (name: string, email: string, password: string) => Promise<boolean>;
  signOut: () => Promise<void>;
  retrySession: () => void;
}
const AuthContext = createContext<AuthContextValue | null>(null);
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [isPending, setPending] = useState(true);
  const [error, setError] = useState("");
  const [sessionUnavailable, setSessionUnavailable] = useState(false);
  const attempt = useRef(0);
  const invalidateAttempt = useCallback(() => {
    attempt.current++;
  }, []);
  const router = useRouter();
  const restoreSession = useCallback(async () => {
    const version = ++attempt.current;
    try {
      const saved = readStored("legacylift-token");
      if (version !== attempt.current) return;
      if (authClient && !saved) {
        if (readStored("legacylift-neon-signed-out")) return;
        const session = await authClient.getSession();
        if (version !== attempt.current) return;
        if (session.error)
          throw new Error(
            session.error.message || "Could not restore your session.",
          );
        if (session.data?.user) setNeonSignedIn(true);
        else return;
      } else if (!saved) return;
      const current = await getMe();
      if (version === attempt.current) {
        setUser(current);
        setError("");
        setSessionUnavailable(false);
      }
    } catch (e) {
      if (version !== attempt.current) return;
      if (e instanceof ApiError && e.status === 401) {
        clearToken();
        setNeonSignedIn(false);
      }
      // A network outage must not discard an otherwise valid saved account.
      setSessionUnavailable(!(e instanceof ApiError && e.status === 401));
      setError((e as Error).message);
    } finally {
      if (version === attempt.current) setPending(false);
    }
  }, []);
  const signOut = useCallback(async () => {
    attempt.current++;
    setUser(null);
    setError("");
    setSessionUnavailable(false);
    setPending(false);
    try {
      await logout();
    } catch {
      setError(
        "Signed out locally. The identity service could not be reached.",
      );
    } finally {
      router.replace("/sign-in");
    }
  }, [router]);
  useEffect(() => {
    let active = true;
    const queuedAttempt = attempt.current;
    setUnauthorizedHandler((message) => {
      attempt.current++;
      setUser(null);
      setPending(false);
      setError(message);
      setSessionUnavailable(false);
      setNeonSignedIn(false);
      router.replace("/sign-in");
    });
    queueMicrotask(() => {
      if (active && attempt.current === queuedAttempt) void restoreSession();
    });
    function syncSession(event: StorageEvent) {
      if (event.key !== "legacylift-token" && event.key !== null) return;
      syncStoredToken(event.newValue ?? "");
      setUser(null);
      setPending(true);
      setError("");
      setSessionUnavailable(false);
      void restoreSession();
    }
    window.addEventListener("storage", syncSession);
    return () => {
      active = false;
      invalidateAttempt();
      setUnauthorizedHandler();
      window.removeEventListener("storage", syncSession);
    };
  }, [router, restoreSession, invalidateAttempt]);
  async function signIn(email: string, password: string) {
    const version = ++attempt.current;
    setError("");
    setSessionUnavailable(false);
    try {
      if (authClient) {
        const result = await authClient.signIn
          .email({ email, password })
          .catch(() => null);
        if (version !== attempt.current) return;
        if (result && !result.error) {
          clearToken();
          setNeonSignedIn(true);
          writeStored("legacylift-neon-signed-out", "");
          const current = await getMe();
          if (version === attempt.current) setUser(current);
          return;
        }
        await authClient.signOut().catch(() => undefined);
        setNeonSignedIn(false);
      }
      await login(email, password);
      const current = await getMe();
      if (version === attempt.current) setUser(current);
    } catch (e) {
      setError((e as Error).message);
      throw e;
    }
  }
  async function signUp(name: string, email: string, password: string) {
    const version = ++attempt.current;
    setError("");
    setSessionUnavailable(false);
    try {
      if (authClient) {
        const result = await authClient.signUp.email({ name, email, password });
        if (result.error)
          throw new Error(
            result.error.message || "Could not create the account.",
          );
        if (version !== attempt.current) return false;
        const session = await authClient.getSession();
        if (session.data?.session) {
          clearToken();
          setNeonSignedIn(true);
          writeStored("legacylift-neon-signed-out", "");
          const current = await getMe();
          if (version === attempt.current) setUser(current);
          return true;
        }
      } else {
        await register(email, password, name);
      }
      return false;
    } catch (e) {
      setError((e as Error).message);
      throw e;
    }
  }
  return (
    <AuthContext.Provider
      value={{
        user,
        isPending,
        error,
        sessionUnavailable,
        signIn,
        signUp,
        signOut,
        retrySession: () => {
          setPending(true);
          void restoreSession();
        },
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth needs AuthProvider");
  return value;
}
