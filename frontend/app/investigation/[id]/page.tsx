"use client";

import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import EvidenceCard from "@/components/EvidenceCard";
import ReportView from "@/components/ReportView";
import { api, DONE, type Evidence, type Investigation, type Label } from "@/lib/api";

const STEPS = ["queued", "researching", "analyzing", "completed"] as const;
const FILTERS: (Label | "all")[] = ["all", "supports", "contradicts", "mixed", "insufficient"];

export default function InvestigationPage() {
  const { id } = useParams<{ id: string }>();
  const [inv, setInv] = useState<Investigation | null>(null);
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<Label | "all">("all");
  const [tab, setTab] = useState<"report" | "evidence">("report");

  useEffect(() => {
    let stop = false;
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const data = await api.get(id);
        if (stop) return;
        setInv(data);
        if (DONE.includes(data.status)) {
          const s = await api.sources(id);
          if (!stop) setEvidence(s.evidence);
          return;
        }
      } catch (e) {
        if (!stop) setError((e as Error).message);
      }
      timer = setTimeout(poll, 2000);
    }
    poll();
    return () => {
      stop = true;
      clearTimeout(timer);
    };
  }, [id]);

  // Map evidence ids to the [E1] labels used in the report.
  const citeIds = useMemo(() => {
    const m: Record<string, string> = {};
    inv?.report?.citations.forEach((c) => (m[c.evidence_id] = c.id));
    return m;
  }, [inv]);

  if (error && !inv) return <p className="text-rose-600">Error: {error}</p>;
  if (!inv) return <p className="text-slate-500">Loading…</p>;

  const done = DONE.includes(inv.status);
  const stepIndex = STEPS.indexOf(inv.status as (typeof STEPS)[number]);
  const shown = evidence.filter((e) => filter === "all" || e.label === filter);
  const subclaimText = Object.fromEntries(inv.subclaims.map((s) => [s.id, `${s.position + 1}. ${s.text}`]));

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs uppercase tracking-wide text-slate-500">Investigation #{inv.id}</p>
        <h1 className="mt-1 text-2xl font-bold">{inv.claim}</h1>
      </div>

      {!done && (
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <div className="flex gap-2">
            {STEPS.map((s, i) => (
              <div key={s} className="flex-1">
                <div className={`h-1.5 rounded ${i <= stepIndex ? "bg-indigo-600" : "bg-slate-200"} ${i === stepIndex ? "animate-pulse" : ""}`} />
                <p className="mt-1 text-xs capitalize text-slate-600">{s}</p>
              </div>
            ))}
          </div>
          {inv.subclaims.length > 0 && (
            <ul className="mt-4 list-disc pl-5 text-sm text-slate-600">
              {inv.subclaims.map((s) => <li key={s.id}>{s.text}</li>)}
            </ul>
          )}
        </div>
      )}

      {inv.status === "failed" && (
        <p className="rounded-lg bg-rose-50 p-4 text-rose-700">Investigation failed: {inv.error}</p>
      )}
      {inv.status === "partial" && (
        <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
          Some steps failed, so this report is based on partial evidence. See limitations.
        </p>
      )}

      {done && inv.report && (
        <>
          <div className="flex gap-4 border-b border-slate-200">
            {(["report", "evidence"] as const).map((t) => (
              <button key={t} onClick={() => setTab(t)}
                className={`-mb-px border-b-2 px-1 pb-2 text-sm font-medium capitalize ${
                  tab === t ? "border-indigo-600 text-indigo-700" : "border-transparent text-slate-500"}`}>
                {t}{t === "evidence" ? ` (${evidence.length})` : ""}
              </button>
            ))}
          </div>

          {tab === "report" && (
            <>
              <ReportView report={inv.report} markdownUrl={api.markdownUrl(inv.id)} />
              <section className="space-y-3">
                <h3 className="font-semibold">Cited evidence</h3>
                {evidence.filter((e) => citeIds[e.id]).map((e) => (
                  <EvidenceCard key={e.id} ev={e} citeId={citeIds[e.id]} />
                ))}
              </section>
            </>
          )}

          {tab === "evidence" && (
            <section className="space-y-3">
              <div className="flex flex-wrap gap-2">
                {FILTERS.map((f) => (
                  <button key={f} onClick={() => setFilter(f)}
                    className={`rounded-full px-3 py-1 text-xs capitalize ${
                      filter === f ? "bg-indigo-600 text-white" : "bg-slate-200 text-slate-700"}`}>
                    {f} ({f === "all" ? evidence.length : evidence.filter((e) => e.label === f).length})
                  </button>
                ))}
              </div>
              {shown.map((e) => (
                <div key={e.id}>
                  <p className="mb-1 text-xs text-slate-500">Subclaim {subclaimText[e.subclaim_id]}</p>
                  <EvidenceCard ev={e} citeId={citeIds[e.id]} />
                </div>
              ))}
              {shown.length === 0 && <p className="text-sm text-slate-500">No evidence in this category.</p>}
            </section>
          )}
        </>
      )}
    </div>
  );
}
