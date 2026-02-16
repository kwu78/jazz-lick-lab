import type { ReactNode } from "react";

export default function PageShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-page text-ink">
      <header className="border-b border-border px-6 py-4">
        <a href="/" className="no-underline">
          <h1 className="text-2xl font-serif">Jazz Lick Lab</h1>
        </a>
      </header>
      <main className="mx-auto max-w-4xl px-6 py-8">{children}</main>
    </div>
  );
}
