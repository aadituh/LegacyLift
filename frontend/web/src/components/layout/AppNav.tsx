"use client";
import Link from "next/link";
import { LayoutGroup, m } from "motion/react";
import { usePathname } from "next/navigation";
import { Upload, Files, ArrowRightLeft, Download } from "lucide-react";
import { useWorkspace } from "@/hooks/useWorkspace";
import { projectUrl } from "@/lib/routes";
export function AppNav() {
  const pathname = usePathname(),
    { state } = useWorkspace();
  const id = state.project?.id;
  const items = [
    { label: "Upload", href: "/upload", icon: Upload },
    {
      label: "Convert",
      href: id ? projectUrl("convert", id) : null,
      icon: ArrowRightLeft,
    },
    {
      label: "Export",
      href: id ? projectUrl("export", id) : null,
      icon: Download,
    },
    { label: "Batch conversion", href: "/batch", icon: Files },
  ];
  return (
    <LayoutGroup id="workspace-nav">
      <nav aria-label="Main" className="workspace-nav">
        <ul className="nav-list">
          {items.map((item) => {
            const active = Boolean(
              item.href && pathname === item.href.split("?")[0],
            );
            return (
              <li key={item.label}>
                {item.href ? (
                  <Link
                    href={item.href}
                    className={active ? "nav-item active" : "nav-item"}
                    aria-current={active ? "page" : undefined}
                  >
                    {active && (
                      <m.span
                        className="nav-active-indicator"
                        layoutId="active-nav"
                        aria-hidden="true"
                        transition={{
                          type: "spring",
                          stiffness: 500,
                          damping: 42,
                        }}
                      />
                    )}
                    <item.icon size={17} aria-hidden="true" />
                    <span>{item.label}</span>
                  </Link>
                ) : (
                  <span
                    className="nav-item nav-disabled"
                    aria-disabled="true"
                    title="Open a project first"
                  >
                    <item.icon size={17} aria-hidden="true" />
                    <span>{item.label}</span>
                    <span className="sr-only"> — Open a project first</span>
                  </span>
                )}
              </li>
            );
          })}
        </ul>
      </nav>
    </LayoutGroup>
  );
}
