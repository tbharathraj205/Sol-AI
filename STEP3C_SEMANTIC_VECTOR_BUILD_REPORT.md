# STEP 3C: PERMANENT SEMANTIC VECTOR BUILD REPORT

**Project:** SOL AI (Tamil Lexical & Contextual Intelligence Engine)  
**Document:** `STEP3C_SEMANTIC_VECTOR_BUILD_REPORT.md`  
**Phase:** Step 3C (Permanent Semantic Vector Build)  
**Status:** COMPLETED & VERIFIED  
**Date:** October 2026  
**Source of Truth:** `data/processed/madurai_exact.db` & `backend/retrieval/semantic_preprocessing.py`  

---

## 1. Status

Step 3C is **COMPLETED AND VERIFIED**. The permanent offline semantic vector representation and accompanying metadata index for the eligible Project Madurai corpus have been deterministically constructed, verified, and saved to disk.

### Strict Scope Boundary Invariants Maintained
- **Semantic adapter created:** NO
- **RetrievalEngine modified:** NO
- **EvidenceAggregator modified:** NO
- **EvidencePack modified:** NO
- **Django modified:** NO
- **Frontend modified:** NO
- **Exact Project Madurai DB modified:** NO (strict read-only `PRAGMA query_only = ON;`, SHA-256 verified)
- **Git commit:** NO
- **Git push:** NO

---

## 2. Input Corpus

The input corpus was dynamically queried from the canonical Project Madurai SQLite database without hardcoding counts:

| Property | Value |
|---|---|
| **Database File** | `data/processed/madurai_exact.db` |
| **Total Canonical Chunks** | **14,383** |
| **Eligible Semantic Passages** | **13,284** |
| **Suppressed Non-Poetic Chunks** | **1,099** |
| **Corpus Integrity Verification** | $13,284 + 1,099 = 14,383$ (100% accounted for) |
| **Database Access Mode** | `file:...mode=ro` with `PRAGMA query_only = ON;` |
| **Canonical Ordering** | `ORDER BY chunk_id ASC` |

---

## 3. Model & Revision

The approved embedding model selected during Step 3B was loaded with an immutable, pinned Hugging Face commit hash:

| Property | Specification |
|---|---|
| **Model ID** | `intfloat/multilingual-e5-small` |
| **Pinned Git Revision** | `614241f622f53c4eeff9890bdc4f31cfecc418b3` |
| **Mutable References Used (`main`, `latest`)** | **NONE** (Strictly prohibited) |
| **Architecture** | BertModel / XLM-RoBERTa multilingual variant (12 layers, 12 heads) |
| **Parameter Count** | 117,653,760 (~117.7M parameters) |
| **Tokenizer** | `XLMRobertaTokenizer` (vocab size: 250,002) |

---

## 4. Embedding Configuration

| Parameter | Configuration | Rationale / Verification |
|---|---|---|
| **Embedding Dimension** | `384` float32 values | Standard E5-small representation |
| **Max Sequence Length** | `512` tokens | Covers 99.9% of corpus passages without truncation; model hardware limit |
| **Padding Strategy** | Dynamic per-batch (`padding=True`) | Optimizes CPU inference efficiency on shorter couplets and aphorisms |
| **Truncation** | `truncation=True` | Safeguards the 12 longest narrative passages from indexing overflows |
| **Pooling Strategy** | Mean pooling with attention mask | Masked average over token representations $\mathbf{e} = \frac{\sum m_i \mathbf{h}_i}{\sum m_i}$ |
| **Normalization** | L2 Normalization (`dim=1, p=2`) | Enforces unit sphere $\|\mathbf{v}\|_2 = 1.0$; dot product equals cosine similarity |
| **Corpus Passage Prefix** | `passage: ` | Standard asymmetric E5 passage prefix |
| **Pre-processing Module** | `prepare_chunk()` | Imported directly from `backend.retrieval.semantic_preprocessing` |

---

## 5. Build Configuration

