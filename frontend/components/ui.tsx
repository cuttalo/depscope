import { ReactNode } from "react";

/* ============================================================
 * CARD
 * ============================================================ */
export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`bg-[var(--bg-card)] border border-[var(--border)] rounded-lg ${className}`}>
      {children}
    </div>
  );
}

export function CardHeader({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`px-5 py-4 border-b border-[var(--border)] ${className}`}>
      {children}
    </div>
  );
}

export function CardBody({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`px-5 py-4 ${className}`}>{children}</div>;
}

export function CardTitle({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <h3 className={`text-sm font-medium text-[var(--text)] ${className}`}>
      {children}
    </h3>
  );
}

/* ============================================================
 * STAT
 * ============================================================ */
export function Stat({
  value,
  label,
  trend,
  color = "var(--text)",
  className = "",
}: {
  value: string | number;
  label: string;
  trend?: string;
  color?: string;
  className?: string;
}) {
  return (
    <div className={className}>
      <div className="text-2xl font-semibold tabular-nums tracking-tight" style={{ color }}>
        {value}
      </div>
      <div className="text-[11px] text-[var(--text-dim)] uppercase tracking-wider mt-1 font-medium">
        {label}
      </div>
      {trend && <div className="text-xs mt-1 text-[var(--text-dim)]">{trend}</div>}
    </div>
  );
}

/* ============================================================
 * BADGE
 * ============================================================ */
type BadgeVariant = "neutral" | "success" | "warning" | "danger" | "info" | "accent";

export function Badge({
  children,
  variant = "neutral",
  className = "",
}: {
  children: ReactNode;
  variant?: BadgeVariant;
  className?: string;
}) {
  const styles: Record<BadgeVariant, string> = {
    neutral: "bg-[var(--bg-hover)] text-[var(--text-dim)] border-[var(--border)]",
    success: "bg-[var(--green)]/10 text-[var(--green)] border-[var(--green)]/30",
    warning: "bg-[var(--orange)]/10 text-[var(--orange)] border-[var(--orange)]/30",
    danger: "bg-[var(--red)]/10 text-[var(--red)] border-[var(--red)]/30",
    info: "bg-[var(--blue)]/10 text-[var(--blue)] border-[var(--blue)]/30",
    accent: "bg-[var(--accent)]/10 text-[var(--accent)] border-[var(--accent)]/30",
  };
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 text-xs font-medium border rounded ${styles[variant]} ${className}`}
    >
      {children}
    </span>
  );
}

/** Mappa una severity OSV a un Badge variant coerente. */
export function SeverityBadge({ severity }: { severity: string }) {
  const s = (severity || "").toLowerCase();
  const variant: BadgeVariant =
    s === "critical" ? "danger" :
    s === "high" ? "warning" :
    s === "medium" ? "warning" :
    s === "low" ? "success" :
    "neutral";
  return <Badge variant={variant} className="uppercase">{s || "unknown"}</Badge>;
}

/** Mappa un'azione raccomandata (safe_to_use, do_not_use, ...) a un Badge. */
export function ActionBadge({ action }: { action: string }) {
  const label = action.replace(/_/g, " ");
  const variant: BadgeVariant =
    action === "safe_to_use" ? "success" :
    action === "do_not_use" ? "danger" :
    action === "find_alternative" ? "warning" :
    action === "update_required" ? "warning" :
    action === "use_with_caution" ? "warning" :
    "neutral";
  return <Badge variant={variant}>{label}</Badge>;
}

/* ============================================================
 * BUTTON
 * ============================================================ */
type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

export function Button({
  children,
  variant = "primary",
  onClick,
  disabled,
  className = "",
  type = "button",
}: {
  children: ReactNode;
  variant?: ButtonVariant;
  onClick?: () => void;
  disabled?: boolean;
  className?: string;
  type?: "button" | "submit";
}) {
  const styles: Record<ButtonVariant, string> = {
    primary: "bg-[var(--accent)] text-black hover:bg-[var(--accent-dim)] font-medium",
    secondary: "bg-[var(--bg-hover)] text-[var(--text)] hover:bg-[var(--border)] border border-[var(--border)]",
    ghost: "text-[var(--text-dim)] hover:text-[var(--text)] hover:bg-[var(--bg-hover)]",
    danger: "bg-[var(--red)] text-white hover:bg-[var(--red-dim)] font-medium",
  };
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-sm transition disabled:opacity-50 disabled:cursor-not-allowed ${styles[variant]} ${className}`}
    >
      {children}
    </button>
  );
}

/* ============================================================
 * TABLE
 * ============================================================ */
export function Table({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className="overflow-x-auto">
      <table className={`w-full text-sm ${className}`}>{children}</table>
    </div>
  );
}

export function Thead({ children }: { children: ReactNode }) {
  return <thead>{children}</thead>;
}

export function Tbody({ children }: { children: ReactNode }) {
  return <tbody>{children}</tbody>;
}

export function Th({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <th
      className={`text-left text-[11px] font-medium text-[var(--text-dim)] uppercase tracking-wider px-4 py-2 border-b border-[var(--border)] ${className}`}
    >
      {children}
    </th>
  );
}

export function Td({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <td className={`px-4 py-2.5 border-b border-[var(--border)] ${className}`}>{children}</td>
  );
}

