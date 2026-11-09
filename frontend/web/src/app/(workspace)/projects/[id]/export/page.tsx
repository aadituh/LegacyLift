import type { Metadata } from "next";
import { ExportScreen } from "@/components/export/ExportScreen";
export const metadata: Metadata = { title: "Export" };
export default async function ExportPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <ExportScreen projectId={id} />;
}
