# STEP 3: SEMANTIC RETRIEVAL LAYER — ARCHITECTURE & DESIGN SPECIFICATION (REVISED)

**Project:** SOL AI (Tamil Lexical & Contextual Intelligence Engine)  
**Document:** `STEP3_SEMANTIC_RETRIEVAL_DESIGN.md`  
**Revision:** 2.0 (Post-Audit Design Corrections)  
**Author:** Senior ML & Search Systems Architect  
**Corpus Source of Truth:** `data/processed/madurai_exact.db` (14,383 canonical chunks, 35 works, SQLite FTS5)  
**Status:** DESIGN REVISED — READY FOR IMPLEMENTATION REVIEW  
**Date:** October 2026  

---

## 1. Executive Summary

SOL AI operates a deterministic multi-resource retrieval pipeline uniting classical Tamil finite-state morphology (ThamizhiMorph), purist lexicography (Thani Thamizh Akarathi), synset semantic networks (Tamil WordNet), classical citations (Sentamizh), and full-corpus literary text search (Project Madurai Exact).

Following the completion of Step 2G, the Project Madurai exact-retrieval database (`madurai_exact.db`) is validated with 100% FTS5 row parity, zero stanza fragmentation, exact couplet alignment in Tirukkural (1,330 couplets), and complete aphoristic retention in Aathichudi (110 stanzas) and Konrai Vendhan (92 stanzas).

This document specifies the revised architecture for **Step 3 — Semantic Retrieval Layer**.

### Foundational Architectural Tenets
1. **Deterministic Retrieval Remains the Immutable Source of Truth:** Semantic retrieval is an additive discovery mechanism designed to uncover literary context based on conceptual, thematic, and paraphrastic meaning when exact lexical surface or morphological lemma overlap is absent or sparse.
2. **Strict Separation of Linguistic Concerns:** 
   - **ThamizhiMorph:** Morphological analysis, inflectional decomposition, and linguistic lemma discovery.
   - **Project Madurai Exact (FTS5):** Exact lexical and morphological token matching.
   - **Semantic Encoder:** Conceptual, thematic, and paraphrastic vector similarity.
   Semantic retrieval does **not** establish linguistic lemmas and is **not** a replacement for morphological analysis.
3. **Exact Database Immutability:** `data/processed/madurai_exact.db` is strictly read-only. Semantic indexing generates clean text representations in memory and saves vector data in separate derived artifacts.
4. **Resilience & Optionality:** Exact retrieval must continue operating with 100% availability if semantic retrieval encounters errors, missing files, or timeouts.

---

## 2. Current Architecture Assessment

An in-depth codebase audit was conducted across `backend/retrieval/`, `backend/resources/`, `backend/interpretation/`, `backend/schemas/`, `backend/sol_django/`, and `tests/`.

### 2.1 Reality & Verification Status

To ensure engineering rigor, the architecture distinguishes three categories of information:

| Category | Components / Parameters | Verification Basis |
|---|---|---|
| **Known / Verified** | • 14,383 canonical chunks in `madurai_exact.db`<br>• 14,383 FTS5 virtual table rows (100% parity)<br>• Exact FTS query latency: 1.4 ms to 6.2 ms<br>• Python 3.12.10 environment<br>• PyTorch 2.14.0 active (CPU-only, `torch.cuda.is_available() == False`)<br>• Installed packages: `transformers 5.17.0`, `sentencepiece`, `tokenizers`, `numpy 2.5.3`<br>• Missing packages: `sentence-transformers`, `faiss-cpu`, `chromadb`<br>• Hardware: AMD Ryzen 5 5600H (6C/12T), RTX 3050 Laptop (4GB VRAM), 8GB RAM, Windows 11 | Direct code inspection, database queries, and test execution (`pytest tests/test_project_madurai.py`) |
| **Expected / Estimated** | • Peak memory overhead for 278M-parameter model: ~1.1 GB RAM<br>• CPU inference latency on Ryzen 5 5600H: ~35–50 ms per query<br>• NumPy matrix vector dot product latency for 14K chunks: ~1.8 ms<br>• Offline indexing duration on CPU (6 threads): ~2–4 minutes | Theoretical parameter-memory sizing and standard AVX2 BLAS performance models |
| **To Be Benchmarked** | • Actual local CPU embedding generation latency across query lengths<br>• Actual peak process RAM footprint during concurrent Django execution<br>• Classical Tamil subword tokenizer fragmentation rates<br>• Empirical similarity score distributions on positive vs negative pairs<br>• Empirical retrieval Recall@K and Precision@K | Empirical benchmark execution during Phase 3B and Phase 3F |

