"""
Pydantic schemas and dataclasses for the SOL AI Contextual Interpretation Layer.
"""

from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
from backend.schemas.evidence import Evidence


class LiteraryContextItem(BaseModel):
    """Represents a single selected literary context occurrence."""

    work: Optional[str] = Field(default=None, description="Name of the literary work (e.g. Kuruntokai)")
    author: Optional[str] = Field(default=None, description="Author if available")
    period: Optional[str] = Field(default=None, description="Historical period (e.g. Sangam)")
    passage: Optional[str] = Field(default=None, description="Classical Tamil verse or passage")
    verse_number: Optional[str] = Field(default=None, description="Verse or line number")
    meaning: Optional[str] = Field(default=None, description="Modern Tamil translation or meaning")
    source: str = Field(default="Sentamizh", description="Source corpus name")


class LexicalSenseItem(BaseModel):
    """Represents a single structured lexical sense/meaning."""

    sense_number: int = Field(description="1-based index of the sense")
    title: str = Field(description="Title or short summary of the sense")
    description: Optional[str] = Field(default=None, description="Detailed explanation or gloss if available")
    english_translation: Optional[str] = Field(default=None, description="English translation if available")
    raw_text: Optional[str] = Field(default=None, description="Full raw sense text")


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

    class Config:
        arbitrary_types_allowed = True
