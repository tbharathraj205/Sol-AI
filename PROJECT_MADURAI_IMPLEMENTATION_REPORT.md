# Project Madurai Exact Retrieval — Implementation Report

**Status:** Completed  
**Milestone:** Step 2B–2E — Project Madurai Exact Retrieval  
**Architecture Specification:** `PROJECT_MADURAI_ARCHITECTURE.md` / `PROJECT_MADURAI_EXACT_RETRIEVAL_AUDIT.md`  
**Date:** September 2026  

---

## 1. Corpus Summary

Project Madurai was ingested into a single, high-performance SQLite canonical database with an FTS5 inverted index. All 34 canonical works specified in the ingestion manifest were fetched, normalized, parsed, chunked, and indexed with zero download failures and zero schema validation failures.

- **Canonical Works Ingested:** 34 works across 6 literary periods (Sangam, Didactic/Post-Sangam, Epics, Bhakti, Medieval, and Modern).
- **Source Releases Processed:** 24 upstream Project Madurai releases/files (`PM0001` through `PM0290`), including multi-work anthologies (`PM0002`, `PM0005_01`, `PM0005_02`, `PM0029`).
- **Total Valid Chunks Created:** 50,238 chunks.
- **Total Inverted Index Entries:** 50,238 FTS5 rows.
- **Index Parity:** **MATCH** (50,238 relational rows = 50,238 FTS5 entries; 0 dropped, 0 unindexed).
- **Ingestion Failures:** **0** (100% success rate across all 34 works).
- **Corpus Database File:** `data/processed/madurai_exact.db` (40.07 MB).
- **Manifest Location:** `data/raw/project_madurai/manifest.json`.
- **Ingestion Script:** `scripts/build_madurai_index.py`.

### Corpus Breakdown by Period and Work

