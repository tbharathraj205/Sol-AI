"""
Pydantic schemas and dataclasses for the SOL AI Contextual Interpretation Layer.
"""

from typing import List, Dict, Any, Optional, Union, Set, Tuple
from pydantic import BaseModel, Field
from backend.schemas.evidence import Evidence


class HighlightOffset(BaseModel):
    """Character offsets [start, end) within text for highlighting."""

    start: int = Field(description="0-based start character index (inclusive)")
    end: int = Field(description="0-based end character index (exclusive)")


class LiteraryContextItem(BaseModel):
    """Represents a single selected literary context occurrence with structured context."""

    work: Optional[str] = Field(default=None, description="Name of the literary work (e.g. Kuruntokai)")
    author: Optional[str] = Field(default=None, description="Author if available")
    period: Optional[str] = Field(default=None, description="Historical period (e.g. Sangam)")
    passage: Optional[str] = Field(default=None, description="Classical Tamil verse or passage")
    verse_number: Optional[str] = Field(default=None, description="Verse or line number")
    meaning: Optional[str] = Field(default=None, description="Modern Tamil translation or meaning")
    source: str = Field(default="Sentamizh", description="Source corpus name")

    # Phase 3: Centralized Context & Snippet Processing
    matched_line: Optional[str] = Field(default=None, description="Specific line/sentence containing the keyword match")
    snippet: Optional[str] = Field(default=None, description="Presentation-ready contextual snippet/window")
    highlight_offsets: List[HighlightOffset] = Field(default_factory=list, description="Highlight offsets within snippet")
    passage_highlight_offsets: List[HighlightOffset] = Field(default_factory=list, description="Highlight offsets within full passage")
    is_featured: bool = Field(default=False, description="True if this occurrence is top-ranked / featured")
    can_expand: bool = Field(default=False, description="True if passage offers additional context beyond snippet")


class LexicalSenseItem(BaseModel):
    """Represents a single structured lexical sense/meaning."""

    sense_number: int = Field(description="1-based index of the sense")
    title: str = Field(description="Title or short summary of the sense")
    description: Optional[str] = Field(default=None, description="Detailed explanation or gloss if available")
    english_translation: Optional[str] = Field(default=None, description="English translation if available")
    raw_text: Optional[str] = Field(default=None, description="Full raw sense text")


class SenseCandidate(BaseModel):
    """
    Structured candidate sense representation for contextual WSD.
    Preserves resource provenance, headword, POS, definition gloss,
    English translation, and raw text.
    """
    source: str = Field(default="", description="Contributing resource name (e.g. Tamil Wiktionary, Thani Thamizh Akarathi)")
    headword: str = Field(description="Headword/lemma for this sense")
    definition: str = Field(description="Tamil definition or gloss text")
    english_meaning: Optional[str] = Field(default=None, description="English translation if available")
    pos: Optional[str] = Field(default=None, description="Part of speech if available")
    raw_text: Optional[str] = Field(default=None, description="Full raw sense text as received from source")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Source provenance and metadata")
    sense_id: Optional[str] = Field(default=None, description="Stable identifier for the candidate")

    @property
    def gloss(self) -> str:
        return self.definition


class CandidateScore(BaseModel):
    """
    Evaluated scoring record for a candidate sense during WSD.
    """
    candidate: SenseCandidate
    score: float = Field(description="Deterministic evidence strength score")
    reasons: List[str] = Field(default_factory=list, description="Scoring breakdown signals")
    formatted_text: Optional[str] = Field(default=None, description="Contextual formatted text if applicable")


