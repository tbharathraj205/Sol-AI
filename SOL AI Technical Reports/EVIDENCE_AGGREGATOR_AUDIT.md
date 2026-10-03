# SOL AI — EvidenceAggregator (`backend/retrieval/aggregator.py`) Technical Audit

> **Module**: `backend.retrieval.aggregator`  
> **Source File**: `backend/retrieval/aggregator.py`  
> **Line Count**: 133 lines  
> **Document Purpose**: Exhaustive technical audit, code-level analysis, priority ranking breakdown, and future vector/semantic retrieval evaluation for the evidence aggregation layer.

---

## Table of Contents
1. [File and Module Overview](#1-file-and-module-overview)
2. [Complete Aggregation Lifecycle](#2-complete-aggregation-lifecycle)
3. [Evidence Filtering Logic](#3-evidence-filtering-logic)
4. [Evidence Ranking & Prioritization Engine](#4-evidence-ranking--prioritization-engine)
5. [Deduplication & Cross-Resource Support Analysis](#5-deduplication--cross-resource-support-analysis)
6. [UnifiedResult Assembly](#6-unifiedresult-assembly)
7. [Architectural Distinction: RetrievalEngine vs. EvidenceAggregator](#7-architectural-distinction-retrievalengine-vs-evidenceaggregator)
8. [Future Vector / Semantic Retrieval Interaction Analysis](#8-future-vector--semantic-retrieval-interaction-analysis)
9. [Minimal Evolutionary Architecture for Hybrid Retrieval](#9-minimal-evolutionary-architecture-for-hybrid-retrieval)
10. [Production Concerns & Risk Triage (P0, P1, P2)](#10-production-concerns--risk-triage-p0-p1-p2)
11. [Key Takeaways](#key-takeaways)

---

## 1. File and Module Overview

- **Exact File Path**: `backend/retrieval/aggregator.py`
- **Main Class**: `EvidenceAggregator` (lines 13–133)
- **Primary Function**: `EvidenceAggregator.aggregate(...)` (static method, lines 20–132)

### Imports & Dependencies
```python
# Lines 1-5
from typing import List, Dict, Any, Set
from collections import defaultdict

from backend.schemas.evidence import Evidence
from backend.schemas.result import UnifiedResult

# Lines 7-10 (Unused artifact)
try:
    from deep_translator import GoogleTranslator
except ImportError:
    GoogleTranslator = None
```

- **`typing` & `collections.defaultdict`**: Used for type hinting and grouping cross-resource support sets.
- **`Evidence` & `UnifiedResult`**: Consumes raw `Evidence` dataclass instances and returns the unified `UnifiedResult` envelope.
- **`deep_translator`**: Imported in lines 7–10 inside a `try/except` block, but **completely unused** throughout the rest of `aggregator.py`. (This is a harmless leftover from an earlier prototype).

### What `EvidenceAggregator` Is Responsible For:
1. **Status-Based Ingestion**: Filtering evidence records for valid `FOUND` statuses before computing candidates or cross-source corroboration.
2. **Candidate Lemma Harvesting**: Extracting unique root lemmas from `ev.lemma`, `ev.metadata["root_word"]`, and `ev.metadata["headword"]`.
3. **Cross-Resource Corroboration**: Computing an independent agreement mapping (`cross_resource_support`) documenting which external databases independently confirm each candidate term.
4. **Deterministic Multi-Tier Ranking**: Applying a strict 3-tuple priority scoring function to place high-confidence linguistic analyses (Core FST) and exact surface matches above fallback guesses and auxiliary data.
5. **Resource Statistics Summary**: Compiling per-adapter hit audits, entry counts, and Core vs. Guesser tallies.
6. **Result Packaging**: Assembling the final `UnifiedResult` object.

### What `EvidenceAggregator` Explicitly Does NOT Do:
1. **No I/O or Storage Operations**: It never opens SQLite connections, reads JSON files, spawns subprocesses, or makes network requests.
2. **No Secondary Retrieval**: It does not trigger second-pass lookups for discovered lemmas (that is strictly coordinated by `RetrievalEngine`).
3. **No Key-Level Deduplication**: It assumes initial deduplication was already performed by `seen_evidence_keys` in `RetrievalEngine.search()`.
4. **No Verse Capping or Work Diversity**: It does not limit the number of literary citations or enforce single-verse-per-work rules (that is delegated downstream to `SentamizhContextSelector`).
5. **No Schema Categorization for LLMs**: It does not bucket evidence into `morphology_evidence`, `lexical_evidence`, or `literary_evidence` (that is performed downstream by `build_evidence_pack`).
6. **No AI Synthesis**: It has zero knowledge of prompts, LLM models, or definitions generation.

---

## 2. Complete Aggregation Lifecycle

When `RetrievalEngine.search()` completes Pass 1 and Pass 2, it invokes:

```python
result = EvidenceAggregator.aggregate(
    query=query,
    normalized_query=target,
    all_evidence=all_evidence,
    errors=errors
)
```

The internal lifecycle proceeds in six deterministic stages:

```
all_evidence: List[Evidence]
  │
  ├─► [Stage 1: Filter FOUND]
  │     Extracts found_evidence = [e for e in all_evidence if e.status == "FOUND"]
  │
  ├─► [Stage 2: Candidate Lemma Extraction]
  │     Scans found_evidence for .lemma, .root_word, .headword
  │     Produces sorted_lemmas = ["மரம்"]
  │
  ├─► [Stage 3: Cross-Resource Support Mapping]
  │     all_targets = { normalized_query } ∪ sorted_lemmas
  │     Cross-matches each target against all found_evidence
  │     Produces cross_resource_support_dict = { "மரம்": ["ThamizhiMorph", "Tamil WordNet", ...] }
  │
  ├─► [Stage 4: Deterministic Priority Sorting]
  │     Calculates get_priority_key(ev) -> (analysis_score, match_score, type_score)
  │     Sorts entire all_evidence list (including NOT_FOUND & ERROR at the bottom)
  │
  ├─► [Stage 5: Resource Summary Statistics]
  │     Iterates over 5 canonical resources
  │     Calculates total entries, status, core_analyses, guesser_analyses
  │
  └─► [Stage 6: UnifiedResult Construction]
        Instantiates and returns UnifiedResult(...)
```

---

## 3. Evidence Filtering Logic

```python
# Line 37
found_evidence = [ev for ev in all_evidence if ev.metadata.get("status") == "FOUND"]
```

### Which Objects Are Accepted vs. Preserved:
1. **For Candidate Lemma Extraction & Cross-Support**:
   - **Accepted**: Only `Evidence` objects where `ev.metadata.get("status") == "FOUND"`.
   - **Ignored**: Records with `status == "NOT_FOUND"` or `status == "ERROR"`. If an adapter fails or finds nothing, it cannot propose root candidates or claim cross-resource agreement.
2. **For the Final `result.evidence` List**:
   - **All records are preserved**: The aggregator does **not** delete or drop `NOT_FOUND` or `ERROR` objects. They remain in the list so that callers (and the UI) can inspect the full provenance trail.
   - However, non-FOUND records receive a priority key of `(0, 0, 0)`:
     ```python
     # Lines 81-83
     status = ev.metadata.get("status", "")
     if status != "FOUND":
         return (0, 0, 0)
     ```
     This deterministically pushes all missing and failed records to the very end of the list.

---

## 4. Evidence Ranking & Prioritization Engine

The ranking engine in `aggregator.py` (lines 80–101) uses Python's stable `sorted(..., reverse=True)` with a **3-tuple lexicographical score**:

$$\text{Priority Key} = (\text{analysis\_score}, \text{match\_score}, \text{type\_score})$$

```python
def get_priority_key(ev: Evidence):
    status = ev.metadata.get("status", "")
    if status != "FOUND":
        return (0, 0, 0)
    
    # Tier 1: Linguistic Rigor
    analysis_score = 10
    if ev.metadata.get("analysis_type") == "guesser":
        analysis_score = 5

    # Tier 2: Surface vs. Discovered Lemma Proximity
    match_score = 8
    if ev.surface != normalized_query and ev.lemma == normalized_query:
        match_score = 6
    elif ev.surface != normalized_query:
        match_score = 4

    # Tier 3: Substantive Evidence vs. Statistical Metadata
    type_score = 8
    if ev.evidence_type == "frequency":
        type_score = 2

    return (analysis_score, match_score, type_score)
```

### Exact Numeric Factors:

#### Tier 1: `analysis_score` (Linguistic Rigor)
- **`10` points**: Core linguistic analyses (transducers built from formal lexicons like `noun.fst`, `verb-*.fst`), lexical dictionary definitions, and verified literary verses.
- **`5` points**: Fallback suffix-guessing transducers (`analysis_type == "guesser"`, such as `noun-guess.fst`, `verb-guess.fst`).
- **Rationale**: A guesser FST must never displace an exact core dictionary parse.

#### Tier 2: `match_score` (Query Surface Proximity)
- **`8` points**: Direct surface match (`ev.surface == normalized_query`). The record was found directly for the word the user typed.
- **`6` points**: Lemma-to-query match (`ev.surface != normalized_query and ev.lemma == normalized_query`).
- **`4` points**: Secondary discovered lemma match (`ev.surface != normalized_query`). Evidence retrieved in Pass 2 where the surface form is a discovered root (e.g., surface is `"மரம்"` while query was `"மரங்களில்"`).
- **Rationale**: What the user actually typed takes precedence over secondary derivations.

#### Tier 3: `type_score` (Evidence Substantiveness)
- **`8` points**: Substantive semantic evidence (`morphology`, `lexical`, `literary_context`).
- **`2` points**: Auxiliary statistical evidence (`evidence_type == "frequency"`, e.g. raw corpus word frequency counts from Tamil WordNet).
- **Rationale**: A dictionary definition or classical verse is fundamentally more informative than a bare frequency count.

---

### Concrete Ranking Walkthrough: `query = "மரங்களில்"`

When `query = "மரங்களில்"` is processed, `all_evidence` contains records from both Pass 1 (surface `"மரங்களில்"`) and Pass 2 (lemma `"மரம்"`). Here is how the aggregator ranks them:

| Rank | Evidence Item | Source | Surface | Lemma / Root | Tier 1 (Analysis) | Tier 2 (Match) | Tier 3 (Type) | Final Tuple | Why It Ranks Here |
|---|---|---|---|---|---|---|---|---|---|
| **1 (Tie)** | Core Noun Parse | ThamizhiMorph | `மரங்களில்` | `மரம்` | 10 | 8 | 8 | **`(10, 8, 8)`** | Direct surface match from core FST (`noun.fst`) |
| **1 (Tie)** | Morphtable Root Mapping | Tamil WordNet | `மரங்களில்` | `மரம்` | 10 | 8 | 8 | **`(10, 8, 8)`** | Direct surface match mapping inflated form to root |
| **3** | WordNet Frequency | Tamil WordNet | `மரங்களில்` | `None` | 10 | 8 | 2 | **`(10, 8, 2)`** | Direct surface match, but penalized for being frequency-only |
| **4** | Guesser Noun Parse | ThamizhiMorph | `மரங்களில்` | `மரம்` | 5 | 8 | 8 | **`(5, 8, 8)`** | Direct surface match, but penalized for coming from `noun-guess.fst` |
| **5 (Tie)** | Classical Verses (24x) | Sentamizh | `மரம்` | `None` | 10 | 4 | 8 | **`(10, 4, 8)`** | Substantive verse evidence, but retrieved via secondary lemma (`surface != query`) |
| **5 (Tie)** | Lexical Definitions | Akarathi / Wiktionary | `மரம்` | `மரம்` | 10 | 4 | 8 | **`(10, 4, 8)`** | Substantive definitions, but retrieved via secondary lemma |
| **5 (Tie)** | Synset Node | Tamil WordNet | `மரம்` | `மரம்` | 10 | 4 | 8 | **`(10, 4, 8)`** | WordNet node 2947, retrieved via secondary lemma |
| **Last** | Missing Surface Lookup | Akarathi | `மரங்களில்` | `None` | 0 | 0 | 0 | **`(0, 0, 0)`** | `NOT_FOUND` record from Pass 1 sinks to the bottom |

---

## 5. Deduplication & Cross-Resource Support Analysis

### Does the Aggregator Deduplicate?
**No.** `aggregator.py` does not contain a deduplication loop. Deduplication is performed exclusively inside `RetrievalEngine.search()` (lines 83–88) via `seen_evidence_keys = (source, evidence_type, surface, lemma, passage, source_id)` before calling the aggregator.

### How `cross_resource_support` Is Constructed
The aggregator calculates genuine multi-resource corroboration in lines 51–77:

```python
cross_support: Dict[str, Set[str]] = defaultdict(set)
all_targets = set([normalized_query] + sorted_lemmas)

for target_str in all_targets:
    for ev in found_evidence:
        source = ev.source
        if not source:
            continue

        matches_surface = (ev.surface == target_str)
        matches_lemma = (ev.lemma == target_str)
        matches_root = (ev.metadata.get("root_word") == target_str)
        matches_headword = (ev.metadata.get("headword") == target_str)

        if matches_surface or matches_lemma or matches_root or matches_headword:
            cross_support[target_str].add(source)
```

1. **Target Pool**: Gathers the normalized query plus all discovered candidate lemmas.
2. **Corroboration Match**: For every target string, it checks all `found_evidence`. If any evidence matches the target via its `surface`, `lemma`, `root_word`, or `headword`, the contributing `source` name is added to a `set`.
3. **Representation**: Output as a dictionary mapping each term to an alphabetical list of unique sources:
   ```json
   {
     "மரங்களில்": ["Tamil WordNet", "ThamizhiMorph"],
     "மரம்": ["Sentamizh", "Tamil Wiktionary", "Tamil WordNet", "ThamizhiMorph", "Thani Thamizh Akarathi"]
   }
   ```
4. **Impact of Source Count on Ranking**:
   - **None.** A candidate supported by 5 resources does **not** receive a higher rank than an item supported by 1 resource.
   - The priority key evaluates each `Evidence` object strictly in isolation. Cross-resource support is preserved as metadata for the UI and the LLM, but is not factored into the sorting tuple.

---

## 6. UnifiedResult Construction

The final step of `aggregator.py` (lines 104–132) compiles and returns the `UnifiedResult` dataclass:

```python
return UnifiedResult(
    query=query,
    normalized_query=normalized_query,
    lemma_candidates=sorted_lemmas,
    evidence=sorted_evidence,
    resource_summary=resource_summary,
    cross_resource_support=cross_resource_support_dict,
    errors=errors
)
```

### Exact Provenance of Every Field:
1. **`query`**: Passed straight through from caller (`RetrievalEngine.search()`).
2. **`normalized_query`**: Passed straight through from caller (`QueryNormalizer.normalize()`).
3. **`lemma_candidates`**: Derived in lines 40–49 from `ev.lemma`, `ev.metadata["root_word"]`, and `ev.metadata["headword"]`, sorted alphabetically.
4. **`evidence`**: The entire `all_evidence` list, sorted descending by `get_priority_key`.
5. **`resource_summary`**: Built in lines 104–122. Iterates over `["ThamizhiMorph", "Thani Thamizh Akarathi", "Tamil WordNet", "Tamil Wiktionary", "Sentamizh"]`:
   ```python
   resource_summary[res] = {
       "status": "FOUND" if found_evs else ("ERROR" if has_error else "NOT_FOUND"),
       "total_entries": len(found_evs),
       "core_analyses": core_count if res == "ThamizhiMorph" else None,
       "guesser_analyses": guesser_count if res == "ThamizhiMorph" else None
   }
   ```
6. **`cross_resource_support`**: The dictionary generated in lines 51–77 mapping terms to corroborating source lists.
7. **`errors`**: Passed straight through from `errors` dictionary populated by `RetrievalEngine` during adapter `try/except` catches.

---

## 7. Architectural Distinction: RetrievalEngine vs. EvidenceAggregator

| Responsibility | `RetrievalEngine` (`engine.py`) | `EvidenceAggregator` (`aggregator.py`) |
|---|---|---|
| **Core Role** | **Search Coordinator & I/O Orchestrator** | **In-Memory Synthesizer & Ranker** |
| **Decides** | **What** to query, **which** adapters to call, **when** to trigger Pass 2, and **how** to handle runtime adapter exceptions. | **How** to order evidence, **which** roots are corroborated, and **what** summary statistics to present. |
| **I/O & Subprocesses** | Executes subprocesses (`flookup`), SQLite queries, and JSON lookups. | Zero I/O; 100% pure in-memory data transformation. |
| **Deduplication** | Computes 6-tuple deduplication keys and drops duplicates. | Does not deduplicate; expects pre-deduplicated list. |
| **Where Vector Retrieval Enters** | **Inside `RetrievalEngine`**: A vector search adapter must be instantiated, queried, and error-bounded here. | **Passive Consumer**: Receives the resulting vector `Evidence` objects and sorts them. |

### Why Keeping These Responsibilities Separate Is Essential:
- **Separation of I/O from Logic**: `RetrievalEngine` deals with files, sockets, database locks, and subprocess pipes. `EvidenceAggregator` is pure, deterministic Python logic that can be tested in sub-millisecond isolation without mocking databases or external binaries.
- **Swappability**: The ranking algorithm in `EvidenceAggregator` can be modified or tuned without risking I/O bugs or breaking adapter network loops in `RetrievalEngine`.

---

## 8. Future Vector / Semantic Retrieval Interaction Analysis

Consider a future semantic retrieval adapter returning an `Evidence` object like:

```python
Evidence(
    surface=query,
    lemma=None,
    source="Project Madurai Semantic Search",
    evidence_type="literary_context",
    passage=verse_text,
    work=work_name,
    verse=verse_number,
    source_id="vector:project_madurai:...",
    metadata={
        "status": "FOUND",
        "retrieval_method": "vector_cosine",
        "similarity_score": 0.89,
        "vector_model": "..."
    }
)
```

### 1. Would the current aggregator accept it?
**Yes, completely.** Because `metadata["status"] == "FOUND"`, the current aggregator will accept it into `found_evidence`, evaluate its priority key, and include it in `result.evidence`.

### 2. Where would it appear in the current ranking?
Let's evaluate `get_priority_key(ev)` on this vector object:
- **`analysis_score`**: `10` (since `analysis_type != "guesser"`).
- **`match_score`**: `8` (since `ev.surface == normalized_query`).
- **`type_score`**: `8` (since `evidence_type != "frequency"`).
- **Total Tuple**: **`(10, 8, 8)`**

> [!WARNING]
> **Critical Ranking Anomaly**:  
> In the current implementation, this vector result would receive a perfect score of `(10, 8, 8)`—**tying with exact Core FST morphological parses and exact keyword dictionary headwords**.  
> Furthermore, it would rank **higher** than exact keyword literary matches retrieved in Pass 2 (which receive `match_score = 4`). A semantic verse with only moderate cosine similarity (`0.72`) would displace an exact, verified Sangam verse!

### 3. Would `similarity_score` currently affect ranking?
**No.** `get_priority_key` does not inspect `metadata["similarity_score"]`. A vector match with similarity `0.45` and one with similarity `0.99` would receive the exact same score `(10, 8, 8)`.

### 4. What existing logic would need to change later?
To support semantic retrieval effectively without breaking exact matching:
1. **Extend `get_priority_key` to a 4-tuple**:
   ```python
   # Add a dedicated retrieval mode score and similarity score
   mode_score = 10 if ev.metadata.get("retrieval_method") == "exact" else 7
   similarity = float(ev.metadata.get("similarity_score", 1.0))
   return (analysis_score, match_score, mode_score, type_score, similarity)
   ```
2. **Make `resources_list` Dynamic**:
   Lines 105–107 currently have a hardcoded list:
   `resources_list = ["ThamizhiMorph", "Thani Thamizh Akarathi", "Tamil WordNet", "Tamil Wiktionary", "Sentamizh"]`
   Any new semantic source (e.g. `"Project Madurai Semantic Search"`) will be completely omitted from `result.resource_summary` unless this list is made dynamic.

### 5. What should remain unchanged?
- The requirement that only `status == "FOUND"` enters candidate extraction and cross-support.
- Preserving non-FOUND / ERROR objects at the bottom of `result.evidence`.
- The immutability of incoming `Evidence` fields.

---

## 9. Minimal Evolutionary Architecture for Hybrid Retrieval

The diagram below illustrates how exact and semantic retrieval naturally merge before entering `EvidenceAggregator`:

```
                 User Query
                     │
                     ▼
          ┌─────────────────────┐
          │   RetrievalEngine   │
          └──────────┬──────────┘
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
┌──────────────────┐   ┌──────────────────┐
│ Exact Adapters   │   │ Semantic Adapter │
│ • ThamizhiMorph  │   │ • Embeddings     │
│ • WordNet (SQL)  │   │ • Vector Search  │
│ • Sentamizh (SQL)│   │ • Qdrant / Faiss │
│ • Akarathi (Dict)│   │ • Cosine Match   │
└────────┬─────────┘   └────────┬─────────┘
         │                      │
         └───────────┬──────────┘
                     ▼
             all_evidence: List[Evidence]
                     │
                     ▼
          ┌─────────────────────┐
          │  EvidenceAggregator │
          │  (4-Tier Priority)  │
          └──────────┬──────────┘
                     ▼
               UnifiedResult
                     │
                     ▼
          ┌─────────────────────┐
          │     EvidencePack    │
          │   ContextSelector   │
          └──────────┬──────────┘
                     ▼
              LLM Interpreter
```

### The Smallest Architectural Change Required:
1. **In `RetrievalEngine`**: Instantiate the semantic adapter in `self.adapters` and append its returned `Evidence` objects into `all_evidence`.
2. **In `EvidenceAggregator`**: Update `get_priority_key` to include `similarity_score` in its comparison tuple, and derive `resources_list` dynamically from `set(e.source for e in all_evidence)`.

---

## 10. Production Concerns & Risk Triage

### P0 — Must Fix Before Deployment
1. **Hardcoded `resources_list`**:  
   Line 105 hardcodes `["ThamizhiMorph", "Thani Thamizh Akarathi", "Tamil WordNet", "Tamil Wiktionary", "Sentamizh"]`. Any newly added adapter will silently fail to appear in `result.resource_summary`. It should be:
   ```python
   all_sources = sorted(list(set(e.source for e in all_evidence if e.source)))
   ```
2. **Pytest Failure in Benchmark Assertion**:  
   `tests/test_unified_benchmark.py` line 44 failed during our test run because `Tamil Wiktionary` was added to `RetrievalEngine` without updating the test's hardcoded resource set.

### P1 — Important for Production Performance & Ranking
1. **Unbounded Vector Ranking Inflation**:  
   As shown in Section 8, any vector match currently gets `(10, 8, 8)` and ranks alongside Core FST analyses. A 4th tier (incorporating `similarity_score` and penalizing fuzzy vector matches below exact string hits) is necessary to keep exact definitions at the top.
2. **Volume Flooding**:  
   If a vector database returns the top 50 nearest-neighbor verses, `all_evidence` will be flooded with 50 large passage objects. The aggregator currently has no cap on `evidence` length, which increases serialization latency and memory usage.

### P2 — Future Improvements
1. **$O(N \times M)$ Cross-Support Matching**:  
   Lines 58–72 execute a nested loop over `all_targets` ($N$) and `found_evidence` ($M$). While fast for $M \le 30$, if vector retrieval introduces $M = 200$, this will execute 2,000+ string comparisons per request. This can be pre-indexed into a hash set.
2. **Multi-Model Score Incommensurability**:  
   If multiple vector models are introduced later, raw cosine similarities from different models cannot be directly compared without a min-max score calibration step.

---

## Key Takeaways

1. **Pure In-Memory Coordinator**: `EvidenceAggregator` executes zero I/O and makes zero database calls. It is a deterministic data processor that takes raw `Evidence` objects and transforms them into an aggregated `UnifiedResult`.
2. **3-Tier Priority Scoring**: Sorting uses `(analysis_score, match_score, type_score)`: Core FST (`10`) beats Guesser FST (`5`); direct surface matches (`8`) beat secondary lemma matches (`4`); substantive definitions and verses (`8`) beat frequency counts (`2`).
3. **Non-Destructive Filtering**: Non-matching (`NOT_FOUND`) and failed (`ERROR`) evidence records are not deleted. They receive `(0, 0, 0)` and sink to the bottom of the list, preserving a full audit trail for the user.
4. **Cross-Resource Corroboration**: It computes which candidate words are backed by multiple databases (e.g., `"மரம்"` supported by 5 resources), but source count does not currently influence ranking order.
5. **No Built-in Deduplication**: Deduplication is handled entirely upstream in `RetrievalEngine.search()`. The aggregator assumes its input is already deduplicated.
6. **Vector Search Readiness**: Future semantic/vector retrieval can plug into the existing aggregator seamlessly, provided that vector evidence is marked with `status="FOUND"` and the priority function is updated to incorporate `similarity_score`.
7. **Hardcoded Resource List**: `resources_list` in line 105 is statically hardcoded to five names, which is the only hard blocker when adding new retrieval adapters.
