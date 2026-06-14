"""Lexical retrieval and bounded context rendering for memoryledger.

No embeddings in the MVP. Scoring follows the brief:

    score = 5 * title_matches + 3 * tag_matches + 1 * body_matches
            + status_boost + type_boost

with the suggested boost maps. Results are sorted by score descending, then
type boost, then updated_at descending, then id.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from memoryledger.config import RetrievalSection
from memoryledger.model import Memory, MemoryStatus, MemoryType

STATUS_BOOST: dict[str, int] = {
    "accepted": 10,
    "candidate": 0,
    "deprecated": -10,
    "rejected": -100,
}

TYPE_BOOST: dict[str, int] = {
    "rule": 4,
    "procedural": 3,
    "semantic": 2,
    "learning": 1,
    "episodic": 1,
    "local": 0,
}

# Default visibility: rejected and deprecated are hidden; local is hidden.
DEFAULT_HIDDEN_STATUSES: frozenset[str] = frozenset({"rejected", "deprecated"})


@dataclass(frozen=True)
class ScoredMemory:
    """A memory plus its computed search score and per-field match counts."""

    memory: Memory
    score: int
    title_matches: int
    tag_matches: int
    body_matches: int

    @property
    def type_boost(self) -> int:
        return TYPE_BOOST.get(self.memory.type.value, 0)

    @property
    def status_boost(self) -> int:
        return STATUS_BOOST.get(self.memory.status.value, 0)


# ---------------------------------------------------------------------------
# Tokenization
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Lowercase alphanumeric tokenization (MVP lexical search)."""
    return [t.lower() for t in _TOKEN_RE.findall(text or "")]


def _count_matches(needles: Sequence[str], haystack_tokens: set[str]) -> int:
    """Return how many distinct query tokens appear in the haystack token set."""
    if not needles:
        return 0
    return sum(1 for token in needles if token in haystack_tokens)


# ---------------------------------------------------------------------------
# Eligibility
# ---------------------------------------------------------------------------


def eligible_memories(
    memories: Iterable[Memory],
    *,
    include_candidates: bool = False,
    include_local: bool = False,
    include_deprecated: bool = False,
    include_rejected: bool = False,
) -> list[Memory]:
    """Filter memories by default visibility rules.

    Defaults match the brief: accepted only (plus accepted deprecated only if
    asked), candidates only with ``include_candidates``, local only with
    ``include_local``, rejected only with ``include_rejected``.
    """
    result: list[Memory] = []
    for mem in memories:
        status = mem.status
        if status == MemoryStatus.rejected and not include_rejected:
            continue
        if status == MemoryStatus.deprecated and not include_deprecated:
            continue
        if status == MemoryStatus.candidate and not include_candidates:
            continue
        if mem.type == MemoryType.local and not include_local:
            continue
        result.append(mem)
    return result


# ---------------------------------------------------------------------------
# Scoring + search
# ---------------------------------------------------------------------------


def score_memory(memory: Memory, query_tokens: Sequence[str]) -> ScoredMemory:
    """Score a single memory against query tokens."""
    title_tokens = set(tokenize(memory.title))
    tag_tokens = {t.lower() for t in memory.tags}
    body_tokens = set(tokenize(memory.body))

    title_matches = _count_matches(query_tokens, title_tokens)
    tag_matches = _count_matches(query_tokens, tag_tokens)
    body_matches = _count_matches(query_tokens, body_tokens)

    raw = (
        5 * title_matches
        + 3 * tag_matches
        + 1 * body_matches
        + STATUS_BOOST.get(memory.status.value, 0)
        + TYPE_BOOST.get(memory.type.value, 0)
    )
    return ScoredMemory(
        memory=memory,
        score=raw,
        title_matches=title_matches,
        tag_matches=tag_matches,
        body_matches=body_matches,
    )


