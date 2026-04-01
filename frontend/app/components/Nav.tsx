"use client";

import { useState } from "react";
import Link from "next/link";
import Image from "next/image";

const NAV_LINKS = [
  { href: "/tools", label: "Tools" },
  { href: "/leaderboard", label: "Leaderboard" },
  { href: "/guide", label: "Guide" },
  { href: "/register", label: "Register" },
  { href: "/trending", label: "Trending" },
  { href: "/compare", label: "Compare" },
  { href: "/docs", label: "Docs" },
];

export default function Nav() {
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 border-b border-card-border/50 backdrop-blur-xl bg-background/80">
      <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-8">
          <Link href="/" className="flex items-center gap-2.5 group">
            <Image
              src="/logos/clarvia-icon.svg"
              alt="Clarvia"
              width={32}
              height={32}
              className="rounded-full group-hover:scale-110 transition-transform duration-200"
            />
            <span className="font-semibold text-base tracking-tight text-foreground">
              clarvia
            </span>
          </Link>
          {/* Desktop nav */}
          <nav className="hidden sm:flex items-center gap-6">
            {NAV_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="text-sm text-muted hover:text-foreground transition-colors"
              >
                {link.label}
              </Link>
            ))}
          </nav>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-xs text-muted/60 font-mono hidden sm:inline">v1.0</span>
          {/* Mobile hamburger */}
          <button
            onClick={() => setOpen(!open)}
            className="sm:hidden flex flex-col gap-1.5 p-1"
            aria-label="Toggle menu"
          >
            <span className={`block w-5 h-0.5 bg-foreground transition-transform duration-200 ${open ? "rotate-45 translate-y-2" : ""}`} />
            <span className={`block w-5 h-0.5 bg-foreground transition-opacity duration-200 ${open ? "opacity-0" : ""}`} />
            <span className={`block w-5 h-0.5 bg-foreground transition-transform duration-200 ${open ? "-rotate-45 -translate-y-2" : ""}`} />
          </button>
        </div>
      </div>
      {/* Mobile menu */}
      {open && (
        <nav className="sm:hidden border-t border-card-border/50 bg-background/95 backdrop-blur-xl px-6 py-4 space-y-3">
          {NAV_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              onClick={() => setOpen(false)}
              className="block text-sm text-muted hover:text-foreground transition-colors py-1"
            >
              {link.label}
            </Link>
          ))}
        </nav>
      )}
    </header>
  );
}
