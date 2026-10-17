import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "SafePulse",
  description: "Multilingual road-hazard intelligence for Chandigarh",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen">
        <header className="border-b bg-white">
          <nav className="mx-auto flex max-w-5xl items-center gap-6 px-4 py-3">
            <Link href="/" className="text-lg font-bold text-slate-900">
              SafePulse
            </Link>
            <Link href="/" className="text-sm text-slate-600 hover:text-slate-900">
              Report
            </Link>
            <Link href="/map" className="text-sm text-slate-600 hover:text-slate-900">
              Map
            </Link>
            <Link href="/tickets" className="text-sm text-slate-600 hover:text-slate-900">
              Tickets
            </Link>
          </nav>
        </header>
        <main className="mx-auto max-w-5xl px-4 py-6">{children}</main>
        <footer className="mx-auto max-w-5xl px-4 py-6 text-xs text-slate-500">
          Map data &amp; geocoding © OpenStreetMap contributors. Priority scores
          are a triage heuristic for human review — not an accident probability.
        </footer>
      </body>
    </html>
  );
}
