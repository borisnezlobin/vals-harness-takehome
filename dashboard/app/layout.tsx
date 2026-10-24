import type { Metadata } from "next";
import { Mona_Sans } from "next/font/google";
import { Suspense } from "react";

import { SiteHeader } from "@/components/SiteHeader";

import "./globals.css";

const mona = Mona_Sans({
  variable: "--font-mona",
  subsets: ["latin"],
  axes: ["wdth"],
});

export const metadata: Metadata = {
  title: { default: "Haggle", template: "%s – Haggle" },
  description: "Buyer and seller negotiation results between language models",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${mona.variable} antialiased`}>
      <body className="min-h-svh bg-page text-ink">
        <Suspense fallback={<SiteHeader.Fallback />}>
          <SiteHeader />
        </Suspense>
        <main className="mx-auto flex w-full max-w-7xl flex-col gap-16 px-4 pt-8 pb-24 sm:px-8">
          {children}
        </main>
      </body>
    </html>
  );
}