---

## 3. Requirements

### 3.1 Functional Requirements
- **Conceptual Discovery:** Retrieve semantically relevant classical literary passages for thematic queries (e.g. `"பெற்றோரை மதித்தல்"` [respecting parents], `"இளமையில் கல்வி"` [learning in youth], `"நிலையாமை"` [impermanence]) where exact lexical keywords are absent.
- **Paraphrastic Robustness:** Match modern conceptual queries to classical poetic phrasings without altering the authoritative text.
- **Strict Provenance Integrity:** Every semantic match must trace back to a valid, unchanged `chunk_id` in `madurai_exact.db`.
- **Zero Hallucination / No Lemma Fabrication:** Semantic retrieval must leave `Evidence.lemma = None` unless a valid lemma was independently established by upstream morphological analysis (`ThamizhiMorph`).
- **Independent Failure Domain:** If semantic search fails, times out, or encounters missing index files, exact search must continue unimpeded with zero user-facing errors.

### 3.2 Non-Functional Requirements
- **Local & Offline Execution:** 100% local inference. Zero external API calls or data transmissions.
- **Engineering Targets (To Be Validated):**
  - Query embedding generation: Target $\le 45\text{ ms}$ on CPU. Actual: Measured during Phase 3B.
  - Vector similarity search (14,383 chunks): Target $\le 3\text{ ms}$. Actual: Measured during Phase 3B.
  - Candidate fusion & deduplication: Target $\le 1\text{ ms}$. Actual: Measured during Phase 3E.
- **Memory Ceiling:** Safe process ceiling $\le 1.5\text{ GB}$ peak RAM to ensure stability on the 8GB host.
- **Deterministic Offline Indexing:** Given identical model weights and corpus, the offline build must generate bit-for-bit identical vector files.

---

## 4. Embedding Model Evaluation

### 4.1 Candidate Evaluation Matrix

The evaluation considers parameter size, context length, Tamil tokenization support, and local viability on the developer workstation (Ryzen 5 5600H, RTX 3050 4GB, 8GB RAM, Windows 11, currently CPU-only PyTorch):

