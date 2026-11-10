# RealityCheck — AI Claim Investigation Engine

RealityCheck investigates a claim and **shows how it reached its conclusion**. It breaks the claim into testable subclaims, searches the web, checks every quote against the page it came from, classifies the evidence, and writes a report where each statement links back to retrieved evidence.

This is the first milestone: one claim → up to 5 sources per subclaim → classified evidence → cited report, with a minimal dashboard.

## How it works

```
claim ─► decompose (Claude) ─► search (Tavily) ─► rank passages (BM25) ─► dedupe
      ─► classify each source (Claude, quote must be verbatim) ─► verdicts (fixed rules)
      ─► report (Claude writes prose; citations are validated)
```

Status lifecycle: `queued → researching → analyzing → completed`, plus `partial` and `failed`.

### Traceability safeguards

| Risk | What the code does | Where |
|---|---|---|
| Invented citations | The report may only cite `E1…En` evidence IDs. Unknown IDs are stripped, and statements left without a citation are marked `uncited`. | `services/report.py` |
| Made-up or paraphrased quotes | A *supports* or *contradicts* label needs a quote that appears verbatim in the retrieved passage. Otherwise the label drops to *insufficient*. | `services/evidence.py`, `text.quote_in_passage` |
| Treating snippets as proof | Results that only came back as a search snippet are shown but don't count toward a verdict. | `counts_toward_verdict` |
| Prompt injection in pages | Page text is wrapped as untrusted data with tags neutralised. Pages that look like AI instructions are flagged and excluded from verdicts. | `text.looks_like_injection`, `sanitize_untrusted` |
| Duplicate reports counted twice | URLs are canonicalised and near-duplicate text is detected (5-gram Jaccard). Each domain counts once per direction. | `retrieve_candidates`, `subclaim_verdict` |
| Correlation vs causation | Subclaims are typed. A causal claim backed only by observational evidence gets *Association found, causation not established*. | `subclaim_verdict` |
| Overconfidence | Verdicts come from fixed rules over the labels, not from the model. With no usable evidence the result is *Insufficient evidence*. | `subclaim_verdict`, `overall_verdict` |

## Run it locally

**Backend** (Python 3.11+)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=... TAVILY_API_KEY=...   # see ../.env.example
uvicorn app.main:app --reload --port 8000
```

**Frontend** (Node 20+)

```bash
cd frontend
npm install
cp .env.local.example .env.local      # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev                            # http://localhost:3000
```

**Tests** (offline: fake LLM and search, real pipeline and database)

```bash
cd backend && python -m pytest -q
```

## API

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/investigations` | Start an investigation `{ "claim": "..." }` → `{ id, status }` |
| GET | `/api/investigations` | Recent investigations |
| GET | `/api/investigations/{id}` | Status, subclaims and report |
| GET | `/api/investigations/{id}/sources` | Sources plus classified evidence |
| GET | `/api/investigations/{id}/graph` | Nodes and edges for React Flow |
| GET | `/api/investigations/{id}/report` | Structured report (JSON) |
| GET | `/api/investigations/{id}/report.md` | Markdown export |
| GET | `/api/health` | Shows whether the API keys are configured |

## Layout

```
backend/app/
  main.py               FastAPI routes, validation, rate limit, background job
  config.py             env settings
  database.py           SQLite schema + queries (stdlib sqlite3)
  services/
    llm.py              Claude wrapper (structured JSON via forced tool use)
    search.py           Tavily client, URL canonicalisation
    text.py             passages, BM25, dedupe, quote check, injection heuristics
    claim_parser.py     decomposition
    evidence.py         retrieval, classification, verdict rules
    report.py           cited report, citation validation, markdown export
    pipeline.py         orchestration + graph builder
backend/tests/          offline tests
frontend/               Next.js 15 + Tailwind: claim form, history, live status, report, evidence filters
```

## Next steps (roadmap weeks 2–4)

- **Evidence graph:** add `reactflow` and render `/graph` (the endpoint already returns nodes and edges).
- **Better ranking:** swap `bm25_rank` for sentence-transformers embeddings behind the same function signature.
- **Evaluation:** run the pipeline on a labeled set such as AVeriTeC and measure label accuracy, citation accuracy (quote-verified rate) and how often it correctly abstains.
- **Production:** PostgreSQL in place of SQLite (only `database.py` changes), Redis + RQ in place of `BackgroundTasks`, per-user rate limits once there is auth.