| Property | Value |
|---|---|
| **Build Script** | `scripts/build_madurai_semantic_vectors.py` |
| **Inference Hardware** | 13th Gen Intel(R) Core(TM) i3-1305U (CPU inference) |
| **PyTorch Configuration** | `torch.inference_mode()`, `model.eval()`, `torch.set_num_threads(6)` |
| **Batch Size** | `32` (stable throughout build, zero OOM events) |
| **Rerunnability** | Safe, deterministic overwrite replacing existing artifacts |

---

## 6. Vector Statistics

| Statistic | Theoretical / Expected | Measured / Actual | Status |
|---|---:|---:|:---:|
| **Vector Count** | 13,284 | **13,284** | MATCH |
| **Dimension** | 384 | **384** | MATCH |
| **Data Type** | `float32` | `float32` | MATCH |
| **NaN Values** | 0 | **0** | PASSED |
| **Inf Values** | 0 | **0** | PASSED |
| **Minimum L2 Norm** | 1.000000 | **0.99999982** | PASSED ($\Delta < 2 \times 10^{-7}$) |
| **Maximum L2 Norm** | 1.000000 | **1.00000012** | PASSED ($\Delta < 2 \times 10^{-7}$) |
| **Mean L2 Norm** | 1.000000 | **1.00000000** | PASSED |
| **Raw Matrix Bytes** | $13,284 \times 384 \times 4 = 20,404,224\text{ B}$ | **20,404,224 B** | MATCH |
| **Actual File Size (`.npy`)** | $20,404,224\text{ B} + 128\text{ B header}$ | **20,404,352 B (19.46 MB)** | MATCH |

---

## 7. Metadata Schema

Permanent metadata is persisted as a single JSON artifact: `data/processed/madurai_semantic_meta.json`.

```json
{
  "schema_version": "1.0.0",
  "build_timestamp": "2026-10-01T16:35:17.078491+00:00",
  "corpus_fingerprint": "a49eb6a13ecbf04aa80f0899ab4eb482aee6587c67bf308940003ce73b9e4a3b",
  "corpus": {
    "name": "Project Madurai",
    "database": "madurai_exact.db",
    "database_sha256": "9eef3a08dd0acf68592036fc230c5607dff09821ea456708101be9eabaefdd41",
    "total_chunks": 14383,
    "eligible_chunks": 13284,
    "suppressed_chunks": 1099,
    "suppression_reasons": {
      "publication_source_header": 1,
      "speaker_attribution": 474,
      "structural_metadata": 557,
      "webmaster_contact": 1,
      "musical_stub": 66
    }
  },
  "embedding": {
    "model_id": "intfloat/multilingual-e5-small",
    "model_revision": "614241f622f53c4eeff9890bdc4f31cfecc418b3",
    "dimension": 384,
    "max_sequence_length": 512,
    "pooling": "mean",
    "normalized": true
  },
  "index": {
    "type": "numpy_dense",
    "metric": "inner_product",
    "ordering": "chunk_id_ascending",
    "vector_count": 13284,
    "dtype": "float32"
  },
  "items": [
    {
      "vector_index": 0,
      "chunk_id": "PM-AATHI-0001",
      "source": "Project Madurai",
      "work_id": "PM0002",
      "work_name": "ஆத்திசூடி",
      "author": "ஔவையார்",
      "period": "Medieval",
      "genre": "Didactic",
      "section": null,
      "sub_section": null,
      "stanza_number": 1,
      "source_url": "https://www.projectmadurai.org/pm_etexts/utf8/pmuni0002.html"
    }
  ]
}
```

### Provenance Guarantee
Every item in `items` maps to an exact row in `data/processed/madurai_exact.db` via `chunk_id`. Passage texts are **not duplicated** in JSON to avoid redundancy and prevent divergent sources of truth.

---

## 8. Alignment Verification

1. **Length Parity:**
   $$\text{len}(\text{metadata.items}) = 13,284 = \text{vectors.shape}[0]$$