def search(
    memories: Iterable[Memory],
    query: str,
    *,
    include_candidates: bool = False,
    include_local: bool = False,
    limit: int | None = None,
) -> list[ScoredMemory]:
    """Return scored, sorted search results.

    Sorting: score desc, type boost desc, updated_at desc, id asc.
    """
    tokens = tokenize(query)
    pool = eligible_memories(
        memories,
        include_candidates=include_candidates,
        include_local=include_local,
    )
    scored = [score_memory(mem, tokens) for mem in pool]
    # When the query is empty, retain all eligible memories ordered by
    # recency/type so ``list`` can reuse the same ordering.
    if tokens:
        scored = [s for s in scored if s.score != _neutral_score(s)]

    # Multi-key sort: highest score first, then type boost, then newest first,
    # then id ascending. Implement via stable sorts from last key to first.
    scored.sort(key=lambda s: s.memory.id)  # id ascending
    scored.sort(key=lambda s: s.memory.updated_at, reverse=True)  # newest first
    scored.sort(key=lambda s: TYPE_BOOST.get(s.memory.type.value, 0), reverse=True)
    scored.sort(key=lambda s: s.score, reverse=True)

    if limit is not None and limit >= 0:
        scored = scored[:limit]
    return scored


def _neutral_score(scored: ScoredMemory) -> int:
    """Return the boost-only score (title/tag/body all zero) for filtering."""
    return scored.status_boost + scored.type_boost


# ---------------------------------------------------------------------------
# Context rendering
# ---------------------------------------------------------------------------


def render_context(
    scored: Sequence[ScoredMemory],
    *,
    max_context_lines: int,
) -> str:
    """Render a bounded Markdown context bundle.

    Each entry shows the title and a snippet of the body. The whole bundle is
    truncated to ``max_context_lines`` lines total.
    """
    lines: list[str] = ["# Retrieved project memory", ""]
    if not scored:
        lines.append("_No matching accepted memory found._")
        return _truncate("\n".join(lines) + "\n", max_context_lines)

    for index, item in enumerate(scored, start=1):
        mem = item.memory
        heading = mem.title or mem.id
        lines.append(f"## {index}. {heading}")
        snippet = _snippet(mem.body, max_lines=max(1, max_context_lines // 6))
        if snippet:
            lines.append(snippet)
        lines.append("")
    return _truncate("\n".join(lines) + "\n", max_context_lines)


def render_context_from_query(
    memories: Iterable[Memory],
    query: str,
    *,
    retrieval: RetrievalSection,
    include_local: bool | None = None,
) -> str:
    """Convenience: filter, score, cap by default_limit, render bounded."""
    pool = eligible_memories(
        memories,
        include_candidates=False,
        include_local=include_local
        if include_local is not None
        else retrieval.include_local_by_default,
    )
    tokens = tokenize(query)
    scored = [score_memory(mem, tokens) for mem in pool]
    if tokens:
        scored = [s for s in scored if s.score != _neutral_score(s)]
    scored.sort(key=lambda s: s.memory.id)
    scored.sort(key=lambda s: s.memory.updated_at, reverse=True)
    scored.sort(key=lambda s: TYPE_BOOST.get(s.memory.type.value, 0), reverse=True)
    scored.sort(key=lambda s: s.score, reverse=True)
    scored = scored[: max(0, retrieval.default_limit)]
    return render_context(scored, max_context_lines=max(0, retrieval.max_context_lines))


def _snippet(body: str, *, max_lines: int) -> str:
    if not body:
        return ""
    lines = [ln for ln in body.splitlines() if ln.strip()]
    if not lines:
        return ""
    if max_lines <= 0:
        return lines[0]
    return "\n".join(lines[:max_lines])


def _truncate(text: str, max_lines: int) -> str:
    if max_lines <= 0:
        return ""
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text if text.endswith("\n") else text + "\n"
    truncated = "\n".join(lines[:max_lines])
    return truncated + "\n"


__all__ = [
    "DEFAULT_HIDDEN_STATUSES",
    "STATUS_BOOST",
    "ScoredMemory",
    "TYPE_BOOST",
    "eligible_memories",
    "render_context",
    "render_context_from_query",
    "score_memory",
    "search",
    "tokenize",
]
