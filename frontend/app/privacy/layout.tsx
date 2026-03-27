import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Privacy Policy — Clarvia",
  description:
    "Clarvia privacy policy. How we handle scan data, API usage, and user information.",
  alternates: {
    canonical: "https://clarvia.art/privacy",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function PrivacyLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
