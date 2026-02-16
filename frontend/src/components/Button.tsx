import type { ButtonHTMLAttributes } from "react";

export default function Button({
  children,
  variant = "primary",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary";
}) {
  const base =
    "px-4 py-2 text-sm rounded border transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer";
  const styles =
    variant === "primary"
      ? "bg-ink text-page border-ink hover:bg-accent"
      : "bg-transparent text-ink border-border hover:bg-ink/5";

  return (
    <button className={`${base} ${styles}`} {...props}>
      {children}
    </button>
  );
}
