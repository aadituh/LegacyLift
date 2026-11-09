import type { Metadata, Viewport } from "next";
import { Providers } from "@/components/Providers";
import "./globals.css";
export const metadata: Metadata = {
  title: { default: "LegacyLift", template: "%s · LegacyLift" },
  description:
    "Upload COBOL files, explore dependencies, and review verified draft Python output with LegacyLift.",
};
export const viewport: Viewport = { themeColor: "#102a43" };
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `try { var t=localStorage.getItem("legacylift-theme"); document.documentElement.dataset.theme=t==="dark"||t==="light"?t:matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light"; } catch {}`,
          }}
        />
      </head>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