class WSDResult(BaseModel):
    """
    Authoritative result of deterministic Word-Sense Disambiguation.
    Retains selected candidate, formatted sense text, evidence strength score,
    confidence level, status, explanation reasons, and competing candidate scores.
    """
    query: str = Field(description="Target query word")
    context: Optional[str] = Field(default=None, description="Surrounding context sentence")
    selected_candidate: Optional[SenseCandidate] = Field(default=None, description="Selected winning sense candidate")
    selected_sense: Optional[str] = Field(default=None, description="Final selected contextual sense text")
    score: float = Field(default=0.0, description="Raw deterministic evidence strength score of selected sense")
    status: str = Field(
        default="no_context",
        description="Disambiguation status: 'selected', 'no_context', 'insufficient_evidence', 'ambiguous', 'conflicting_signals', 'single_sense'"
    )
    confidence: str = Field(
        default="none",
        description="Categorical confidence level: 'high', 'medium', 'low', 'none'"
    )
    reasons: List[str] = Field(default_factory=list, description="Explanatory reasons for selection or abstention")
    candidates: List[CandidateScore] = Field(default_factory=list, description="All evaluated candidate senses with scores and reasons")

    def __iter__(self):
        """Allow backwards-compatible unpacking as (selected_sense, score, reasons)."""
        return iter((self.selected_sense, self.score, self.reasons))


class MorphemeSegment(BaseModel):
    """Represents a single morpheme segment breakdown."""

    tamil: str = Field(description="Tamil surface segment or word")
    latin: str = Field(default="", description="Transliteration if available")
    role: str = Field(default="", description="Grammatical role or tag sequence")


class StructuredMorphology(BaseModel):
    """Structured morphology representation produced by backend linguistic parsing."""

    pos: Optional[str] = Field(default=None, description="Part of speech (e.g. noun, verb)")
    case: Optional[str] = Field(default=None, description="Grammatical case (e.g. Nominative, Locative)")
    number: Optional[str] = Field(default=None, description="Grammatical number (e.g. Singular, Plural)")
    tense: Optional[str] = Field(default=None, description="Grammatical tense (e.g. Past, Present, Future)")
    analysis_type: str = Field(default="core", description="FST analysis type: 'core', 'guesser', or 'lexical_mapping'")
    fst_model: Optional[str] = Field(default=None, description="Name of the matching FST model file")
    raw_morphology: Optional[str] = Field(default=None, description="Original raw FST morphology tag sequence")
    segments: List[MorphemeSegment] = Field(default_factory=list, description="Morpheme breakdown segments")

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def __contains__(self, item: str) -> bool:
        return hasattr(self, item) and getattr(self, item) is not None


def build_lexical_senses(
    meanings: List[str],
    english_meanings: Optional[List[str]] = None,
) -> List[LexicalSenseItem]:
    """
    Build structured LexicalSenseItem objects from distinct lexical meaning strings.
    Extracts title and description if separated by standard punctuation ('—', '-', ':').
    """
    import re
    senses: List[LexicalSenseItem] = []
    for idx, raw_sense in enumerate(meanings):
        clean_text = raw_sense.strip()
        if not clean_text:
            continue

        parts = re.split(r"\s*[—\-:]\s*", clean_text, maxsplit=1)
        if len(parts) > 1 and parts[1]:
            title = parts[0].strip()
            desc = parts[1].strip()
        else:
            title = clean_text
            desc = None

        eng_trans = None
        if english_meanings and idx < len(english_meanings) and english_meanings[idx]:
            eng_trans = english_meanings[idx].strip() or None

        senses.append(
            LexicalSenseItem(
                sense_number=idx + 1,
                title=title,
                description=desc,
                english_translation=eng_trans,
                raw_text=clean_text,
            )
        )
    return senses


def parse_senses_from_meaning_string(
    meaning_str: Optional[str],
    english_meaning_str: Optional[str] = None,
) -> List[LexicalSenseItem]:
    """
    Parse a semicolon-separated meaning string into structured LexicalSenseItem instances.
    """
    if not meaning_str:
        return []
    raw_senses = [s.strip() for s in meaning_str.split(";") if s.strip()]
    eng_senses = (
        [s.strip() for s in english_meaning_str.split(";")]
        if english_meaning_str
        else None
    )
    return build_lexical_senses(raw_senses, eng_senses)


