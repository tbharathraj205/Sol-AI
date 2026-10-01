"""
SOL AI — Semantic Preprocessing & Canonical Embedding-Text Construction Layer.

Phase 3A of SOL AI's Semantic Retrieval Layer.
Specification: STEP3_SEMANTIC_RETRIEVAL_DESIGN.md

Responsibilities:
1. Semantic text cleaning:
   - Residual navigation artifact removal (e.g. trailing 'Back' in Thiruvasagam)
   - Zero-width character filtering and canonical Unicode NFC normalization
   - Deterministic whitespace normalization while preserving poetic line breaks
   - Absolute preservation of legitimate Tamil characters, diacritics, and literary content
2. Semantic-index eligibility classification:
   - Suppresses non-poetic structural stubs (speaker attributions, musical pann metadata, TOC entries)
   - Suppresses administrative / webmaster contact headers (e.g. kalyan@geocities.com)
   - Suppresses publication source headers (e.g. PM-CHINTHAMANI-0003)
   - Guarantees autonomous didactic aphorisms (Aathichudi, Konrai Vendhan) and couplets remain eligible
3. Canonical embedding passage construction:
   - Tirukkural (PM-TK-*): 'passage: அதிகாரம்: {chapter}. {cleaned_text}' (with single-line couplet)
   - Didactic aphorisms: 'passage: {cleaned_text}' (pure aphorism, zero author/work clutter)
   - Sangam & Epic poetry: 'passage: {canto}: {cleaned_text}' (only when valid canto exists)
   - Generic fallback: 'passage: {cleaned_text}' (no fabricated metadata)
4. Dynamic corpus statistics:
   - Strictly read-only computation from data/processed/madurai_exact.db without hardcoded counts.

Invariants:
- data/processed/madurai_exact.db is strictly immutable and read-only.
- No morphological analysis is performed here (ThamizhiMorph handles morphology).
- No model inference, PyTorch, or vector indices are introduced in this phase.
"""

import os
import re
import sqlite3
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple, Union

# Asymmetric E5 prefix specifications (for embedding passage construction)
PASSAGE_PREFIX = "passage: "
QUERY_PREFIX = "query: "  # Documented for future query encoding; unused at runtime in Phase 3A

# Regular expression patterns for artifact detection and cleaning
RE_ZERO_WIDTH = re.compile(r"[\u200B-\u200D\uFEFF]")
RE_TRAILING_BACK = re.compile(r"(?:\r?\n\s*|\s+)\[?Back\]?\.?\s*$", flags=re.IGNORECASE)
RE_EMAIL = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+")

# Structural stub patterns
RE_PANN_STUB = re.compile(r"^பண்\s*[-:]\s*[\u0B80-\u0BFF\s]+$", flags=re.UNICODE)
RE_SPEAKER_KOOTRU = re.compile(
    r"^(?:(?:குறிஞ்சி|முல்லை|மருதம்|நெய்தல்|பாலை)\s*[-:]\s*)?[\u0B80-\u0BFF\s]{1,40}\s*கூற்று$",
    flags=re.UNICODE
)
RE_SPEAKER_SOLLIYATHU = re.compile(
    r"^[^\n\.;]{1,70}\s*(?:சொல்லியது|கூறியது|உரைத்தது)$",
    flags=re.UNICODE
)
RE_THINAI_POET = re.compile(
    r"^\d+\s+(?:குறிஞ்சி|முல்லை|மருதம்|நெய்தல்|பாலை)\s*-\s*[\u0B80-\u0BFF\s\(\)\?]+$",
    flags=re.UNICODE
)
RE_TOC_ETEXT = re.compile(
    r"^[^\n]+(?:மின்பதிப்பு|\(\d+\s*-\s*\d+\))\s*$",
    flags=re.UNICODE
)
RE_SECTION_STUB = re.compile(
    r"^(?:\d+\s+[\u0B80-\u0BFF\s]{2,25}|(?:அறத்து|பொருட்|காமத்து)ப்பால்(?:\s*\(.*?\))?.*)$",
    flags=re.UNICODE
)

# Works classified under classical Sangam and Epic literature
SANGAM_EPIC_WORKS = (
    "குறுந்தொகை",
    "நற்றிணை",
    "புறநானூறு",
    "அகநானூறு",
    "கலித்தொகை",
    "பரிபாடல்",
    "பதிற்றுப்பத்து",
    "சிலப்பதிகாரம்",
    "மணிமேகலை",
    "சீவக சிந்தாமணி",
)


