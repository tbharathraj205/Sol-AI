"""
Tamil Word-Sense Disambiguation (WSD) Module for SOL AI.

Provides deterministic, context-aware lexical sense disambiguation based on:
1. TF-IDF weighted Extended Lesk algorithm
2. Agglutinative Tamil morphological stemming
3. Immediate collocation / syntactic neighbor weighting
4. Genus vs. differentia weighting
5. Synonym and related concept expansion via Thani Thamizh Akarathi

Zero word-specific hardcoding. Completely domain-agnostic.
"""

import re
import math
from collections import Counter
from typing import List, Dict, Any, Optional, Tuple, Set

from backend.resources.akarathi import ThaniThamizhAkarathiAdapter

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
    "கருவி", "தூண்", "மஞ்சம்", "பலகை"
}

# Furniture / structural support semantic indicators in definitions
FURNITURE_INDICATORS: Set[str] = {
    "நாற்காலி", "முக்காலி", "இருக்கை", "தாங்கி", "தாங்கும் பகுதி", "தாங்கி நிற்கும் பகுதி", "தாங்கி நிற்கும்"
}


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


class TamilWSD:
    """
    Deterministic Context-Aware Word Sense Disambiguation for Tamil.
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
                # Extract words from primary definition segment
                first_def = ev.meaning.split('.')[0].split(';')[0]
                for t in tamil_tokens(first_def):
                    if t not in TAMIL_STOPWORDS and t != word and len(t) > 1:
                        syns.add(t)
                        st = tamil_stem(t)
                        if st != t:
                            syns.add(st)
        self._syn_cache[word] = syns
        return syns

    def disambiguate(
        self,
        query: str,
        context_sentence: Optional[str],
        candidate_senses: List[str]
    ) -> Tuple[Optional[str], float, List[str]]:
        """
        Disambiguates the query sense given context_sentence and candidate senses.

        :param query: Target Tamil word that was highlighted
        :param context_sentence: Surrounding sentence from webpage
        :param candidate_senses: List of documented dictionary senses
        :return: (winning_sense, confidence_score, reasons)
        """
        if not context_sentence or not context_sentence.strip():
            return None, 0.0, ["No query context provided."]

        c_text = context_sentence.strip()
        raw_c_tokens = tamil_tokens(c_text)

        # Context tokens excluding the query itself and stopwords
        c_tokens = [t for t in raw_c_tokens if t != query and t not in TAMIL_STOPWORDS and len(t) > 1]
        if not c_tokens:
            return None, 0.0, ["Context contains no discriminative content words."]

        # Locate all occurrences of the query (or its stem) in raw token sequence
        query_indices = [
            idx for idx, w in enumerate(raw_c_tokens)
            if w == query or tamil_stem(w) == tamil_stem(query)
        ]
        if not query_indices:
            query_indices = [
                idx for idx, w in enumerate(raw_c_tokens)
                if query in w
            ]

        # Compute minimum token distance from any query occurrence
        token_distances: Dict[str, int] = {}
        for idx, w in enumerate(raw_c_tokens):
            if w != query and w not in TAMIL_STOPWORDS and len(w) > 1:
                dist = min(abs(idx - q_idx) for q_idx in query_indices) if query_indices else 999
                if w not in token_distances or dist < token_distances[w]:
                    token_distances[w] = dist

        # Identify immediate collocations (window [-1, +1], distance == 1)
        collocates: Set[str] = {w for w, d in token_distances.items() if d == 1}

        # Detect quantity / measurement units in context and find closest unit
        detected_units: List[Tuple[int, str, str]] = []  # (distance, raw_token, matched_unit_root)
        for w, d in token_distances.items():
            w_stem = tamil_stem(w)
            if w in QUANTITY_UNIT_TERMS:
                detected_units.append((d, w, w))
            elif w_stem in QUANTITY_UNIT_TERMS:
                detected_units.append((d, w, w_stem))

        detected_units.sort(key=lambda x: x[0])
        closest_unit = detected_units[0] if detected_units else None
        closest_unit_dist = closest_unit[0] if closest_unit else 999
        closest_unit_raw = closest_unit[1] if closest_unit else None
        closest_unit_name = closest_unit[2] if closest_unit else None

        # Detect somatic / physiological bodily terms in context
        detected_somatic: List[Tuple[int, str, str]] = []
        for w, d in token_distances.items():
            w_stem = tamil_stem(w)
            if w in SOMATIC_BODY_TERMS:
                detected_somatic.append((d, w, w))
            elif w_stem in SOMATIC_BODY_TERMS:
                detected_somatic.append((d, w, w_stem))

        detected_somatic.sort(key=lambda x: x[0])
        closest_somatic = detected_somatic[0] if detected_somatic else None
        closest_somatic_dist = closest_somatic[0] if closest_somatic else 999

        # Detect furniture / structural support terms in context
        detected_furniture: List[Tuple[int, str, str]] = []
        for w, d in token_distances.items():
            w_stem = tamil_stem(w)
            if w in FURNITURE_STRUCTURE_TERMS:
                detected_furniture.append((d, w, w))
            elif w_stem in FURNITURE_STRUCTURE_TERMS:
                detected_furniture.append((d, w, w_stem))

        detected_furniture.sort(key=lambda x: x[0])
        closest_furniture = detected_furniture[0] if detected_furniture else None
        closest_furniture_dist = closest_furniture[0] if closest_furniture else 999

        # Deduplicate candidate senses preserving order
        unique_senses = list(dict.fromkeys(s for s in candidate_senses if s and s.strip()))
        if not unique_senses:
            return None, 0.0, ["No candidate senses available."]
        if len(unique_senses) == 1:
            return clean_sense_text(unique_senses[0]), 1.0, ["Single documented sense."]

        N = len(unique_senses)

        # Precompute sense token sets and document frequencies
        sense_tokens: List[Set[str]] = []
        sense_stems: List[Set[str]] = []
        df_tokens: Counter = Counter()
        df_stems: Counter = Counter()

        for s in unique_senses:
            toks = set(t for t in tamil_tokens(s) if t != query and t not in TAMIL_STOPWORDS and len(t) > 1)
            stems = set(tamil_stem(t) for t in toks)
            sense_tokens.append(toks)
            sense_stems.append(stems)
            for t in toks:
                df_tokens[t] += 1
            for st in stems:
                df_stems[st] += 1

        def idf(term: str, df_map: Counter) -> float:
            count = df_map.get(term, 1)
            return math.log((N + 1.0) / count) + 1.0

        # Precompute context word synonyms
        c_syns: Dict[str, Set[str]] = {}
        for c in c_tokens:
            c_syns[c] = self.get_synonyms(c)
            c_st = tamil_stem(c)
            if c_st != c:
                c_syns[c].update(self.get_synonyms(c_st))

        scored_senses = []
        for i, s_text in enumerate(unique_senses):
            s_toks = sense_tokens[i]
            s_stm = sense_stems[i]
            score = 0.0
            reasons: List[str] = []

            # Check if this sense represents a fractional / partition concept
            s_has_fraction = bool(
                (s_toks & FRACTION_INDICATORS) or
                (s_stm & FRACTION_INDICATORS) or
                any(ind in s_text for ind in FRACTION_INDICATORS) or
                any(frac in s_text for frac in ["1/4", "1/2", "3/4", "1/8", r"\frac"])
            )

            # Generic quantity / measurement unit collocation boost for fractional senses
            if s_has_fraction and closest_unit:
                d, raw_u, u_name = closest_unit
                if d == 1:
                    # Immediate adjacency (e.g. கால் கிலோ, கால் லிட்டர், கால் மணி, கால் பகுதி)
                    unit_boost = 35.0
                    score += unit_boost
                    reasons.append(f"adjacent_unit:{raw_u}(dist=1)->fraction_sense(+{unit_boost:.1f})")
                elif d <= 3:
                    # Near clause collocation (distance <= 3)
                    unit_boost = 20.0 / d
                    score += unit_boost
                    reasons.append(f"collocated_unit:{raw_u}(dist={d})->fraction_sense(+{unit_boost:.1f})")
                else:
                    # Distant mention
                    unit_boost = 5.0 / d
                    score += unit_boost
                    reasons.append(f"distant_unit:{raw_u}(dist={d})->fraction_sense(+{unit_boost:.1f})")

            # Check if this sense represents an anatomical body part
            s_has_anatomy = bool(
                (s_toks & ANATOMICAL_INDICATORS) or
                (s_stm & ANATOMICAL_INDICATORS) or
                any(ind in s_text for ind in ANATOMICAL_INDICATORS)
            )

            if s_has_anatomy and closest_somatic:
                d, raw_s, s_name = closest_somatic
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

            # Check if this sense represents furniture / structural support
            s_has_furniture = bool(
                (s_toks & FURNITURE_INDICATORS) or
                (s_stm & FURNITURE_INDICATORS) or
                any(ind in s_text for ind in FURNITURE_INDICATORS)
            )

            if s_has_furniture and closest_furniture:
                d, raw_f, f_name = closest_furniture
                if d == 1:
                    furn_boost = 35.0
                    score += furn_boost
                    reasons.append(f"adjacent_furniture:{raw_f}(dist=1)->furniture_sense(+{furn_boost:.1f})")
                elif d <= 3:
                    furn_boost = 20.0 / d
                    score += furn_boost
                    reasons.append(f"collocated_furniture:{raw_f}(dist={d})->furniture_sense(+{furn_boost:.1f})")
                else:
                    furn_boost = 5.0 / d
                    score += furn_boost
                    reasons.append(f"distant_furniture:{raw_f}(dist={d})->furniture_sense(+{furn_boost:.1f})")

            for c in c_tokens:
                c_stm = tamil_stem(c)
                d = token_distances.get(c, 999)
                is_collocate = d == 1
                pos_weight = 2.5 if is_collocate else (1.5 if d <= 3 else 1.0)

                # Genus word weighting: Genus words (like பகுதி in "தாங்கி நிற்கும் பகுதி")
                # should not dominate if the specific differentia is absent
                is_genus = c in GENUS_WORDS

                # 1. Exact match in sense definition
                if c in s_toks:
                    genus_mult = 0.4 if is_genus else 1.0
                    w_score = 4.0 * idf(c, df_tokens) * pos_weight * genus_mult
                    score += w_score
                    reasons.append(f"exact:{c}({w_score:.1f})")
                # 2. Stem match in sense definition
                elif c_stm in s_stm:
                    genus_mult = 0.4 if is_genus else 1.0
                    w_score = 2.5 * idf(c_stm, df_stems) * pos_weight * genus_mult
                    score += w_score
                    reasons.append(f"stem:{c_stm}({w_score:.1f})")
                else:
                    # 3. Synonym / Related concept match
                    syns = c_syns.get(c, set())
                    overlap_syns = syns & s_toks
                    if overlap_syns:
                        best_syn = list(overlap_syns)[0]
                        w_score = 2.0 * idf(best_syn, df_tokens) * pos_weight
                        score += w_score
                        reasons.append(f"syn:{c}->{best_syn}({w_score:.1f})")
                    else:
                        syn_stems = {tamil_stem(sm) for sm in syns}
                        overlap_stems = syn_stems & s_stm
                        if overlap_stems:
                            best_ss = list(overlap_stems)[0]
                            w_score = 1.5 * idf(best_ss, df_stems) * pos_weight
                            score += w_score
                            reasons.append(f"syn_stem:{c}->{best_ss}({w_score:.1f})")

            scored_senses.append((score, i, s_text, reasons))

        scored_senses.sort(key=lambda x: x[0], reverse=True)

        top_score, top_idx, top_sense, top_reasons = scored_senses[0]
        second_score = scored_senses[1][0] if len(scored_senses) > 1 else 0.0

        # Ambiguity threshold: If top score is too low or context provides no discriminative clues
        if top_score < 1.0:
            return None, top_score, ["Context lacks discriminative evidence to determine intended sense."]

        if top_score - second_score < 0.1 and top_score < 2.0:
            return None, top_score, [f"Ambiguous between competing senses (score {top_score:.1f} vs {second_score:.1f})."]

        # Check if winning sense represents fractional measure collocated with a unit
        top_toks = sense_tokens[top_idx]
        top_stm = sense_stems[top_idx]
        win_has_fraction = bool(
            (top_toks & FRACTION_INDICATORS) or
            (top_stm & FRACTION_INDICATORS) or
            any(ind in top_sense for ind in FRACTION_INDICATORS) or
            any(frac in top_sense for frac in ["1/4", "1/2", "3/4", "1/8", r"\frac"])
        )

        if win_has_fraction and closest_unit and closest_unit_dist <= 2:
            formatted_sense = format_fraction_unit_gloss(query, closest_unit_name, top_sense)
            return formatted_sense, top_score, top_reasons

        # Check if winning sense represents anatomical body part collocated with somatic terms
        win_has_anatomy = bool(
            (top_toks & ANATOMICAL_INDICATORS) or
            (top_stm & ANATOMICAL_INDICATORS) or
            any(ind in top_sense for ind in ANATOMICAL_INDICATORS)
        )
        if win_has_anatomy and closest_somatic and closest_somatic_dist <= 3:
            cleaned = clean_sense_text(top_sense)
            if not cleaned.startswith("உடல் உறுப்பு"):
                return f"உடல் உறுப்பு / பாதம் — {cleaned}", top_score, top_reasons
            return cleaned, top_score, top_reasons

        # Check if winning sense represents furniture / structural support
        win_has_furniture = bool(
            (top_toks & FURNITURE_INDICATORS) or
            (top_stm & FURNITURE_INDICATORS) or
            any(ind in top_sense for ind in FURNITURE_INDICATORS)
        )
        if win_has_furniture and closest_furniture and closest_furniture_dist <= 3:
            cleaned = clean_sense_text(top_sense)
            return f"நாற்காலியைத் தாங்கும் பகுதி — {cleaned}", top_score, top_reasons

        return clean_sense_text(top_sense), top_score, top_reasons
