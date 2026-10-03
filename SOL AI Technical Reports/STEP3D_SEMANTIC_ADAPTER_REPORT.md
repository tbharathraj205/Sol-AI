# SOL AI — Step 3D: Project Madurai Semantic Retrieval Adapter Implementation Report

## 1. Status

- **Step Status:** **COMPLETE & FULLY VERIFIED**
- **Artifacts:** Isolated Project Madurai Semantic Adapter implemented and verified
- **Test Suite:** 17/17 isolated semantic adapter tests passing; 104/104 full regression test suite passing
- **Deterministic Pipeline Impact:** ZERO modifications to existing exact retrieval components or databases

---

## 2. Adapter Location & Interface

- **Module Path:** `backend/resources/project_madurai_semantic.py`
- **Class:** `ProjectMaduraiSemanticAdapter`
- **Inheritance:** `backend.resources.base.ResourceAdapter`
- **Signature:**
  ```python
  def lookup(
      self,
      query: str,
      lemma: Optional[str] = None,
      top_k: int = 10,
  ) -> List[Evidence]:
  ```
- **Separation of Concerns:**
  - `backend/resources/project_madurai.py` remains 100% untouched and dedicated to exact FTS5 retrieval.
  - `backend/resources/project_madurai_semantic.py` is an isolated, independently testable component designed strictly for dense semantic similarity search.

---

## 3. Model Loading & Lifecycle Management

- **Model Specification:**
  - **ID:** `intfloat/multilingual-e5-small`
  - **Revision (pinned commit):** `614241f622f53c4eeff9890bdc4f31cfecc418b3`
  - **Embedding Dimension:** `384`
  - **Dtype:** `float32`
  - **Pooling:** Mean pooling over non-padded tokens respecting attention mask
  - **Normalization:** L2 unit normalization (`||v||_2 = 1.0`)
- **Lazy Process-Local Lifecycle:**
  - Neither the PyTorch model nor the vector matrix/metadata are loaded upon module import or adapter instantiation.
  - Loading occurs lazily on the first invocation of `lookup()` or explicit call to `ensure_loaded()`.
  - Process-local thread-safe caching (`_MODEL_CACHE` with `threading.Lock`) ensures weights are reused across lookups and instances without duplicate memory overhead or cross-process state.
  - Evaluation mode (`model.eval()`) with `torch.inference_mode()` is strictly enforced.

---

## 4. Defensive Artifact Validation

The adapter verifies the integrity and compatibility of all permanent vector artifacts prior to accepting them:

1. **File Existence:**
   - Vector file: `data/processed/madurai_semantic_vectors.npy`
   - Metadata file: `data/processed/madurai_semantic_meta.json`
2. **Vector Matrix Schema:**
   - Dtype strictly `float32`
   - 2-dimensional matrix (`ndim == 2`)
   - Column dimension exactly `384` (`shape[1] == 384`)
   - Absence of `NaN` or `Inf`
3. **Metadata Schema:**
   - Top-level `schema_version` present
   - Embedding configuration matches pinned `model_id`, `model_revision`, and `dimension == 384`
   - Metadata `items` list present and aligns 1-to-1 with vector count
4. **1-to-1 Alignment & Contiguity:**
   - Vector matrix rows count strictly equals metadata `items` count (`13,284`)
   - Sequential indexing: `items[i]["vector_index"] == i` for all $i \in [0, 13283]$
   - All `chunk_id` values are non-empty and globally unique
5. **Numerical Normalization:**
   - Validates unit L2 normalization across representative vector samples (`atol=1e-3`)
6. **Corpus Fingerprint & Database Reference:**
   - Reads and records `corpus_fingerprint` (`d6ab06f533104b7df9172fdf34a2d90c6a058eb84c2b17bf5db3339e7b6084fe`) and database SHA-256 (`9eef3a08dd0acf68592036fc230c5607dff09821ea456708101be9eabaefdd41`).
   - Rebuilding is never triggered silently if fingerprints do not match.

---

## 5. Query Encoding

- **E5 Prefixing:**
  - Queries are explicitly prefixed as:
    ```text
    query: {user_query}
    ```
  - Corpus vectors previously built in Step 3C use `passage: ...`.
  - Asymmetric contrastive query-passage alignment is preserved without query reconstruction.
- **Normalization Policy:**
  - Leading/trailing whitespace is stripped (`query.strip()`).
  - No morphological derivation, lemmatization, FTS, or ThamizhiMorph invocation occurs inside the semantic adapter.
- **Encoding Output:**
  - 1D NumPy array of shape `(384,)`, `float32`, unit L2-normalized, strictly finite.

---

## 6. Similarity Search

- **Exhaustive Dense NumPy Inner Product:**
  - Because corpus vectors $V \in \mathbb{R}^{13284 \times 384}$ and query vector $q \in \mathbb{R}^{384}$ are L2-normalized:
    $$\text{CosineSimilarity}(q, V_i) = \langle q, V_i \rangle$$
  - Computed via single vectorized matrix-vector multiplication:
    ```python
    scores = self._vectors @ query_vector
    ```
  - Eliminates external vector index dependencies (no FAISS, no Chroma).
  - Search latency across all 13,284 candidates: $\approx 1.1\text{ ms}$.

