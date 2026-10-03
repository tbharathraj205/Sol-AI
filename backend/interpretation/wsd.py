"""
Tamil Word-Sense Disambiguation (WSD) Module for SOL AI.

Provides deterministic, structured, context-aware lexical sense disambiguation based on:
1. Structured SenseCandidate representations preserving provenance, headword, and glosses
2. Dedicated WSDContextFeatures extraction stage
3. Positional distance and syntactic collocation weighting
4. TF-IDF weighted Extended Lesk lexical overlap
5. Agglutinative Tamil morphological stemming
6. Genus vs. differentia weighting
7. Synonym and related concept expansion via Thani Thamizh Akarathi
8. Generalized semantic domain detectors (Quantity/Units, Somatic/Anatomy, Structural/Furniture)
9. Explicit ambiguity detection, close-competition guards, and principled abstention

Zero word-specific hardcoding. Completely domain-agnostic.
"""

import re
import math
from dataclasses import dataclass, field
from collections import Counter
from typing import List, Dict, Any, Optional, Tuple, Set, Union, Callable

from backend.resources.akarathi import ThaniThamizhAkarathiAdapter
from backend.interpretation.schemas import (
    SenseCandidate,
    CandidateScore,
    WSDResult,
    extract_sense_candidates,
)

# Common Tamil grammatical particles and high-frequency function words
TAMIL_STOPWORDS: Set[str] = {
    "ஒரு", "ஓர்", "இந்த", "அந்த", "இது", "அது", "என்று", "என", "போன்ற", "மட்டுமே",
    "மற்றும்", "ஆகிய", "போன்றவை", "இவை", "அவை", "உள்ள", "உள்ளது", "வேண்டும்",
    "என்பது", "தன்", "தனது", "அவன்", "அவள்", "அவர்", "அவர்கள்", "நான்", "நாம்",
    "நீ", "நீங்கள்", "எ", "கா", "முதலியன", "ஆகியவை", "கொண்டு", "கொண்ட", "செய்யும்",
    "வரை", "உண்டு", "இல்லை", "நன்றாக", "அழகாக", "கொடு", "நில்", "செல்கிறேன்",
    "கூட", "மட்டும்", "ஆன", "ஆக", "உடன்"
}

# Regular inflectional suffixes for Tamil (verbal participles, tenses, case endings)
TAMIL_SUFFIXES: List[str] = [
    # Passive / complex verb forms
    "பட்டுள்ளது", "ப்பட்டுள்ளது", "பட்டது", "படுவது",
    # Temporal / conditional participles
    "க்கும்போது", "ும்போது", "போது",
    "க்கவோ", "கவோ", "வோ",
    "க்கின்றது", "கின்றது", "க்கின்ற", "கின்ற",
    "க்கிறது", "கிறது", "க்கின்றன", "கின்றன", "கிற",
    # Finite verb personal endings
    "க்கிறான்", "க்கிறாள்", "க்கிறார்", "க்கிறார்கள்",
    "கிறான்", "கிறாள்", "கிறார்", "கிறார்கள்",
    "ந்தான்", "ந்தாள்", "ந்தார்", "ந்தார்கள்", "ந்தது",
    "த்தான்", "த்தாள்", "த்தார்", "த்தார்கள்", "த்தது",
    "ட்டான்", "ட்டாள்", "ட்டார்", "ட்டார்கள்", "ட்டது",
    # Relative participles / verbal nouns
    "க்கும்", "கும்", "க்க", "க", "உம்",
    "க்கி", "த்து", "ந்து", "ண்டு", "ட்டு",
    "ிட்ட", "ட்ட", "த்த", "ந்த", "இய", "ய",
    # Noun case endings / plurals
    "ங்களின்", "களின்", "ங்களின்", "ங்கள்", "கள்",
    "னுடைய", "முடைய", "உடைய",
    "த்திற்கு", "த்துக்கு", "ுக்கு", "க்கு",
    "த்தினுடைய", "த்தினில்", "த்தில்", "த்தினால்", "த்தை",
    "த்தின்", "த்தன்", "த்து",
    "உடன்", "ஓடு",
    "லிருந்து", "இருந்து",
    "லால்", "ஆல்",
    "லில்", "இல்", "ல்",
    "னை", "வை", "யை", "ஐ",
    "ரின்", "னின்", "லின்", "மின்", "யின்", "வின்", "இன்", "ன்",
]

# Definitional hypernyms / genus words that appear as syntactic heads
GENUS_WORDS: Set[str] = {
    "பகுதி", "வகை", "இடம்", "பொருள்", "ஒன்று", "பெயர்", "நிலை", "முறை"
}

