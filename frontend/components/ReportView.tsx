import type { CitedText, Report } from "@/lib/api";
import VerdictBadge from "./VerdictBadge";

function Cites({ item }: { item: CitedText }) {
  if (item.uncited) return <span className="ml-1 text-xs text-amber-700">(uncited)</span>;
  return (
    <>
      {item.citations.map((c) => (
        <a key={c} href={`#${c}`} className="ml-1 text-xs font-medium text-indigo-600 hover:underline">[{c}]</a>
      ))}
    </>
  );
}

export default function ReportView({ report, markdownUrl }: { report: Report; markdownUrl: string }) {
  return (
    <section className="space-y-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <VerdictBadge value={report.verdict} large />
        <a href={markdownUrl} className="text-sm text-indigo-600 hover:underline" download>
          Export report (.md)
        </a>
      </div>
      <p className="text-lg leading-relaxed">{report.summary}</p>

      <div>
        <h3 className="mb-2 font-semibold">Subclaims</h3>
        <ol className="space-y-2">
          {report.subclaims.map((s) => (
            <li key={s.position} className="rounded-lg bg-slate-50 p-3">
              <div className="flex items-start justify-between gap-3">
                <span>{s.position + 1}. {s.text}</span>
                <VerdictBadge value={s.verdict} />
              </div>
              <p className="mt-1 text-xs text-slate-500">{s.reason}</p>
            </li>
          ))}
        </ol>
      </div>

      {report.findings.length > 0 && (
        <div>
          <h3 className="mb-2 font-semibold">Findings</h3>
          <ul className="list-disc space-y-1 pl-5">
            {report.findings.map((f, i) => <li key={i}>{f.text}<Cites item={f} /></li>)}
          </ul>
        </div>
      )}

      {report.conflicting_evidence.length > 0 && (
        <div>
          <h3 className="mb-2 font-semibold">Conflicting evidence</h3>
          <ul className="list-disc space-y-1 pl-5">
            {report.conflicting_evidence.map((f, i) => <li key={i}>{f.text}<Cites item={f} /></li>)}
          </ul>
        </div>
      )}

      <div>
        <h3 className="mb-2 font-semibold">Limitations</h3>
        <ul className="list-disc space-y-1 pl-5 text-sm text-slate-600">
          {report.limitations.map((l, i) => <li key={i}>{l}</li>)}
        </ul>
      </div>
    </section>
  );
}
