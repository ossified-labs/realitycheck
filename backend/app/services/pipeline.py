"""Orchestrates one investigation: queued -> researching -> analyzing -> completed | partial | failed."""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

from ..config import Settings
from ..database import Database
from .claim_parser import decompose_claim
from .evidence import classify, overall_verdict, retrieve_candidates, subclaim_verdict
from .llm import LLM
from .report import build_report
from .search import SearchProvider

log = logging.getLogger("realitycheck.pipeline")


def run_investigation(db: Database, llm: LLM, search: SearchProvider, settings: Settings, inv_id: str) -> None:
    inv = db.get_investigation(inv_id)
    if not inv:
        return
    claim = inv["claim"]
    problems: list[str] = []
    try:
        # 1. Decompose ----------------------------------------------------
        db.set_status(inv_id, "researching")
        dec = decompose_claim(llm, claim, settings.max_subclaims, settings.queries_per_subclaim)
        if not dec.is_checkable:
            report = build_report(None, claim, [], [], "insufficient")
            report["summary"] = f"This claim can't be fact-checked as stated: {dec.not_checkable_reason}"
            db.save_report(inv_id, "insufficient", report)
            db.set_status(inv_id, "completed")
            return

        sc_ids = [
            db.add_subclaim(inv_id, i, sc.text, sc.claim_type, sc.qualifiers, sc.search_queries)
            for i, sc in enumerate(dec.subclaims)
        ]

        # 2. Retrieve -----------------------------------------------------
        work = []  # (subclaim, subclaim_id, candidate, source_id)
        for sc, sc_id in zip(dec.subclaims, sc_ids):
            try:
                cands = retrieve_candidates(search, sc.text, sc.search_queries,
                                            settings.results_per_query, settings.sources_per_subclaim)
            except Exception as exc:  # one failed search should not sink the investigation
                log.exception("search failed")
                problems.append(f"Search failed for subclaim {sc.text!r}: {exc}")
                continue
            url_to_src: dict[str, str] = {}
            for c in cands:
                src_id = db.add_source(
                    inv_id, url=c.result.url, canonical_url=c.canonical_url, title=c.result.title,
                    domain=c.domain, published_date=c.result.published_date,
                    content=c.result.content[:20000],
                    duplicate_of=url_to_src.get(c.duplicate_of_url) if c.duplicate_of_url else None,
                    injection_flag=c.injection_flag, snippet_only=c.result.is_snippet_only,
                )
                url_to_src[c.canonical_url] = src_id
                work.append((sc, sc_id, c, src_id))

        # 3. Classify -----------------------------------------------------
        db.set_status(inv_id, "analyzing")

        def _do(item):
            sc, sc_id, cand, src_id = item
            try:
                return item, classify(llm, sc.text, sc.claim_type, cand), None
            except Exception as exc:
                return item, None, exc

        with ThreadPoolExecutor(max_workers=4) as pool:
            for (sc, sc_id, cand, src_id), cls, err in pool.map(_do, work):
                if err or cls is None:
                    problems.append(f"Could not classify {cand.result.url}: {err}")
                    continue
                db.add_evidence(inv_id, sc_id, src_id, label=cls.label, passage=cls.passage,
                                quote=cls.quote, quote_verified=cls.quote_verified,
                                explanation=cls.explanation, evidence_type=cls.evidence_type,
                                shows_causation=cls.shows_causation, relevance=cand.relevance)

        # 4. Verdicts (deterministic) ------------------------------------
        evidence = db.get_evidence(inv_id)
        subclaims = db.get_subclaims(inv_id)
        for s in subclaims:
            v, reason = subclaim_verdict([e for e in evidence if e["subclaim_id"] == s["id"]], s["claim_type"])
            db.set_subclaim_verdict(s["id"], v, reason)
        subclaims = db.get_subclaims(inv_id)
        overall = overall_verdict([s["verdict"] for s in subclaims])

        # 5. Report -------------------------------------------------------
        report = build_report(llm, claim, subclaims, evidence, overall)
        if problems:
            report["limitations"] = problems + report["limitations"]
        db.save_report(inv_id, overall, report)
        db.set_status(inv_id, "partial" if problems else "completed")
    except Exception as exc:
        log.exception("investigation %s failed", inv_id)
        db.set_status(inv_id, "failed", error=str(exc)[:500])


def build_graph(db: Database, inv_id: str) -> dict:
    """Nodes/edges in React Flow-friendly shape: claim -> subclaims -> sources (edge label = stance)."""
    inv = db.get_investigation(inv_id)
    if not inv:
        return {"nodes": [], "edges": []}
    nodes = [{"id": "claim", "type": "claim", "data": {"label": inv["claim"], "verdict": inv.get("verdict")}}]
    edges = []
    for s in db.get_subclaims(inv_id):
        nid = f"sc-{s['id']}"
        nodes.append({"id": nid, "type": "subclaim", "data": {"label": s["text"], "verdict": s.get("verdict")}})
        edges.append({"id": f"e-claim-{nid}", "source": "claim", "target": nid})
    seen_src = set()
    for e in db.get_evidence(inv_id):
        sid = f"src-{e['source_id']}"
        if sid not in seen_src:
            seen_src.add(sid)
            nodes.append({"id": sid, "type": "source",
                          "data": {"label": e.get("title") or e["domain"], "url": e["url"], "domain": e["domain"],
                                   "duplicate_of": e.get("duplicate_of"), "flagged": bool(e.get("injection_flag"))}})
        edges.append({"id": f"e-{e['id']}", "source": f"sc-{e['subclaim_id']}", "target": sid,
                      "label": e["label"], "data": {"quote": e.get("quote"), "verified": bool(e["quote_verified"])}})
    return {"nodes": nodes, "edges": edges}
