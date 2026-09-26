from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Protocol


def sanitize_untrusted_content(content: str) -> str:
    """Sanitizes external web content to prevent prompt injection and system instruction hijacking.

    Wraps untrusted content in strict demarcation tags and escapes potential closing tags or system prompt exploits.
    """
    if not content:
        return "<untrusted_content></untrusted_content>"

    cleaned = content.replace("</untrusted_content>", "&lt;/untrusted_content&gt;")
    cleaned = cleaned.replace("<|im_end|>", "").replace("<|im_start|>", "")
    cleaned = cleaned.replace("SYSTEM_INSTRUCTION:", "[REDACTED_SYSTEM_LABEL]")

    return f"<untrusted_content>\n{cleaned.strip()}\n</untrusted_content>"


@dataclass(frozen=True, slots=True)
class DecomposedQuery:
    original_topic: str
    sub_queries: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_topic": self.original_topic,
            "sub_queries": list(self.sub_queries),
        }


class QueryDecomposer:
    """Decomposes complex research topics into targeted search queries."""

    def decompose(self, topic: str, max_queries: int = 3) -> DecomposedQuery:
        cleaned = topic.strip()
        if not cleaned:
            return DecomposedQuery(original_topic="", sub_queries=())

        queries: list[str] = [cleaned]

        words = cleaned.split()
        if len(words) > 3:
            queries.append(f"{cleaned} key facts evidence")
            queries.append(f"{cleaned} comparison analysis")

        unique_queries = tuple(dict.fromkeys(queries[:max_queries]))
        return DecomposedQuery(original_topic=cleaned, sub_queries=unique_queries)


@dataclass(frozen=True, slots=True)
class SearchResult:
    title: str
    url: str
    snippet: str
    score: float = 1.0


@dataclass(frozen=True, slots=True)
class FetchedDocument:
    url: str
    title: str
    content: str
    content_hash: str = field(init=False)

    def __post_init__(self) -> None:
        hash_val = hashlib.sha256(f"{self.url}:{self.content}".encode()).hexdigest()
        object.__setattr__(self, "content_hash", hash_val)


class SearchProvider(Protocol):
    def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        ...


class FetchProvider(Protocol):
    def fetch(self, url: str) -> FetchedDocument:
        ...


class MockSearchProvider:
    """Mock search provider for testing and deterministic research execution."""

    def __init__(self, mock_results: dict[str, list[SearchResult]] | None = None) -> None:
        self._mock_results = mock_results or {}

    def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        if query in self._mock_results:
            return self._mock_results[query][:limit]
        return [
            SearchResult(
                title=f"Result for {query}",
                url=f"https://example.com/search?q={hashlib.md5(query.encode()).hexdigest()[:8]}",
                snippet=f"Synthetic research evidence snippet regarding {query}.",
                score=0.9,
            )
        ][:limit]


class MockFetchProvider:
    """Mock page fetch provider."""

    def __init__(self, mock_pages: dict[str, str] | None = None) -> None:
        self._mock_pages = mock_pages or {}

    def fetch(self, url: str) -> FetchedDocument:
        if url in self._mock_pages:
            content = self._mock_pages[url]
            return FetchedDocument(url=url, title=f"Page at {url}", content=content)
        return FetchedDocument(
            url=url,
            title=f"Page at {url}",
            content=f"Detailed fetched web content from {url}. Contains research facts.",
        )


@dataclass
class EvidenceItem:
    id: str
    source_url: str
    title: str
    text: str
    relevance_score: float = 1.0
    sanitized_text: str = field(default="", init=False)

    def __post_init__(self) -> None:
        if not self.sanitized_text:
            self.sanitized_text = sanitize_untrusted_content(self.text)


