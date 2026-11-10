const STYLES: Record<string, string> = {
  supported: "bg-emerald-100 text-emerald-800 ring-emerald-300",
  weakly_supported: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  partially_supported: "bg-lime-50 text-lime-800 ring-lime-200",
  association_only: "bg-amber-50 text-amber-800 ring-amber-200",
  mixed: "bg-amber-100 text-amber-900 ring-amber-300",
  contradicted: "bg-rose-100 text-rose-800 ring-rose-300",
  weakly_contradicted: "bg-rose-50 text-rose-700 ring-rose-200",
  insufficient: "bg-slate-100 text-slate-700 ring-slate-300",
  supports: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  contradicts: "bg-rose-50 text-rose-700 ring-rose-200",
};

const NAMES: Record<string, string> = {
  supported: "Supported",
  weakly_supported: "Weakly supported",
  partially_supported: "Partially supported",
  association_only: "Association only",
  mixed: "Mixed",
  contradicted: "Contradicted",
  weakly_contradicted: "Weakly contradicted",
  insufficient: "Insufficient",
  supports: "Supports",
  contradicts: "Contradicts",
};

export default function VerdictBadge({ value, large = false }: { value: string | null; large?: boolean }) {
  const v = value ?? "insufficient";
  return (
    <span
      className={`inline-flex items-center rounded-full ring-1 font-medium ${STYLES[v] ?? STYLES.insufficient} ${
        large ? "px-3 py-1 text-sm" : "px-2 py-0.5 text-xs"
      }`}
    >
      {NAMES[v] ?? v}
    </span>
  );
}
