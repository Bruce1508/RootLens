import type { Metadata } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans, IBM_Plex_Serif } from "next/font/google";
import Link from "next/link";
import { DemoBanner } from "@/components/demo-banner";
import "./globals.css";

// IBM Plex across three roles, matching the three registers the product
// actually speaks in: mono for machine readout (SQL, evidence ids,
// timings), serif for a conclusion drawn from that readout, sans for the
// interface around both.
const plexSans = IBM_Plex_Sans({
  variable: "--font-plex-sans",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

const plexMono = IBM_Plex_Mono({
  variable: "--font-plex-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
});

const plexSerif = IBM_Plex_Serif({
  variable: "--font-plex-serif",
  subsets: ["latin"],
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "RootLens",
  description:
    "A local-first AI analyst that investigates why a business metric changed, with every claim backed by an executed query.",
};

function Mark() {
  return (
    <svg width="20" height="20" viewBox="0 0 112 112" aria-hidden="true">
      <line
        x1="76"
        y1="76"
        x2="102"
        y2="102"
        stroke="var(--color-signal)"
        strokeWidth="10"
        strokeLinecap="round"
      />
      <circle cx="46" cy="46" r="34" stroke="var(--color-signal)" strokeWidth="8" fill="none" />
      <circle cx="46" cy="46" r="30" fill="var(--color-bg)" />
      <polyline
        points="24,58 36,50 46,64 58,34 68,40"
        fill="none"
        stroke="var(--color-positive)"
        strokeWidth="5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${plexSans.variable} ${plexMono.variable} ${plexSerif.variable} min-h-screen`}
      >
        {process.env.NEXT_PUBLIC_DEMO_MODE && <DemoBanner />}
        <header className="border-b border-line">
          <div className="mx-auto flex max-w-6xl items-center gap-8 px-6 py-3">
            <Link href="/" className="flex items-center gap-2.5">
              <Mark />
              <span className="font-mono text-sm font-medium tracking-tight">RootLens</span>
            </Link>
            <nav className="flex items-center gap-5 font-mono text-xs text-muted">
              <Link href="/" className="transition-colors hover:text-ink">
                Dashboard
              </Link>
              <Link href="/evaluations" className="transition-colors hover:text-ink">
                Benchmark
              </Link>
            </nav>
          </div>
        </header>
        {children}
      </body>
    </html>
  );
}