| Candidate Model | Parameter Size | Embedding Dim | Max Context | Tamil Tokenizer Architecture | License | Local Deployment Status | Role in Step 3 |
|---|---|---|---|---|---|---|---|
| **`intfloat/multilingual-e5-base`** | 278M | 768 | 512 tokens | XLM-RoBERTa 250k vocab (Strong Dravidian coverage) | MIT | Fully compatible with local `transformers` | **Primary Candidate to Benchmark** |
| `intfloat/multilingual-e5-small` | 118M | 384 | 512 tokens | XLM-RoBERTa 250k vocab | MIT | Fully compatible with local `transformers` | **Fallback Candidate (Low-Resource Tier)** |
| `google/muril-base-cased` | 237M | 768 | 512 tokens | Indic BERT vocab (Direct Indic script pre-training) | Apache 2.0 | Fully compatible | Alternative Candidate (Requires pooling calibration) |
| `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | 118M | 384 | 128 tokens | Multilingual WordPiece | Apache 2.0 | Requires `sentence-transformers` | Secondary Alternative (Short context limit) |
| `BAAI/bge-m3` | 567M | 1024 | 8192 tokens | XLM-RoBERTa | MIT | Memory risk (>2.3 GB RAM) | Disqualified (Exceeds 8GB RAM budget) |

### 4.2 Candidate Role Clarification
- **`intfloat/multilingual-e5-base` is NOT an already-proven production choice.** It is designated as the **Primary candidate model to benchmark**.
- In Phase 3B, its local CPU latency, memory footprint, and Tamil tokenization quality will be benchmarked directly on the workstation before any full corpus vector build is performed.
- If it exceeds the memory ceiling or latency targets on CPU, **`intfloat/multilingual-e5-small`** will be evaluated as the immediate lightweight alternative.

---

## 5. Candidate Model Selection (Primary Candidate to Benchmark)

### Primary Candidate: `intfloat/multilingual-e5-base`
- **Hugging Face ID:** `intfloat/multilingual-e5-base`
- **Model Revision:** Strict immutable git commit hash pinned in metadata (e.g. `d13111270745...`). Branch names such as `main` are strictly prohibited.
- **Asymmetric Prefix Support:** Uses `"query: "` and `"passage: "` prefixes to optimize the vector space for asymmetric retrieval (short search query $\rightarrow$ long literary stanza).
- **Context Length:** 512 tokens (covers 100% of Project Madurai chunks).
- **Embedding Dimension:** 768 float32 values ($3,072\text{ bytes per vector}$).
- **Final Selection:** **PENDING LOCAL BENCHMARK** (Phase 3B).

---

## 6. Embedding Input Format

Embedding classical Tamil poetry requires sufficient context without allowing metadata to drown out poetic meaning.

### 6.1 Format Rules (Embedding-Time Derivation)

All embedding representations are constructed **in memory** during offline indexing without modifying `madurai_exact.db`.

```text
Format Pattern:
passage: {thematic_context}{cleaned_passage}
```

1. **Tirukkural Couplets (`PM-TK-*`):**
   Prepend the thematic chapter (`chapter`) to provide topical grounding without metadata clutter:
   ```text
   passage: அதிகாரம்: {chapter}. {cleaned_text}
   ```
   *Example (`PM-TK-0001`):*
   `passage: அதிகாரம்: கடவுள் வாழ்த்து. அகர முதல எழுத்தெல்லாம் ஆதி பகவன் முதற்றே உலகு.`

2. **Autonomous Didactic Aphorisms (*Aathichudi*, *Konrai Vendhan*):**
   Embed the text directly without prepending work title or author:
   ```text
   passage: {cleaned_text}
   ```
   *Example (`PM-AATHI-0002`):*
   `passage: அறம் செய விரும்பு.`
   *(Rationale: In a 3-word aphorism, adding "ஆத்திசூடி ஔவையார்" accounts for >60% of tokens, causing author bias to dominate conceptual search).*

3. **Sangam & Epic Poetry (*Kuruntogai*, *Natrinai*, *Silappadikaram*):**
   Prepend the classical Canto or Thinai if present:
   ```text
   passage: {canto}: {cleaned_text}
   ```

4. **Runtime Query Prefixing:**
   Search queries are formatted with the E5 query prefix:
   ```text
   query: {normalized_user_query}
   ```

---

## 7. Short-Chunk Strategy & Count Derivation

### 7.1 Database Verification Mandate
> **Short-chunk statistics must be calculated directly from the current `madurai_exact.db` during implementation/build time.**

The exact database will not be modified to resolve historical reporting variances between audit runs. The build script must dynamically query the database for chunk length distributions.

### 7.2 Short-Chunk Classification Rules

Inspection of short chunks reveals two functionally distinct categories:

1. **Category 1: Autonomous Didactic Aphorisms (Keep & Embed)**
   - *Examples:* `அறம் செய விரும்பு.`, `ஏவா மக்கள் மூவா மருந்து.`
   - *Nature:* Complete, grammatically independent, profound moral maxims.
   - *Treatment:* **Indexed in the vector space** with direct passage embedding.
2. **Category 2: Standalone Structural Metadata (Suppress from Vector Index)**
   - *Examples:* Colophons (`குறிஞ்சி - தோழி கூற்று`), musical pann stubs (`பண் - நட்டபாடை`), chapter stubs (`1 செல்வம் நிலையாமை`).
   - *Nature:* Structural labeling artifacts from raw e-text layout. They contain zero poetry.
   - *Treatment:* **Suppressed from vector indexing.** They remain fully searchable via exact FTS5 in `madurai_exact.db`.

---

## 8. Semantic Preprocessing Strategy

All cleaning operations are **derived embedding-time filters** executed in memory or recorded in derived artifacts:

```text
Exact DB (madurai_exact.db)
           │
      (Read-Only)
           │
           ▼
