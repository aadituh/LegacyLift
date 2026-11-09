import type { Metadata } from "next";
import { AuthLayout } from "@/components/auth/AuthLayout";
import { AuthForm } from "@/components/auth/AuthForm";
export const metadata: Metadata = { title: "Create account" };
export default function SignUp() {
  return (
    <AuthLayout>
      <AuthForm mode="sign-up" />
    </AuthLayout>
  );
}
