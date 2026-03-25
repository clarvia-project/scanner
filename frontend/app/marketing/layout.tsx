import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Marketing KPI — Clarvia (Internal)",
  robots: { index: false, follow: false },
};

export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