Semantic Preprocessing (In-Memory)
  • Strip residual 'Back'
  • Filter email contact headers
  • Filter publication source headers
  • Normalize whitespace
           │
           ▼
Canonical Embedding String
           │
           ▼
Vector Embedding Generation
```

### Preprocessing Actions:
1. **Residual Navigation Anchor (`Back`):** Strip trailing `Back` and `திருச்சிற்றம்பலம் Back` in Thiruvasagam passages.
2. **Webmaster Contact Header:** Exclude `PM-SILAP_MADURAI-0003` (`kalyan@geocities.com`) from vector indexing.
3. **Publication Source Header:** Exclude `PM-CHINTHAMANI-0003` (`Source: "சீவகசிந்தாமணி...`) from vector indexing.
4. **Authoritative Corpus Integrity:** `original_text`, `normalized_text`, chunk IDs, and FTS records in `madurai_exact.db` remain 100% untouched.

---

## 9. Vector Index Technology

### 9.1 Initial Vector Architecture: NumPy Normalized Dense Matrix
- **Index File:** `data/processed/madurai_semantic_vectors.npy`
- **Metadata File:** `data/processed/madurai_semantic_meta.json`
- **Data Representation:** Contiguous 2D NumPy array of shape $(N, 768)$ in `float32`.
- **Memory Footprint:** For ~14.3K vectors, total file size is **~42.1 MB**.
- **Search Mechanism:** Exhaustive matrix-vector dot product (`numpy.dot`) on unit-normalized vectors.
- **Rationale:**
  - Zero external C++ or DLL compilation issues on Windows 11.
  - Zero new dependencies (NumPy is already installed).
  - 100% exact top-$K$ precision (no approximate nearest-neighbor recall loss).
  - Fully reversible, inspectable, and deterministic.
- **Future Scaling:** A FAISS adapter (`IndexFlatIP` / `IndexHNSWFlat`) remains a documented optional scaling path for when the corpus expands past 100,000 chunks, but is **not required for Step 3**.

---

## 10. Similarity Metric

### Metric: Cosine Similarity via Inner Product of Unit Vectors
1. Offline index embeddings are $L_2$-normalized upon creation:
   $$\mathbf{v}_{norm} = \frac{\mathbf{v}}{\|\mathbf{v}\|_2}$$
2. Query embeddings are $L_2$-normalized at runtime:
   $$\mathbf{q}_{norm} = \frac{\mathbf{q}}{\|\mathbf{q}\|_2}$$
3. Cosine similarity reduces to the inner product:
   $$\text{sim}(\mathbf{q}, \mathbf{v}) = \mathbf{q}_{norm} \cdot \mathbf{v}_{norm} \in [-1.0, 1.0]$$

---

## 11. Top-K and Threshold Calibration Plan

### 11.1 Removal of Predetermined Thresholds
> **Semantic similarity thresholds will be determined empirically from the semantic benchmark.**

No production similarity threshold (e.g. 0.70 or 0.75) is assumed prior to benchmarking. Threshold calibration will be performed during Phase 3F by evaluating precision-recall trade-offs on ground-truth benchmark pairs.

### 11.2 Experimental Candidate Pool
To avoid freezing top-$K$ prematurely:
- **Experimentation Candidate Pool:** Retrieve an initial pool of:
  $$\text{initial\_candidate\_pool} = 25$$
- During Phase 3F benchmarking, evaluate:
  - Recall@5, Recall@10, Recall@15, Recall@25
  - Precision@5, Precision@10
  - Mean Reciprocal Rank (MRR)
  - False-positive rate on negative controls
