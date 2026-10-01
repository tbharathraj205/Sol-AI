"""
SOL AI — Step 3D: Project Madurai Semantic Retrieval Adapter Tests.

Verifies:
A. Lazy process-local initialization
B. Defensive artifact validation & safe failure behavior
C. Query embedding properties (dimension, normalization, numerical validity)
D. Semantic candidate retrieval and Evidence schema mapping
E. Known semantic benchmark queries and candidate relevance
F. Deterministic top-K ordering
G. Nested top-K subset invariants (top_1 ⊆ top_5 ⊆ top_10 ⊆ top_25)
H. Empty and whitespace-only query handling
"""

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from backend.resources.project_madurai_semantic import (
    PINNED_EMBEDDING_DIM,
    PINNED_MODEL_ID,
    PINNED_MODEL_REVISION,
    ProjectMaduraiSemanticAdapter,
    SemanticArtifactError,
)
from backend.schemas.evidence import Evidence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VECTORS_PATH = PROJECT_ROOT / "data" / "processed" / "madurai_semantic_vectors.npy"
METADATA_PATH = PROJECT_ROOT / "data" / "processed" / "madurai_semantic_meta.json"
DB_PATH = PROJECT_ROOT / "data" / "processed" / "madurai_exact.db"
BENCHMARK_PATH = PROJECT_ROOT / "tests" / "data" / "semantic_benchmark.json"