class EvidenceStore:
    """In-memory store for research evidence with deduplication, ranking, and contradiction checking."""

    def __init__(self) -> None:
        self._items: dict[str, EvidenceItem] = {}
        self._url_index: set[str] = set()

    def add_evidence(self, item: EvidenceItem) -> bool:
        """Adds evidence item if not already present by ID or URL duplicate."""
        if item.id in self._items or item.source_url in self._url_index:
            return False
        self._items[item.id] = item
        self._url_index.add(item.source_url)
        return True

    def get_ranked_evidence(self, min_score: float = 0.0) -> list[EvidenceItem]:
        """Returns evidence items sorted by relevance score descending."""
        items = [item for item in self._items.values() if item.relevance_score >= min_score]
        return sorted(items, key=lambda x: x.relevance_score, reverse=True)

    def detect_contradictions(self) -> list[dict[str, Any]]:
        """Scans evidence store for opposing statements or contradictions."""
        items = list(self._items.values())
        contradictions: list[dict[str, Any]] = []

        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                item_a, item_b = items[i], items[j]
                text_a, text_b = item_a.text.lower(), item_b.text.lower()
                if ("not " in text_a and "not " not in text_b) or ("not " in text_b and "not " not in text_a):
                    words_a = set(re.findall(r"\w+", text_a))
                    words_b = set(re.findall(r"\w+", text_b))
                    shared = words_a.intersection(words_b) - {
                        "not", "the", "a", "is", "are", "in", "of", "and", "or", "for", "to", "this", "that"
                    }
                    if len(shared) >= 2:
                        contradictions.append({
                            "evidence_a": item_a.id,
                            "evidence_b": item_b.id,
                            "reason": f"Potential contradiction between evidence '{item_a.title}' and '{item_b.title}'.",
                            "shared_keywords": sorted(shared),
                        })
        return contradictions

    def clear(self) -> None:
        self._items.clear()
        self._url_index.clear()


@dataclass(frozen=True, slots=True)
class ResearchReport:
    topic: str
    decomposed_query: DecomposedQuery
    evidence: tuple[EvidenceItem, ...]
    contradictions: tuple[dict[str, Any], ...]
    summary: str
    citations: tuple[dict[str, str], ...]


class ResearchEngine:
    """Coordinates search, page fetching, evidence storage, contradiction checks, and report generation."""

    def __init__(
        self,
        search_provider: SearchProvider | None = None,
        fetch_provider: FetchProvider | None = None,
    ) -> None:
        self.search_provider = search_provider or MockSearchProvider()
        self.fetch_provider = fetch_provider or MockFetchProvider()

    def research(self, topic: str, max_pages: int = 3) -> ResearchReport:
        decomposer = QueryDecomposer()
        decomposed = decomposer.decompose(topic)

        store = EvidenceStore()
        item_counter = 1

        for query in decomposed.sub_queries:
            results = self.search_provider.search(query, limit=2)
            for res in results[:max_pages]:
                doc = self.fetch_provider.fetch(res.url)
                evidence_id = f"EV-{item_counter:03d}"
                item = EvidenceItem(
                    id=evidence_id,
                    source_url=doc.url,
                    title=res.title or doc.title,
                    text=f"{res.snippet}\n{doc.content}",
                    relevance_score=res.score,
                )
                if store.add_evidence(item):
                    item_counter += 1

        ranked_evidence = tuple(store.get_ranked_evidence())
        contradictions = tuple(store.detect_contradictions())

        citations = tuple(
            {"id": item.id, "title": item.title, "url": item.source_url}
            for item in ranked_evidence
        )

        summary_lines = [f"### Research Report: {topic}", ""]
        if ranked_evidence:
            summary_lines.append("#### Evidence Summary:")
            for item in ranked_evidence:
                summary_lines.append(
                    f"- [{item.id}] {item.title}: {item.text[:150].strip()}... (Source: {item.source_url})"
                )
        else:
            summary_lines.append("No evidence found.")

        if contradictions:
            summary_lines.append("")
            summary_lines.append("#### Contradiction Warnings:")
            for c in contradictions:
                summary_lines.append(f"- Warning: {c['reason']}")

        summary = "\n".join(summary_lines)

        return ResearchReport(
            topic=topic,
            decomposed_query=decomposed,
            evidence=ranked_evidence,
            contradictions=contradictions,
            summary=summary,
            citations=citations,
        )