- The production cutoff $K_{semantic}$ and minimum threshold $\tau_{semantic}$ will be selected based on benchmark data.

---

## 12. Exact + Semantic Fusion Architecture

### 12.1 Conceptual Query Pipeline

```text
                    USER QUERY
                        │
                        ▼
                QueryNormalizer
                        │
             ┌──────────┴──────────┐
             ▼                     ▼
      EXACT PIPELINE          SEMANTIC PIPELINE
             │                     │
      Surface + Lemma         E5 candidate model
             │                     │
             │                Vector search
             │                     │
             └──────────┬──────────┘
                        ▼
                 Deduplication
                        │
                        ▼
               EvidenceAggregator
                        │
                        ▼
             Existing Context Selector
                        │
                        ▼
                   EvidencePack
                        │
                        ▼
                  LLM Interpreter
```

### 12.2 Strict Preservation of Existing Context Selection
The initial Step 3 implementation will **NOT** modify `SentamizhContextSelector`. 

The existing context selector will receive aggregated evidence without alteration. Only after benchmark results demonstrate an empirical context-selection deficiency will modifying `SentamizhContextSelector` be considered.

### 12.3 Priority Ranking Hierarchy
In `EvidenceAggregator`, candidates are prioritized deterministically:
1. **Exact Surface Match** (FTS5 Pass 1)
2. **Exact Lemma Match** (FTS5 Pass 2 via ThamizhiMorph lemma)
3. **Semantic Match** (Dense vector search)

Semantic similarity is recorded in `metadata["similarity_score"]`. No global arbitrary scoring weights (e.g. $0.6 \times \text{exact} + 0.4 \times \text{semantic}$) will be introduced.

---

## 13. Evidence Contract Integration

Semantic retrieval results map directly into the existing `Evidence` dataclass (`backend/schemas/evidence.py`):

```python
Evidence(
    surface=clean_query,
    lemma=None,  # NEVER fabricated by semantic retrieval
    source="Project Madurai",
    evidence_type="literary_context",
    passage=chunk["original_text"],
    work=chunk["work"],
    author=chunk["author"],
    period=chunk["period"],
    genre=chunk["genre"],
    verse=verse_val,
    source_url=chunk["source_url"],
    source_id=chunk["chunk_id"],
    metadata={
        "chunk_id": chunk["chunk_id"],
        "corpus_version": chunk["corpus_version"],
        "release_no": chunk["release_no"],
        "canto": chunk["canto"],
        "chapter": chunk["chapter"],
        "stanza_number": chunk["stanza_number"],
        "retrieval_method": "semantic",  # or "exact+semantic"
        "similarity_score": round(float(score), 4),
        "status": "FOUND"
    }
)
```

---

## 14. Semantic Adapter Design & Lifecycle

### 14.1 Independent Adapter Contract
Encapsulated in `ProjectMaduraiSemanticAdapter(ResourceAdapter)`:
- Maintains its own thread-safe, read-only connection to the vector index.
- Does not modify or depend on internal state of `ProjectMaduraiExactAdapter`.

### 14.2 Lazy Process-Local Lifecycle
To preserve the current Django architecture and prevent worker boot delays:
- **Django Starts:** Semantic model is **NOT** loaded.
- **First Semantic Query:** Model and vector index are lazily loaded into worker memory.
- **Subsequent Queries:** Reused process-locally via `SOLServiceRegistry`.
- **Worker Isolation:** Exact retrieval remains available immediately upon boot, even before the semantic model is loaded.
- **No Eager Warm-Up:** Automatic model warm-up during worker boot is omitted in the initial implementation.

---

## 15. Deduplication Strategy

### 15.1 Intra-Resource Deduplication: `(source, chunk_id)`
If a chunk is retrieved by both exact FTS and semantic search:
- The exact candidate is preserved as the base `Evidence` object.
- It is annotated with semantic information:
  ```python
  ev.metadata["retrieval_method"] = "exact+semantic"
  ev.metadata["similarity_score"] = float(semantic_score)
  ```
- Zero duplicate evidence entries are produced.