class TestProjectMaduraiSemanticAdapter(unittest.TestCase):
    """Test suite for isolated Project Madurai Semantic Adapter."""

    @classmethod
    def setUpClass(cls):
        """Ensure canonical artifacts exist before running adapter tests."""
        if not VECTORS_PATH.exists():
            raise FileNotFoundError(f"Missing vector file: {VECTORS_PATH}")
        if not METADATA_PATH.exists():
            raise FileNotFoundError(f"Missing metadata file: {METADATA_PATH}")

        # Shared loaded adapter for query and retrieval tests
        cls.adapter = ProjectMaduraiSemanticAdapter(
            vectors_path=VECTORS_PATH,
            metadata_path=METADATA_PATH,
            db_path=DB_PATH,
        )
        cls.adapter.ensure_loaded()

    # -------------------------------------------------------------------------
    # A. Initialization
    # -------------------------------------------------------------------------

    def test_lazy_initialization(self):
        """Verify model and vectors are NOT loaded upon adapter instantiation."""
        fresh_adapter = ProjectMaduraiSemanticAdapter(
            vectors_path=VECTORS_PATH,
            metadata_path=METADATA_PATH,
            db_path=DB_PATH,
        )
        self.assertFalse(fresh_adapter.is_loaded)
        self.assertIsNone(fresh_adapter._vectors)
        self.assertIsNone(fresh_adapter._metadata)
        self.assertIsNone(fresh_adapter._model)
        self.assertIsNone(fresh_adapter._tokenizer)

        # Trigger load
        fresh_adapter.ensure_loaded()
        self.assertTrue(fresh_adapter.is_loaded)
        self.assertIsNotNone(fresh_adapter._vectors)
        self.assertIsNotNone(fresh_adapter._metadata)
        self.assertIsNotNone(fresh_adapter._model)
        self.assertIsNotNone(fresh_adapter._tokenizer)
        self.assertEqual(fresh_adapter.vector_count, 13284)
        self.assertIsNotNone(fresh_adapter.corpus_fingerprint)
        self.assertIsNotNone(fresh_adapter.database_sha256)

    # -------------------------------------------------------------------------
    # B. Artifact Validation & Defensive Failure Handling
    # -------------------------------------------------------------------------

    def test_missing_vector_file_fails_safely(self):
        """Verify missing vector file raises on validate and returns ERROR on lookup."""
        nonexistent = PROJECT_ROOT / "data" / "processed" / "does_not_exist_vecs.npy"
        bad_adapter = ProjectMaduraiSemanticAdapter(
            vectors_path=nonexistent,
            metadata_path=METADATA_PATH,
        )
        with self.assertRaises(FileNotFoundError):
            bad_adapter.validate_artifacts()

        # Lookup must fail safely without raising unhandled exception
        results = bad_adapter.lookup("மரம்")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].metadata.get("status"), "ERROR")
        self.assertIn("error", results[0].metadata)

    def test_missing_metadata_file_fails_safely(self):
        """Verify missing metadata file raises on validate and returns ERROR on lookup."""
        nonexistent = PROJECT_ROOT / "data" / "processed" / "does_not_exist_meta.json"
        bad_adapter = ProjectMaduraiSemanticAdapter(
            vectors_path=VECTORS_PATH,
            metadata_path=nonexistent,
        )
        with self.assertRaises(FileNotFoundError):
            bad_adapter.validate_artifacts()

        results = bad_adapter.lookup("மரம்")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].metadata.get("status"), "ERROR")

    def test_corrupt_metadata_json_fails_safely(self):
        """Verify malformed JSON metadata fails safely."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_meta = Path(tmpdir) / "corrupt_meta.json"
            bad_meta.write_text("{invalid json...", encoding="utf-8")

            bad_adapter = ProjectMaduraiSemanticAdapter(
                vectors_path=VECTORS_PATH,
                metadata_path=bad_meta,
            )
            with self.assertRaises(SemanticArtifactError):
                bad_adapter.validate_artifacts()

            results = bad_adapter.lookup("மரம்")
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].metadata.get("status"), "ERROR")

    def test_invalid_dimension_fails_safely(self):
        """Verify vector dimension mismatch fails safely."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_vec_path = Path(tmpdir) / "bad_dim_vectors.npy"
            bad_vectors = np.ones((5, 128), dtype=np.float32)
            np.save(bad_vec_path, bad_vectors)

            bad_meta_path = Path(tmpdir) / "bad_dim_meta.json"
            meta_payload = {
                "schema_version": "1.0.0",
                "embedding": {
                    "model_id": PINNED_MODEL_ID,
                    "model_revision": PINNED_MODEL_REVISION,
                    "dimension": 128,  # Mismatch with expected 384
                },
                "items": [{"vector_index": i, "chunk_id": f"PM-TEST-{i:04d}"} for i in range(5)],
            }
            bad_meta_path.write_text(json.dumps(meta_payload), encoding="utf-8")

            bad_adapter = ProjectMaduraiSemanticAdapter(
                vectors_path=bad_vec_path,
                metadata_path=bad_meta_path,
            )
            with self.assertRaises(SemanticArtifactError):
                bad_adapter.validate_artifacts()

            results = bad_adapter.lookup("மரம்")
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].metadata.get("status"), "ERROR")

    def test_vector_metadata_count_mismatch_fails_safely(self):
        """Verify count mismatch between vector matrix and metadata fails safely."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_vec_path = Path(tmpdir) / "mismatch_vectors.npy"
            bad_vectors = np.ones((5, PINNED_EMBEDDING_DIM), dtype=np.float32)
            # Normalize
            bad_vectors = bad_vectors / np.linalg.norm(bad_vectors, axis=1, keepdims=True)
            np.save(bad_vec_path, bad_vectors)

            bad_meta_path = Path(tmpdir) / "mismatch_meta.json"
            meta_payload = {
                "schema_version": "1.0.0",
                "embedding": {
                    "model_id": PINNED_MODEL_ID,
                    "model_revision": PINNED_MODEL_REVISION,
                    "dimension": PINNED_EMBEDDING_DIM,
                },
                # 4 items vs 5 vectors
                "items": [{"vector_index": i, "chunk_id": f"PM-TEST-{i:04d}"} for i in range(4)],
            }
            bad_meta_path.write_text(json.dumps(meta_payload), encoding="utf-8")

            bad_adapter = ProjectMaduraiSemanticAdapter(
                vectors_path=bad_vec_path,
                metadata_path=bad_meta_path,
            )
            with self.assertRaises(SemanticArtifactError):
                bad_adapter.validate_artifacts()

            results = bad_adapter.lookup("மரம்")
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].metadata.get("status"), "ERROR")

    def test_duplicate_chunk_id_fails_safely(self):
        """Verify duplicate chunk_id in metadata fails safely."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_vec_path = Path(tmpdir) / "dup_vectors.npy"
            bad_vectors = np.ones((2, PINNED_EMBEDDING_DIM), dtype=np.float32)
            bad_vectors = bad_vectors / np.linalg.norm(bad_vectors, axis=1, keepdims=True)
            np.save(bad_vec_path, bad_vectors)

            bad_meta_path = Path(tmpdir) / "dup_meta.json"
            meta_payload = {
                "schema_version": "1.0.0",
                "embedding": {
                    "model_id": PINNED_MODEL_ID,
                    "model_revision": PINNED_MODEL_REVISION,
                    "dimension": PINNED_EMBEDDING_DIM,
                },
                # Duplicate chunk_id
                "items": [
                    {"vector_index": 0, "chunk_id": "PM-DUP-0001"},
                    {"vector_index": 1, "chunk_id": "PM-DUP-0001"},
                ],
            }
            bad_meta_path.write_text(json.dumps(meta_payload), encoding="utf-8")

            bad_adapter = ProjectMaduraiSemanticAdapter(
                vectors_path=bad_vec_path,
                metadata_path=bad_meta_path,
            )
            with self.assertRaises(SemanticArtifactError):
                bad_adapter.validate_artifacts()

            results = bad_adapter.lookup("மரம்")
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].metadata.get("status"), "ERROR")

    def test_invalid_model_revision_fails_safely(self):
        """Verify metadata with unexpected model revision fails safely."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_vec_path = Path(tmpdir) / "rev_vectors.npy"
            bad_vectors = np.ones((1, PINNED_EMBEDDING_DIM), dtype=np.float32)
            bad_vectors = bad_vectors / np.linalg.norm(bad_vectors, axis=1, keepdims=True)
            np.save(bad_vec_path, bad_vectors)

            bad_meta_path = Path(tmpdir) / "rev_meta.json"
            meta_payload = {
                "schema_version": "1.0.0",
                "embedding": {
                    "model_id": PINNED_MODEL_ID,
                    "model_revision": "unpinned_main_branch_hash",
                    "dimension": PINNED_EMBEDDING_DIM,
                },
                "items": [{"vector_index": 0, "chunk_id": "PM-REV-0001"}],
            }
            bad_meta_path.write_text(json.dumps(meta_payload), encoding="utf-8")

            bad_adapter = ProjectMaduraiSemanticAdapter(
                vectors_path=bad_vec_path,
                metadata_path=bad_meta_path,
            )
            with self.assertRaises(SemanticArtifactError):
                bad_adapter.validate_artifacts()

    def test_invalid_vector_dtype_fails_safely(self):
        """Verify vector matrix with float64 dtype fails safely."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_vec_path = Path(tmpdir) / "float64_vectors.npy"
            bad_vectors = np.ones((1, PINNED_EMBEDDING_DIM), dtype=np.float64)
            np.save(bad_vec_path, bad_vectors)

            bad_meta_path = Path(tmpdir) / "float64_meta.json"
            meta_payload = {
                "schema_version": "1.0.0",
                "embedding": {
                    "model_id": PINNED_MODEL_ID,
                    "model_revision": PINNED_MODEL_REVISION,
                    "dimension": PINNED_EMBEDDING_DIM,
                },
                "items": [{"vector_index": 0, "chunk_id": "PM-F64-0001"}],
            }
            bad_meta_path.write_text(json.dumps(meta_payload), encoding="utf-8")

            bad_adapter = ProjectMaduraiSemanticAdapter(
                vectors_path=bad_vec_path,
                metadata_path=bad_meta_path,
            )
            with self.assertRaises(SemanticArtifactError):
                bad_adapter.validate_artifacts()

    # -------------------------------------------------------------------------
    # C. Query Embedding
    # -------------------------------------------------------------------------

    def test_query_embedding_properties(self):
        """Verify query encoding produces 384D unit float32 vectors with no NaN/Inf."""
        test_queries = ["மரம்", "அறம்", "இனிது"]
        for query in test_queries:
            vec = self.adapter.encode_query(query)
            self.assertEqual(vec.ndim, 1, f"Vector for {query} is not 1D")
            self.assertEqual(vec.shape[0], PINNED_EMBEDDING_DIM, f"Vector shape mismatch for {query}")
            self.assertEqual(vec.dtype, np.float32, f"Vector dtype for {query} is not float32")
            self.assertFalse(np.isnan(vec).any(), f"Vector for {query} contains NaN")
            self.assertFalse(np.isinf(vec).any(), f"Vector for {query} contains Inf")

            norm = float(np.linalg.norm(vec))
            self.assertAlmostEqual(
                norm,
                1.0,
                places=4,
                msg=f"Vector for {query} not unit normalized: norm={norm}",
            )

    # -------------------------------------------------------------------------
    # D. Semantic Candidate Retrieval & Evidence Schema Mapping
    # -------------------------------------------------------------------------

    def test_representative_retrieval_and_evidence_contract(self):
        """Verify retrieval for representative queries produces valid Evidence objects."""
        test_queries = ["மரம்", "அறம்", "இனிது", "யாழ்", "பாரதி"]
        top_k = 5

        for q in test_queries:
            results = self.adapter.lookup(q, top_k=top_k)
            self.assertIsInstance(results, list, f"Lookup result for {q} must be a list")
            self.assertGreater(len(results), 0, f"Lookup result for {q} should not be empty")
            self.assertLessEqual(len(results), top_k, f"Lookup result for {q} exceeds top_k={top_k}")

            chunk_ids = []
            prev_score = float("inf")

            for ev in results:
                self.assertIsInstance(ev, Evidence, f"Item for {q} is not Evidence instance")
                self.assertEqual(ev.surface, q)
                self.assertIsNone(ev.lemma, "Semantic adapter must not fabricate a lemma")
                self.assertEqual(ev.source, "Project Madurai")
                self.assertEqual(ev.evidence_type, "literary_context")
                self.assertIsNotNone(ev.passage, f"Passage missing for chunk {ev.source_id}")
                self.assertGreater(len(ev.passage), 0, f"Passage empty for chunk {ev.source_id}")
                self.assertIsNotNone(ev.work, f"Work missing for chunk {ev.source_id}")
                self.assertIsNotNone(ev.source_id, f"source_id missing for chunk {ev.source_id}")

                meta = ev.metadata
                self.assertEqual(meta.get("status"), "FOUND")
                self.assertEqual(meta.get("retrieval_mode"), "semantic")
                self.assertEqual(meta.get("retrieval_method"), "semantic")

                score = meta.get("similarity_score")
                self.assertIsInstance(score, float)
                self.assertFalse(np.isnan(score))
                self.assertFalse(np.isinf(score))

                # Ordered descending
                self.assertLessEqual(score, prev_score, f"Scores for {q} not ordered descending")
                prev_score = score

                chunk_ids.append(ev.source_id)

            # Unique chunk IDs
            self.assertEqual(len(chunk_ids), len(set(chunk_ids)), f"Duplicate chunk IDs for {q}")

    def test_caller_supplied_lemma_preserved(self):
        """Verify caller-supplied lemma is preserved and not overwritten."""
        results = self.adapter.lookup("மரங்கள்", lemma="மரம்", top_k=3)
        self.assertGreater(len(results), 0)
        for ev in results:
            self.assertEqual(ev.lemma, "மரம்", "Caller-supplied lemma must be preserved")

    # -------------------------------------------------------------------------
    # E. Known Semantic Behavior & Benchmark Validation
    # -------------------------------------------------------------------------

    def test_known_semantic_benchmark_queries(self):
        """Verify semantic retrieval returns relevant candidate passages for benchmark queries."""
        with open(BENCHMARK_PATH, encoding="utf-8") as f:
            bench_data = json.load(f)

        bench_map = {item["query"]: item["gold_chunk_ids"] for item in bench_data}

        # Check conceptual and exact benchmark queries with strong gold annotations
        check_queries = [
            "அறம்",
            "யாழ்",
            "பாரதி",
            "கல்வியின் பெருமையும் கற்கும் முறையும்",
            "மன்னனின் கடமையும் சிறந்த ஆட்சியும்",
            "மழையின் சிறப்பும் இயற்கை வளமும்",
        ]
        for q in check_queries:
            self.assertIn(q, bench_map, f"Benchmark query '{q}' not found in benchmark data")
            gold_ids = set(bench_map[q])
            results = self.adapter.lookup(q, top_k=25)
            retrieved_ids = {ev.source_id for ev in results}

            # At least one gold passage should be retrieved in top 25
            overlap = gold_ids.intersection(retrieved_ids)
            self.assertGreater(
                len(overlap),
                0,
                f"For query '{q}', none of gold chunks {gold_ids} retrieved in top 25: {retrieved_ids}",
            )

        # In addition, verify that broad noun query 'மரம்' retrieves plausible tree-related candidates with high score
        maram_results = self.adapter.lookup("மரம்", top_k=5)
        self.assertGreaterEqual(len(maram_results), 1)
        self.assertGreater(maram_results[0].metadata["similarity_score"], 0.80)
        self.assertTrue(any("மரம்" in ev.passage or "மர" in ev.passage for ev in maram_results if ev.passage))

    # -------------------------------------------------------------------------
    # F. Determinism
    # -------------------------------------------------------------------------

    def test_search_determinism(self):
        """Verify identical queries yield identical ordered results and scores."""
        query = "அறம்"
        run1 = self.adapter.lookup(query, top_k=10)
        run2 = self.adapter.lookup(query, top_k=10)

        self.assertEqual(len(run1), len(run2))
        for ev1, ev2 in zip(run1, run2):
            self.assertEqual(ev1.source_id, ev2.source_id)
            self.assertEqual(ev1.passage, ev2.passage)
            self.assertAlmostEqual(
                ev1.metadata["similarity_score"],
                ev2.metadata["similarity_score"],
                places=6,
            )

    # -------------------------------------------------------------------------
    # G. Top-K Behavior & Nested Subset Guarantee
    # -------------------------------------------------------------------------

    def test_top_k_nested_subsets(self):
        """Verify top_1 ⊆ top_5 ⊆ top_10 ⊆ top_25 with deterministic prefix alignment."""
        query = "மரம்"
        k_values = [1, 5, 10, 25]
        results_by_k = {}

        for k in k_values:
            evs = self.adapter.lookup(query, top_k=k)
            self.assertEqual(len(evs), k, f"Expected {k} results, got {len(evs)}")
            results_by_k[k] = [ev.source_id for ev in evs]

        # Verify strict prefix alignment: results_1 is prefix of results_5, etc.
        self.assertEqual(results_by_k[1], results_by_k[5][:1])
        self.assertEqual(results_by_k[5], results_by_k[10][:5])
        self.assertEqual(results_by_k[10], results_by_k[25][:10])

        # Verify set containment
        set1 = set(results_by_k[1])
        set5 = set(results_by_k[5])
        set10 = set(results_by_k[10])
        set25 = set(results_by_k[25])

        self.assertTrue(set1.issubset(set5))
        self.assertTrue(set5.issubset(set10))
        self.assertTrue(set10.issubset(set25))

    # -------------------------------------------------------------------------
    # H. Empty / Invalid Query Behavior
    # -------------------------------------------------------------------------

    def test_empty_and_whitespace_query(self):
        """Verify empty and whitespace queries return empty lists without crashing."""
        self.assertEqual(self.adapter.lookup(""), [])
        self.assertEqual(self.adapter.lookup("   "), [])
        self.assertEqual(self.adapter.lookup("\t\n"), [])

    def test_zero_or_negative_top_k(self):
        """Verify top_k <= 0 returns empty list safely."""
        self.assertEqual(self.adapter.lookup("மரம்", top_k=0), [])
        self.assertEqual(self.adapter.lookup("மரம்", top_k=-5), [])


if __name__ == "__main__":
    unittest.main()