---

## 7. Deterministic Top-K Ordering

- **Ranking Strategy:**
  - Primary sort key: Descending similarity score (`-scores`)
  - Secondary sort key: Ascending `chunk_id` string lexicographic order (`self._chunk_ids`)
  - Implemented via NumPy `lexsort`:
    ```python
    order = np.lexsort((self._chunk_ids, -scores))
    top_indices = order[:min(top_k, len(order))]
    ```
- **Strict Invariants:**
  - Identical queries yield bit-for-bit identical candidate rankings and floating-point scores.
  - Nested subset guarantee:
    $$\text{results}_1 \subseteq \text{results}_5 \subseteq \text{results}_{10} \subseteq \text{results}_{25}$$
  - $\text{results}_1$ is strictly the prefix of $\text{results}_5$, $\text{results}_5$ is strictly the prefix of $\text{results}_{10}$, etc.
- **Parameter Support:**
  - Supports arbitrary positive $K$ (e.g. $1, 5, 10, 25$).
  - Conservative default $K = 10$ for isolated testing.
  - **No production threshold applied:** similarity scores are exposed on metadata; no candidate filtering threshold ($< 0.7$, etc.) is applied at this stage.

---

## 8. Evidence Mapping & Provenance

Matches the existing `Evidence` dataclass contract (`backend/schemas/evidence.py`):

| Evidence Field | Value | Source / Rationale |
| :--- | :--- | :--- |
| `surface` | `clean_query` | User surface query input |
| `lemma` | `lemma` or `None` | Preserves caller-supplied lemma; **NEVER** fabricated |
| `source` | `"Project Madurai"` | Standard source identifier |
| `evidence_type` | `"literary_context"` | Categorized under literary contexts for aggregator/packs |
| `passage` | `original_text` | Retrieved from canonical read-only SQLite DB via `chunk_id` |
| `work` | `work` / `work_name` | Canonical work title |
| `author` | `author` | Work author |
| `period` | `period` | Literary period (e.g. Sangam, Medieval) |
| `genre` | `genre` | Literary genre |
| `verse` | `verse_number` / `stanza_number` | Stanza or verse identifier |
| `source_url` | `source_url` | Canonical Project Madurai URL |
| `source_id` | `chunk_id` | Unique chunk ID (e.g. `PM-TK-0216`) |
| `metadata['status']` | `"FOUND"` | Required for EvidenceAggregator candidate filtering |
| `metadata['retrieval_mode']` | `"semantic"` | Distinguishes semantic evidence from exact evidence |
| `metadata['similarity_score']` | `float` | Cosine similarity score (rounded to 6 decimal places) |
| `metadata['corpus_version']` | `corpus_version` | Corpus version |
| `metadata['line_range']` | `line_range` | Line range in original source file |

---

## 9. Failure Handling & Closed Boundaries

- **Fail-Closed Policy:**
  - Missing vector or metadata file
  - Malformed metadata JSON
  - Dimensionality mismatch (e.g. 128 vs 384)
  - Vector/metadata count mismatch
  - Duplicate chunk IDs in metadata
  - Incompatible vector dtype (e.g. float64 vs float32)
  - Corrupted vector files
  - Model loading or PyTorch execution failure
- **Error Behavior:**
  - Direct validation calls raise descriptive exceptions (`FileNotFoundError`, `SemanticArtifactError`).
  - Runtime `lookup()` calls catch errors, log diagnostic messages, and return safe error Evidence:
    ```python
    Evidence(
        surface=clean_query,
        lemma=lemma,
        source="Project Madurai",
        evidence_type="literary_context",
        metadata={
            "error": str(e),
            "status": "ERROR",
            "retrieval_mode": "semantic",
        }
    )
    ```
  - Empty queries (`""`, whitespace) safely return `[]`.
  - Semantic lookup failures **NEVER** throw uncaught exceptions or interrupt deterministic exact retrieval.

---

## 10. Performance Measurements

Measured on isolated `ProjectMaduraiSemanticAdapter` (Windows x64, Python 3.12, PyTorch CPU, 25 repetitions per query, $K=10$):

### Cold Initialization

- **One-time Loading Time:** `4,568.58 ms`
  - Includes: Pinned E5 model & tokenizer loading, JSON metadata parsing (7.3 MB), and 13,284-vector float32 matrix loading.

### Warm Retrieval Latency

