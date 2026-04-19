"use client";
import { useState } from "react";

export function CopyButton({
  text,
  label = "Copy",
  labelCopied = "Copied",
  className = "",
}: {
  text: string;
  label?: string;
  labelCopied?: string;
  className?: string;
}) {
  const [copied, setCopied] = useState(false);

  const copy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <button
      onClick={copy}
      className={`text-xs font-medium px-2 py-1 rounded border transition ${
        copied
          ? "border-[var(--green)]/40 text-[var(--green)] bg-[var(--green)]/10"
          : "border-[var(--border)] text-[var(--text-dim)] hover:text-[var(--accent)] hover:border-[var(--accent)]/40"
      } ${className}`}
    >
      {copied ? labelCopied : label}
    </button>
  );
}