def extract_sense_candidates(
    pack_or_evidence: Union["EvidencePack", List[Evidence]],
    query: Optional[str] = None,
) -> List[SenseCandidate]:
    """
    Extract structured SenseCandidate objects from EvidencePack or lexical Evidence list.
    Preserves individual definitions from Wiktionary, preserves source entries from Akarathi,
    and excludes items without glosses (such as WordNet records with meaning=None).
    """
    if hasattr(pack_or_evidence, "lexical_evidence"):
        ev_list = pack_or_evidence.lexical_evidence
        q = query or getattr(pack_or_evidence, "query", "")
    else:
        ev_list = pack_or_evidence
        q = query or ""

    candidates: List[SenseCandidate] = []
    seen: Set[Tuple[str, str]] = set()

    for idx, ev in enumerate(ev_list):
        if not ev.meaning or not str(ev.meaning).strip():
            # Exclude records without definitions (e.g. Tamil WordNet where meaning=None)
            continue

        raw_meaning = str(ev.meaning).strip()
        hw = ev.lemma or ev.surface or q
        src = ev.source or "Lexical Resource"

        # Deduplicate identical (source, definition)
        key = (src, raw_meaning)
        if key in seen:
            continue
        seen.add(key)

        cand_id = ev.source_id or f"{src.lower().replace(' ', '_')}:{hw}:{idx}"
        candidates.append(
            SenseCandidate(
                source=src,
                headword=hw,
                definition=raw_meaning,
                english_meaning=ev.english_meaning,
                pos=ev.pos,
                raw_text=raw_meaning,
                metadata=dict(ev.metadata) if ev.metadata else {},
                sense_id=cand_id,
            )
        )

    return candidates


class SOLResponse(BaseModel):
    """
    Structured response schema for SOL AI interpretation layer.
    Strictly grounded in retrieved evidence.
    """

    query: str = Field(description="Original user query string")
    normalized_query: str = Field(description="Normalized query string")
    lemma: Optional[str] = Field(default=None, description="Primary root/lemma determined from evidence")
    meaning: Optional[str] = Field(default=None, description="Primary meaning(s) supported by dictionary evidence")
    english_meaning: Optional[str] = Field(default=None, description="English translation of the meaning")
    senses: List[LexicalSenseItem] = Field(
        default_factory=list, description="Structured list of distinct lexical senses"
    )
    morphology: Optional[Union[StructuredMorphology, Dict[str, Any]]] = Field(
        default=None, description="Structured morphological breakdown (POS, case, number, tense, root, suffixes, model type)"
    )
    contextual_meaning: Optional[str] = Field(
        default=None, description="Precise meaning specifically derived from the query_context, if provided"
    )
    contextual_interpretation: Optional[str] = Field(
        default=None, description="Grounded explanation synthesizing available evidence without fabrication"
    )
    wsd_result: Optional[WSDResult] = Field(
        default=None, description="Detailed deterministic WSD analysis result"
    )
    literary_context: List[LiteraryContextItem] = Field(
        default_factory=list, description="Selected representative classical literary verses/passages"
    )
    related_words: List[str] = Field(
        default_factory=list, description="Related lemmas or synset terms found in evidence"
    )
    sources: List[str] = Field(
        default_factory=list, description="List of contributing resource names"
    )
    uncertainties: List[str] = Field(
        default_factory=list, description="Explicit notes on missing data, conflicts, or guesser analyses"
    )
    evidence_summary: Dict[str, Any] = Field(
        default_factory=dict, description="Summary counts and resource hit statuses"
    )


class EvidencePack(BaseModel):
    """
    Container for all structured evidence passed to the LLM interpreter.
    Preserves original Evidence objects in un-flattened form.
    """

    query: str
    normalized_query: str
    query_context: Optional[str] = None
    lemma_candidates: List[str] = Field(default_factory=list)
    morphology_evidence: List[Evidence] = Field(default_factory=list)
    lexical_evidence: List[Evidence] = Field(default_factory=list)
    literary_evidence: List[Evidence] = Field(default_factory=list)
    related_evidence: List[Evidence] = Field(default_factory=list)
    conflicts: List[Dict[str, Any]] = Field(default_factory=list)
    source_provenance: Dict[str, Any] = Field(default_factory=dict)
    evidence_counts: Dict[str, int] = Field(default_factory=dict)
    wsd_result: Optional[WSDResult] = Field(
        default=None, description="Authoritative deterministic WSD result passed to interpreters"
    )

    class Config:
        arbitrary_types_allowed = True
