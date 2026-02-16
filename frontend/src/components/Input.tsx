import type { InputHTMLAttributes } from "react";

export default function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className="border border-border rounded px-3 py-2 text-sm bg-transparent text-ink placeholder:text-muted focus:outline-none focus:border-ink"
      {...props}
    />
  );
}
