"use client";
import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { ArrowRight, Eye, EyeOff } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "@/components/ui/Button";
export function AuthForm({ mode }: { mode: "sign-in" | "sign-up" }) {
  const signup = mode === "sign-up";
  const created = useSearchParams().get("created") === "1";
  const notice =
    !signup && created
      ? "Account created. Sign in to open your workspace."
      : undefined;
  const {
    user,
    signIn,
    signUp,
    error,
    sessionUnavailable,
    retrySession,
    isPending,
  } = useAuth();
  const router = useRouter();
  const [busy, setBusy] = useState(false),
    [visible, setVisible] = useState(false),
    [localError, setLocalError] = useState("");
  useEffect(() => {
    if (user) router.replace("/upload");
  }, [user, router]);
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    const form = event.currentTarget,
      data = new FormData(form);
    const email = String(data.get("email")).trim(),
      password = String(data.get("password")),
      name = String(data.get("name") ?? "").trim();
    setLocalError("");
    if (
      signup &&
      (!name ||
        password.length < 8 ||
        password.length > 128 ||
        !/[a-z]/i.test(password) ||
        !/\d/.test(password))
    ) {
      setLocalError(
        !name
          ? "Enter your name."
          : "Password must be 8 to 128 characters and include a letter and a number.",
      );
      return;
    }
    setBusy(true);
    try {
      if (signup) {
        const signedIn = await signUp(name, email, password);
        form.reset();
        router.replace(signedIn ? "/upload" : "/sign-in?created=1");
      } else {
        await signIn(email, password);
        form.reset();
        router.replace("/upload");
      }
    } catch {
      /* The provider exposes the API error. */
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="auth-form-wrap">
      <p className="eyebrow">A FRESH START FOR YOUR LEGACY CODE</p>
      <h1>{signup ? "Create your workspace." : "Welcome back."}</h1>
      <p className="page-description">
        {signup
          ? "Bring your COBOL forward. One project at a time."
          : "Your next chapter starts with the code you already have."}
      </p>
      {notice && (
        <p className="notice success" role="status">
          {notice}
        </p>
      )}
      {(localError || error) && (
        <p className="notice danger" role="alert">
          {localError || error}
        </p>
      )}
      {sessionUnavailable && (
        <Button onClick={retrySession} isPending={isPending}>
          Reconnect saved session
        </Button>
      )}
      <form onSubmit={submit} className="auth-form">
        {signup && (
          <div className="field">
            <label htmlFor="name">Full name</label>
            <input
              id="name"
              name="name"
              autoComplete="name"
              placeholder="Your name"
              required
              maxLength={100}
              disabled={busy}
            />
          </div>
        )}
        <div className="field">
          <label htmlFor="email">Email address</label>
          <input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            placeholder="you@example.com"
            required
            disabled={busy}
          />
        </div>
        <div className="field">
          <label htmlFor="password">Password</label>
          <div className="password-input">
            <input
              id="password"
              name="password"
              type={visible ? "text" : "password"}
              autoComplete={signup ? "new-password" : "current-password"}
              required
              minLength={signup ? 8 : undefined}
              maxLength={128}
              placeholder={
                signup ? "At least 8 characters" : "Enter your password"
              }
              disabled={busy}
            />
            <button
              type="button"
              aria-label={visible ? "Hide password" : "Show password"}
              aria-pressed={visible}
              onClick={() => setVisible((v) => !v)}
            >
              {visible ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>
          {signup && (
            <p className="hint">
              Use 8–128 characters, including a letter and a number.
            </p>
          )}
        </div>
        <Button type="submit" variant="primary" isPending={busy}>
          {busy
            ? signup
              ? "Creating account…"
              : "Signing in…"
            : signup
              ? "Create account"
              : "Sign in"}
          {!busy && <ArrowRight size={18} aria-hidden="true" />}
        </Button>
      </form>
      <p className="auth-switch">
        {signup ? "Already have an account?" : "New to LegacyLift?"}{" "}
        <Link href={signup ? "/sign-in" : "/sign-up"}>
          {signup ? "Sign in" : "Create an account"}{" "}
          <ArrowRight size={14} aria-hidden="true" />
        </Link>
      </p>
      <div className="auth-footnote">
        Built for careful transitions. Your source stays yours.
      </div>
    </div>
  );
}
