import type { Evidence } from "@/lib/api";
import VerdictBadge from "./VerdictBadge";

export default function EvidenceCard({ ev, citeId }: { ev: Evidence; citeId?: string }) {
  const flags: string[] = [];
  if (ev.duplicate_of) flags.push("Near-duplicate");
  if (ev.injection_flag) flags.push("Suspicious instructions in page");
  if (ev.snippet_only) flags.push("Snippet only");
  if (ev.quote && !ev.quote_verified) flags.push("Quote not found in source");

  return (
    <article id={citeId} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <a href={ev.url} target="_blank" rel="noopener noreferrer"
             className="block truncate font-medium text-indigo-700 hover:underline">
            {citeId && <span className="mr-1 text-slate-500">[{citeId}]</span>}
            {ev.title || ev.domain}
          </a>
          <p className="text-xs text-slate-500">
            {ev.domain}
            {ev.published_date ? ` · ${ev.published_date.slice(0, 10)}` : ""} · {ev.evidence_type.replace(/_/g, " ")}
          </p>
        </div>
        <VerdictBadge value={ev.label} />
      </div>
      {ev.quote && (
        <blockquote className="mt-3 border-l-4 border-slate-300 pl-3 text-sm italic text-slate-700">
          “{ev.quote}”
        </blockquote>
      )}
      <p className="mt-2 text-sm text-slate-600">{ev.explanation}</p>
      {flags.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {flags.map((f) => (
            <span key={f} className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600">{f}</span>
          ))}
        </div>
      )}
    </article>
  );
}
