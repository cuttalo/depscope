"use client";

import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { useTransition } from "react";
import { Select } from "../../../components/ui";

interface Props {
  current: string;
  ecosystems: string[];
  labels: Record<string, string>;
}

export default function EcosystemFilter({ current, ecosystems, labels }: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [pending, startTransition] = useTransition();

  const onChange = (value: string) => {
    const params = new URLSearchParams(searchParams?.toString() || "");
    if (value === "all") {
      params.delete("ecosystem");
    } else {
      params.set("ecosystem", value);
    }
    const qs = params.toString();
    const url = qs ? `${pathname}?${qs}` : pathname;
    startTransition(() => {
      router.push(url);
    });
  };

  return (
    <Select
      value={current}
      onChange={(e) => onChange(e.target.value)}
      disabled={pending}
    >
      {ecosystems.map((e) => (
        <option key={e} value={e}>
          {labels[e] || e}
        </option>
      ))}
    </Select>
  );
}
