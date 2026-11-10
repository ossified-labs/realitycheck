export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Status = "queued" | "researching" | "analyzing" | "completed" | "partial" | "failed";
export type Label = "supports" | "contradicts" | "mixed" | "insufficient";

export interface Subclaim {
  id: string;
  position: number;
  text: string;
  claim_type: string;
  qualifiers: Record<string, string>;
  queries: string[];
  verdict: string | null;
  verdict_reason: string | null;
}

export interface Investigation {
  id: string;
  claim: string;
  status: Status;
  error: string | null;
  verdict: string | null;
  created_at: string;
  subclaims: Subclaim[];
  report: Report | null;
}

export interface Evidence {
  id: string;
  subclaim_id: string;
  source_id: string;
  label: Label;
  passage: string;
  quote: string | null;
  quote_verified: number;
  explanation: string;
  evidence_type: string;
  shows_causation: number | null;
  relevance: number;
  url: string;
  title: string | null;
  domain: string;
  published_date: string | null;
  duplicate_of: string | null;
  injection_flag: number;
  snippet_only: number;
}

export interface CitedText {
  text: string;
  citations: string[];
  uncited: boolean;
}

export interface Report {
  claim: string;
  verdict: string;
  verdict_label: string;
  summary: string;
  subclaims: { position: number; text: string; verdict: string; verdict_label: string; reason: string }[];
  findings: CitedText[];
  conflicting_evidence: CitedText[];
  limitations: string[];
  citations: {
    id: string;
    evidence_id: string;
    url: string;
    title: string | null;
    domain: string;
    quote: string | null;
    label: Label;
    counted: boolean;
  }[];
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {}
    throw new Error(detail || `Request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  create: (claim: string) =>
    req<{ id: string; status: Status }>("/api/investigations", { method: "POST", body: JSON.stringify({ claim }) }),
  list: () => req<Pick<Investigation, "id" | "claim" | "status" | "verdict" | "created_at">[]>("/api/investigations"),
  get: (id: string) => req<Investigation>(`/api/investigations/${id}`),
  sources: (id: string) => req<{ evidence: Evidence[] }>(`/api/investigations/${id}/sources`),
  markdownUrl: (id: string) => `${API_URL}/api/investigations/${id}/report.md`,
};

export const DONE: Status[] = ["completed", "partial", "failed"];
