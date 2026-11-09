import type { Metadata } from "next";
import { ConvertScreen } from "@/components/convert/ConvertScreen";
export const metadata: Metadata = { title: "Convert" };
export default async function ConvertPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <ConvertScreen projectId={id} />;
}
