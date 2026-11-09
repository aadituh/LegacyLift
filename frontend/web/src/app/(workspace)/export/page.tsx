import type { Metadata } from "next";
import { Suspense } from "react";
import { ExportScreen } from "@/components/export/ExportScreen";
import { Skeleton } from "@/components/ui/Spinner";
export const metadata: Metadata = { title: "Export" };
export default function ExportPage() {
  return (
    <Suspense fallback={<Skeleton label="Loading your project…" />}>
      <ExportScreen />
    </Suspense>
  );
}