### 15.2 Cross-Resource Agreement
If both Sentamizh and Project Madurai yield matching passages:
- They remain distinct `Evidence` instances to reflect multi-resource validation.

---

## 16. Failure & Fallback Behavior

| Scenario | Detection | Fallback Behavior | System Impact |
|---|---|---|---|
| Vector file missing (`madurai_semantic_vectors.npy`) | File existence check fails | Log warning; return empty semantic evidence | Exact retrieval unaffected |
| Model weights missing / offline | Checkpoint load failure | Log warning; disable semantic adapter | Exact retrieval unaffected |
| Checksum mismatch | DB checksum != metadata checksum | Log error; refuse to load stale vector index | Exact retrieval unaffected |
| Dimension mismatch | Model dim != vector dim | Log error; bypass semantic retrieval | Exact retrieval unaffected |
| Query timeout (> 150 ms) | Adapter execution timer | Terminate semantic search; log warning | Exact retrieval unaffected |

---

## 17. Benchmark Design & Gold-Standard Requirements

A dedicated benchmark suite will be specified in `research/SEMANTIC_BENCHMARK.md`:

### 17.1 Benchmark Query Classes
1. **Class A: Exact Lexical Controls** (e.g. `மரம்`, `அறம்`, `யாழ்`)
   - Verifies that adding semantic retrieval causes zero regressions on existing lexical lookups.
2. **Class B: Inflectional Queries** (e.g. `மரங்களில்`, `மனிதர்களுக்கு`, `செய்தார்கள்`)
   - Evaluates retrieval across FTS, ThamizhiMorph + lemma expansion, and semantic search.
   - Clarifies that semantic retrieval bridges inflectional gaps via vector proximity without performing grammatical analysis.
3. **Class C: Conceptual Queries (Primary Objective)**
   - Queries testing thematic concepts with zero lexical overlap:
     - Respecting parents (`பெற்றோரை மதித்தல்`)
     - Value of education in youth (`இளமையில் கல்வி`)
     - Impermanence of wealth/life (`நிலையாமை`)
     - Dignity of agriculture (`உழவுத் தொழில் மாண்பு`)
     - Truthfulness (`வாய்மை / உண்மை`)
     - Steadfast friendship (`உண்மையான நட்பு`)
     - Courage in battle (`போர்க்கள வீரம்`)
     - Surrender and devotion (`இறைபக்தி / சரணாகதி`)
4. **Class D: Negative / Out-of-Domain Controls**
   - Modern slang, foreign terms, nonsense queries (`போலிவார்த்தை123`).
   - Used to calibrate false-positive rejection.

### 17.2 Gold-Label Ground Truth Schema
To avoid assuming an expected stanza is automatically gold-standard, every benchmark case must record:
```json
{
  "query_id": "SEM-C001",
  "query": "பெற்றோரை மதித்தல்",
  "category": "conceptual",
  "gold_chunks": [
    {
      "work": "கொன்றை வேந்தன்",
      "chunk_id": "PM-KONRAI-0002",
      "canonical_verse": "அன்னையும் பிதாவும் முன்னறி தெய்வம்.",
      "relevance_rationale": "Direct didactic imperative establishing parents as primary visible deities.",
      "label_justification": "Traditional Tamil didactic canon (Avvaiyar)."
    }
  ]
}
```

---

## 18. Evaluation Metrics

1. **Recall@K ($K \in \{5, 10, 15, 25\}$)**
2. **Precision@K ($K \in \{5, 10\}$)**
3. **Mean Reciprocal Rank (MRR)**
4. **Exact-Only vs Semantic-Only vs Hybrid Recall**
5. **False Positive Rate (FPR)** on Class D controls
6. **Query Latency Distribution:** Actual $p50, p95, p99$ measured during execution.

---

## 19. Classical Tamil-Specific Evaluation

The benchmark must evaluate:
- **Sandhi Compounds:** Agglutinated poetry lines where compound words lack token separation.
- **Archaic Vocabulary:** Classical terms with obsolete grammatical inflections.
- **Metaphorical Couplets:** Allegorical expressions (e.g. life as a bubble on water representing impermanence).

