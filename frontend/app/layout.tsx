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
  keywords: [
    "AEO",
    "AI Engine Optimization",
    "agent readiness",
    "API score",
    "MCP",
    "AI agents",
    "Clarvia",
  ],
  openGraph: {
    title: "Clarvia AEO Scanner",
    description:
      "Is your service ready for AI agents? Get your Clarvia Score — the AEO standard for agent discoverability and trust.",
    url: "https://clarvia.art",
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
  metadataBase: new URL("https://clarvia.art"),
  robots: {
    index: true,
    follow: true,
  },
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
      <head>
        <meta name="theme-color" content="#0b0f18" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
        <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
        <link rel="icon" href="/favicon.ico" sizes="any" />
        <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
      </head>
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
