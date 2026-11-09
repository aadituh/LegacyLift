"use client";
import { AuthProvider } from "@/hooks/useAuth";
import { LazyMotion, domMax, MotionConfig } from "motion/react";
export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <LazyMotion features={domMax}>
      <MotionConfig reducedMotion="user" transition={{ duration: 0.18 }}>
        <AuthProvider>{children}</AuthProvider>
      </MotionConfig>
    </LazyMotion>
  );
}
