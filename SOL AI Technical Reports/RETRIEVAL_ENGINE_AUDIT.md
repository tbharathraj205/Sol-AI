# SOL AI — RetrievalEngine (`backend/retrieval/engine.py`) Technical Deep Dive

> **Module**: `backend.retrieval.engine`  
> **Source File**: `backend/retrieval/engine.py`  
> **Line Count**: 150 lines  
> **Document Purpose**: Exhaustive code-level audit and architectural walkthrough of the deterministic retrieval coordinator.

---

## Table of Contents
1. [Imports and Dependencies](#1-imports-and-dependencies)
2. [RetrievalEngine Class](#2-retrievalengine-class)
3. [__init__ / Initialization](#3-__init__--initialization)
4. [search() Function](#4-search-function)
5. [Query Normalization](#5-query-normalization)
6. [Pass 1 — Surface Lookup Across All Adapters](#6-pass-1--surface-lookup-across-all-adapters)
7. [Error Handling Across Individual Adapters](#7-error-handling-across-individual-adapters)
8. [Candidate Lemma Extraction](#8-candidate-lemma-extraction)
9. [Pass 2 — Secondary Lookup for Candidate Lemmas](#9-pass-2--secondary-lookup-for-candidate-lemmas)
10. [Deduplication Mechanism](#10-deduplication-mechanism)
11. [Data Handoff to EvidenceAggregator](#11-data-handoff-to-evidenceaggregator)
12. [UnifiedResult Return Structure](#12-unifiedresult-return-structure)
13. [Concrete Execution Example: query = "மரங்களில்"](#13-concrete-execution-example-query--மரங்களில்)
14. [Architectural Responsibilities & Vector Integration](#14-architectural-responsibilities--vector-integration)

---

## 1. Imports and Dependencies

```python
# Lines 1-3
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# Lines 5-12
from backend.query.normalizer import QueryNormalizer
from backend.schemas.evidence import Evidence
from backend.schemas.result import UnifiedResult
from backend.resources.thamizhimorph import ThamizhiMorphAdapter
from backend.resources.akarathi import ThaniThamizhAkarathiAdapter
from backend.resources.wordnet import TamilWordNetAdapter
from backend.resources.sentamizh import SentamizhAdapter
from backend.retrieval.aggregator import EvidenceAggregator
```

### Purpose of Each Dependency:
1. **`sys`, `pathlib.Path`, `typing`**: Python standard library utilities for filesystem resolution and type signatures (`List`, `Dict`, `Any`, `Optional`).
2. **`QueryNormalizer`** (`backend/query/normalizer.py`): Performs Unicode NFC composition and whitespace cleanup.
3. **`Evidence`** (`backend/schemas/evidence.py`): Canonical dataclass representing an atomic linguistic discovery (POS tag, morpheme chain, dictionary definition, Sangam verse passage, or corpus frequency).
4. **`UnifiedResult`** (`backend/schemas/result.py`): Top-level dataclass holding sorted evidence, candidate root lemmas, cross-resource agreements, and error logs.
5. **Core Resource Adapters**:
   - `ThamizhiMorphAdapter` (`backend/resources/thamizhimorph.py`): Foma Finite-State Transducer (FST) morphological analyzer.
   - `ThaniThamizhAkarathiAdapter` (`backend/resources/akarathi.py`): Purist Tamil dictionary adapter.
   - `TamilWordNetAdapter` (`backend/resources/wordnet.py`): SQLite Tamil WordNet graph, morphtable, and frequency index.
   - `SentamizhAdapter` (`backend/resources/sentamizh.py`): SQLite Sangam literary corpus verse index.
6. **`EvidenceAggregator`** (`backend/retrieval/aggregator.py`): Multi-signal sorting, cross-resource support evaluator, and summary builder.
7. *(Note: `TamilWiktionaryAdapter` is not imported here at the top; it is lazily imported inside `__init__`)*.

---

## 2. RetrievalEngine Class

- **Defined at**: Line 15
- **Role**: Central coordinator / facade for deterministic retrieval across all Tamil lexical, morphological, and literary sources.
- **Design Pattern**: Facade & Coordinator. Holds references to adapters, receives queries, coordinates the two-pass retrieval flow, and passes accumulated evidence to the aggregator.

---

## 3. `__init__` / Initialization

```python
# Lines 22-53
def __init__(
    self,
    thamizhimorph: Optional[ThamizhiMorphAdapter] = None,
    akarathi: Optional[ThaniThamizhAkarathiAdapter] = None,
    wordnet: Optional[TamilWordNetAdapter] = None,
    sentamizh: Optional[SentamizhAdapter] = None
):
    self.thamizhimorph = thamizhimorph or ThamizhiMorphAdapter()
    self.akarathi = akarathi or ThaniThamizhAkarathiAdapter()
    self.wordnet = wordnet or TamilWordNetAdapter()
    self.sentamizh = sentamizh or SentamizhAdapter()
    
    # Lazy load Wiktionary so it doesn't fail if the db is still building
    try:
        from backend.resources.wiktionary import TamilWiktionaryAdapter
        self.wiktionary = TamilWiktionaryAdapter()
    except ImportError:
        self.wiktionary = None

    self.adapters = {
        "ThamizhiMorph": self.thamizhimorph,
        "Tamil Wiktionary": self.wiktionary,
        "Thani Thamizh Akarathi": self.akarathi,
        "Tamil WordNet": self.wordnet,
        "Sentamizh": self.sentamizh
    }
    # Remove any None adapters
    self.adapters = {k: v for k, v in self.adapters.items() if v is not None}
```

### Breakdown:
- **Inputs**: Optional adapter instances (allowing dependency injection for mock testing).
- **Outputs**: Initialized `RetrievalEngine` instance.
- **Line-by-line logic**:
  - **Lines 33–36**: Instantiates default adapters if none are injected (`self.thamizhimorph`, `self.akarathi`, `self.wordnet`, `self.sentamizh`).
    - *Startup cost note*: When `ThaniThamizhAkarathiAdapter()` initializes, it loads the 140.8 MB `akarathi_index.json` into memory. When `TamilWordNetAdapter()` and `SentamizhAdapter()` initialize, they verify their respective SQLite `.db` files exist.
  - **Lines 39–43**: Dynamically imports `TamilWiktionaryAdapter` inside a `try/except ImportError` block. If missing or failing import, it falls back to `self.wiktionary = None`.
  - **Lines 45–53**: Packs all active adapters into an ordered dictionary `self.adapters` mapping string names to instances, filtering out any `None` values.

---

## 4. `search()` Function

- **Defined at**: Line 55
- **Signature**: `def search(self, query: str) -> UnifiedResult:`
- **Inputs**: `query: str` (The raw user input string, e.g., `"மரங்களில்"`).
- **Outputs**: `UnifiedResult` (The complete aggregated retrieval packet).
- **Overall Purpose**: Executes the complete deterministic search pipeline: normalization -> Pass 1 surface lookup -> lemma candidate extraction -> Pass 2 secondary root lookup -> evidence aggregation.

---

## 5. Query Normalization

```python
# Lines 64-76
norm_query = QueryNormalizer.normalize(query)
target = norm_query.normalized_query

if not target:
    return UnifiedResult(
        query=query,
        normalized_query="",
        lemma_candidates=[],
        evidence=[],
        resource_summary={},
        cross_resource_support={},
        errors={}
    )
```

### Line-by-line logic:
- **Line 64**: Passes raw `query` to `QueryNormalizer.normalize()`.
- **Line 65**: Extracts `target = norm_query.normalized_query`. This string has been trimmed of leading/trailing whitespace and normalized to Unicode NFC (canonical composition).
- **Lines 67–76**: Guard clause for empty or whitespace-only inputs. If `target` is empty string `""`, it immediately aborts further lookup and returns an empty `UnifiedResult` with empty lists and dictionaries.

---

## 6. Pass 1 — Surface Lookup Across All Adapters

```python
# Lines 78-94
all_evidence: List[Evidence] = []
errors: Dict[str, str] = {}
seen_evidence_keys = set()

# Helper to safely append deduplicated evidence (Lines 83-88)
def add_evidence(ev_list: List[Evidence]):
    for ev in ev_list:
        key = (ev.source, ev.evidence_type, ev.surface, ev.lemma, ev.passage, ev.source_id)
        if key not in seen_evidence_keys:
            seen_evidence_keys.add(key)
            all_evidence.append(ev)

# Pass 1 Loop (Lines 91-94)
for name, adapter in self.adapters.items():
    try:
        evs = adapter.lookup(target)
        add_evidence(evs)
    ...
```

### Line-by-line logic:
- **Lines 78–80**: Sets up:
  - `all_evidence`: Master accumulator list for all `Evidence` objects collected during both passes.
  - `errors`: Dictionary tracking `{adapter_name: error_message}` if any resource fails.
  - `seen_evidence_keys`: Set tracking unique tuples to prevent duplicate entries.
- **Lines 91–94**: Iterates through `self.adapters` in order:
  1. `"ThamizhiMorph"`: calls `ThamizhiMorphAdapter.lookup(target)` (runs FST transducers via `flookup`).
  2. `"Tamil Wiktionary"`: calls `TamilWiktionaryAdapter.lookup(target)` (queries SQLite `definitions`).
  3. `"Thani Thamizh Akarathi"`: calls `ThaniThamizhAkarathiAdapter.lookup(target)` (queries in-memory JSON dict).
  4. `"Tamil WordNet"`: calls `TamilWordNetAdapter.lookup(target)` (queries SQLite `twn_index`, `morphtable_index`, etc.).
  5. `"Sentamizh"`: calls `SentamizhAdapter.lookup(target)` (queries SQLite `verse_tokens` JOIN `verses`).
- Every adapter returns a `List[Evidence]`. Each returned list is immediately passed to `add_evidence(evs)`.

---

## 7. Error Handling Across Individual Adapters

```python
# Lines 95-108
    except Exception as e:
        errors[name] = str(e)
        # Ensure a graceful error evidence object is attached
        add_evidence([
            Evidence(
                surface=target,
                lemma=None,
                source=name,
                metadata={
                    "error": str(e),
                    "status": "ERROR"
                }
            )
        ])
```

### Line-by-line logic:
- **Line 95**: Every adapter call is enclosed in its own `try/except Exception` boundary.
- **Line 96**: If an adapter raises an exception (e.g., Foma binary missing, corrupted SQLite file, missing table), the exception string is captured: `errors[name] = str(e)`.
- **Lines 98–108**: Instead of crashing the server or failing silently, an explicit `Evidence` tombstone object is created with:
  - `surface = target`
  - `lemma = None`
  - `source = name` (the failing adapter name)
  - `metadata = {"error": str(e), "status": "ERROR"}`
- This error object is appended to `all_evidence` so that downstream layers and the user UI can inspect the exact provenance failure without throwing an unhandled HTTP 500 error.

---

## 8. Candidate Lemma Extraction

```python
# Lines 111-117
candidate_lemmas = set()
for ev in all_evidence:
    if ev.metadata.get("status") == "FOUND":
        if ev.lemma and ev.lemma != target:
            candidate_lemmas.add(ev.lemma.strip())
        if ev.metadata.get("root_word") and ev.metadata.get("root_word") != target:
            candidate_lemmas.add(ev.metadata.get("root_word").strip())
```

### Line-by-line logic:
- **Line 111**: `candidate_lemmas` is initialized as a Python `set()` to ensure roots are deduplicated.
- **Line 112**: Iterates through all `Evidence` objects collected in Pass 1.
- **Line 113**: Filters strictly for `ev.metadata.get("status") == "FOUND"`. (Ignored: `NOT_FOUND` and `ERROR` objects).
- **Lines 114–115**: If `ev.lemma` is present and **is not equal to the original surface target** (`ev.lemma != target`), it is added to `candidate_lemmas`.
  - *Example*: If `target` is `"மரங்களில்"`, and `ThamizhiMorph` returned `ev.lemma = "மரம்"`, `"மரம்"` is added.
- **Lines 116–117**: If `ev.metadata.get("root_word")` is present (from WordNet morphtable mappings) and is not equal to `target`, it is added.
  - *Example*: `TamilWordNet` morphtable mapping produces `root_word = "மரம்"`.

---

## 9. Pass 2 — Secondary Lookup for Candidate Lemmas

```python
# Lines 120-139
secondary_adapters = {
    "Tamil Wiktionary": self.wiktionary,
    "Thani Thamizh Akarathi": self.akarathi,
    "Tamil WordNet": self.wordnet,
    "Sentamizh": self.sentamizh
}
secondary_adapters = {k: v for k, v in secondary_adapters.items() if v is not None}

for lemma in candidate_lemmas:
    for name, adapter in secondary_adapters.items():
        if name in errors:
            continue
        try:
            evs = adapter.lookup(lemma)
            # Filter out NOT_FOUND responses for secondary candidate lemma queries
            found_evs = [e for e in evs if e.metadata.get("status") == "FOUND"]
            add_evidence(found_evs)
        except Exception as e:
            # Do not overwrite primary error if secondary lookup fails
            pass
```

### Why these specific adapters:
- **Excluded**: `ThamizhiMorph` is **excluded** from Pass 2.
  - *Reason*: `ThamizhiMorph` was already used in Pass 1 to discover the lemma. Calling the morphological parser again on the base root (e.g. analyzing `"மரம்"` after analyzing `"மரங்களில்"`) would just return the base lemma again and waste unnecessary FST execution cycles.
- **Included**: `Tamil Wiktionary`, `Thani Thamizh Akarathi`, `Tamil WordNet`, and `Sentamizh`.
  - *Reason*: An inflected surface word like `"மரங்களில்"` ("in the trees") does not exist as a dictionary headword in a pure lexicon like Thani Thamizh Akarathi, nor does Sentamizh have an exact token for every modern oblique case inflection. By querying the discovered lemma `"மரம்"` against lexical dictionaries and literary corpora, SOL AI retrieves:
    1. The dictionary definition of "tree" from Akarathi and Wiktionary.
    2. Senses, synsets, and hypernyms of "tree" from WordNet.
    3. Classical Sangam verses containing the root token `"மரம்"` from Sentamizh.
- **Line 130–131**: Skips any adapter that already threw an error in Pass 1 (`if name in errors: continue`).
- **Line 135**: Crucial filtering: `found_evs = [e for e in evs if e.metadata.get("status") == "FOUND"]`. If a dictionary does *not* contain the secondary lemma, that `NOT_FOUND` record is discarded so it does not pollute the primary query's evidence list.

---

## 10. Deduplication Mechanism

```python
# Lines 80, 83-88
seen_evidence_keys = set()

def add_evidence(ev_list: List[Evidence]):
    for ev in ev_list:
        key = (ev.source, ev.evidence_type, ev.surface, ev.lemma, ev.passage, ev.source_id)
        if key not in seen_evidence_keys:
            seen_evidence_keys.add(key)
            all_evidence.append(ev)
```

### Line-by-line logic:
- **Deduplication key**: A 6-field tuple:
  `key = (ev.source, ev.evidence_type, ev.surface, ev.lemma, ev.passage, ev.source_id)`
- **Mechanism**:
  - `seen_evidence_keys` persists across both Pass 1 and Pass 2.
  - When `add_evidence()` is called, each candidate `ev` has its key computed.
  - If `key` is already in `seen_evidence_keys`, the evidence item is discarded.
  - If `key` is new, it is added to `seen_evidence_keys`, and `ev` is appended to `all_evidence`.
  - This prevents duplicate verses if both surface form and lemma match the same verse, and prevents identical dictionary entries from being appended twice.

---

## 11. Data Handoff to EvidenceAggregator

```python
# Lines 142-147
result = EvidenceAggregator.aggregate(
    query=query,
    normalized_query=target,
    all_evidence=all_evidence,
    errors=errors
)

return result
```

### Line-by-line logic:
- `RetrievalEngine` delegates all ranking, cross-resource analysis, and summary generation to static method `EvidenceAggregator.aggregate()`.
- **Arguments passed**:
  - `query=query`: The original surface string as typed by the user.
  - `normalized_query=target`: The NFC-normalized string.
  - `all_evidence=all_evidence`: The flat, deduplicated list of all `Evidence` objects collected across Pass 1 and Pass 2 (including `FOUND`, `NOT_FOUND`, and `ERROR` objects).
  - `errors=errors`: Dictionary of adapter error strings.

---

## 12. UnifiedResult Return Structure

`EvidenceAggregator.aggregate()` returns a `UnifiedResult` dataclass instance (`backend/schemas/result.py`):

```python
@dataclass
class UnifiedResult:
    query: str
    normalized_query: str
    lemma_candidates: List[str]
    evidence: List[Evidence]
    resource_summary: Dict[str, Dict[str, Any]]
    cross_resource_support: Dict[str, List[str]]
    errors: Dict[str, str]
```

### Fields returned:
1. **`query`**: Original query string (e.g., `"மரங்களில்"`).
2. **`normalized_query`**: Normalized surface string (e.g., `"மரங்களில்"`).
3. **`lemma_candidates`**: Sorted list of all discovered unique candidate root lemmas (e.g., `["மரம்"]`).
4. **`evidence`**: The complete list of `Evidence` objects, sorted by priority score (Core FST analyses first, followed by Guesser FST, direct surface matches, lemma matches, and frequency-only matches).
5. **`resource_summary`**: Dictionary mapping each adapter name to its status (`FOUND`, `NOT_FOUND`, or `ERROR`) and entry counts.
6. **`cross_resource_support`**: Mapping of candidate strings to the list of resources that independently corroborated them (e.g., `{"மரம்": ["ThamizhiMorph", "Tamil WordNet", "Sentamizh", "Thani Thamizh Akarathi"]}`).
7. **`errors`**: Any captured resource error messages.

---

## 13. Concrete Execution Example: `query = "மரங்களில்"`

Step-by-step trace inside `engine.py` when `engine.search("மரங்களில்")` is invoked:

### Step 1: Normalization (Lines 64-65)
- `QueryNormalizer.normalize("மரங்களில்")` runs.
- `target` becomes `"மரங்களில்"` (Unicode NFC).

### Step 2: Pass 1 — Surface Form Lookup (Lines 91-94)
`engine.py` loops through `self.adapters`:
1. **`ThamizhiMorph.lookup("மரங்களில்")`**:
   - `noun.fst` matches!
   - Returns `Evidence` with `lemma="மரம்"`, `pos="noun"`, `morphology="noun+pl+loc"`, `status="FOUND"`, `analysis_type="core"`.
   - `noun-guess.fst` also returns guesser analyses.
   - All added to `all_evidence` via `add_evidence()`.
2. **`Tamil Wiktionary.lookup("மரங்களில்")`**:
   - SQLite query `SELECT * FROM definitions WHERE headword = 'மரங்களில்'` returns 0 rows.
   - Returns 1 `Evidence` with `status="NOT_FOUND"`. Added to `all_evidence`.
3. **`Thani Thamizh Akarathi.lookup("மரங்களில்")`**:
   - `self.index_data.get("மரங்களில்")` returns `[]`.
   - Returns 1 `Evidence` with `status="NOT_FOUND"`. Added to `all_evidence`.
4. **`Tamil WordNet.lookup("மரங்களில்")`**:
   - `morphtable_index WHERE inflated_unicode = 'மரங்களில்'` matches!
   - Returns `Evidence` with `lemma="மரம்"`, `root_word="மரம்"`, `status="FOUND"`. Added to `all_evidence`.
5. **`Sentamizh.lookup("மரங்களில்")`**:
   - Queries `verse_tokens WHERE token = 'மரங்களில்'`. (Returns 0 rows as ancient classical Sangam verses use older case endings). Returns `status="NOT_FOUND"`.

### Step 3: Candidate Lemma Extraction (Lines 111-117)
- `engine.py` scans `all_evidence` for `FOUND` items.
- Finds `ev.lemma = "மரம்"` from ThamizhiMorph. Since `"மரம்" != "மரங்களில்"`, adds `"மரம்"` to `candidate_lemmas`.
- Finds `ev.metadata["root_word"] = "மரம்"` from Tamil WordNet morphtable. Adds `"மரம்"` to `candidate_lemmas`.
- Result: `candidate_lemmas = {"மரம்"}`.

### Step 4: Pass 2 — Secondary Lookup for "மரம்" (Lines 128-139)
`engine.py` queries `secondary_adapters` for `"மரம்"`:
1. **`Tamil Wiktionary.lookup("மரம்")`**:
   - Matches! Returns definitions: `"தாவர வகை"`, `"உயர்ந்த தண்டுடைய தாவரம்"`. Only `FOUND` evidence appended to `all_evidence`.
2. **`Thani Thamizh Akarathi.lookup("மரம்")`**:
   - Matches! Returns entries from dictionary search index. Only `FOUND` evidence appended.
3. **`Tamil WordNet.lookup("மரம்")`**:
   - Matches! Returns `twn_index` node 2947 (POS: Noun, hypernym: தாவரம்). Appended.
4. **`Sentamizh.lookup("மரம்")`**:
   - Queries `verse_tokens WHERE token = 'மரம்'`.
   - Finds **24 verse occurrences** across Kuruntokai, Natrinai, Purananuru, and Manimekalai!
   - All 24 `FOUND` literary verse `Evidence` objects are appended to `all_evidence`.

### Step 5: Handoff to Aggregator (Lines 142-149)
- `EvidenceAggregator.aggregate()` receives the full pool of evidence for both `"மரங்களில்"` and `"மரம்"`.
- Calculates cross-resource support: `"மரம்"` is supported by `ThamizhiMorph`, `Tamil WordNet`, `Tamil Wiktionary`, `Thani Thamizh Akarathi`, and `Sentamizh`.
- Returns the sorted `UnifiedResult` back to caller.

---

## 14. Architectural Responsibilities & Vector Integration

### A. What is `engine.py` responsible for?
1. **Coordination**: Acts as the central dispatcher orchestrating communication between the API server and the underlying resource adapters.
2. **Two-Pass Expansion**: Connecting inflectional morphological analysis (Pass 1) to lexical and literary lookups (Pass 2). Without `engine.py`, inflected words would fail to find dictionary definitions or Sangam literature.
3. **Fault Tolerance / Error Boundaries**: Ensuring an exception inside one adapter (e.g. Foma FST binary failure) does not crash the entire search or prevent other resources (WordNet, Sentamizh) from returning data.
4. **Deduplication**: Ensuring that multiple passes or overlapping adapters do not flood the pipeline with identical evidence records.

---

### B. What is `engine.py` NOT responsible for?
1. **Data Parsing & Database Queries**: It does not know how SQLite tables work, how Foma FST lines are parsed, or how JSON files are structured. All resource-specific querying belongs entirely inside `backend/resources/*`.
2. **Linguistic Stemming & Normalization**: It does not implement Tamil grammatical or character composition rules. That belongs in `backend/query/normalizer.py`.
3. **Evidence Ranking & Scoring**: It does not prioritize Core FST over Guesser FST, nor does it rank exact surface matches over lemma matches. That belongs in `backend/retrieval/aggregator.py`.
4. **Literary Context Selection**: It does not decide which Sangam verses are best or enforce work diversity. That belongs in `backend/interpretation/context_selector.py`.
5. **AI Synthesis & Prompt Formatting**: It does not interact with Gemini, Groq, or prompt templates. That belongs in `backend/interpretation/*`.

---

### C. Where would semantic/vector retrieval eventually plug into this architecture?
Semantic/vector retrieval would plug into `engine.py` in two distinct places without altering the existing two-pass flow:

1. **As an additional Adapter in `self.adapters`**:
   - Create a `SentamizhSemanticAdapter` (or `VectorCorpusAdapter`) implementing the base `ResourceAdapter` interface.
   - Add it to `self.adapters["Sentamizh Semantic"] = self.vector_adapter` in `__init__`.
   - In Pass 1 or Pass 2, `engine.py` calls `adapter.lookup()`, which generates query embeddings and performs a vector nearest-neighbor search (e.g., against `sqlite-vec` or a vector store), returning matching passages as standard `Evidence(evidence_type="semantic_literary")` objects.
2. **As an optional Pass 3 (Thematic / Semantic Fallback Pass)**:
   - If Pass 1 and Pass 2 return zero literary evidence (e.g., for modern, rare, or abstract words), `engine.py` can invoke a Pass 3 semantic search to retrieve classical verses that express conceptually similar themes or meanings.

---

### D. What parts of `engine.py` should probably remain unchanged?
1. **The Abstract `ResourceAdapter` Calling Pattern**: The uniform `adapter.lookup(target)` interface ensures clean modularity.
2. **The `try/except` Fault Boundary Pattern (Lines 95–108)**: Wrapping adapter calls and converting failures into `Evidence(metadata={"status": "ERROR"})` is critical for production resilience.
3. **The 6-Tuple Deduplication Mechanism (`add_evidence`)**: Preserving unique evidence keys based on `(source, evidence_type, surface, lemma, passage, source_id)` is battle-tested and clean.
4. **The Handoff to `EvidenceAggregator`**: Keeping ranking, sorting, and cross-resource support calculations strictly outside `engine.py` preserves clean separation of concerns.
