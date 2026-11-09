import type { Metadata } from "next";
import { Suspense } from "react";
import { ConvertScreen } from "@/components/convert/ConvertScreen";
import { Skeleton } from "@/components/ui/Spinner";
export const metadata: Metadata = { title: "Convert" };
export default function ConvertPage() {
  return (
    <Suspense
      fallback={<Skeleton label="Loading project and saved results…" />}
    >
      <ConvertScreen />
    </Suspense>
  );
}