def _get_field(chunk: Any, key: str, default: Any = None) -> Any:
    """
    Safely retrieve a field from a dict, sqlite3.Row, or object.
    """
    if isinstance(chunk, dict):
        return chunk.get(key, default)
    try:
        if hasattr(chunk, "keys") and key in chunk.keys():
            val = chunk[key]
            return val if val is not None else default
    except Exception:
        pass
    if hasattr(chunk, key):
        val = getattr(chunk, key)
        return val if val is not None else default
    return default


def clean_semantic_text(text: Optional[str]) -> str:
    """
    Apply deterministic semantic cleaning to a Project Madurai chunk text.
    
    1. Unicode NFC normalization.
    2. Strips zero-width characters (ZWSP, ZWNJ, ZWJ, BOM).
    3. Strips residual trailing navigation text ('Back', '[Back]', etc.)
       at the end of the passage without globally removing the word 'back'
       from legitimate contexts.
    4. Deterministic whitespace normalization:
       - Collapses repeated horizontal whitespace (spaces, tabs) per line.
       - Strips leading and trailing whitespace from each line.
       - Omits consecutive blank lines.
       - Strictly preserves poetic line breaks (\n) for multi-line verse.
    5. Preserves all Tamil characters, diacritics, and punctuation intact.
    
    :param text: Raw text from database (original_text or normalized_text).
    :return: Cleaned text string.
    """
    if not text:
        return ""
    if not isinstance(text, str):
        text = str(text)

    # 1. Unicode NFC normalization
    cleaned = unicodedata.normalize("NFC", text)

    # 2. Strip non-printing and zero-width characters
    cleaned = RE_ZERO_WIDTH.sub("", cleaned)

    # 3. Strip trailing navigation anchor: 'Back' / '[Back]'
    # Targets the known Project Madurai residual navigation pattern at the end of text
    cleaned = RE_TRAILING_BACK.sub("", cleaned)

    # If the text was solely a navigation artifact
    if cleaned.strip().lower() in ("back", "[back]", "back."):
        return ""

    # 4. Deterministic whitespace normalization line by line
    raw_lines = cleaned.splitlines()
    norm_lines: List[str] = []
    for line in raw_lines:
        line_clean = re.sub(r"[ \t]+", " ", line).strip()
        if line_clean:
            norm_lines.append(line_clean)

    return "\n".join(norm_lines)