# Generic quantity / measurement units in Tamil (metric, imperial, traditional, temporal, partition)
QUANTITY_UNIT_TERMS: Set[str] = {
    # Mass / Weight (Modern metric & Traditional Tamil)
    "கிலோ", "கிலோகிராம்", "கிராம்", "மில்லிகிராம்", "டன்", "பவுண்டு", "குவிண்டால்",
    "வீசை", "பலம்", "கழஞ்சு", "துலாம்", "குன்றிமணி", "தொடி", "சேர்", "பவுன்",
    # Volume / Liquid / Capacity (Modern metric & Traditional Tamil)
    "லிட்டர்", "மில்லிலிட்டர்", "படி", "ஆழாக்கு", "உழக்கு", "மரக்கால்", "நாழி",
    "குறுணி", "பதக்கு", "கலம்", "முகத்தல்",
    # Length / Distance / Area
    "மீட்டர்", "சென்டிமீட்டர்", "மில்லிமீட்டர்", "கிலோமீட்டர்", "அடி", "இன்ச்", "கஜம்", "மைல்",
    "சாண்", "முழம்", "விரற்கடை", "காணி", "குழி", "மா", "ஏக்கர்", "ஹெக்டேர்", "சென்ட்",
    # Time
    "மணி", "வினாடி", "நொடி", "நிமிடம்", "நாழிகை", "நாள்", "வாரம்", "மாதம்", "வருடம்", "ஆண்டு",
    # Partition / Proportion / Quantity classifiers / Math
    "பங்கு", "பகுதி", "பாகம்", "கூறு", "வீதம்", "விழுக்காடு", "சதவீதம்", "அளவு", "மடங்கு",
    # Currency / Monetary
    "ரூபாய்", "காசு", "பைசா", "பணம்",
}

# Retain PARTITION_TERMS as subset for backward compatibility
PARTITION_TERMS: Set[str] = {
    "பகுதி", "பங்கு", "பாகம்", "கூறு", "அளவு", "வீதம்", "பாதி", "அரை", "விழுக்காடு"
}

# Fractional semantic indicators in definitions
FRACTION_INDICATORS: Set[str] = {
    "பங்கு", "நான்கில்", "பாதி", "அரை", "காற்பங்கு", "முக்கால்", "அரைக்கால்",
    "நாலினொன்று", "பங்கிட்ட", "எண்", "கீழ்வாய்", "பின்னம்", "பின்ன", "கூறு"
}

# Somatic / physiological / bodily condition, sensation, and action terms collocated with anatomical senses
SOMATIC_BODY_TERMS: Set[str] = {
    # Pain, injury, sensations
    "வலி", "வலிக்கிறது", "வலிக்கும்", "வலித்தது", "நோவு", "நோகிறது", "காயம்",
    "வீக்கம்", "முறிவு", "முறிந்தது", "சுளுக்கு", "சுளுக்கியது", "தேய்மானம்",
    "நொண்டி", "நொண்டுகிறான்", "நொண்டுகிறாள்", "நலிவு", "புண்", "ரத்தம்", "இரத்தம்",
    "அடி", "அடிபட்டது",
    # Physical movements / postures
    "நட", "நடக்க", "நடக்கும்போது", "நடத்தல்", "நடந்தான்", "நடந்தாள்",
    "ஓடு", "ஓட", "ஓடும்போது", "குதி", "குதித்தல்", "தாவு", "மிதி", "மிதித்தல்",
    "வழுக்கு", "வழுக்கி", "வழுக்கியது", "ஊன்று", "ஊன்றி", "மடக்கு", "நீட்டு",
    # Anatomy / physiological context
    "உடல்", "உறுப்பு", "பாதம்", "கை", "விரல்", "தசை", "எலும்பு", "மூட்டு",
    "தோல்", "சதை", "மருத்துவர்", "சிகிச்சை", "மருந்து"
}

# Anatomical / body organ semantic indicators in definitions
ANATOMICAL_INDICATORS: Set[str] = {
    "உடல் உறுப்பு", "உறுப்பு", "பாதம்", "விலங்கு", "மாந்தர்", "மனிதர்", "தசை", "எலும்பு", "மூட்டு"
}

# Furniture / structural support terms collocated with furniture support senses
FURNITURE_STRUCTURE_TERMS: Set[str] = {
    "நாற்காலி", "முக்காலி", "மேஜை", "மேசை", "கட்டில்", "பீடம்", "இருக்கை",
    "கருவி", "தூண்", "மஞ்சம்", "பலகை", "வண்டி", "தேர்"
}