2. **Contiguity:**
   $$\forall i \in [0, 13283], \quad \text{items}[i][\text{"vector\_index"}] == i$$
3. **Uniqueness:**
   All 13,284 `chunk_id` strings are distinct.
4. **Deterministic Sorting:**
   $$\text{items}[i][\text{"chunk\_id"}] < \text{items}[i+1][\text{"chunk\_id"}]$$
   Strictly ascending lexicographical chunk ID order matching `ORDER BY chunk_id ASC`.

---

## 9. Suppression Verification

Known non-poetic stubs and editorial artifacts were confirmed **strictly absent** from the semantic vectors and metadata:

| Chunk ID | Suppressed Category | Reason | Verified Absent? |
|---|---|---|:---:|
| `PM-SILAP_MADURAI-0003` | `webmaster_contact` | Webmaster email (`kalyan@geocities.com`) | **YES** |
| `PM-CHINTHAMANI-0003` | `publication_source_header` | Publication metadata colophon | **YES** |
| `PM-THEVARAM_APP-0001` | `musical_stub` | Standalone pann musical mode header | **YES** |
| `PM-KURUN-0001` | `speaker_attribution` | Standalone speaker colophon stub | **YES** |

Simultaneously, legitimate short aphorisms and couplets were confirmed **retained**:

| Chunk ID | Work | Stanza / Passage | Verified Present? |
|---|---|---|:---:|
| `PM-AATHI-0001` | ஆத்திசூடி | Invocation verse | **YES** (Index 0) |
| `PM-AATHI-0002` | ஆத்திசூடி | `அறம் செய விரும்பு` | **YES** (Index 1) |
| `PM-KONRAI-0001` | கொன்றை வேந்தன் | Invocation verse | **YES** (Index 110) |
| `PM-KONRAI-0002` | கொன்றை வேந்தன் | `அன்னையும் பிதாவும் முன்னறி தெய்வம்` | **YES** (Index 111) |
| `PM-TK-0001` | திருக்குறள் | `அகர முதல எழுத்தெல்லாம்...` | **YES** (Index 11954) |
| `PM-TK-0035` | திருக்குறள் | `அழுக்காறு அவாவெகுளி...` | **YES** (Index 11988) |
| `PM-TK-1330` | திருக்குறள் | Couplet 1330 (Final Kural) | **YES** (Index 13283) |

---

## 10. Determinism / Reproducibility

### Sample Re-encoding Consistency Check
A deterministic cross-section of 12 passages across the entire corpus was independently re-encoded from raw database text through `prepare_chunk()` and compared against the saved vector rows:

| Chunk ID | Vector Index | Work | Cosine Similarity | Max Absolute Difference |
|---|---:|---|---:|---:|
| `PM-AATHI-0001` | 0 | ஆத்திசூடி | 1.000000 | $4.47 \times 10^{-8}$ |
| `PM-AATHI-0002` | 1 | ஆத்திசூடி | 1.000000 | $4.47 \times 10^{-8}$ |
| `PM-KALI-0649` | 3321 | கலித்தொகை | 1.000000 | $0.00$ |
| `PM-PATHITRU-0103` | 6642 | பதிற்றுப்பத்து | 1.000000 | $4.47 \times 10^{-8}$ |
| `PM-SILAP_PUGAR-0178` | 8805 | சிலப்பதிகாரம் | 1.000000 | $5.22 \times 10^{-8}$ |
| `PM-THEVARAM_1-0669` | 9963 | தேவாரம் | 1.000000 | $5.96 \times 10^{-8}$ |
| `PM-TK-0001` | 11954 | திருக்குறள் | 1.000000 | $3.73 \times 10^{-8}$ |
| `PM-TK-0035` | 11988 | திருக்குறள் | 1.000000 | $3.73 \times 10^{-8}$ |
| `PM-TK-0066` | 12019 | திருக்குறள் | 1.000000 | $3.73 \times 10^{-8}$ |
| `PM-TK-0216` | 12169 | திருக்குறள் | 1.000000 | $3.82 \times 10^{-8}$ |
| `PM-TK-0279` | 12232 | திருக்குறள் | 1.000000 | $4.47 \times 10^{-8}$ |
| `PM-TK-1330` | 13283 | திருக்குறள் | 1.000000 | $4.47 \times 10^{-8}$ |

