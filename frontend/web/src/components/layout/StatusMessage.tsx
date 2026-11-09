"use client";
import { AlertCircle, CheckCircle2, WifiOff } from "lucide-react";
import { useWorkspace } from "@/hooks/useWorkspace";
export function StatusMessage() {
  const { state } = useWorkspace();
  if (state.error)
    return (
      <div className="notice danger" role="alert">
        <AlertCircle size={18} aria-hidden="true" />
        <span>{state.error}</span>
      </div>
    );
  if (state.checked && !state.ready)
    return (
      <div className="notice warning" role="status">
        <WifiOff size={18} aria-hidden="true" />
        <span>
          The API is offline. Start the backend, then use the connection retry
          button above.
        </span>
      </div>
    );
  if (!state.status) return null;
  return (
    <div className="notice" role="status">
      <CheckCircle2 size={18} aria-hidden="true" />
      <span>{state.status}</span>
    </div>
  );
}
