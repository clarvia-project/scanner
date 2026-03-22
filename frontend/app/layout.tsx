import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Clarvia AEO Scanner — Is your service ready for AI agents?",
  description:
    "Get your Clarvia Score — the AEO standard for agent discoverability and trust. Scan any API to measure AI Engine Optimization readiness.",
  openGraph: {
    title: "Clarvia AEO Scanner",
    description:
      "Is your service ready for AI agents? Get your Clarvia Score — the AEO standard for agent discoverability and trust.",
    url: "https://scanner.clarvia.io",
    siteName: "Clarvia",
    type: "website",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "Clarvia AEO Scanner",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Clarvia AEO Scanner",
    description:
      "Is your service ready for AI agents? Get your Clarvia Score.",
    images: ["/og-image.png"],
  },
  metadataBase: new URL("https://scanner.clarvia.io"),
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
