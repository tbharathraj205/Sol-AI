# SOL AI — Evidence & UnifiedResult Schemas Deep Dive

> **Source Files**:  
> - `backend/schemas/evidence.py` (54 lines)  
> - `backend/schemas/result.py` (31 lines)  
> **Document Purpose**: Complete technical reference and comparative analysis of SOL AI's foundational data structures.

---

## Table of Contents
1. [What is the Evidence Dataclass?](#1-what-is-the-evidence-dataclass)
2. [Complete Field Inventory of Evidence](#2-complete-field-inventory-of-evidence)
3. [Field Semantics & Definitions](#3-field-semantics--definitions)
4. [Required vs. Optional Fields](#4-required-vs-optional-fields)
5. [Concrete Evidence Examples Across All Resource Adapters](#5-concrete-evidence-examples-across-all-resource-adapters)
   - [ThamizhiMorph](#a-from-thamizhimorph)
   - [Tamil WordNet](#b-from-tamil-wordnet)
   - [Thani Thamizh Akarathi](#c-from-thani-thamizh-akarathi)
   - [Sentamizh Corpus](#d-from-sentamizh-corpus)
   - [Tamil Wiktionary](#e-from-tamil-wiktionary)
6. [What is UnifiedResult?](#6-what-is-unifiedresult)
7. [UnifiedResult Field Breakdown](#7-unifiedresult-field-breakdown)
8. [Lifecycle: How Evidence Becomes Part of UnifiedResult](#8-lifecycle-how-evidence-becomes-part-of-unifiedresult)
9. [Architectural Comparison: Evidence vs. UnifiedResult](#9-architectural-comparison-evidence-vs-unifiedresult)
10. [The Atomic Knowledge Model](#10-the-atomic-knowledge-model)
11. [Future-Proofing: Semantic / Vector Retrieval Integration](#11-future-proofing-semantic--vector-retrieval-integration)

---

## 1. What is the `Evidence` Dataclass?

Defined in `backend/schemas/evidence.py` (lines 6–53), `Evidence` is the **canonical atomic data container** of SOL AI.

In a heterogeneous linguistic architecture, different resources yield completely different types of information:
- A finite-state transducer returns morpheme tags.
- A dictionary returns a headword and definition.
- A semantic network returns hypernyms, relation codes, and synsets.
- A corpus returns verse lines, meter, poetics, and historical periods.

`Evidence` is the single normalized interface that unifies all four linguistic dimensions (morphological, lexical, semantic, and literary). Every resource adapter in `backend/resources/*` transforms its raw output into one or more `Evidence` objects before anything reaches the retrieval engine or the LLM.

---

## 2. Complete Field Inventory of `Evidence`

Here is the exact code definition from `backend/schemas/evidence.py`:

```python
@dataclass
class Evidence:
    surface: str
    lemma: Optional[str] = None
    source: str = ""
    evidence_type: str = ""
    meaning: Optional[str] = None
    english_meaning: Optional[str] = None
    pos: Optional[str] = None
    morphology: Optional[str] = None
    passage: Optional[str] = None
    work: Optional[str] = None
    author: Optional[str] = None
    period: Optional[str] = None
    genre: Optional[str] = None
    verse: Optional[str] = None
    line: Optional[str] = None
    relations: List[Any] = field(default_factory=list)
    source_url: Optional[str] = None
    source_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
```

---

## 3. Field Semantics & Definitions

| Field Name | Type | Meaning & Purpose in SOL AI |
|---|---|---|
| **`surface`** | `str` | The exact surface token that was searched or evaluated (e.g., `"மரங்களில்"` or `"மரம்"`). |
| **`lemma`** | `Optional[str]` | The underlying dictionary headword or root form extracted from this specific piece of evidence (e.g., `"மரம்"`). |
| **`source`** | `str` | The canonical name of the resource producing the record (`"ThamizhiMorph"`, `"Thani Thamizh Akarathi"`, `"Tamil WordNet"`, `"Sentamizh"`, or `"Tamil Wiktionary"`). |
| **`evidence_type`** | `str` | The category of evidence: `"morphology"`, `"lexical"`, `"literary_context"`, or `"frequency"`. Used by `EvidencePack` for category grouping. |
| **`meaning`** | `Optional[str]` | The Tamil definition or gloss retrieved from a lexicon or modern commentary. |
| **`english_meaning`**| `Optional[str]` | English translation of the definition, if available in the source or translation layer. |
| **`pos`** | `Optional[str]` | Part of speech (`"noun"`, `"verb"`, `"Noun"`, `"Verb"`, etc.). |
| **`morphology`** | `Optional[str]` | Morphological breakdown string (e.g., `"noun+pl+loc"` or `"fin+sim+past=த்+3pl=ஆர்கள்"`). |
| **`passage`** | `Optional[str]` | The actual classical verse, poetry line, or literary quotation text. |
| **`work`** | `Optional[str]` | Name of the classical work (e.g., `"புறநானூறு"`, `"குறுந்தொகை"`, `"மணிமேகலை"`, `"தேவாரம்"`). |
| **`author`** | `Optional[str]` | Poet, author, or speaker role associated with the passage. |
| **`period`** | `Optional[str]` | Historical timeframe (e.g., `"சங்க காலம்"`, `"3rd century BCE – 3rd century CE"`). |
| **`genre`** | `Optional[str]` | Literary layer or classification (e.g., `"Sangam"`, `"Bhakti"`, `"Epic"`). |
| **`verse`** | `Optional[str]` | Verse number or chapter index (e.g., `"182"`, `"42"`, `"392"`). |
| **`line`** | `Optional[str]` | Specific line number within a poem. |
| **`relations`** | `List[Any]` | Related semantic terms, synonyms, or synset identifiers. |
| **`source_url`** | `Optional[str]` | Online link or digital archive URL for the record. |
| **`source_id`** | `Optional[str]` | Unique deterministic provenance identifier (e.g., `"wordnet:twn:2947"`, `"verse_PUR-182"`). |
| **`metadata`** | `Dict[str, Any]` | Flexible dictionary holding resource-specific raw properties: `status` (`"FOUND"` / `"NOT_FOUND"` / `"ERROR"`), `analysis_type` (`"core"` / `"guesser"`), `thinai`, `turai`, `corpus_frequency`, `raw_foma_output`, etc. |

---

## 4. Required vs. Optional Fields

Python `@dataclass` fields without a default value are positional and mandatory. Fields with default values (`= None`, `= ""`, or `= field(...)`) are optional.

### Strictly Required Field:
- **`surface: str`** — The only positional argument without a default value. An `Evidence` object cannot be instantiated without specifying the query surface string.

### Optional Fields (all have defaults):
- Defaults to `None`: `lemma`, `meaning`, `english_meaning`, `pos`, `morphology`, `passage`, `work`, `author`, `period`, `genre`, `verse`, `line`, `source_url`, `source_id`.
- Defaults to empty string `""`: `source`, `evidence_type`.
- Defaults to empty list `[]`: `relations`.
- Defaults to empty dictionary `{}`: `metadata`.

---

## 5. Concrete Evidence Examples Across All Resource Adapters

### A. From `ThamizhiMorph` (`backend/resources/thamizhimorph.py`)
When querying `"மரங்களில்"`:
```python
Evidence(
    surface="மரங்களில்",
    lemma="மரம்",
    source="ThamizhiMorph",
    evidence_type="morphology",
    pos="noun",
    morphology="noun+pl+loc",
    metadata={
        "fst_model": "noun.fst",
        "analysis_type": "core",
        "raw_foma_output": "மரங்களில்\tமரம்+noun+pl+loc",
        "normalization_status": "NORMALIZED",
        "status": "FOUND"
    }
)
```

### B. From `Tamil WordNet` (`backend/resources/wordnet.py`)
1. **Lexical Synset Node Match** (for `"மரம்"`):
```python
Evidence(
    surface="மரம்",
    lemma="மரம்",
    source="Tamil WordNet",
    evidence_type="lexical",
    pos="Noun",
    meaning=None,  # AU-KBC dump glosses are 100% NULL
    source_id="wordnet:twn:2947",
    metadata={
        "nodeindex": "2947",
        "raw_label": "maram",
        "relation_code": "3",
        "feature_code": "1",
        "hypernym": "தாவரம்",
        "hypercount": 1,
        "corpus_frequency": 428,
        "transliteration_status": "CONVERTED",
        "status": "FOUND"
    }
)
```
2. **Morphtable Root Mapping** (for `"மரங்களில்"`):
```python
Evidence(
    surface="மரங்களில்",
    lemma="மரம்",
    source="Tamil WordNet",
    evidence_type="morphology",
    source_id="wordnet:morphtable:மரங்களில்",
    metadata={
        "inflated_word": "மரங்களில்",
        "inflated_raw": "marangkaLil",
        "root_word": "மரம்",
        "root_raw": "maram",
        "corpus_frequency": 428,
        "transliteration_status": "CONVERTED",
        "status": "FOUND"
    }
)
```

### C. From `Thani Thamizh Akarathi` (`backend/resources/akarathi.py`)
When querying `"அகதி"`:
```python
Evidence(
    surface="அகதி",
    lemma="அகதி",
    source="Thani Thamizh Akarathi",
    evidence_type="lexical",
    meaning="ஏதிலி",
    source_id="akarathi:plain_text_dicts/Pav_Words.txt:அகதி:0",
    metadata={
        "source_file": "plain_text_dicts/Pav_Words.txt",
        "source_name": "Devaneya Pavanar Pure Tamil Dictionary",
        "entry_format": "WORD\n==\nMEANING",
        "raw_entry": "அகதி\n==\nஏதிலி",
        "status": "FOUND"
    }
)
```

### D. From `Sentamizh Corpus` (`backend/resources/sentamizh.py`)
When querying `"மரம்"`:
```python
Evidence(
    surface="மரம்",
    lemma=None,
    source="Sentamizh",
    evidence_type="literary_context",
    passage="மரம் கொல் தச்சன் கைவல் சிறாஅர்\nமழு உடை காட்டகத்து அற்றே...",
    work="புறநானூறு",
    author="ஔவையார்",
    period="3rd century BCE – 3rd century CE",
    genre="Sangam",
    verse="311",
    source_id="PUR-311",
    metadata={
        "verse_id": "PUR-311",
        "thinai": "வாகை",
        "turai": "வல்லாண் முல்லை",
        "akam_or_puram": "புறம்",
        "speaker_role": "புலவர்",
        "rasa_primary": "வீரம்",
        "cultural_context": "போர்க்கள வீரம்",
        "english": "Like an axe-wielding carpenter's boy entering the forest...",
        "status": "FOUND"
    }
)
```

### E. From `Tamil Wiktionary` (`backend/resources/wiktionary.py`)
When querying `"வீடு"`:
```python
Evidence(
    surface="வீடு",
    lemma="வீடு",
    source="Tamil Wiktionary",
    evidence_type="lexical",
    meaning="மனிதர்கள் வசிப்பதற்கென கட்டப்பட்ட கட்டிடம்; இல்லம்; மனை.",
    source_id="wiktionary:வீடு:0",
    metadata={
        "status": "FOUND"
    }
)
```

---

## 6. What is `UnifiedResult`?

Defined in `backend/schemas/result.py` (lines 7–31), `UnifiedResult` is the **aggregate search result** generated at the end of the deterministic retrieval phase.

While `Evidence` represents a single atomic discovery from one database, `UnifiedResult` is the unified envelope that bundles all discovered evidence items together, provides cross-source agreement calculations, tracks candidate lemmas, and documents per-resource status codes.

---

## 7. `UnifiedResult` Field Breakdown

Here is the exact code definition from `backend/schemas/result.py`:

```python
@dataclass
class UnifiedResult:
    query: str
    normalized_query: str
    lemma_candidates: List[str] = field(default_factory=list)
    evidence: List[Evidence] = field(default_factory=list)
    resource_summary: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    cross_resource_support: Dict[str, List[str]] = field(default_factory=dict)
    errors: Dict[str, str] = field(default_factory=dict)
```

| Field Name | Type | Description |
|---|---|---|
| **`query`** | `str` | The exact surface query entered by the user (e.g., `"மரங்களில்"`). |
| **`normalized_query`** | `str` | The NFC Unicode normalized surface query. |
| **`lemma_candidates`** | `List[str]` | Deduplicated, sorted list of candidate root words discovered across all morphological and lexical adapters (e.g., `["மரம்"]`). |
| **`evidence`** | `List[Evidence]` | The complete list of sorted, deduplicated `Evidence` objects collected from all adapters in Pass 1 and Pass 2. |
| **`resource_summary`** | `Dict[str, Dict[str, Any]]` | Per-adapter summary: `{ "ThamizhiMorph": {"status": "FOUND", "total_entries": 3, "core_analyses": 1, ...}, ... }`. |
| **`cross_resource_support`** | `Dict[str, List[str]]` | Map showing which candidate terms are supported by which resources: `{"மரம்": ["Sentamizh", "Tamil WordNet", "ThamizhiMorph", "Thani Thamizh Akarathi"]}`. |
| **`errors`** | `Dict[str, str]` | Log of any resource exceptions encountered during execution: `{"ThamizhiMorph": "flookup not found"}`. |

---

## 8. Lifecycle: How `Evidence` Becomes Part of `UnifiedResult`

1. **Generation**: In Pass 1 and Pass 2 of `RetrievalEngine.search()`, each adapter's `.lookup()` returns a `List[Evidence]`.
2. **Deduplication**: `add_evidence()` filters them through `seen_evidence_keys = (source, evidence_type, surface, lemma, passage, source_id)` and appends to `all_evidence: List[Evidence]`.
3. **Prioritization**: `EvidenceAggregator.aggregate()` calculates a 3-tuple sort key for each `Evidence` object:
   - Analysis priority: Core FST (`10`) vs. Guesser FST (`5`).
   - Match priority: Exact surface match (`8`) vs. Discovered lemma match (`6`).
   - Evidence type priority: Direct evidence (`8`) vs. Frequency count (`2`).
4. **Assembly**: `EvidenceAggregator.aggregate()` constructs `UnifiedResult` by placing `sorted_evidence` into `result.evidence`.

---

## 9. Architectural Comparison: `Evidence` vs. `UnifiedResult`

| Aspect | `Evidence` (`evidence.py`) | `UnifiedResult` (`result.py`) |
|---|---|---|
| **Scope** | **Microscopic (Atomic)**: Represents one single fact, definition, verse, or morpheme analysis from one resource. | **Macroscopic (Aggregate)**: Represents the entire search response across all resources. |
| **Cardinality** | Multiple instances exist per search (typically 5 to 30 objects). | Exactly **one** instance returned per search. |
| **Provenance** | Points to a single `source` (e.g. `"Sentamizh"` or `"Tamil WordNet"`). | Cross-resource provenance map (`cross_resource_support`, `resource_summary`). |
| **Errors** | Represents a single adapter failure as an error tombstone (`metadata={"status": "ERROR"}`). | Stores global dictionary of errors across all failing adapters (`errors={"ThamizhiMorph": "..."}`). |
| **Consumers** | Consumed by `EvidenceAggregator`, `context_selector.py`, and `build_evidence_pack()`. | Consumed by `server.py`, `build_evidence_pack()`, and benchmark evaluation scripts. |

---

## 10. The Atomic Knowledge Model

An `Evidence` object does not try to tell the whole story of a word. Instead, it acts as an **immutable audit record** for one specific claim from one authoritative database:

- If ThamizhiMorph parses `"வந்தார்கள்"` as past-tense 3rd-person plural, that is **one Evidence object** (`evidence_type="morphology"`).
- If Devaneya Pavanar defines `"அகதி"` as `"ஏதிலி"`, that is **one Evidence object** (`evidence_type="lexical"`).
- If Neelambigai Ammaiyar also defines `"அகதி"` as `"வறியன், யாருமற்றவன்"`, that is a **second distinct Evidence object** (`evidence_type="lexical"`).
- If Purananuru verse 182 contains the word `"அமிழ்தம்"`, that is **one Evidence object** (`evidence_type="literary_context"`).

By keeping each piece of evidence atomic:
1. Different dictionaries never overwrite or squash each other's distinct historical definitions.
2. Contradictory analyses (e.g., noun vs. verb homonym parses) can coexist side-by-side.
3. The LLM interpretation layer receives exact provenance for every single claim.

---

## 11. Future-Proofing: Semantic / Vector Retrieval Integration

If a semantic/vector retrieval system is added later (e.g., retrieving classical verses by theme, mood, or meaning), **how must it populate an `Evidence` object so downstream components process it transparently without knowing it came from a vector store?**

Because all downstream layers (`aggregator.py`, `context_selector.py`, `evidence_pack.py`, `server.py`, and `prompts.py`) read only the standardized attributes of `Evidence`, a vector retrieval adapter simply needs to populate the standard fields:

```python
# Concrete Example: Semantic Verse Retrieval via Vector Embeddings
Evidence(
    surface=query,                          # The user's semantic search term or concept (e.g., "கடல் அலைகள்")
    lemma=None,                             # Or thematic keyword
    source="Sentamizh Semantic Search",     # Canonical source name
    evidence_type="literary_context",       # Tells EvidencePack and UI this is a literary quote
    passage=verse_text,                     # The retrieved classical Tamil passage
    work=work_name,                         # e.g., "நற்றிணை"
    author=author_name,                     # e.g., "கபிலர்"
    period="சங்க காலம்",                    # e.g., "Sangam Era"
    genre="சங்க இலக்கியம்",                  # e.g., "Ettuthokai"
    verse=str(verse_number),                # e.g., "172"
    source_id=f"vector:sentamizh:{verse_id}",
    metadata={
        "status": "FOUND",                  # CRITICAL: Must be "FOUND" to pass aggregator filters
        "retrieval_method": "vector_cosine",# Documents semantic provenance
        "similarity_score": 0.894,          # Embedding cosine similarity
        "vector_model": "bge-m3",           # Embedding model used
        "matched_theme": "நெய்தல் திணை",   # Thematic concept matched
        "modern_tamil": modern_gloss        # Modern translation for UI
    }
)
```

### Why this works with zero architectural changes:
1. **Aggregator filtering**: `aggregator.py` checks `ev.metadata.get("status") == "FOUND"`. The vector result passes immediately.
2. **Context selection**: `context_selector.py` inspects `ev.passage`, `ev.work`, `ev.period`, and `ev.meaning` to score the passage and enforce work diversity.
3. **Evidence pack categorization**: `evidence_pack.py` checks `ev.evidence_type in ["literary", "corpus", "citation"]` (or `"literary_context"`), routing the vector match directly into `pack.literary_evidence`.
4. **Server override**: `server.py` extracts `pack.literary_evidence` into `LiteraryContextItem` objects and injects them into the final JSON response.
5. **Frontend rendering**: `LiteraryContextCard.jsx` renders the vector-retrieved verse in classical Tamil typography with period badges and translation without knowing whether it came from a SQL exact match or a high-dimensional vector index.
