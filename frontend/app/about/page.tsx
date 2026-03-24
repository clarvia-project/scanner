import Link from "next/link";
import Image from "next/image";

export default function AboutPage() {
  return (
    <div className="flex flex-col min-h-screen bg-gradient-mesh">
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
            <nav className="hidden sm:flex items-center gap-6">
              <Link href="/leaderboard" className="text-sm text-muted hover:text-foreground transition-colors">Leaderboard</Link>
              <Link href="/guide" className="text-sm text-muted hover:text-foreground transition-colors">Guide</Link>
              <Link href="/methodology" className="text-sm text-muted hover:text-foreground transition-colors">Methodology</Link>
              <Link href="/docs" className="text-sm text-muted hover:text-foreground transition-colors">Docs</Link>
            </nav>
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-3xl mx-auto w-full px-6 py-12 space-y-12">
        {/* Hero */}
        <div className="text-center space-y-4">
          <div className="flex justify-center">
            <Image
              src="/logos/clarvia-icon.svg"
              alt="Clarvia"
              width={64}
              height={64}
              className="rounded-full"
            />
          </div>
          <h1 className="text-3xl font-bold">About Clarvia</h1>
          <p className="text-muted max-w-xl mx-auto text-sm leading-relaxed">
            The discovery &amp; trust standard for the agent economy.
          </p>
        </div>

        {/* Mission */}
        <div className="space-y-4">
          <h2 className="text-xs font-mono text-accent uppercase tracking-widest">
            Mission
          </h2>
          <div className="glass-card rounded-xl px-6 py-5 space-y-3 text-sm text-muted leading-relaxed">
            <p>
              We&apos;re building the standard for AI agent discoverability.
              Clarvia helps API providers understand how well AI agents can
              discover, access, and trust their services.
            </p>
            <p>
              Every API deserves to know its agent-readiness score &mdash; and
              every agent deserves APIs it can rely on.
            </p>
          </div>
        </div>

        {/* Why AEO */}
        <div className="space-y-4">
          <h2 className="text-xs font-mono text-accent uppercase tracking-widest">
            Why AEO?
          </h2>
          <div className="glass-card rounded-xl px-6 py-5 space-y-3 text-sm text-muted leading-relaxed">
            <p>
              <strong className="text-foreground">Agent Engine Optimization</strong> is
              the next evolution after SEO. As AI agents become the primary
              consumers of APIs &mdash; discovering services, negotiating
              integrations, and executing workflows autonomously &mdash; the
              rules of discoverability are changing.
            </p>
            <p>
              SEO optimized for human search engines. AEO optimizes for agent
              search engines. Structured schemas, machine-readable docs, trust
              signals, and MCP compatibility matter more than keywords and
              backlinks.
            </p>
          </div>
        </div>

        {/* The Team */}
        <div className="space-y-4">
          <h2 className="text-xs font-mono text-accent uppercase tracking-widest">
            The Team
          </h2>
          <div className="glass-card rounded-xl px-6 py-5 text-sm text-muted leading-relaxed">
            <p>
              Clarvia is built by a team passionate about the agent economy. We
              believe every API should be agent-ready &mdash; and we&apos;re
              building the tools to make that measurable.
            </p>
          </div>
        </div>

        {/* Methodology */}
        <div className="space-y-4">
          <h2 className="text-xs font-mono text-accent uppercase tracking-widest">
            Methodology
          </h2>
          <div className="glass-card rounded-xl px-6 py-5 space-y-3 text-sm text-muted leading-relaxed">
            <p>
              The Clarvia Score evaluates APIs across four dimensions:{" "}
              <strong className="text-foreground">API Accessibility</strong>,{" "}
              <strong className="text-foreground">Data Structuring</strong>,{" "}
              <strong className="text-foreground">Agent Compatibility</strong>, and{" "}
              <strong className="text-foreground">Trust Signals</strong>. Weights
              are derived from real-world agent failure frequencies.
            </p>
            <p>
              <Link
                href="/methodology"
                className="text-accent hover:text-accent-hover transition-colors font-medium"
              >
                Read the full methodology &rarr;
              </Link>
            </p>
          </div>
        </div>

        {/* Contact */}
        <div className="space-y-4">
          <h2 className="text-xs font-mono text-accent uppercase tracking-widest">
            Contact
          </h2>
          <div className="glass-card rounded-xl px-6 py-5 text-sm text-muted leading-relaxed">
            <div className="flex flex-col sm:flex-row gap-6">
              <a
                href="https://x.com/clarvia_ai"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 text-accent hover:text-accent-hover transition-colors font-medium"
              >
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
                </svg>
                @clarvia_ai
              </a>
              <a
                href="https://github.com/clarvia-project"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 text-accent hover:text-accent-hover transition-colors font-medium"
              >
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12" />
                </svg>
                GitHub
              </a>
            </div>
          </div>
        </div>

        <div className="text-center">
          <Link
            href="/"
            className="inline-block btn-gradient text-white px-8 py-3 rounded-xl text-sm font-medium"
          >
            Scan Your Service
          </Link>
        </div>
      </main>

      <footer className="border-t border-card-border/50 px-6 py-8">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-muted">
          <div className="flex items-center gap-3">
            <Image
              src="/logos/clarvia-icon.svg"
              alt="Clarvia"
              width={24}
              height={24}
              className="rounded-full"
            />
            <span>Clarvia &mdash; Discovery &amp; Trust standard for the agent economy</span>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/privacy" className="hover:text-foreground transition-colors">Privacy</Link>
            <a href="https://github.com/clarvia-project" target="_blank" rel="noopener noreferrer" className="hover:text-foreground transition-colors">GitHub</a>
            <a href="https://x.com/clarvia_ai" target="_blank" rel="noopener noreferrer" className="hover:text-foreground transition-colors">@clarvia_ai</a>
            <Link href="/about" className="hover:text-foreground transition-colors">About</Link>
            <Link href="#" className="hover:text-foreground transition-colors" title="Coming soon">Terms</Link>
            <Link href="/methodology" className="hover:text-foreground transition-colors">Methodology</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
