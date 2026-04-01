import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Analytics } from "@vercel/analytics/react";
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
        url: "/api/og",
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
    images: ["/api/og"],
  },
  metadataBase: new URL("https://clarvia.art"),
  alternates: {
    canonical: "./",
  },
  robots: {
    index: true,
    follow: true,
  },
  verification: {
    google: "cy8UwhbYQumpI801zDgXW-kbgt_EtxhiN8YweUV-c2A",
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
      <body className="min-h-full flex flex-col">
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "SoftwareApplication",
              "name": "Clarvia",
              "applicationCategory": "DeveloperApplication",
              "description": "AEO (Agent Engine Optimization) scanner — scores and benchmarks 27,843+ AI agent tools for discoverability, quality, and agent compatibility",
              "url": "https://clarvia.art",
              "offers": {
                "@type": "Offer",
                "price": "0",
                "priceCurrency": "USD"
              },
              "operatingSystem": "Web",
              "softwareVersion": "1.0.2",
              "creator": {
                "@type": "Organization",
                "name": "Clarvia",
                "url": "https://clarvia.art"
              }
            })
          }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "FAQPage",
              "mainEntity": [
                {
                  "@type": "Question",
                  "name": "What is AEO?",
                  "acceptedAnswer": {
                    "@type": "Answer",
                    "text": "AEO (AI Engine Optimization) measures how easily AI agents can discover and use your API or MCP server. It is the equivalent of SEO for the agent economy — instead of optimizing for search engines, AEO optimizes for AI systems that autonomously consume APIs, tools, and services."
                  }
                },
                {
                  "@type": "Question",
                  "name": "What is a Clarvia Score?",
                  "acceptedAnswer": {
                    "@type": "Answer",
                    "text": "A 0-100 score measuring agent readiness across 4 dimensions: API Accessibility, Data Structuring, Agent Compatibility, and Trust Signals. Higher scores indicate better discoverability and usability by AI agents."
                  }
                },
                {
                  "@type": "Question",
                  "name": "How do I improve my AEO score?",
                  "acceptedAnswer": {
                    "@type": "Answer",
                    "text": "Scan your URL on Clarvia, review the dimension breakdowns to identify weak areas, and follow the Improvement Playbook with actionable recommendations for each dimension. Common improvements include adding OpenAPI specs, structured error responses, and MCP server support."
                  }
                },
                {
                  "@type": "Question",
                  "name": "Is Clarvia free?",
                  "acceptedAnswer": {
                    "@type": "Answer",
                    "text": "Yes, scanning, tool search, side-by-side comparison, weekly trending, and embeddable AEO badges are all free. Clarvia indexes over 27,843 tools across the AI agent ecosystem."
                  }
                }
              ]
            })
          }}
        />
        {children}
        <Analytics />
      </body>
    </html>
  );
}
