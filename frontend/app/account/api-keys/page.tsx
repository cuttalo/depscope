"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Badge,
  Section,
  PageHeader,
  Button,
  Input,
  Table,
  Thead,
  Tbody,
  Th,
  Td,
  Tr,
  Footer,
} from "../../../components/ui";

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

interface CreatedKey {
  id: number;
  key: string;
  prefix: string;
  name: string;
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

export default function ApiKeysPage() {
  const router = useRouter();
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newTest, setNewTest] = useState(false);
  const [created, setCreated] = useState<CreatedKey | null>(null);
  const [creating, setCreating] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    const r = await fetch("/api/auth/keys", { credentials: "include" });
    if (r.status === 401) {
      router.replace("/login");
      return;
    }
    const d = await r.json();
    setKeys(d.keys || []);
    setLoading(false);
  };

  useEffect(() => {
    load();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const create = async () => {
    setCreating(true);
    setError("");
    try {
      const r = await fetch("/api/auth/keys", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ name: newName || "API Key", test: newTest }),
      });
      if (!r.ok) {
        const d = await r.json().catch(() => ({}));
        throw new Error(d.detail || d.error || "Create failed");
      }
      const data = await r.json();
      setCreated({ id: data.id, key: data.key, prefix: data.prefix, name: data.name });
      setNewName("");
      setNewTest(false);
      setShowCreate(false);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Create failed");
    } finally {
      setCreating(false);
    }
  };

  const revoke = async (id: number) => {
    if (!confirm("Revoke this key? Any client using it will stop working immediately.")) return;
    const r = await fetch(`/api/auth/keys/${id}`, {
      method: "DELETE",
      credentials: "include",
    });
    if (r.ok) load();
  };

  const copy = async (txt: string) => {
    try {
      await navigator.clipboard.writeText(txt);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* ignore */
    }
  };

  return (
    <div className="min-h-screen">
      <main className="max-w-5xl mx-auto px-4 py-8">
        <PageHeader
          eyebrow="Account"
          title="API Keys"
          description="Manage keys used to authenticate API requests with higher rate limits."
          actions={
            <div className="flex items-center gap-2">
              <a
                href="/dashboard"
                className="inline-flex items-center text-xs font-medium px-3 py-1.5 rounded border border-[var(--border)] hover:bg-[var(--bg-hover)] transition"
              >
                Dashboard
              </a>
              <Button
                variant="primary"
                onClick={() => {
                  setCreated(null);
                  setShowCreate(true);
                }}
              >
                + Create key
              </Button>
            </div>
          }
        />

        {created && (
          <Section className="mb-6">
            <Card className="border-[var(--accent)]">
              <CardBody>
                <div className="text-sm text-[var(--text-dim)] mb-2">
                  New key <strong className="text-[var(--text)]">{created.name}</strong> created. Save it now — it will not be shown again.
                </div>
                <div className="flex gap-2 items-center bg-[var(--bg-input)] border border-[var(--border)] rounded px-3 py-2 font-mono text-xs overflow-x-auto">
                  <span className="flex-1 break-all">{created.key}</span>
                  <button
                    onClick={() => copy(created.key)}
                    className="text-[var(--accent)] hover:underline shrink-0"
                  >
                    {copied ? "Copied!" : "Copy"}
                  </button>
                </div>
                <button
                  onClick={() => setCreated(null)}
                  className="text-xs text-[var(--text-dim)] underline mt-3"
                >
                  I saved it, dismiss
                </button>
              </CardBody>
            </Card>
          </Section>
        )}

        {showCreate && (
          <Section className="mb-6">
            <Card>
              <CardHeader>
                <CardTitle>Create a new key</CardTitle>
              </CardHeader>
              <CardBody>
                <div className="space-y-3">
                  <Input
                    type="text"
                    placeholder="Name (e.g. Production, CI)"
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    className="w-full"
                  />
                  <label className="flex items-center gap-2 text-sm text-[var(--text-dim)]">
                    <input
                      type="checkbox"
                      checked={newTest}
                      onChange={(e) => setNewTest(e.target.checked)}
                    />
                    Test key (prefix <code className="font-mono">ds_test_</code>, no billing, still rate-limited)
                  </label>
                  {error && <p className="text-xs text-[var(--red)]">{error}</p>}
                  <div className="flex gap-2">
                    <Button variant="primary" onClick={create} disabled={creating}>
                      {creating ? "Creating..." : "Create"}
                    </Button>
                    <Button variant="ghost" onClick={() => setShowCreate(false)}>
                      Cancel
                    </Button>
                  </div>
                </div>
              </CardBody>
            </Card>
          </Section>
        )}

        <Section>
          <Card>
            {loading ? (
              <div className="p-8 text-center text-sm text-[var(--text-dim)]">Loading...</div>
            ) : keys.length === 0 ? (
              <div className="p-8 text-center text-sm text-[var(--text-dim)]">
                No keys yet. Click <strong>+ Create key</strong> to generate your first one.
              </div>
            ) : (
              <Table>
                <Thead>
                  <Tr>
                    <Th>Name</Th>
                    <Th>Key</Th>
                    <Th>Type</Th>
                    <Th className="text-right">Calls / mo</Th>
                    <Th>Last used</Th>
                    <Th>&nbsp;</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {keys.map((k) => (
                    <Tr key={k.id}>
                      <Td className="font-medium">{k.name}</Td>
                      <Td className="font-mono text-xs text-[var(--text-dim)]">{k.key_prefix}…</Td>
                      <Td>
                        <div className="flex items-center gap-2">
                          <Badge variant={k.is_test ? "warning" : "success"}>
                            {k.is_test ? "test" : "live"}
                          </Badge>
                          <span className="text-xs text-[var(--text-dim)]">{k.tier}</span>
                        </div>
                      </Td>
                      <Td className="text-right tabular-nums font-mono">
                        {k.requests_this_month.toLocaleString()}
                      </Td>
                      <Td className="text-xs text-[var(--text-dim)]">
                        {k.last_used_at ? formatRel(k.last_used_at) : "never"}
                        {k.last_used_ip ? ` · ${k.last_used_ip}` : ""}
                      </Td>
                      <Td className="text-right">
                        <button
                          onClick={() => revoke(k.id)}
                          className="text-xs text-[var(--red)] hover:underline"
                        >
                          Revoke
                        </button>
                      </Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            )}
          </Card>
        </Section>

        <p className="text-xs text-[var(--text-dim)] mt-6">
          Authenticate by sending the header{" "}
          <code className="font-mono text-[var(--accent)]">Authorization: Bearer ds_live_...</code> on any{" "}
          <code className="font-mono">/api/</code> request.
        </p>
      </main>
      <Footer />
    </div>
  );
}