---

## 20. Performance Targets (Engineering Goals vs Actuals)

All performance metrics represent engineering targets to be verified during benchmarking:

| Metric | Engineering Target | Status / Actual |
|---|---|---|
| Offline Ingestion (14K chunks, CPU 6-threads) | $\le 4\text{ minutes}$ | To be measured in Phase 3C |
| Peak Build Memory | $\le 1.8\text{ GB}$ | To be measured in Phase 3C |
| Query Embedding Latency (CPU) | $\le 45\text{ ms}$ | To be measured in Phase 3B |
| Vector Search Latency (NumPy dot product) | $\le 2.5\text{ ms}$ | To be measured in Phase 3B |
| Candidate Fusion Latency | $\le 0.5\text{ ms}$ | To be measured in Phase 3E |
| Total Net Engine Latency Increase | $\le 50\text{ ms}$ | To be measured in Phase 3F |

---

## 21. Testing Strategy

### Unit Tests (`tests/test_semantic_retrieval.py`)
- Text formatting for Tirukkural, aphorisms, and poetry.
- Embedding-time filtering of navigation links and contact headers.
- Unit-vector normalization and dot-product mathematical correctness.
- Adapter initialization, error handling, and thresholding.

### Integration Tests (`tests/test_semantic_integration.py`)
- Candidate deduplication with exact FTS results.
- Verification that exact matches strictly outrank semantic matches.
- Graceful degradation when the `.npy` vector index is missing or unreadable.

### Regression Tests
- All 35 existing tests (`test_project_madurai.py`, `test_retrieval.py`, `test_unified_benchmark.py`) must remain 100% green.

---

## 22. Security & Data Hygiene

- Webmaster contact header in `PM-SILAP_MADURAI-0003` is filtered from vector indexing.
- Model weights are verified using immutable git commit hashes.
- Zero network telemetry or cloud API dependencies.

---

## 23. Future Scaling

The flat NumPy matrix architecture scales cleanly:
- 14.3K chunks: ~42 MB RAM, ~1.8 ms search.
- 50K chunks: ~146 MB RAM, ~5.5 ms search.
- 100K chunks: ~293 MB RAM, ~11.0 ms search.
Above 100K chunks, FAISS HNSW or IVF indexing can be introduced without altering adapter interfaces.

---

## 24. Index Versioning & Metadata Schema

Index files in `data/processed/`:
- `madurai_semantic_vectors.npy`: L2-normalized float32 matrix.
- `madurai_semantic_meta.json`: Version manifest with pinned commit hash.

```json
{
  "semantic_index_version": "1.0.0",
  "corpus_version": "1.0.0",
  "manifest_version": "1.0.0",
  "source_db_file": "madurai_exact.db",
  "source_db_sha256": "<computed_sha256>",
  "build_timestamp_utc": "2026-10-01T12:00:00Z",
  "embedding_model": {
    "name": "intfloat/multilingual-e5-base",
    "revision": "d13111270745fc77764722db3c7dd927515c0e17",
    "dimension": 768,
    "max_sequence_length": 512,
    "prefix_query": "query: ",
    "prefix_passage": "passage: "
  },
  "vector_storage": {
    "file_name": "madurai_semantic_vectors.npy",
    "sha256": "<computed_sha256>",
    "total_vectors": 14381,
    "metric": "inner_product_cosine",
    "dtype": "float32"
  },
  "preprocessing": {
    "version": "1.0.0",
    "suppressed_chunk_ids": [
      "PM-SILAP_MADURAI-0003",
      "PM-CHINTHAMANI-0003"
    ],
    "short_chunk_treatment": "aphorisms_indexed_colophons_suppressed"
  },
  "chunk_id_sequence": [
    "PM-TK-0001",
    "PM-TK-0002"
  ]
}
```

---