**Conclusion:** The permanent index is 100% numerically deterministic with zero indexing offset.

---

## 11. Database Immutability

The Project Madurai SQLite database (`data/processed/madurai_exact.db`) was strictly verified before and after the build process:

| Property | Before Build | After Build | Verification |
|---|---|---|:---:|
| **SHA-256** | `9eef3a08dd0acf68592036fc230c5607dff09821ea456708101be9eabaefdd41` | `9eef3a08dd0acf68592036fc230c5607dff09821ea456708101be9eabaefdd41` | **MATCH (Bit-for-bit)** |
| **Modification Time** | `1790777271.5575325` | `1790777271.5575325` | **MATCH (Untouched)** |
| **File Size** | 25,735,168 bytes | 25,735,168 bytes | **MATCH** |
| **Canonical Chunks** | 14,383 rows | 14,383 rows | **MATCH** |
| **FTS5 Index Rows** | 14,383 rows | 14,383 rows | **MATCH** |

---

## 12. Performance

| Metric | Measured Value |
|---|---|
| **Cold Model Load Time** | 4.23 s |
| **Total Passages Encoded** | 13,284 passages |
| **Batch Size** | 32 passages / batch |
| **Total Build Duration** | **989.47 s (16.49 minutes)** |
| **Average Encoding Throughput** | **13.43 texts / second** (74.48 ms / passage) |
| **Peak RAM Overhead** | ~720 MB total process RAM |
| **OOM / Crash Count** | 0 |

---

## 13. Test Results

Comprehensive unit, structural integrity, and regression testing were executed across all retrieval components:

```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Vishwa\Projects\SOL_AI
plugins: anyio-4.15.1
collected 87 items

tests\test_semantic_preprocessing.py ................................... [ 40%]
tests\test_project_madurai.py ...........................                [ 71%]
tests\test_retrieval.py .....                                            [ 77%]
tests\test_unified_benchmark.py ...                                      [ 80%]
tests\test_embedding_benchmark.py .......                                [ 88%]
tests\test_semantic_vectors.py ..........                                [100%]

======================== 87 passed in 63.69s (0:01:03) ========================
```

---

## 14. Output Artifacts

The following permanent artifacts were produced in `data/processed/`:

### 1. Vector Matrix
- **File:** `data/processed/madurai_semantic_vectors.npy`
- **File Size:** **20,404,352 bytes (19.46 MB)**
- **SHA-256:** `633253c3122165425ced99081e62ed49600e5ef932e71026a0a3afe33cf3ecef`
- **Shape:** `(13284, 384)`
- **Data Type:** `float32`
- **Normalization:** L2-normalized ($\|\mathbf{v}\|_2 = 1.0$)

### 2. Metadata Index
- **File:** `data/processed/madurai_semantic_meta.json`
- **File Size:** **7,323,272 bytes (6.98 MB)**
- **SHA-256:** `c68fc4f55a4f2d4760d865f9aecfe7ec139fe598d9289e79c98d4cc8d8c2ceb3`
- **Items Count:** 13,284 records
- **Format:** Formatted UTF-8 JSON

### Engineering Invariant Assertions
```text
Semantic adapter created: NO
RetrievalEngine modified: NO
EvidenceAggregator modified: NO
EvidencePack modified: NO
Django modified: NO
Frontend modified: NO
Exact Project Madurai DB modified: NO
Git commit: NO
Git push: NO
```

---

## 15. Next Step Readiness

With Step 3C completed and verified, the offline permanent vector representation is ready for consumption by **Step 3D (Semantic Adapter Implementation)**, where an in-memory NumPy dense cosine similarity adapter will be integrated following the `ResourceAdapter` contract.
