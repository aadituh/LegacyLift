import type { Metadata } from "next";
import { Suspense } from "react";
import { AuthLayout } from "@/components/auth/AuthLayout";
import { AuthForm } from "@/components/auth/AuthForm";
export const metadata: Metadata = { title: "Sign in" };
export default function SignIn() {
  return (
    <AuthLayout>
      <Suspense>
        <AuthForm mode="sign-in" />
      </Suspense>
    </AuthLayout>
  );
}
