"""
Centralized literary context processor for SOL AI.
Extracts relevant verse lines, context snippets/windows, highlight offsets,
and expansion metadata from classical Tamil literary evidence.
"""

import re
from typing import List, Optional, Any
from backend.interpretation.schemas import HighlightOffset, LiteraryContextItem
from backend.schemas.evidence import Evidence


def extract_relevant_line(text: str, keywords: List[str]) -> str:
    """
    Extract the most relevant line or sentence containing the keyword from a literary passage.
    Falls back to the first line/sentence if no keywords match.
    """
    if not text:
        return ""

    # Split by standard sentence-ending punctuation or line breaks
    sentences = [
        s.strip()
        for s in re.split(r"(?:(?<=[.!?|])\s+|\r?\n+)", text)
        if s.strip()
    ]
    if not sentences:
        sentences = [text.strip()]

    valid_kws = [k.strip() for k in keywords if k and k.strip()]
    if valid_kws:
        for s in sentences:
            s_lower = s.lower()
            if any(k.lower() in s_lower for k in valid_kws):
                return s

    return sentences[0]


def build_context_window(
    matched_line: str, keywords: List[str], max_chars: int = 120
) -> str:
    """
    Build a focused context window around the keyword match if the line is excessively long.
    """
    if not matched_line:
        return ""

    if len(matched_line) <= max_chars:
        return matched_line

    valid_kws = [k.strip() for k in keywords if k and k.strip()]
    earliest_idx = -1
    matched_kw_len = 0

    if valid_kws:
        line_lower = matched_line.lower()
        for k in valid_kws:
            idx = line_lower.find(k.lower())
            if idx != -1 and (earliest_idx == -1 or idx < earliest_idx):
                earliest_idx = idx
                matched_kw_len = len(k)

    if earliest_idx > -1:
        start = max(0, earliest_idx - 40)
        end = min(len(matched_line), earliest_idx + matched_kw_len + 60)
        prefix = "... " if start > 0 else ""
        suffix = " ..." if end < len(matched_line) else ""
        return prefix + matched_line[start:end].strip() + suffix

    return matched_line[:max_chars].strip() + "..."


def compute_highlight_offsets(
    text: str, keywords: List[str]
) -> List[HighlightOffset]:
    """
    Find 0-based character offsets [start, end) for all occurrences of keywords within text.
    Longer keywords match first to prevent prefix shadowing.
    """
    if not text or not keywords:
        return []

    valid_kws = sorted(
        list(set(k.strip() for k in keywords if k and k.strip())),
        key=len,
        reverse=True,
    )
    if not valid_kws:
        return []

    pattern = "|".join(re.escape(k) for k in valid_kws)
    offsets: List[HighlightOffset] = []
    for m in re.finditer(pattern, text, re.IGNORECASE):
        offsets.append(HighlightOffset(start=m.start(), end=m.end()))

    return offsets


def process_literary_evidence(
    evidence_list: List[Any], query: str, lemma: Optional[str] = None
) -> List[LiteraryContextItem]:
    """
    Process a list of literary evidence items into structured, presentation-ready
    LiteraryContextItem models with normalized matched lines, snippets, highlights,
    relevance flags, and expansion metadata.
    """
    if not evidence_list:
        return []

    keywords = [query]
    if lemma and lemma != query:
        keywords.append(lemma)

    items: List[LiteraryContextItem] = []

    for idx, ev in enumerate(evidence_list):
        # Extract base fields from Evidence object, LiteraryContextItem, or dict
        if isinstance(ev, Evidence):
            work = ev.work or (ev.metadata.get("source_text") if ev.metadata else None)
            author = ev.author
            period = ev.period or (ev.metadata.get("period") if ev.metadata else None)
            passage = ev.passage or (ev.metadata.get("classical_tamil") if ev.metadata else "") or ""
            verse_number = str(ev.metadata.get("verse_number", ev.metadata.get("verse_id", ""))) if ev.metadata else ""
            meaning = ev.meaning or (ev.metadata.get("modern_tamil") if ev.metadata else None)
            source = ev.source or "Sentamizh"
        elif isinstance(ev, LiteraryContextItem):
            work = ev.work
            author = ev.author
            period = ev.period
            passage = ev.passage or ""
            verse_number = ev.verse_number or ""
            meaning = ev.meaning
            source = ev.source
        elif isinstance(ev, dict):
            work = ev.get("work")
            author = ev.get("author")
            period = ev.get("period")
            passage = ev.get("passage") or ev.get("quote") or ev.get("text_segment") or ""
            verse_number = str(ev.get("verse_number", ""))
            meaning = ev.get("meaning") or ev.get("translation")
            source = ev.get("source", "Sentamizh")
        else:
            work = getattr(ev, "work", None)
            author = getattr(ev, "author", None)
            period = getattr(ev, "period", None)
            passage = getattr(ev, "passage", "") or ""
            verse_number = str(getattr(ev, "verse_number", ""))
            meaning = getattr(ev, "meaning", None)
            source = getattr(ev, "source", "Sentamizh")

        passage_clean = passage.strip()

        # Extract relevant line and context window
        matched_line = extract_relevant_line(passage_clean, keywords)
        snippet = build_context_window(matched_line, keywords)

        # Highlight offsets for snippet and full passage
        snippet_offsets = compute_highlight_offsets(snippet, keywords)
        passage_offsets = compute_highlight_offsets(passage_clean, keywords)

        # Determine expandability and featured status
        can_expand = bool(
            len(passage_clean) > len(snippet) + 10 or "\n" in passage_clean
        )
        is_featured = (idx == 0)

        items.append(
            LiteraryContextItem(
                work=work,
                author=author,
                period=period,
                passage=passage_clean,
                verse_number=verse_number,
                meaning=meaning,
                source=source,
                matched_line=matched_line,
                snippet=snippet,
                highlight_offsets=snippet_offsets,
                passage_highlight_offsets=passage_offsets,
                is_featured=is_featured,
                can_expand=can_expand,
            )
        )

    return items
