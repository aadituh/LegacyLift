import type { Metadata } from "next";
import { ManualScreen } from "@/components/manual/ManualScreen";
import { wikiPage } from "@/lib/wiki";

export const metadata: Metadata = { title: "User manual" };
export const dynamic = "force-static";

export default function ManualHome() {
  const page = wikiPage("Home");
  if (!page) throw new Error("The Home wiki page is missing.");
  return <ManualScreen page={page} />;
}