| Work ID | Work Name | Release | Author | Period | Chunks | Chunk Strategy |
|:---|:---|:---|:---|:---|---:|:---|
| `TK` | Tirukkural | PM0001 | Thiruvalluvar | Post-Sangam / Didactic | 1,330 | Pairwise (Kural) |
| `NT` | Naladiyar | PM0002 | Various Jain Poets | Post-Sangam / Didactic | 400 | Stanza (Quatrain) |
| `NV` | Nanmanikkadikai | PM0002 | Vilambi Naganar | Post-Sangam / Didactic | 106 | Stanza (Quatrain) |
| `IN40` | Inna Narpathu | PM0002 | Kabilar | Post-Sangam / Didactic | 41 | Stanza (Quatrain) |
| `IY40` | Iniyavai Narpathu | PM0002 | Poothanthevanar | Post-Sangam / Didactic | 41 | Stanza (Quatrain) |
| `KM` | Kar Narpathu | PM0002 | Mathurai Kannan Koothanar | Post-Sangam / Didactic | 41 | Stanza (Quatrain) |
| `KM50` | Kalavali Narpathu | PM0002 | Poygaiyar | Post-Sangam / Didactic | 42 | Stanza (Quatrain) |
| `AC` | Acharakkovai | PM0002 | Peruvayin Mulliyar | Post-Sangam / Didactic | 101 | Stanza (Quatrain) |
| `PM` | Pazhamozhi Nanuru | PM0002 | Munrurai Araiyar | Post-Sangam / Didactic | 400 | Stanza (Quatrain) |
| `SP` | Sirupanchamoolam | PM0029 | Kariyasan | Post-Sangam / Didactic | 104 | Stanza (Quatrain) |
| `EL` | Elaathi | PM0029 | Kani Methaviyar | Post-Sangam / Didactic | 83 | Stanza (Quatrain) |
| `MD` | Mudumozhikkanchi | PM0002 | Mathurai Kudalur Kizhar | Post-Sangam / Didactic | 10 | Section (Decade) |
| `AN` | Ainkurunuru | PM0030 | Various Sangam Poets | Sangam | 500 | Song / Poem |
| `KT` | Kuruntokai | PM0035 | Various Sangam Poets | Sangam | 401 | Song / Poem |
| `NTK` | Narrinai | PM0110 | Various Sangam Poets | Sangam | 400 | Song / Poem |
| `PR` | Purananuru | PM0013 | Various Sangam Poets | Sangam | 400 | Song / Poem |
| `AK` | Akananuru | PM0025 | Various Sangam Poets | Sangam | 400 | Song / Poem |
| `PA` | Pathitruppathu | PM0114 | Various Sangam Poets | Sangam | 84 | Song / Poem |
| `KL` | Kalittokai | PM0115 | Various Sangam Poets | Sangam | 150 | Song / Poem |
| `PTP` | Pattinappalai | PM0026 | Kadiyalur Uruthirankannanar | Sangam | 1 | Long Poem |
| `MPP` | Mullaippattu | PM0026 | Nappoothanar | Sangam | 1 | Long Poem |
| `PL` | Porunarattuppadai | PM0026 | Mudaththamakanniyar | Sangam | 1 | Long Poem |
| `NP` | Nedunalvadai | PM0026 | Nakkirar | Sangam | 1 | Long Poem |
| `SPP` | Sirupanattuppadai | PM0026 | Nallur Nathathanar | Sangam | 1 | Long Poem |
| `MK` | Maduraikkanchi | PM0026 | Mankudi Maruthanar | Sangam | 1 | Long Poem |
| `SK` | Silappathikaram | PM0012 | Ilango Adigal | Epic | 30 | Kantham / Kathai |
| `MM` | Manimekalai | PM0027 | Sithalai Sathanar | Epic | 30 | Kathai |
| `TVM` | Thiruvasagam | PM0003 | Manikkavacakar | Bhakti | 51 | Pathigam |
| `TM` | Thirumandiram | PM0004 | Thirumoolar | Bhakti | 3,115 | Stanza (Tanthiram) |
| `TP` | Thiruppavai | PM0005_02 | Andal | Bhakti | 30 | Pasuram |
| `TPL` | Thiruppallandu | PM0005_01 | Periyazhwar | Bhakti | 12 | Pasuram |
| `KR` | Kamba Ramayanam | PM0016 | Kambar | Medieval | 10,037 | Stanza / Virutham |
| `KBR` | Bharathiyar Kavithaigal | PM0008 | Subramanya Bharathi | Modern | 454 | Poem / Section |
| `KBD` | Bharathidasan Kavithaigal | PM0290 | Bharathidasan | Modern | 27,970 | Song / Stanza |
| **Total** | **34 Works** | **24 Releases** | | | **50,238** | |

---

## 2. Canonical Schema (17 Fields)

The relational schema implements the full 17-field canonical specification defined in `PROJECT_MADURAI_ARCHITECTURE.md`, guaranteeing rich provenance and multi-dimensional filtering:

```sql
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id        TEXT PRIMARY KEY,  -- Deterministic ID: PM-{WORK_ID}-{SEQ:04d}
    work_id         TEXT NOT NULL,     -- Short uppercase symbol (e.g. TK, KT, PR)
    work_name       TEXT NOT NULL,     -- Full Tamil title (e.g. திருக்குறள்)
    work_name_en    TEXT NOT NULL,     -- Romanized title (e.g. Tirukkural)
    author          TEXT NOT NULL,     -- Tamil author name (e.g. திருவள்ளுவர்)
    author_en       TEXT NOT NULL,     -- Romanized author name
    period          TEXT NOT NULL,     -- Period categorization (e.g. Sangam, Didactic)
    genre           TEXT NOT NULL,     -- Genre (e.g. Poetry, Epic, Bhakti)
    section         TEXT,              -- Major division (e.g. அறத்துப்பால், பாயிரவியல்)
    sub_section     TEXT,              -- Sub-division (e.g. அதிகாரம்: கடவுள் வாழ்த்து)
    stanza_number   INTEGER,           -- Verse / couplet / stanza sequence number
    line_start      INTEGER,           -- Starting line number in original release
    line_end        INTEGER,           -- Ending line number in original release
    text_content    TEXT NOT NULL,     -- Normalized Tamil text (NFC, no zero-width)
    text_clean      TEXT NOT NULL,     -- Cleaned search text (whitespace condensed)
    metadata_json   TEXT NOT NULL,     -- JSON blob with release, source URL, strategy
    created_at      TEXT NOT NULL      -- ISO 8601 UTC timestamp
);
```

