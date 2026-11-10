"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";

const EXAMPLES = [
  "Drinking coffee improves long-term memory.",
  "The Great Wall of China is visible from space with the naked eye.",
  "Daylight saving time reduces energy consumption.",
];

export default function ClaimInput() {
  const router = useRouter();
  const [claim, setClaim] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const text = claim.trim();
    if (text.length < 8) return setError("Please enter a full claim (at least 8 characters).");
    setBusy(true);
    setError(null);
    try {
      const { id } = await api.create(text);
      router.push(`/investigation/${id}`);
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      <textarea
        value={claim}
        onChange={(e) => setClaim(e.target.value)}
        maxLength={1000}
        rows={3}
        placeholder="Enter a claim to investigate…"
        className="w-full rounded-xl border border-slate-300 bg-white p-4 text-base shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200"
      />
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="submit"
          disabled={busy}
          className="rounded-lg bg-indigo-600 px-5 py-2.5 font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {busy ? "Starting…" : "Investigate"}
        </button>
        <span className="text-sm text-slate-500">Try:</span>
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            type="button"
            onClick={() => setClaim(ex)}
            className="rounded-full bg-slate-200 px-3 py-1 text-xs text-slate-700 hover:bg-slate-300"
          >
            {ex}
          </button>
        ))}
      </div>
      {error && <p className="text-sm text-rose-600">{error}</p>}
    </form>
  );
}
