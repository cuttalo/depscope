"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Stat,
  Badge,
  Section,
  PageHeader,
  Button,
  Footer,
} from "../../components/ui";

interface Me {
  email: string;
  role: string;
  plan: string;
}

interface ApiKey {
  id: number;
  key_prefix: string;
  name: string;
  tier: string;
  is_test: boolean;
  last_used_at: string | null;
  last_used_ip: string | null;
  requests_this_month: number;
  created_at: string;
  expires_at: string | null;
}

interface Usage {
  total: number;
  by_day: { day: string; calls: number }[];
}

function formatRel(iso: string): string {
  const d = new Date(iso).getTime();
  const now = Date.now();
  const diff = Math.max(0, now - d);
  const min = Math.floor(diff / 60000);
  if (min < 1) return "just now";
  if (min < 60) return `${min}m ago`;
  const h = Math.floor(min / 60);
  if (h < 24) return `${h}h ago`;
  const days = Math.floor(h / 24);
  return `${days}d ago`;
}

export default function DashboardPage() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [usage, setUsage] = useState<Usage | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const r = await fetch("/api/auth/me", { credentials: "include" });
        if (!r.ok) {
          router.replace("/login");
          return;
        }
        setMe(await r.json());
        const [kr, ur] = await Promise.all([
          fetch("/api/auth/keys", { credentials: "include" }).then((x) => x.json()),
          fetch("/api/auth/usage", { credentials: "include" }).then((x) => x.json()),
        ]);
        setKeys(kr.keys || []);
        setUsage(ur);
      } catch {
        router.replace("/login");
      } finally {
        setLoading(false);
      }
    })();
  }, [router]);

  const logout = async () => {
    await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
    router.replace("/");
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-[var(--text-dim)]">
        Loading dashboard...
      </div>
    );
  }
  if (!me) return null;

  const todayCalls = usage?.by_day?.[usage.by_day.length - 1]?.calls ?? 0;

  return (
    <div className="min-h-screen">
      <main className="max-w-5xl mx-auto px-4 py-8">
        <PageHeader
          eyebrow="Account"
          title="Dashboard"
          description={`Signed in as ${me.email}`}
          actions={
            <div className="flex items-center gap-2">
              <Badge variant="accent">{me.plan}</Badge>
              <a
                href="/account/api-keys"
                className="inline-flex items-center gap-1 text-xs font-medium px-3 py-1.5 rounded border border-[var(--border)] hover:bg-[var(--bg-hover)] transition"
              >
                API keys
              </a>
              <Button variant="ghost" onClick={logout}>
                Logout
              </Button>
            </div>
          }
        />

        <Section className="mb-6">
          <Card>
            <div className="grid grid-cols-1 sm:grid-cols-3 divide-y sm:divide-y-0 sm:divide-x divide-[var(--border)]">
              <div className="p-5">
                <Stat value={(usage?.total ?? 0).toLocaleString()} label="Calls this month" />
              </div>
              <div className="p-5">
                <Stat value={todayCalls.toLocaleString()} label="Calls today" color="var(--accent)" />
              </div>
              <div className="p-5">
                <Stat value={keys.length} label="Active keys" color="var(--green)" />
              </div>
            </div>
          </Card>
        </Section>

        <Section
          title="Your API keys"
          actions={
            <a
              href="/account/api-keys"
              className="inline-flex items-center text-xs font-medium px-3 py-1.5 rounded bg-[var(--accent)] text-black hover:bg-[var(--accent-dim)] transition"
            >
              Manage keys
            </a>
          }
          className="mb-6"
        >
          <Card>
            {keys.length === 0 ? (
              <CardBody>
                <p className="text-sm text-[var(--text-dim)]">
                  No keys yet.{" "}
                  <a href="/account/api-keys" className="underline text-[var(--accent)]">Create one</a>{" "}
                  to start calling the API with higher limits.
                </p>
              </CardBody>
            ) : (
              <ul className="divide-y divide-[var(--border)]">
                {keys.slice(0, 5).map((k) => (
                  <li key={k.id} className="flex justify-between items-center px-4 py-3 gap-3">
                    <div className="min-w-0">
                      <div className="font-mono text-sm text-[var(--text)]">{k.key_prefix}…</div>
                      <div className="text-xs text-[var(--text-dim)]">
                        {k.name} · {k.tier}{" "}
                        <Badge variant={k.is_test ? "warning" : "success"}>{k.is_test ? "test" : "live"}</Badge>
                      </div>
                    </div>
                    <div className="text-right text-xs text-[var(--text-dim)] shrink-0">
                      <div className="tabular-nums font-mono">
                        {k.requests_this_month.toLocaleString()} / mo
                      </div>
                      <div className="text-[var(--text-faded)]">
                        {k.last_used_at ? formatRel(k.last_used_at) : "never used"}
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </Section>

        <Section title="Last 30 days">
          <Card>
            <CardHeader>
              <CardTitle>Daily API calls</CardTitle>
            </CardHeader>
            <CardBody>
              {usage && usage.by_day.length > 0 ? (
                <div className="flex items-end gap-1 h-32">
                  {usage.by_day.map((d) => {
                    const max = Math.max(...usage.by_day.map((x) => x.calls), 1);
                    const h = Math.max(2, Math.round((d.calls / max) * 100));
                    return (
                      <div
                        key={d.day}
                        title={`${d.day}: ${d.calls}`}
                        className="flex-1 bg-[var(--accent)] rounded-t opacity-80 hover:opacity-100 transition"
                        style={{ height: `${h}%` }}
                      />
                    );
                  })}
                </div>
              ) : (
                <p className="text-sm text-[var(--text-dim)]">No usage yet.</p>
              )}
            </CardBody>
          </Card>
        </Section>
      </main>
      <Footer />
    </div>
  );
}