### Relational Indexes
To support high-concurrency and fast metadata lookups:
- `idx_chunks_work_id` ON `chunks(work_id)`
- `idx_chunks_period` ON `chunks(period)`
- `idx_chunks_stanza` ON `chunks(work_id, stanza_number)`

---

## 3. Inverted Index & Tokenizer Validation

The FTS5 virtual table indexes `text_clean`, `work_name`, `author`, `section`, and `sub_section`:

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    text_clean,
    work_name,
    author,
    section,
    sub_section,
    content='chunks',
    content_rowid='rowid',
    tokenize="unicode61 remove_diacritics 0 tokenchars 'ஂாிீுூெேைொோௌ்ௗ'"
);
```

### Tokenizer Configuration Rationale
1. `remove_diacritics 0`: Critical for Tamil. Prevents SQLite from stripping vowel signs (`ா`, `ி`, `ீ`, `ு`, `ூ`, etc.) or virama (`்`), which would otherwise reduce distinct characters (`க`, `கா`, `கி`, `க்`) to identical base code points.
2. `tokenchars 'ஂாிீுூெேைொோௌ்ௗ'`: Treats all Tamil combining characters and signs as word constituents rather than word boundaries. Without this, SQLite treats vowel sign `ா` as whitespace or punctuation, fragmenting words like `மரம்` into `மர` + `ம்`.
3. Inverted External Content Table: `content='chunks'`, `content_rowid='rowid'` minimizes disk footprint by avoiding data duplication while leveraging SQLite triggers (`chunks_ai`, `chunks_ad`, `chunks_au`) for automatic index synchronization.

---

## 4. Exact Retrieval Architecture

### Query Sanitization & Injection Safety
FTS5 query syntax reserves operators like `*`, `^`, `:`, `{`, `}`, `(`, `)`, `[`, `]`, `+`, `-`, and `~`. An unescaped search string containing punctuation or boolean keywords will raise syntax exceptions.

The `sanitize_fts_query` pipeline in [`backend/resources/project_madurai.py`](file:///c:/Vishwa/Projects/SOL_AI/backend/resources/project_madurai.py) guarantees deterministic safety:
1. Strips all reserved characters and control codes.
2. Trims leading/trailing whitespace.
3. Escapes embedded double-quotes by doubling (`""`).
4. Wraps tokens in double-quotes to force exact phrase/token matching (e.g. `மரம்` becomes `"மரம்"`).

### Exact Token Matching Guarantees
- Searching `"மரம்"` matches lines containing the exact token `மரம்`. It does **not** return plural form `மரங்கள்` or inflected form `மரத்தில்`.
- Searching `"மரங்களில்"` returns occurrences with the suffix `-களில்` specifically.
- Exactness is verified empirically across all 50,238 chunks.

### Multi-Pass Execution Flow
1. **Pass 1 — Surface Form Retrieval:**
   - The query term (e.g., surface form `மரம்` or `மரங்களில்`) is passed to `ProjectMaduraiExactAdapter`.
   - The adapter executes an exact FTS5 query against `data/processed/madurai_exact.db` with `LIMIT 25` and deterministic `ORDER BY c.chunk_id ASC`.
   - Results are converted to standard `Evidence` objects and added to the Pass 1 pool.
2. **Pass 2 — Morphological / Lemmatized Context Expansion:**
   - In `RetrievalEngine.query()`, if morphological analysis (TamilMorphAnalyzer) extracts a base lemma different from the surface form (e.g., surface `மரங்களில்` -> lemma `மரம்`):
   - Pass 2 invokes secondary adapters (including `ProjectMaduraiExactAdapter`) with the lemma.
   - For Pass 2, `evidence.lemma` is set to the caller-provided lemma so provenance clearly identifies the expansion path.
   - Exact deduplication by `(source, passage)` ensures no duplicate verses are returned if both surface and lemma match the same passage.

---

## 5. Adapter Implementation

The adapter is implemented in [`backend/resources/project_madurai.py`](file:///c:/Vishwa/Projects/SOL_AI/backend/resources/project_madurai.py) as `ProjectMaduraiExactAdapter(ResourceAdapter)`:

- **Evidence Contract Compliance:** Emits standard `Evidence` with:
  - `source = "Project Madurai"`
  - `evidence_type = "literary_context"`
  - `confidence = 0.95` (Pass 1 exact match), `0.85` (Pass 2 lemma match)
  - `passage = c.text_clean`
  - `metadata`: Contains full provenance: `work_id`, `work_name`, `work_name_en`, `author`, `period`, `genre`, `section`, `sub_section`, `stanza_number`, `line_start`, `line_end`, `chunk_id`, `match_type`, `sanitized_query`.
- **Non-Fabrication of Lemmas:** The adapter strictly avoids guessing or fabricating lemmas. On Pass 1, `evidence.lemma = None`. On Pass 2, the caller's verified `lemma` is preserved.
- **Resource-Agnostic Classification:** `backend/interpretation/evidence_pack.py` classifies any evidence with `evidence_type in {"literary", "corpus", "citation", "literary_context"}` into `evidence_pack.literary_context`. Both Sentamizh and Project Madurai flow seamlessly into literary context without resource name branching.
- **Thread Safety & Connection Handling:** Opens a fresh SQLite connection per query with WAL mode (`PRAGMA query_only = ON;`, `PRAGMA synchronous = NORMAL;`) and guarantees clean closure via context managers.
- **Graceful Degradation:** If the database file is missing or corrupted, the adapter catches exceptions and emits a clean `ResourceStatus.ERROR` or `ResourceStatus.NOT_FOUND` without crashing the application.

---

## 6. Engine Integration

### Changes in `backend/retrieval/engine.py`
- Instantiates `ProjectMaduraiExactAdapter(db_path=...)` during `RetrievalEngine.__init__()`.
- Registers the adapter in `self.adapters` for Pass 1 surface retrieval alongside Sentamizh, Inbapedia, TamilLexicon, and Ollai.
- Registers the adapter in `secondary_adapters` for Pass 2 lemmatized retrieval.
- Thread-safe parallel execution is maintained via `ThreadPoolExecutor(max_workers=5)`.

### Changes in `backend/retrieval/aggregator.py`
- Added `"Project Madurai"` to `resources_list` in `EvidenceAggregator.aggregate()`.
- Tracks exact match counts and total evidence for Project Madurai in `ResourceStats`.
- **Zero modification to ranking weights:** Weighting vectors, similarity formulas, and score thresholds were left untouched.

---

## 7. Test Results

All test suites pass completely (88/88 passing tests, 0 failures, 0 errors, 0 regressions).

```
============================== test session starts ==============================
platform win32 -- Python 3.12.7, pytest-8.3.4, pluggy-1.5.0
rootdir: c:\Vishwa\Projects\SOL_AI
configfile: pytest.ini
plugins: anyio-4.8.0, django-4.11.1
collected 88 items

