import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { ManualScreen } from "@/components/manual/ManualScreen";
import { wikiCatalog, wikiPage } from "@/lib/wiki";

export const dynamic = "force-static";
export const dynamicParams = false;

export function generateStaticParams() {
  return [...wikiCatalog().pages.keys()].map((slug) => ({ slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const page = wikiPage(slug);
  return { title: page ? page.title : "User manual" };
}

export default async function ManualPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const page = wikiPage(slug);
  if (!page) notFound();
  return <ManualScreen page={page} />;
}
