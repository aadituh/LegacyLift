import type { Metadata } from "next";
import { BatchScreen } from "@/components/batch/BatchScreen";
export const metadata: Metadata = { title: "Batch conversion" };
export default function BatchPage() {
  return <BatchScreen />;
}
