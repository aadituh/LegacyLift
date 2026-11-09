"use client";
import { usePathname } from "next/navigation";
import { m, useReducedMotion } from "motion/react";
export function RouteTransition({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const reduced = useReducedMotion();
  return (
    <m.div
      key={path}
      className="route-content"
      initial={{ opacity: reduced ? 1 : 0, y: reduced ? 0 : 5 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: reduced ? 0 : 0.18 }}
    >
      {children}
    </m.div>
  );
}
