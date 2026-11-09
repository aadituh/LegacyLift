import { WorkspaceShell } from "@/components/layout/WorkspaceShell";
export default function WorkspaceLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <WorkspaceShell>{children}</WorkspaceShell>;
}
