import type { Metadata } from "next";
import { AuthLayout } from "@/components/auth/AuthLayout";
import { AuthForm } from "@/components/auth/AuthForm";
export const metadata: Metadata = { title: "Sign in" };
export default async function SignIn({
  searchParams,
}: {
  searchParams: Promise<{ created?: string }>;
}) {
  const query = await searchParams;
  return (
    <AuthLayout>
      <AuthForm
        mode="sign-in"
        notice={
          query.created === "1"
            ? "Account created. Sign in to open your workspace."
            : undefined
        }
      />
    </AuthLayout>
  );
}