| Query | Category | E5 Encoding p50 | NumPy Search + DB p50 | Total Latency p50 | Total Latency p95 |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `மரம்` | Base noun | $11.94\text{ ms}$ | $3.36\text{ ms}$ | **$15.30\text{ ms}$** | **$17.45\text{ ms}$** |
| `அறம்` | Base noun | $13.03\text{ ms}$ | $3.28\text{ ms}$ | **$16.05\text{ ms}$** | **$17.36\text{ ms}$** |
| `இனிது` | Adjective/Stative | $12.74\text{ ms}$ | $3.37\text{ ms}$ | **$15.81\text{ ms}$** | **$16.97\text{ ms}$** |
| **Aggregate** | — | **$12.57\text{ ms}$** | **$3.34\text{ ms}$** | **$15.72\text{ ms}$** | **$17.26\text{ ms}$** |

- Exhaustive matrix dot product over 13,284 vectors plus SQLite primary-key passage retrieval completes in $\approx 3.3\text{ ms}$.
- Over 75% of execution time is single-query forward inference in E5-small.

---

## 11. Test Results

### Isolated Semantic Adapter Suite (`tests/test_project_madurai_semantic.py`)

```text
tests/test_project_madurai_semantic.py::TestProjectMaduraiSemanticAdapter::test_caller_supplied_lemma_preserved PASSED
tests/test_project_madurai_semantic.py::TestProjectMaduraiSemanticAdapter::test_corrupt_metadata_json_fails_safely PASSED
tests/test_project_madurai_semantic.py::TestProjectMaduraiSemanticAdapter::test_duplicate_chunk_id_fails_safely PASSED
tests/test_project_madurai_semantic.py::TestProjectMaduraiSemanticAdapter::test_empty_and_whitespace_query PASSED
tests/test_project_madurai_semantic.py::TestProjectMaduraiSemanticAdapter::test_invalid_dimension_fails_safely PASSED
tests/test_project_madurai_semantic.py::TestProjectMaduraiSemanticAdapter::test_invalid_model_revision_fails_safely PASSED
tests/test_project_madurai_semantic.py::TestProjectMaduraiSemanticAdapter::test_invalid_vector_dtype_fails_safely PASSED
tests/test_project_madurai_semantic.py::TestProjectMaduraiSemanticAdapter::test_known_semantic_benchmark_queries PASSED
tests/test_project_madurai_semantic.py::TestProjectMaduraiSemanticAdapter::test_lazy_initialization PASSED
tests/test_project_madurai_semantic.py::TestProjectMaduraiSemanticAdapter::test_missing_metadata_file_fails_safely PASSED
tests/test_project_madurai_semantic.py::TestProjectMaduraiSemanticAdapter::test_missing_vector_file_fails_safely PASSED
tests/test_project_madurai_semantic.py::TestProjectMaduraiSemanticAdapter::test_query_embedding_properties PASSED
tests/test_project_madurai_semantic.py::TestProjectMaduraiSemanticAdapter::test_representative_retrieval_and_evidence_contract PASSED
tests/test_project_madurai_semantic.py::TestProjectMaduraiSemanticAdapter::test_search_determinism PASSED
tests/test_project_madurai_semantic.py::TestProjectMaduraiSemanticAdapter::test_top_k_nested_subsets PASSED
tests/test_project_madurai_semantic.py::TestProjectMaduraiSemanticAdapter::test_vector_metadata_count_mismatch_fails_safely PASSED
tests/test_project_madurai_semantic.py::TestProjectMaduraiSemanticAdapter::test_zero_or_negative_top_k PASSED

============================= 17 passed in 8.44s ==============================
```

### Full Regression Suite

```text
pytest tests/test_semantic_preprocessing.py tests/test_project_madurai.py tests/test_retrieval.py tests/test_unified_benchmark.py tests/test_embedding_benchmark.py tests/test_semantic_vectors.py tests/test_project_madurai_semantic.py

tests/test_semantic_preprocessing.py ................................... [ 33%]
tests/test_project_madurai.py ...........................                [ 59%]
tests/test_retrieval.py .....                                            [ 64%]
tests/test_unified_benchmark.py ...                                      [ 67%]
tests/test_embedding_benchmark.py .......                                [ 74%]
tests/test_semantic_vectors.py ..........                                [ 83%]
tests/test_project_madurai_semantic.py .................                 [100%]

======================= 104 passed in 77.21s (0:01:17) ========================
```

---

## 12. Strict Scope Boundary Verification

```text
Permanent vectors regenerated: NO
Permanent vectors modified: NO
Exact Project Madurai DB modified: NO
Exact adapter modified: NO
RetrievalEngine modified: NO
EvidenceAggregator modified: NO
EvidencePack modified: NO
Django modified: NO
Frontend modified: NO
Chrome extension modified: NO
Production K finalized: NO
Production threshold finalized: NO
Hybrid ranking implemented: NO
Git commit: NO
Git push: NO
```

---

## 13. Conclusion & Readiness for Step 3E

Step 3D is fully implemented, verified, and isolated. The semantic adapter strictly satisfies the `ResourceAdapter` contract, exposes transparent similarity metadata, executes in $\approx 15\text{ ms}$, guarantees deterministic top-K ordering, and fails closed without affecting the deterministic retrieval pipeline.

No production integration has been performed. Step 3E may now proceed to integrate this adapter into `RetrievalEngine` and `EvidenceAggregator`.
