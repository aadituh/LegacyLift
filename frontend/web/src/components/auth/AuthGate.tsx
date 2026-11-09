"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { Skeleton } from "@/components/ui/Spinner";
export function AuthGate({ children }: { children: React.ReactNode }) {
  const { user, isPending } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (!isPending && !user) router.replace("/sign-in");
  }, [isPending, user, router]);
  if (isPending || !user)
    return (
      <div className="session-loading">
        <Skeleton label="Checking session…" />
      </div>
    );
  return children;
}