export function Tr({
  children,
  onClick,
  className = "",
}: {
  children: ReactNode;
  onClick?: () => void;
  className?: string;
}) {
  return (
    <tr
      onClick={onClick}
      className={`${onClick ? "cursor-pointer hover:bg-[var(--bg-hover)]" : ""} ${className}`}
    >
      {children}
    </tr>
  );
}

/* ============================================================
 * INPUT / SELECT
 * ============================================================ */
export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  const { className = "", ...rest } = props;
  return (
    <input
      {...rest}
      className={`bg-[var(--bg-input)] border border-[var(--border)] rounded px-3 py-2 text-sm text-[var(--text)] placeholder:text-[var(--text-faded)] focus:outline-none focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)]/30 transition ${className}`}
    />
  );
}

export function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  const { className = "", children, ...rest } = props;
  return (
    <select
      {...rest}
      className={`bg-[var(--bg-input)] border border-[var(--border)] rounded px-3 py-2 text-sm text-[var(--text)] focus:outline-none focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)]/30 cursor-pointer transition ${className}`}
    >
      {children}
    </select>
  );
}

/* ============================================================
 * PAGE HEADER
 * ============================================================ */
export function PageHeader({
  title,
  description,
  actions,
  eyebrow,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
  eyebrow?: string;
}) {
  return (
    <div className="flex items-start justify-between gap-4 mb-6 pb-4 border-b border-[var(--border)]">
      <div>
        {eyebrow && (
          <div className="text-[11px] font-mono uppercase tracking-wider text-[var(--accent)] mb-1">
            {eyebrow}
          </div>
        )}
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {description && (
          <p className="text-sm text-[var(--text-dim)] mt-1 max-w-2xl">{description}</p>
        )}
      </div>
      {actions && <div className="flex gap-2 shrink-0">{actions}</div>}
    </div>
  );
}

/* ============================================================
 * SECTION
 * ============================================================ */
export function Section({
  title,
  description,
  children,
  actions,
  className = "",
}: {
  title?: string;
  description?: string;
  children: ReactNode;
  actions?: ReactNode;
  className?: string;
}) {
  return (
    <section className={className}>
      {(title || actions) && (
        <div className="flex items-end justify-between gap-4 mb-3">
          <div>
            {title && <h2 className="text-sm font-semibold tracking-tight">{title}</h2>}
            {description && (
              <p className="text-xs text-[var(--text-dim)] mt-0.5">{description}</p>
            )}
          </div>
          {actions && <div className="flex gap-2">{actions}</div>}
        </div>
      )}
      {children}
    </section>
  );
}

/* ============================================================
 * KBD
 * ============================================================ */
export function Kbd({ children }: { children: ReactNode }) {
  return (
    <kbd className="font-mono text-[10px] px-1.5 py-0.5 border border-[var(--border)] rounded bg-[var(--bg-input)] text-[var(--text-dim)]">
      {children}
    </kbd>
  );
}

/* ============================================================
 * FOOTER
 * ============================================================ */
export function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="border-t border-[var(--border)] mt-16 py-8 text-sm text-[var(--text-dim)]">
      <div className="max-w-6xl mx-auto px-4 grid md:grid-cols-3 gap-8">
        <div>
          <div className="font-mono font-semibold text-[var(--text)] mb-2">DepScope</div>
          <p className="text-xs leading-relaxed">
            Package intelligence for AI agents. Free, no auth, 17 ecosystems.
          </p>
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-wider text-[var(--text-dim)] font-medium mb-2">
            Resources
          </div>
          <div className="flex flex-col gap-1 text-xs">
            <a href="/api-docs" className="hover:text-[var(--accent)] transition">API Documentation</a>
            <a href="/docs" className="hover:text-[var(--accent)] transition">Swagger / OpenAPI</a>
            <a href="/popular" className="hover:text-[var(--accent)] transition">Popular Packages</a>
            <a href="/stats" className="hover:text-[var(--accent)] transition">Coverage</a>
            <a href="/.well-known/ai-plugin.json" className="hover:text-[var(--accent)] transition">AI Plugin</a>
          </div>
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-wider text-[var(--text-dim)] font-medium mb-2">
            Legal
          </div>
          <div className="flex flex-col gap-1 text-xs">
            <a href="/privacy" className="hover:text-[var(--accent)] transition">Privacy Policy</a>
            <a href="/contact" className="hover:text-[var(--accent)] transition">Contact</a>
            <a href="mailto:depscope@cuttalo.com" className="hover:text-[var(--accent)] transition">
              depscope@cuttalo.com
            </a>
            <a href="/zh" className="hover:text-[var(--accent)] transition">中文</a>
          </div>
        </div>
      </div>
      <div className="max-w-6xl mx-auto px-4 mt-6 pt-4 border-t border-[var(--border)] text-xs flex flex-col md:flex-row justify-between gap-2">
        <span>
          &copy; {year}{" "}
          <a href="https://cuttalo.com" className="hover:text-[var(--accent)] transition">
            Cuttalo srl
          </a>{" "}
          — Italy · VAT IT03242390734
        </span>
        <span className="text-[var(--text-faded)]">Built for AI agents</span>
      </div>
    </footer>
  );
}
