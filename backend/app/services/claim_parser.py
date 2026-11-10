"""Step 1: break a claim into testable subclaims and search queries."""
from __future__ import annotations

from dataclasses import dataclass, field

from .llm import LLM

CLAIM_TYPES = ["causal", "correlational", "descriptive", "quantitative", "comparative", "other"]

SYSTEM = """You are the claim-analysis stage of a fact-checking system.
Break the user's claim into the smallest set of independently verifiable subclaims.
Rules:
- Preserve every qualifier: population (who), timeframe (when/how long), measure (what outcome),
  and the strength of the relationship. Do not broaden or soften the claim.
- Mark claim_type = "causal" whenever the claim says or implies X causes, improves, prevents,
  reduces or leads to Y. Use "correlational" only when the claim itself is about an association.
- If the claim is pure opinion, a prediction, or too vague to test, set is_checkable=false and explain.
- Write search queries a careful researcher would use: neutral wording (do not presuppose the answer),
  include at least one query aimed at disconfirming evidence, and prefer terms that surface primary
  research, systematic reviews or official statistics."""

SCHEMA = {
    "type": "object",
    "properties": {
        "is_checkable": {"type": "boolean"},
        "not_checkable_reason": {"type": "string"},
        "subclaims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Self-contained, testable statement"},
                    "claim_type": {"type": "string", "enum": CLAIM_TYPES},
                    "qualifiers": {
                        "type": "object",
                        "properties": {
                            "population": {"type": "string"},
                            "timeframe": {"type": "string"},
                            "measure": {"type": "string"},
                        },
                    },
                    "search_queries": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["text", "claim_type", "search_queries"],
            },
        },
    },
    "required": ["is_checkable", "subclaims"],
}


@dataclass
class Subclaim:
    text: str
    claim_type: str
    qualifiers: dict = field(default_factory=dict)
    search_queries: list[str] = field(default_factory=list)


@dataclass
class Decomposition:
    is_checkable: bool
    subclaims: list[Subclaim]
    not_checkable_reason: str = ""


def decompose_claim(llm: LLM, claim: str, max_subclaims: int, queries_per_subclaim: int) -> Decomposition:
    out = llm.structured(
        system=SYSTEM,
        prompt=f"Claim to analyse:\n<claim>\n{claim}\n</claim>\n\n"
               f"Return at most {max_subclaims} subclaims and {queries_per_subclaim} search queries each.",
        tool_name="claim_decomposition",
        schema=SCHEMA,
    )
    subclaims = []
    for item in (out.get("subclaims") or [])[:max_subclaims]:
        text = (item.get("text") or "").strip()
        if not text:
            continue
        ctype = item.get("claim_type") if item.get("claim_type") in CLAIM_TYPES else "other"
        queries = [q.strip() for q in item.get("search_queries") or [] if q and q.strip()]
        subclaims.append(Subclaim(
            text=text,
            claim_type=ctype,
            qualifiers={k: v for k, v in (item.get("qualifiers") or {}).items() if v},
            search_queries=(queries or [text])[:queries_per_subclaim],
        ))
    checkable = bool(out.get("is_checkable")) and bool(subclaims)
    return Decomposition(
        is_checkable=checkable,
        subclaims=subclaims if checkable else [],
        not_checkable_reason=out.get("not_checkable_reason") or ("" if checkable else "No testable subclaims found."),
    )
