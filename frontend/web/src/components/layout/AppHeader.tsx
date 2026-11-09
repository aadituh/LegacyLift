"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronRight, LogOut, RefreshCw } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { useWorkspace } from "@/hooks/useWorkspace";
import { useBackendStatus } from "@/hooks/useBackendStatus";
import { Button } from "@/components/ui/Button";
import { Logo } from "@/components/brand/Logo";
import { AppNav } from "./AppNav";
import { ThemeMenu } from "@/components/ui/ThemeMenu";
export function AppHeader() {
  const { state } = useWorkspace();
  const edited =
    state.results.some(
      (file) => file.python !== state.originalPython[file.python_name],
    ) ||
    state.batchResults.some(
      (file) => file.python !== state.batchOriginal[file.python_name],
    );
  const { user, signOut } = useAuth();
  const backend = useBackendStatus(),
    path = usePathname();
  const screen = path.includes("convert")
    ? "Convert"
    : path.includes("export")
      ? "Export"
      : path === "/batch"
        ? "Batch conversion"
        : "Upload";
  return (
    <>
      <header className="app-header">
        <div className="app-header-inner">
          <Link href="/upload" className="header-brand">
            <Logo />
          </Link>
          <AppNav />
          <div className="header-right">
            <ThemeMenu />
            <div
              className={`connection ${backend.ready ? "online" : "offline"}`}
              role="status"
            >
              <span />
              {backend.checked
                ? backend.ready
                  ? "API connected"
                  : "API offline"
                : "Connecting…"}
            </div>
            {backend.checked && !backend.ready && (
              <Button
                variant="ghost"
                size="sm"
                onClick={backend.retry}
                aria-label="Retry API connection"
              >
                <RefreshCw size={16} />
              </Button>
            )}
            <div className="user-avatar" title={user?.display_name}>
              {user?.display_name.slice(0, 2).toUpperCase()}
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                if (
                  !edited ||
                  window.confirm(
                    "Sign out and discard local Python edits? Download them first to keep your changes.",
                  )
                )
                  void signOut();
              }}
              aria-label="Sign out"
            >
              <LogOut size={17} aria-hidden="true" />
              <span className="signout-label">Sign out</span>
            </Button>
          </div>
        </div>
      </header>
      <div className="workspace-context">
        <div className="breadcrumbs">
          <span>Workspace</span>
          <ChevronRight size={14} aria-hidden="true" />
          <strong>{screen}</strong>
          {state.project && path !== "/batch" && (
            <>
              <ChevronRight size={14} aria-hidden="true" />
              <span className="breadcrumb-project" title={state.project.name}>
                {state.project.name}
              </span>
            </>
          )}
        </div>
        {!state.project && path !== "/batch" && (
          <p className="context-hint">
            Open a project to enable Convert and Export.
          </p>
        )}
      </div>
    </>
  );
}