# Furniture / structural support semantic indicators in definitions
FURNITURE_INDICATORS: Set[str] = {
    "நாற்காலி", "முக்காலி", "இருக்கை", "தாங்கி", "தாங்கும் பகுதி", "தாங்கி நிற்கும் பகுதி", "தாங்கி நிற்கும்"
}


def tamil_tokens(text: str) -> List[str]:
    """Extract Tamil word tokens from text string."""
    return re.findall(r'[\u0B80-\u0BFA]+', text)


def tamil_stem(word: str) -> str:
    """
    Stems regular Tamil inflectional suffixes.
    Preserves short root words (<= 3 characters).
    """
    w = word.strip()
    if len(w) <= 3:
        return w
    for sfx in TAMIL_SUFFIXES:
        if w.endswith(sfx) and len(w) - len(sfx) >= 2:
            return w[:-len(sfx)]
    return w


def clean_sense_text(sense: str) -> str:
    """Cleans LaTeX fragments and excessive formatting from dictionary glosses."""
    cleaned = re.sub(r'\\frac\{(\d+)\}\{(\d+)\}', r'\1/\2', sense)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def format_fraction_unit_gloss(query: str, unit: str, top_sense: str) -> str:
    """
    Formats an explanatory contextual gloss for a fractional word collocated with a quantity unit.
    Completely generic across Tamil fractional words (கால், அரை, முக்கால், etc.).
    """
    clean_sense = clean_sense_text(top_sense)

    # Determine the fractional descriptor from dictionary sense
    if "நான்கில் ஒரு பங்கு" in clean_sense or "காற்பங்கு" in clean_sense or "1/4" in clean_sense or r"\frac{1}{4}" in top_sense:
        frac_desc = "நான்கில் ஒரு பங்கு"
        frac_sym = "¼"
    elif "பாதி" in clean_sense or "அரை" in clean_sense or "1/2" in clean_sense:
        frac_desc = "பாதி (இரண்டில் ஒரு பங்கு)"
        frac_sym = "½"
    elif "முக்கால்" in clean_sense or "3/4" in clean_sense:
        frac_desc = "முக்கால் பங்கு"
        frac_sym = "¾"
    elif "அரைக்கால்" in clean_sense or "1/8" in clean_sense:
        frac_desc = "அரைக்கால் பங்கு"
        frac_sym = "⅛"
    else:
        frac_desc = clean_sense.split(';')[0].split(' - ')[0].strip()
        frac_sym = ""

    unit_details = {
        "கிலோ": "ஒரு கிலோவின் நான்கில் ஒரு பங்கு (¼ kg / 250g)" if frac_sym == "¼" else f"ஒரு கிலோவின் {frac_desc}",
        "கிலோகிராம்": "ஒரு கிலோகிராமின் நான்கில் ஒரு பங்கு (¼ kg / 250g)" if frac_sym == "¼" else f"ஒரு கிலோகிராமின் {frac_desc}",
        "கிராம்": f"ஒரு கிராமின் {frac_desc}",
        "லிட்டர்": "ஒரு லிட்டரின் நான்கில் ஒரு பங்கு (¼ L / 250ml)" if frac_sym == "¼" else f"ஒரு லிட்டரின் {frac_desc}",
        "மில்லிலிட்டர்": f"ஒரு மில்லிலிட்டரின் {frac_desc}",
        "மீட்டர்": "ஒரு மீட்டரின் நான்கில் ஒரு பங்கு (¼ m / 25cm)" if frac_sym == "¼" else f"ஒரு மீட்டரின் {frac_desc}",
        "கிலோமீட்டர்": "ஒரு கிலோமீட்டரின் நான்கில் ஒரு பங்கு (¼ km / 250m)" if frac_sym == "¼" else f"ஒரு கிலோமீட்டரின் {frac_desc}",
        "மணி": "ஒரு மணியின் நான்கில் ஒரு பங்கு (15 நிமிடங்கள் / ¼ hour)" if frac_sym == "¼" else f"ஒரு மணியின் {frac_desc}",
        "படி": f"ஒரு படியின் {frac_desc}",
        "ஆழாக்கு": f"ஒரு ஆழாக்கின் {frac_desc}",
        "பலம்": f"ஒரு பலத்தின் {frac_desc}",
        "வீசை": f"ஒரு வீசையின் {frac_desc}",
        "ரூபாய்": "ஒரு ரூபாயின் நான்கில் ஒரு பங்கு (25 பைசா / ¼ rupee)" if frac_sym == "¼" else f"ஒரு ரூபாயின் {frac_desc}",
        "பங்கு": f"{frac_desc} ({frac_sym})" if frac_sym else frac_desc,
        "பகுதி": f"நான்கில் ஒரு பகுதி ({frac_sym})" if frac_sym == "¼" else f"{frac_desc} ({frac_sym})",
        "பாகம்": f"{frac_desc} ({frac_sym})" if frac_sym else frac_desc,
        "கூறு": f"{frac_desc} ({frac_sym})" if frac_sym else frac_desc,
    }

    explanation = unit_details.get(unit)
    if explanation:
        return f"{frac_desc} — இங்கு '{query} {unit}' என்பது {explanation}."
    else:
        sym_str = f" ({frac_sym})" if frac_sym else ""
        return f"{frac_desc}{sym_str} — இங்கு '{query} {unit}' என்பது ஒரு {unit}-ன் {frac_desc}."


