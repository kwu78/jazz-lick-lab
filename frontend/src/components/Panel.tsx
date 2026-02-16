import type { ReactNode } from "react";

export default function Panel({
  title,
  children,
}: {
  title?: string;
  children: ReactNode;
}) {
  return (
    <section className="border border-border rounded p-5 mb-6">
      {title && (
        <h2 className="font-serif text-lg mb-3 pb-2 border-b border-border">
          {title}
        </h2>
      )}
      {children}
    </section>
  );
}
