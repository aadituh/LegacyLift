import { FolderOpen } from "lucide-react";
export function EmptyState({
  icon,
  children,
  action,
}: {
  icon?: React.ReactNode;
  children: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div className="empty-state">
      <span className="empty-icon" aria-hidden="true">
        {icon ?? <FolderOpen size={25} />}
      </span>
      <div>{children}</div>
      {action}
    </div>
  );
}