def is_eligible_for_semantic_index(
    chunk: Mapping[str, Any],
    cleaned_text: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """
    Determine whether a Project Madurai chunk is eligible for semantic vector indexing.
    
    Returns (True, None) if eligible, or (False, suppression_reason) if suppressed.
    
    Suppression Categories:
    - 'empty_passage' / 'navigation_artifact': Text is empty or purely navigation artifact.
    - 'webmaster_contact': Webmaster contact information (e.g. kalyan@geocities.com in PM-SILAP_MADURAI-0003).
    - 'publication_source_header': Upstream publication header (e.g. PM-CHINTHAMANI-0003).
    - 'musical_stub': Musical mode metadata (e.g. 'பண் - நட்டபாடை' in Thevaram).
    - 'speaker_attribution': Standalone speaker colophon (e.g. 'குறிஞ்சி - தோழி கூற்று', 'தலைவி கூற்று').
    - 'structural_metadata': Standalone structural label (thinai-poet stubs, TOC entries with 'மின்பதிப்பு', etc.).
    
    Autonomous didactic aphorisms (Aathichudi, Konrai Vendhan) and poetic couplets
    are guaranteed to remain eligible.
    
    :param chunk: Mapping containing chunk metadata ('chunk_id', 'work', 'original_text', etc.).
    :param cleaned_text: Optional pre-cleaned text; if None, clean_semantic_text will be called.
    :return: (eligible: bool, suppression_reason: Optional[str])
    """
    raw_text = _get_field(chunk, "original_text") or _get_field(chunk, "normalized_text") or ""
    chunk_id = str(_get_field(chunk, "chunk_id") or "")

    if cleaned_text is None:
        cleaned_text = clean_semantic_text(raw_text)

    # 1. Empty or pure navigation artifact
    if not cleaned_text:
        is_back = bool(re.search(r"\bback\b", raw_text, flags=re.IGNORECASE))
        return False, "navigation_artifact" if is_back else "empty_passage"

    # 2. Webmaster contact filter (PM-SILAP_MADURAI-0003 or any contact email)
    if chunk_id == "PM-SILAP_MADURAI-0003" or RE_EMAIL.search(raw_text):
        return False, "webmaster_contact"

    # 3. Publication source header filter (PM-CHINTHAMANI-0003 or publishing colophon)
    raw_trimmed = raw_text.strip()
    if chunk_id == "PM-CHINTHAMANI-0003" or (
        raw_trimmed.startswith("Source:")
        and ("Published by:" in raw_trimmed or "பதிப்புக் கழகம்" in raw_trimmed or "[Copy-right]" in raw_trimmed)
    ):
        return False, "publication_source_header"

    # 4. Musical pann metadata stub (e.g. 'பண் - நட்டபாடை', 'பண் - தக்கராகம்')
    if RE_PANN_STUB.match(cleaned_text):
        return False, "musical_stub"

    # 5. Standalone speaker attributions / colophons (e.g. 'குறிஞ்சி - தோழி கூற்று', '...சொல்லியது')
    if RE_SPEAKER_KOOTRU.match(cleaned_text) or RE_SPEAKER_SOLLIYATHU.match(cleaned_text):
        return False, "speaker_attribution"

    # 6. Standalone structural-only metadata labels (thinai-poet stubs, TOC stubs, section stubs)
    if (
        RE_THINAI_POET.match(cleaned_text)
        or RE_TOC_ETEXT.match(cleaned_text)
        or RE_SECTION_STUB.match(cleaned_text)
    ):
        return False, "structural_metadata"

    return True, None


def construct_canonical_embedding_text(
    chunk: Mapping[str, Any],
    cleaned_text: str
) -> str:
    """
    Construct the canonical embedding text representation for an eligible chunk.
    
    Format Rules:
    1. Tirukkural (PM-TK-*):
       Couplet lines are joined with space, prepended by valid chapter context:
       'passage: அதிகாரம்: {chapter}. {cleaned_text}'
       If chapter is missing or empty:
       'passage: {cleaned_text}'
    2. Autonomous Didactic Aphorisms (Aathichudi, Konrai Vendhan):
       Aphorism embedded directly with zero author/work/genre prepended:
       'passage: {cleaned_text}'
    3. Sangam & Epic Poetry:
       Prepend classical canto / kathai if genuinely present in metadata:
       'passage: {canto}: {cleaned_text}'
       If canto is missing or empty:
       'passage: {cleaned_text}'
    4. Generic Fallback:
       'passage: {cleaned_text}'
       (No fabricated metadata or author injection)
    
    :param chunk: Mapping containing metadata ('chunk_id', 'work', 'chapter', 'canto', etc.).
    :param cleaned_text: Cleaned passage string.
    :return: Canonical embedding string starting with 'passage: '.
    """
    chunk_id = str(_get_field(chunk, "chunk_id") or "")
    work = str(_get_field(chunk, "work") or "")
    chapter = str(_get_field(chunk, "chapter") or "").strip()
    canto = str(_get_field(chunk, "canto") or "").strip()

    # Category 1: Tirukkural couplets
    if chunk_id.startswith("PM-TK-") or work == "திருக்குறள்":
        kural_text = " ".join(cleaned_text.splitlines())
        if chapter:
            return f"{PASSAGE_PREFIX}அதிகாரம்: {chapter}. {kural_text}"
        return f"{PASSAGE_PREFIX}{kural_text}"

    # Category 2: Didactic aphorisms (Aathichudi, Konrai Vendhan)
    if (
        chunk_id.startswith("PM-AATHI-")
        or chunk_id.startswith("PM-KONRAI-")
        or work in ("ஆத்திசூடி", "கொன்றை வேந்தன்")
    ):
        return f"{PASSAGE_PREFIX}{cleaned_text}"

    # Category 3: Sangam and Epic literature
    is_sangam_or_epic = any(w in work for w in SANGAM_EPIC_WORKS) or _get_field(chunk, "period") in ("Sangam", "Epic")
    if is_sangam_or_epic:
        if canto:
            return f"{PASSAGE_PREFIX}{canto}: {cleaned_text}"
        return f"{PASSAGE_PREFIX}{cleaned_text}"

    # Category 4: Generic fallback (Bhakti, Didactic, Modern, etc.)
    return f"{PASSAGE_PREFIX}{cleaned_text}"


@dataclass(frozen=True)
class SemanticPreparation:
    """
    Derived semantic preparation container for a Project Madurai chunk.
    
    Attributes:
        eligible: Whether chunk is eligible for semantic vector indexing.
        cleaned_text: Cleaned semantic passage text.
        embedding_text: Canonical 'passage: ...' string if eligible; None if suppressed.
        suppression_reason: Deterministic reason code if suppressed; None if eligible.
    """
    eligible: bool
    cleaned_text: str
    embedding_text: Optional[str] = None
    suppression_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert container to standard Python dictionary."""
        return {
            "eligible": self.eligible,
            "cleaned_text": self.cleaned_text,
            "embedding_text": self.embedding_text,
            "suppression_reason": self.suppression_reason,
        }


def prepare_chunk(chunk: Mapping[str, Any]) -> SemanticPreparation:
    """
    High-level deterministic preparation entry point for a single Project Madurai chunk.
    
    Accepts any mapping or row object (e.g. sqlite3.Row, dict), cleans text,
    evaluates semantic eligibility, and constructs canonical embedding text.
    
    :param chunk: Raw chunk mapping from madurai_exact.db or test fixtures.
    :return: SemanticPreparation instance.
    """
    raw_text = _get_field(chunk, "original_text") or _get_field(chunk, "normalized_text") or ""
    cleaned_text = clean_semantic_text(raw_text)

    eligible, suppression_reason = is_eligible_for_semantic_index(chunk, cleaned_text=cleaned_text)

    if eligible:
        embedding_text = construct_canonical_embedding_text(chunk, cleaned_text)
        return SemanticPreparation(
            eligible=True,
            cleaned_text=cleaned_text,
            embedding_text=embedding_text,
            suppression_reason=None,
        )
    else:
        return SemanticPreparation(
            eligible=False,
            cleaned_text=cleaned_text,
            embedding_text=None,
            suppression_reason=suppression_reason,
        )


def get_corpus_statistics(
    db_path: Optional[Union[str, Path]] = None
) -> Dict[str, Any]:
    """
    Dynamically calculate corpus preprocessing and length distribution statistics
    directly from madurai_exact.db.
    
    Opens the database strictly read-only ('file:...mode=ro' with PRAGMA query_only = ON).
    Does NOT modify the database in any way.
    
    :param db_path: Optional path to madurai_exact.db. Defaults to data/processed/madurai_exact.db.
    :return: Dictionary containing dynamic counts, distributions, and suppression reasons.
    """
    if db_path is None:
        project_root = Path(__file__).resolve().parents[2]
        db_file = project_root / "data" / "processed" / "madurai_exact.db"
    else:
        db_file = Path(db_path).resolve()

    if not db_file.exists():
        raise FileNotFoundError(f"Project Madurai database not found at: {db_file}")

    # Explicit SQLite read-only connection
    uri = f"file:{db_file.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=10.0)
    conn.row_factory = sqlite3.Row

    try:
        cur = conn.cursor()
        cur.execute("PRAGMA query_only = ON;")
        cur.execute("SELECT * FROM chunks ORDER BY chunk_id ASC;")
        rows = cur.fetchall()
    finally:
        conn.close()

    total_chunks = len(rows)
    eligible_count = 0
    suppressed_count = 0

    reasons_breakdown: Dict[str, int] = {}
    length_dist_original: Dict[str, int] = {
        "<25": 0,
        "25-50": 0,
        "50-100": 0,
        "100-200": 0,
        "200-500": 0,
        ">500": 0,
    }
    length_dist_cleaned: Dict[str, int] = {
        "<25": 0,
        "25-50": 0,
        "50-100": 0,
        "100-200": 0,
        "200-500": 0,
        ">500": 0,
    }

    for row in rows:
        prep = prepare_chunk(row)
        orig_text = (_get_field(row, "original_text") or "").strip()
        cleaned_text = prep.cleaned_text

        # Length distribution - Original Text
        len_orig = len(orig_text)
        if len_orig < 25:
            length_dist_original["<25"] += 1
        elif len_orig <= 50:
            length_dist_original["25-50"] += 1
        elif len_orig <= 100:
            length_dist_original["50-100"] += 1
        elif len_orig <= 200:
            length_dist_original["100-200"] += 1
        elif len_orig <= 500:
            length_dist_original["200-500"] += 1
        else:
            length_dist_original[">500"] += 1

        # Length distribution - Cleaned Text
        len_clean = len(cleaned_text)
        if len_clean < 25:
            length_dist_cleaned["<25"] += 1
        elif len_clean <= 50:
            length_dist_cleaned["25-50"] += 1
        elif len_clean <= 100:
            length_dist_cleaned["50-100"] += 1
        elif len_clean <= 200:
            length_dist_cleaned["100-200"] += 1
        elif len_clean <= 500:
            length_dist_cleaned["200-500"] += 1
        else:
            length_dist_cleaned[">500"] += 1

        if prep.eligible:
            eligible_count += 1
        else:
            suppressed_count += 1
            reason = prep.suppression_reason or "unknown"
            reasons_breakdown[reason] = reasons_breakdown.get(reason, 0) + 1

    return {
        "total_chunks": total_chunks,
        "eligible_chunks": eligible_count,
        "suppressed_chunks": suppressed_count,
        "length_distribution": length_dist_original,
        "cleaned_length_distribution": length_dist_cleaned,
        "suppression_reasons": reasons_breakdown,
    }