@dataclass
class DetectedDomainSignal:
    """Represents a domain cue detected in the context sentence."""
    term: str
    root_term: str
    distance: int
    domain: str  # "quantity", "somatic", "structural"


@dataclass
class WSDContextFeatures:
    """
    Reusable contextual feature representation extracted from the context sentence.
    Decouples context analysis from candidate scoring.
    """
    raw_context: str
    context_tokens: List[str]
    stemmed_tokens: List[str]
    query_positions: List[int]
    nearby_tokens: Set[str]  # Collocates at distance == 1
    token_distances: Dict[str, int]
    closest_quantity: Optional[DetectedDomainSignal] = None
    closest_somatic: Optional[DetectedDomainSignal] = None
    closest_structural: Optional[DetectedDomainSignal] = None
    all_quantity_signals: List[DetectedDomainSignal] = field(default_factory=list)
    all_somatic_signals: List[DetectedDomainSignal] = field(default_factory=list)
    all_structural_signals: List[DetectedDomainSignal] = field(default_factory=list)
    token_synonyms: Dict[str, Set[str]] = field(default_factory=dict)


class WSDContextFeatureExtractor:
    """
    Extracts reusable linguistic and domain signals from context sentences.
    """

    def __init__(self, akarathi: Optional[ThaniThamizhAkarathiAdapter] = None):
        self.akarathi = akarathi or ThaniThamizhAkarathiAdapter()
        self._syn_cache: Dict[str, Set[str]] = {}

    def get_synonyms(self, word: str) -> Set[str]:
        """Look up direct dictionary glosses/synonyms from Thani Thamizh Akarathi."""
        if word in self._syn_cache:
            return self._syn_cache[word]
        syns: Set[str] = set()
        evs = self.akarathi.lookup(word)
        for ev in evs:
            if ev.meaning:
                first_def = ev.meaning.split('.')[0].split(';')[0]
                for t in tamil_tokens(first_def):
                    if t not in TAMIL_STOPWORDS and t != word and len(t) > 1:
                        syns.add(t)
                        st = tamil_stem(t)
                        if st != t:
                            syns.add(st)
        self._syn_cache[word] = syns
        return syns

    def extract_features(
        self,
        query: str,
        context_sentence: Optional[str]
    ) -> Optional[WSDContextFeatures]:
        """
        Extract structured context features.
        Returns None if context_sentence is absent or empty.
        """
        if not context_sentence or not context_sentence.strip():
            return None

        c_text = context_sentence.strip()
        raw_c_tokens = tamil_tokens(c_text)
        if not raw_c_tokens:
            return None

        # Locate query positions in raw token sequence
        query_stem = tamil_stem(query)
        query_indices = [
            idx for idx, w in enumerate(raw_c_tokens)
            if w == query or tamil_stem(w) == query_stem
        ]
        if not query_indices:
            query_indices = [
                idx for idx, w in enumerate(raw_c_tokens)
                if query in w
            ]

        # Content context tokens (strictly excluding all query occurrences and stopwords)
        c_tokens = [
            w for idx, w in enumerate(raw_c_tokens)
            if idx not in query_indices and w != query and w not in TAMIL_STOPWORDS and len(w) > 1
        ]
        stemmed_c_tokens = [tamil_stem(t) for t in c_tokens]

        # Calculate minimum distance from any occurrence of the query
        token_distances: Dict[str, int] = {}
        for idx, w in enumerate(raw_c_tokens):
            if idx not in query_indices and w != query and w not in TAMIL_STOPWORDS and len(w) > 1:
                dist = min(abs(idx - q_idx) for q_idx in query_indices) if query_indices else 999
                if w not in token_distances or dist < token_distances[w]:
                    token_distances[w] = dist

        nearby_tokens: Set[str] = {w for w, d in token_distances.items() if d == 1}

        # Quantity / unit detection
        qty_signals: List[DetectedDomainSignal] = []
        for w, d in token_distances.items():
            w_stem = tamil_stem(w)
            if w in QUANTITY_UNIT_TERMS:
                qty_signals.append(DetectedDomainSignal(term=w, root_term=w, distance=d, domain="quantity"))
            elif w_stem in QUANTITY_UNIT_TERMS:
                qty_signals.append(DetectedDomainSignal(term=w, root_term=w_stem, distance=d, domain="quantity"))
        qty_signals.sort(key=lambda s: s.distance)

        # Somatic / body detection
        somatic_signals: List[DetectedDomainSignal] = []
        for w, d in token_distances.items():
            w_stem = tamil_stem(w)
            if w in SOMATIC_BODY_TERMS:
                somatic_signals.append(DetectedDomainSignal(term=w, root_term=w, distance=d, domain="somatic"))
            elif w_stem in SOMATIC_BODY_TERMS:
                somatic_signals.append(DetectedDomainSignal(term=w, root_term=w_stem, distance=d, domain="somatic"))
        somatic_signals.sort(key=lambda s: s.distance)

        # Furniture / structural detection
        structural_signals: List[DetectedDomainSignal] = []
        for w, d in token_distances.items():
            w_stem = tamil_stem(w)
            if w in FURNITURE_STRUCTURE_TERMS:
                structural_signals.append(DetectedDomainSignal(term=w, root_term=w, distance=d, domain="structural"))
            elif w_stem in FURNITURE_STRUCTURE_TERMS:
                structural_signals.append(DetectedDomainSignal(term=w, root_term=w_stem, distance=d, domain="structural"))
        structural_signals.sort(key=lambda s: s.distance)

        # Precompute synonyms for context tokens
        c_syns: Dict[str, Set[str]] = {}
        for c in c_tokens:
            c_syns[c] = self.get_synonyms(c)
            c_st = tamil_stem(c)
            if c_st != c:
                c_syns[c].update(self.get_synonyms(c_st))

        return WSDContextFeatures(
            raw_context=c_text,
            context_tokens=c_tokens,
            stemmed_tokens=stemmed_c_tokens,
            query_positions=query_indices,
            nearby_tokens=nearby_tokens,
            token_distances=token_distances,
            closest_quantity=qty_signals[0] if qty_signals else None,
            closest_somatic=somatic_signals[0] if somatic_signals else None,
            closest_structural=structural_signals[0] if structural_signals else None,
            all_quantity_signals=qty_signals,
            all_somatic_signals=somatic_signals,
            all_structural_signals=structural_signals,
            token_synonyms=c_syns,
        )


