"""Web search via Tavily, plus URL canonicalisation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_PARAMS = {"fbclid", "gclid", "mc_cid", "mc_eid", "ref", "ref_src", "igshid"}


@dataclass
class SearchResult:
    url: str
    title: str
    content: str               # best available text (raw page text if we got it, else snippet)
    is_snippet_only: bool      # True when we only have the search engine's snippet
    published_date: str | None = None
    score: float = 0.0


class SearchProvider(Protocol):
    def search(self, query: str, max_results: int) -> list[SearchResult]: ...


class TavilySearch:
    URL = "https://api.tavily.com/search"

    def __init__(self, api_key: str, timeout: float = 30.0):
        if not api_key:
            raise RuntimeError("TAVILY_API_KEY is not set")
        self.api_key = api_key
        self.timeout = timeout

    def search(self, query: str, max_results: int) -> list[SearchResult]:
        import httpx  # lazy import

        resp = httpx.post(
            self.URL,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "query": query,
                "search_depth": "advanced",
                "max_results": max_results,
                "include_raw_content": True,
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        out: list[SearchResult] = []
        for r in resp.json().get("results", []):
            raw = (r.get("raw_content") or "").strip()
            out.append(SearchResult(
                url=r.get("url", ""),
                title=r.get("title") or "",
                content=raw or (r.get("content") or ""),
                is_snippet_only=not raw,
                published_date=r.get("published_date"),
                score=float(r.get("score") or 0.0),
            ))
        return out


def canonicalize_url(url: str) -> str:
    """Normalise a URL so the same page reached via different links dedupes."""
    parts = urlsplit(url.strip())
    host = parts.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    if host.startswith("m."):
        host = host[2:]
    query = urlencode(sorted(
        (k, v) for k, v in parse_qsl(parts.query)
        if not k.lower().startswith("utm_") and k.lower() not in TRACKING_PARAMS
    ))
    path = parts.path.rstrip("/") or "/"
    return urlunsplit(("https", host, path, query, ""))


def domain_of(url: str) -> str:
    host = urlsplit(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host