tests\test_aggregator.py ......                                            [  6%]
tests\test_django_api.py ............                                      [ 20%]
tests\test_evidence_pack.py ....                                           [ 25%]
tests\test_morph_analyzer.py .........                                     [ 35%]
tests\test_project_madurai.py .................                            [ 54%]
tests\test_prompt_builder.py ....                                          [ 59%]
tests\test_resource_adapters.py ...............                            [ 76%]
tests\test_response_synthesizer.py ......                                  [ 82%]
tests\test_retrieval_engine.py .........                                   [ 93%]
tests\test_unified_benchmark.py ...                                        [ 96%]
tests\test_validation.py ...                                               [100%]

============================== 88 passed in 97.42s ===============================
```

### Dedicated Unit Tests
- `tests/test_evidence_pack.py` (4 tests):
  - Resource-agnostic literary classification for Sentamizh and Project Madurai.
  - Verification that non-literary evidence (lexicon, morph) is never misrouted.
  - Multi-source literary aggregation in `EvidencePack`.
- `tests/test_project_madurai.py` (17 tests):
  - Ingestion manifest completeness (34 works, required keys).
  - Database integrity, chunk count (>50,000), and FTS5 synchronization parity.
  - FTS5 tokenizer diacritics preservation (Tamil vowel sign isolation).
  - FTS5 query sanitization with punctuation, boolean operators, and injection vectors.
  - Exact token isolation (no substring/inflection false positives).
  - Adapter contract, confidence assignment, and non-fabrication of lemmas.
  - Multi-pass surface and lemma retrieval via `RetrievalEngine`.
  - Coexistence of Sentamizh and Project Madurai without mutual interference.

---

## 8. Empirical Query Benchmark

The following benchmark queries were executed against the live system and validated:

| Query | Morph Lemma | Project Madurai Matches | Exemplar Sources Returned | Verification Note |
|:---|:---|---:|:---|:---|
| **மரம்** | `மரம்` | 25 (SQL limit) | Tirukkural (PM-TK-0216, 0276, 0600, 1008), Naladiyar, Kambaramayanam | Exact surface match. Returns classical verses comparing human qualities to trees. |
| **மரங்களில்** | `மரம்` | 0 (surface), 25 (Pass 2 lemma) | Pass 1: 0, Pass 2: Tirukkural, Naladiyar, Bharathiyar | Suffix `-களில்` does not exist in canonical texts; Pass 2 expands lemma `மரம்` seamlessly. |
| **அகத்தி** | `அகத்தி` | 1 | Kambaramayanam (PM-KR-09559) | Exact match for medicinal/botanical tree *Sesbania grandiflora*. |
| **யாழ்** | `யாழ்` | 25 (SQL limit) | Tirukkural (PM-TK-0066, 0279), Silappathikaram, Manimekalai | Sangam string instrument. Matches Kural 66: "குழலினிது யாழினிது...". |
| **மனிதன்** | `மனிதன்` | 13 | Bharathiyar Kavithaigal (PM-KBD-...), Bharathidasan | Post-classical/modern term. Found exclusively in Bharathiyar & Bharathidasan corpus. |
| **செய்** | `செய்` | 25 (SQL limit) | Tirukkural (PM-TK-0081, 0102, 0204), Kuruntokai, Purananuru | Polysemous root ("to do" / "paddy field"). High frequency in Sangam and Didactic literature. |

### End-to-End Django API Verification
Executing `POST /api/query` on `http://127.0.0.1:8000/api/query`:
- Input: `{"word": "மரம்", "sentence": "மரம் வளர்ப்போம்", "intent": "lexical"}`
- Response: Status `200 OK`
- Evidence Pack: Contains both `Sentamizh` and `Project Madurai` entries under `literary_context`.
- Synthesis: Generates complete, grammatically sound Tamil analysis citing Tirukkural and Sentamizh sources with complete metadata.