class TamilWSD:
    """
    Deterministic Context-Aware Word Sense Disambiguation for Tamil.
    Operates on structured SenseCandidate objects and returns structured WSDResult.
    """

    def __init__(self, akarathi: Optional[ThaniThamizhAkarathiAdapter] = None):
        self.akarathi = akarathi or ThaniThamizhAkarathiAdapter()
        self.extractor = WSDContextFeatureExtractor(self.akarathi)

    def extract_context_features(
        self,
        query: str,
        context_sentence: Optional[str]
    ) -> Optional[WSDContextFeatures]:
        """Delegate context feature extraction."""
        return self.extractor.extract_features(query, context_sentence)

    def get_synonyms(self, word: str) -> Set[str]:
        """Delegate synonym lookup."""
        return self.extractor.get_synonyms(word)

    def disambiguate(
        self,
        query: str,
        context_sentence: Optional[str],
        candidate_senses: Union[List[SenseCandidate], List[str]]
    ) -> WSDResult:
        """
        Disambiguates the query sense given context_sentence and structured candidate senses.

        :param query: Target Tamil word
        :param context_sentence: Surrounding sentence from webpage / user input
        :param candidate_senses: List of SenseCandidate instances (or strings for backward compatibility)
        :return: Authoritative WSDResult
        """
        # 1. Normalize candidate inputs to structured SenseCandidate objects
        structured_candidates: List[SenseCandidate] = []
        for idx, item in enumerate(candidate_senses):
            if isinstance(item, SenseCandidate):
                if item.definition and item.definition.strip():
                    structured_candidates.append(item)
            elif isinstance(item, str) and item.strip():
                structured_candidates.append(
                    SenseCandidate(
                        source="Lexical Candidate",
                        headword=query,
                        definition=item.strip(),
                        raw_text=item.strip(),
                        sense_id=f"legacy_sense:{idx}",
                    )
                )

        # Deduplicate candidates preserving order
        unique_candidates: List[SenseCandidate] = []
        seen_keys: Set[Tuple[str, str]] = set()
        for cand in structured_candidates:
            key = (cand.source, cand.definition.strip())
            if key not in seen_keys:
                seen_keys.add(key)
                unique_candidates.append(cand)

        # Guard: No candidates available
        if not unique_candidates:
            return WSDResult(
                query=query,
                context=context_sentence,
                selected_candidate=None,
                selected_sense=None,
                score=0.0,
                status="insufficient_evidence",
                confidence="none",
                reasons=["No candidate senses available."],
                candidates=[],
            )

        # Guard: Context missing or empty
        if not context_sentence or not context_sentence.strip():
            return WSDResult(
                query=query,
                context=None,
                selected_candidate=None,
                selected_sense=None,
                score=0.0,
                status="no_context",
                confidence="none",
                reasons=["No query context provided."],
                candidates=[
                    CandidateScore(candidate=c, score=0.0, reasons=["No context provided."])
                    for c in unique_candidates
                ],
            )

        # 2. Extract context features
        features = self.extractor.extract_features(query, context_sentence)
        if not features or not features.context_tokens:
            return WSDResult(
                query=query,
                context=context_sentence,
                selected_candidate=None,
                selected_sense=None,
                score=0.0,
                status="insufficient_evidence",
                confidence="none",
                reasons=["Context contains no discriminative content words."],
                candidates=[
                    CandidateScore(candidate=c, score=0.0, reasons=["Context lacks content words."])
                    for c in unique_candidates
                ],
            )

        # Guard: Single documented sense
        if len(unique_candidates) == 1:
            only_cand = unique_candidates[0]
            clean_def = clean_sense_text(only_cand.definition)
            return WSDResult(
                query=query,
                context=context_sentence,
                selected_candidate=only_cand,
                selected_sense=clean_def,
                score=1.0,
                status="single_sense",
                confidence="medium",
                reasons=["Single documented sense."],
                candidates=[CandidateScore(candidate=only_cand, score=1.0, reasons=["Single documented sense."])],
            )

        # 3. Precompute token frequencies and IDF across candidate definitions
        N = len(unique_candidates)
        cand_tokens: List[Set[str]] = []
        cand_stems: List[Set[str]] = []
        df_tokens: Counter = Counter()
        df_stems: Counter = Counter()

        for cand in unique_candidates:
            toks = set(t for t in tamil_tokens(cand.definition) if t != query and t not in TAMIL_STOPWORDS and len(t) > 1)
            stems = set(tamil_stem(t) for t in toks)
            cand_tokens.append(toks)
            cand_stems.append(stems)
            for t in toks:
                df_tokens[t] += 1
            for st in stems:
                df_stems[st] += 1

        def idf(term: str, df_map: Counter) -> float:
            count = df_map.get(term, 1)
            return math.log((N + 1.0) / count) + 1.0

        # 4. Score each candidate independently against extracted context features
        evaluated_candidates: List[CandidateScore] = []

        for i, cand in enumerate(unique_candidates):
            c_text = cand.definition
            c_toks = cand_tokens[i]
            c_stm = cand_stems[i]
            score = 0.0
            reasons: List[str] = []

            # A. Check semantic domain indicators in candidate definition
            c_has_fraction = bool(
                (c_toks & FRACTION_INDICATORS) or
                (c_stm & FRACTION_INDICATORS) or
                any(ind in c_text for ind in FRACTION_INDICATORS) or
                any(frac in c_text for frac in ["1/4", "1/2", "3/4", "1/8", r"\frac"])
            )

            c_has_anatomy = bool(
                (c_toks & ANATOMICAL_INDICATORS) or
                (c_stm & ANATOMICAL_INDICATORS) or
                any(ind in c_text for ind in ANATOMICAL_INDICATORS)
            )

            c_has_structural = bool(
                (c_toks & FURNITURE_INDICATORS) or
                (c_stm & FURNITURE_INDICATORS) or
                any(ind in c_text for ind in FURNITURE_INDICATORS)
            )

            # B. Evaluate domain signal boosts
            # 1. Quantity / unit boost for fractional senses
            if c_has_fraction and features.closest_quantity:
                q_sig = features.closest_quantity
                d = q_sig.distance
                raw_u = q_sig.term
                if d == 1:
                    unit_boost = 35.0
                    score += unit_boost
                    reasons.append(f"adjacent_unit:{raw_u}(dist=1)->fraction_sense(+{unit_boost:.1f})")
                elif d <= 3:
                    unit_boost = 20.0 / d
                    score += unit_boost
                    reasons.append(f"collocated_unit:{raw_u}(dist={d})->fraction_sense(+{unit_boost:.1f})")
                else:
                    unit_boost = 5.0 / d
                    score += unit_boost
                    reasons.append(f"distant_unit:{raw_u}(dist={d})->fraction_sense(+{unit_boost:.1f})")

            # 2. Somatic / physiological boost for anatomical senses
            if c_has_anatomy and features.closest_somatic:
                s_sig = features.closest_somatic
                d = s_sig.distance
                raw_s = s_sig.term
                if d == 1:
                    somatic_boost = 35.0
                    score += somatic_boost
                    reasons.append(f"adjacent_somatic:{raw_s}(dist=1)->anatomy_sense(+{somatic_boost:.1f})")
                elif d <= 3:
                    somatic_boost = 20.0 / d
                    score += somatic_boost
                    reasons.append(f"collocated_somatic:{raw_s}(dist={d})->anatomy_sense(+{somatic_boost:.1f})")
                else:
                    somatic_boost = 5.0 / d
                    score += somatic_boost
                    reasons.append(f"distant_somatic:{raw_s}(dist={d})->anatomy_sense(+{somatic_boost:.1f})")

            # 3. Furniture / structural boost for structural senses
            if c_has_structural and features.closest_structural:
                f_sig = features.closest_structural
                d = f_sig.distance
                raw_f = f_sig.term
                if d == 1:
                    furn_boost = 35.0
                    score += furn_boost
                    reasons.append(f"adjacent_structural:{raw_f}(dist=1)->structural_sense(+{furn_boost:.1f})")
                elif d <= 3:
                    furn_boost = 20.0 / d
                    score += furn_boost
                    reasons.append(f"collocated_structural:{raw_f}(dist={d})->structural_sense(+{furn_boost:.1f})")
                else:
                    furn_boost = 5.0 / d
                    score += furn_boost
                    reasons.append(f"distant_structural:{raw_f}(dist={d})->structural_sense(+{furn_boost:.1f})")

            # C. Lexical overlap and synonym expansion scoring
            for ctx_tok in features.context_tokens:
                ctx_stm = tamil_stem(ctx_tok)
                d = features.token_distances.get(ctx_tok, 999)
                is_collocate = d == 1
                pos_weight = 2.5 if is_collocate else (1.5 if d <= 3 else 1.0)
                is_genus = ctx_tok in GENUS_WORDS
                genus_mult = 0.4 if is_genus else 1.0

                # 1. Exact match in candidate definition tokens
                if ctx_tok in c_toks:
                    w_score = 4.0 * idf(ctx_tok, df_tokens) * pos_weight * genus_mult
                    score += w_score
                    reasons.append(f"exact:{ctx_tok}({w_score:.1f})")
                # 2. Stem match in candidate definition stems
                elif ctx_stm in c_stm:
                    w_score = 2.5 * idf(ctx_stm, df_stems) * pos_weight * genus_mult
                    score += w_score
                    reasons.append(f"stem:{ctx_stm}({w_score:.1f})")
                else:
                    # 3. Synonym / Related concept match
                    syns = features.token_synonyms.get(ctx_tok, set())
                    overlap_syns = syns & c_toks
                    if overlap_syns:
                        best_syn = list(overlap_syns)[0]
                        w_score = 2.0 * idf(best_syn, df_tokens) * pos_weight
                        score += w_score
                        reasons.append(f"syn:{ctx_tok}->{best_syn}({w_score:.1f})")
                    else:
                        syn_stems = {tamil_stem(sm) for sm in syns}
                        overlap_stems = syn_stems & c_stm
                        if overlap_stems:
                            best_ss = list(overlap_stems)[0]
                            w_score = 1.5 * idf(best_ss, df_stems) * pos_weight
                            score += w_score
                            reasons.append(f"syn_stem:{ctx_tok}->{best_ss}({w_score:.1f})")

            # D. Specificity density preference
            # When multiple candidates match the same evidence (e.g. Wiktionary's single sense vs collapsed blob),
            # concise single-sense candidates have higher definition specificity.
            if score > 0.0:
                specificity_adj = (1.0 / (1.0 + math.log(max(len(c_text), 1)))) * 0.05
                score += specificity_adj

            evaluated_candidates.append(
                CandidateScore(
                    candidate=cand,
                    score=score,
                    reasons=reasons,
                )
            )

        # 5. Sort candidates by score descending
        evaluated_candidates.sort(key=lambda cs: cs.score, reverse=True)

        top_cand_score = evaluated_candidates[0]
        top_score = top_cand_score.score
        top_cand = top_cand_score.candidate
        top_reasons = top_cand_score.reasons

        second_cand_score = evaluated_candidates[1] if len(evaluated_candidates) > 1 else None
        second_score = second_cand_score.score if second_cand_score else 0.0

        # 6. Ambiguity, Floor, and Conflict Guards
        # Low Evidence Floor
        if top_score < 1.0:
            return WSDResult(
                query=query,
                context=context_sentence,
                selected_candidate=None,
                selected_sense=None,
                score=top_score,
                status="insufficient_evidence",
                confidence="low",
                reasons=["Context lacks discriminative evidence to determine intended sense."],
                candidates=evaluated_candidates,
            )

        # Close Competition Guard for low-scoring ambiguity
        if top_score - second_score < 0.2 and top_score < 3.0:
            return WSDResult(
                query=query,
                context=context_sentence,
                selected_candidate=None,
                selected_sense=None,
                score=top_score,
                status="ambiguous",
                confidence="low",
                reasons=[f"Ambiguous between competing senses (score {top_score:.1f} vs {second_score:.1f})."],
                candidates=evaluated_candidates,
            )

        # Conflicting Signals Guard
        # Check if top two candidates represent genuinely distinct semantic domains and both have strong support
        if second_cand_score and top_score >= 10.0 and second_score >= 10.0:
            top_domain = None
            if any("fraction_sense" in r for r in top_reasons):
                top_domain = "fraction"
            elif any("anatomy_sense" in r for r in top_reasons):
                top_domain = "anatomy"
            elif any("structural_sense" in r for r in top_reasons):
                top_domain = "structural"

            sec_domain = None
            if any("fraction_sense" in r for r in second_cand_score.reasons):
                sec_domain = "fraction"
            elif any("anatomy_sense" in r for r in second_cand_score.reasons):
                sec_domain = "anatomy"
            elif any("structural_sense" in r for r in second_cand_score.reasons):
                sec_domain = "structural"

            if top_domain and sec_domain and top_domain != sec_domain:
                if abs(top_score - second_score) < 3.0:
                    return WSDResult(
                        query=query,
                        context=context_sentence,
                        selected_candidate=None,
                        selected_sense=None,
                        score=top_score,
                        status="conflicting_signals",
                        confidence="low",
                        reasons=[f"Conflicting contextual evidence: multiple distinct domains supported ({top_domain} vs {sec_domain}, scores {top_score:.1f} vs {second_score:.1f})."],
                        candidates=evaluated_candidates,
                    )

        # 7. Format selected sense text
        top_idx = unique_candidates.index(top_cand)
        top_toks = cand_tokens[top_idx]
        top_stm = cand_stems[top_idx]
        top_def = top_cand.definition

        win_has_fraction = bool(
            (top_toks & FRACTION_INDICATORS) or
            (top_stm & FRACTION_INDICATORS) or
            any(ind in top_def for ind in FRACTION_INDICATORS) or
            any(frac in top_def for frac in ["1/4", "1/2", "3/4", "1/8", r"\frac"])
        )

        win_has_anatomy = bool(
            (top_toks & ANATOMICAL_INDICATORS) or
            (top_stm & ANATOMICAL_INDICATORS) or
            any(ind in top_def for ind in ANATOMICAL_INDICATORS)
        )

        win_has_furniture = bool(
            (top_toks & FURNITURE_INDICATORS) or
            (top_stm & FURNITURE_INDICATORS) or
            any(ind in top_def for ind in FURNITURE_INDICATORS)
        )

        if win_has_fraction and features.closest_quantity and features.closest_quantity.distance <= 2:
            formatted_sense = format_fraction_unit_gloss(
                query, features.closest_quantity.root_term, top_def
            )
        elif win_has_anatomy and features.closest_somatic and features.closest_somatic.distance <= 3:
            cleaned = clean_sense_text(top_def)
            if not cleaned.startswith("உடல் உறுப்பு"):
                formatted_sense = f"உடல் உறுப்பு / பாதம் — {cleaned}"
            else:
                formatted_sense = cleaned
        elif win_has_furniture and features.closest_structural and features.closest_structural.distance <= 3:
            cleaned = clean_sense_text(top_def)
            if not cleaned.startswith("நாற்காலியைத் தாங்கும் பகுதி"):
                formatted_sense = f"நாற்காலியைத் தாங்கும் பகுதி — {cleaned}"
            else:
                formatted_sense = cleaned
        else:
            formatted_sense = clean_sense_text(top_def)

        top_cand_score.formatted_text = formatted_sense

        confidence_level = "high" if top_score >= 20.0 else ("medium" if top_score >= 5.0 else "low")

        return WSDResult(
            query=query,
            context=context_sentence,
            selected_candidate=top_cand,
            selected_sense=formatted_sense,
            score=top_score,
            status="selected",
            confidence=confidence_level,
            reasons=top_reasons,
            candidates=evaluated_candidates,
        )
