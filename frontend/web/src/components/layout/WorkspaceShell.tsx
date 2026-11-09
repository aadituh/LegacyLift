"use client";
import { AuthGate } from "@/components/auth/AuthGate";
import { useAuth } from "@/hooks/useAuth";
import { WorkspaceProvider } from "@/hooks/useWorkspace";
import { AppHeader } from "./AppHeader";
import { StatusMessage } from "./StatusMessage";
import { RouteTransition } from "./RouteTransition";
import { DraftExitGuard } from "./DraftExitGuard";
export function WorkspaceShell({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  return (
    <AuthGate>
      <WorkspaceProvider key={user?.id}>
        <DraftExitGuard />
        <a href="#main-content" className="skip-link">
          Skip to content
        </a>
        <div className="app-shell">
          <div className="app-body">
            <AppHeader />
            <main id="main-content" className="main-content" tabIndex={-1}>
              <StatusMessage />
              <RouteTransition>{children}</RouteTransition>
            </main>
            <footer className="workspace-footer">
              <span>Legacy code. Lasting possibilities.</span>
              <span>LegacyLift · COBOL → Python</span>
            </footer>
          </div>
        </div>
      </WorkspaceProvider>
    </AuthGate>
  );
}