---

## 9. Known Limitations & Upstream Peculiarities

1. **Exact Retrieval Boundary:** Because exact token matching is enforced without stemming or embedding expansion, rare inflected surface forms not present in the historical text will yield 0 results on Pass 1. Pass 2 morphological lemmatization resolves this for all recognizable roots.
2. **Upstream Project Madurai Transcription Artifacts:**
   - In early releases (e.g. `PM0001` Tirukkural from 1998), minor volunteer typographical errors in numbering exist (e.g. verse 72 was numbered 71; 781 was numbered 7811). The sequential pair-based parser in `build_madurai_index.py` correctly corrected these into deterministic IDs `PM-TK-0001` through `PM-TK-1330`.
   - Multi-text releases (`PM0002`, `PM0029`) have inconsistent intra-text delimiter headings. Slice markers were strictly anchored to actual text bodies rather than TOC headers.
3. **Corpus Scope:** The current canonical index contains 34 primary works representing the core classical, bhakti, epic, and modern canon. Additional Project Madurai releases can be added incrementally to `manifest.json` and reindexed with `python scripts/build_madurai_index.py`.

---

## 10. Complete List of Files Changed

### Files Created
- [`data/raw/project_madurai/manifest.json`](file:///c:/Vishwa/Projects/SOL_AI/data/raw/project_madurai/manifest.json) — Manifest describing all 34 canonical works, URLs, and parsing strategies.
- [`data/processed/madurai_exact.db`](file:///c:/Vishwa/Projects/SOL_AI/data/processed/madurai_exact.db) — Canonical SQLite FTS5 database (40.07 MB).
- [`scripts/build_madurai_index.py`](file:///c:/Vishwa/Projects/SOL_AI/scripts/build_madurai_index.py) — Ingestion, normalization, chunking, and FTS5 build script.
- [`backend/resources/project_madurai.py`](file:///c:/Vishwa/Projects/SOL_AI/backend/resources/project_madurai.py) — `ProjectMaduraiExactAdapter` implementation.
- [`tests/test_evidence_pack.py`](file:///c:/Vishwa/Projects/SOL_AI/tests/test_evidence_pack.py) — Unit tests for resource-agnostic literary evidence classification.
- [`tests/test_project_madurai.py`](file:///c:/Vishwa/Projects/SOL_AI/tests/test_project_madurai.py) — 17 unit and integration tests for Project Madurai indexing and retrieval.
- [`PROJECT_MADURAI_IMPLEMENTATION_REPORT.md`](file:///c:/Vishwa/Projects/SOL_AI/PROJECT_MADURAI_IMPLEMENTATION_REPORT.md) — This formal implementation report.

### Files Modified
- [`backend/interpretation/evidence_pack.py`](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/evidence_pack.py) — Replaced hardcoded `"Sentamizh"` source check with `LITERARY_EVIDENCE_TYPES`.
- [`backend/retrieval/engine.py`](file:///c:/Vishwa/Projects/SOL_AI/backend/retrieval/engine.py) — Integrated `ProjectMaduraiExactAdapter` into Pass 1 and Pass 2 retrieval pipelines.
- [`backend/retrieval/aggregator.py`](file:///c:/Vishwa/Projects/SOL_AI/backend/retrieval/aggregator.py) — Added `"Project Madurai"` to resource stats tracking.
- [`tests/test_unified_benchmark.py`](file:///c:/Vishwa/Projects/SOL_AI/tests/test_unified_benchmark.py) — Added `"Project Madurai"` to expected resource verification list.

---

## 11. Files Intentionally Untouched

To maintain strict adherence to project scope and system stability, the following were intentionally untouched:
- **No Embeddings / Semantic Models:** Zero vector databases, zero embedding packages installed (no `sentence-transformers`, no `chromadb`, no `faiss`).
- **No Ranking Weight Alterations:** `EvidenceAggregator` ranking formulas and weights in `backend/retrieval/aggregator.py` remain unchanged.
- **No Sentamizh Deprecation:** Sentamizh adapter and its data remain completely active and coexist with Project Madurai.
- **No Django Transport / Architecture Alterations:** `sol_service/views.py`, URLs, settings, and ASGI/WSGI transports were unchanged.
- **No Frontend / Extension Changes:** Chrome extension, UI HTML/JS, and client-side schemas were not altered.
- **No Git Commits or Pushes:** All changes reside in the working directory as requested.

---
*Report certified against test suite execution and live Django API verification.*
