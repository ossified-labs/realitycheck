"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import ClaimInput from "@/components/ClaimInput";
import VerdictBadge from "@/components/VerdictBadge";
import { api, type Investigation } from "@/lib/api";

type Row = Pick<Investigation, "id" | "claim" | "status" | "verdict" | "created_at">;

export default function Home() {
  const [history, setHistory] = useState<Row[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.list().then(setHistory).catch((e: Error) => setError(e.message));
  }, []);

  return (
    <div className="space-y-10">
      <section className="space-y-4">
        <h1 className="text-3xl font-bold tracking-tight">Investigate a claim</h1>
        <p className="text-slate-600">
          RealityCheck breaks a claim into testable parts, searches for evidence, checks every quote against
          its source, and reports what the evidence does and doesn&apos;t show.
        </p>
        <ClaimInput />
      </section>

      <section>
        <h2 className="mb-3 text-lg font-semibold">Recent investigations</h2>
        {error && <p className="text-sm text-rose-600">Couldn&apos;t reach the API: {error}</p>}
        {!error && history.length === 0 && <p className="text-sm text-slate-500">None yet.</p>}
        <ul className="divide-y divide-slate-200 rounded-xl border border-slate-200 bg-white">
          {history.map((h) => (
            <li key={h.id}>
              <Link href={`/investigation/${h.id}`} className="flex items-center justify-between gap-3 p-3 hover:bg-slate-50">
                <span className="truncate">{h.claim}</span>
                {h.verdict ? <VerdictBadge value={h.verdict} /> : <span className="text-xs text-slate-500">{h.status}</span>}
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
