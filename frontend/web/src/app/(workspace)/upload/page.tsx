import type { Metadata } from "next";
import { Suspense } from "react";
import { UploadScreen } from "@/components/upload/UploadScreen";
import { Skeleton } from "@/components/ui/Spinner";
export const metadata: Metadata = { title: "Upload" };
export default function UploadPage() {
  return (
    <Suspense fallback={<Skeleton label="Opening Upload…" />}>
      <UploadScreen />
    </Suspense>
  );
}