## 25. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Classical Tamil token fragmentation | Vocabulary dilution | Thematic chapter prefixing; exact FTS remains primary |
| Memory pressure on 8GB host | Process sluggishness | Lazy process-local loading; fallback model option |
| Semantic drift / false positives | Dilution of high-precision exact results | Empirical threshold calibration; exact > lemma > semantic priority |
| PyTorch CPU cold-start latency | Initial query delay | Handled lazily; exact retrieval remains available immediately |

---

## 26. Final Recommendation

### **PROCEED TO STEP 3 IMPLEMENTATION UPON APPROVAL**
- **Primary Model Candidate:** `intfloat/multilingual-e5-base` (to be locally benchmarked in Phase 3B).
- **Initial Vector Index:** Flat NumPy memory-mapped matrix (`madurai_semantic_vectors.npy`).
- **Context Selector:** Retain existing `SentamizhContextSelector` unchanged for initial implementation.
- **Fusion:** Exact Surface > Exact Lemma > Semantic, with deduplication by `(source, chunk_id)`.

---

## 27. Corrected Step 3 Implementation Plan

Execution will proceed in 6 sequential phases:

### Phase 3A — Semantic Preprocessing
- Implement `backend/retrieval/semantic_preprocessing.py`.
- Implement canonical embedding text formatting and in-memory residual filters.
- Derive exact short-chunk statistics dynamically from `madurai_exact.db`.
- Unit tests verifying clean text formatting and artifact suppression.

### Phase 3B — Embedding Benchmark & Model Validation
- Load candidate model `intfloat/multilingual-e5-base` locally.
- Verify local CPU execution on Ryzen 5 5600H.
- Measure actual memory footprint, single-query latency, and batch throughput.
- Inspect subword tokenization behavior on representative classical Tamil verses.
- If primary candidate exceeds memory or latency ceilings, evaluate fallback candidate `intfloat/multilingual-e5-small`.

### Phase 3C — Offline Vector Index Build
- Implement `scripts/build_madurai_semantic_index.py`.
- Generate L2-normalized embeddings for valid chunks.
- Serialize `madurai_semantic_vectors.npy` and `madurai_semantic_meta.json`.
- Verify checksums, row/chunk parity, and build time.

### Phase 3D — Semantic Adapter
- Implement `backend/resources/project_madurai_semantic.py` (`ProjectMaduraiSemanticAdapter`).
- Implement vector search with NumPy inner product.
- Configure candidate pool size ($\text{initial\_candidate\_pool} = 25$) and threshold parameter.
- Implement lazy model/index loading and graceful failure handling.
- Unit test adapter lookup, thresholding, and top-$K$.

### Phase 3E — Retrieval Integration
- Register `ProjectMaduraiSemanticAdapter` in `RetrievalEngine`.
- Implement candidate fusion and deduplication by `(source, chunk_id)`.
- Enforce Exact Surface > Exact Lemma > Semantic ranking priority.
- Preserve existing `SentamizhContextSelector` without modification.
- Integration tests verifying deduplication and fallback.

### Phase 3F — Benchmark & Empirical Calibration
- Implement `scripts/run_semantic_benchmark.py` and `research/SEMANTIC_BENCHMARK.md`.
- Evaluate exact controls, inflectional comparisons, conceptual queries, and negative controls.
- Measure Recall@K, Precision@K, MRR, false-positive rate, and latency percentiles ($p50, p95, p99$).
- Empirically calibrate production threshold $\tau_{semantic}$ and cutoff $K_{semantic}$.
- Verify that all 35 existing tests remain 100% green.

---

STATUS:
DESIGN REVISED — READY FOR IMPLEMENTATION REVIEW

MODEL:
Primary candidate: intfloat/multilingual-e5-base
Final selection: PENDING LOCAL BENCHMARK

VECTOR INDEX:
NumPy normalized dense matrix

THRESHOLD:
PENDING EMPIRICAL CALIBRATION

TOP-K:
PENDING EMPIRICAL CALIBRATION

CONTEXT SELECTOR:
UNCHANGED FOR INITIAL IMPLEMENTATION

MODEL LOADING:
LAZY PROCESS-LOCAL

EXACT DATABASE:
IMMUTABLE

IMPLEMENTATION:
NOT PERFORMED
