"""
SOL AI — Step 3C: Semantic Vector Artifacts & Metadata Integrity Tests.

Verifies:
1. Permanent vector artifacts exist and match required shapes, dtypes, and L2 norms.
2. Metadata JSON matches schema specification, model revision, and dimensionality.
3. Metadata-to-vector 1-to-1 alignment and index contiguity.
4. Correct corpus filtering (suppressed stubs excluded, didactic aphorisms and couplets retained).
5. Exact Project Madurai database immutability.
"""

import hashlib
import json
import sqlite3
import unittest
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "data" / "processed" / "madurai_exact.db"
VECTORS_PATH = PROJECT_ROOT / "data" / "processed" / "madurai_semantic_vectors.npy"
METADATA_PATH = PROJECT_ROOT / "data" / "processed" / "madurai_semantic_meta.json"

EXPECTED_DB_SHA256 = "9eef3a08dd0acf68592036fc230c5607dff09821ea456708101be9eabaefdd41"
EXPECTED_TOTAL_CHUNKS = 14383
EXPECTED_ELIGIBLE_CHUNKS = 13284
EXPECTED_SUPPRESSED_CHUNKS = 1099
PINNED_MODEL_ID = "intfloat/multilingual-e5-small"
PINNED_MODEL_REVISION = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
PINNED_EMBEDDING_DIM = 384


class TestSemanticVectorArtifacts(unittest.TestCase):
    """Test suite for permanent semantic vector matrix and metadata."""

    @classmethod
    def setUpClass(cls):
        if not VECTORS_PATH.exists():
            raise FileNotFoundError(f"Vector matrix not found at {VECTORS_PATH}. Run scripts/build_madurai_semantic_vectors.py first.")
        if not METADATA_PATH.exists():
            raise FileNotFoundError(f"Metadata JSON not found at {METADATA_PATH}. Run scripts/build_madurai_semantic_vectors.py first.")

        cls.vectors = np.load(VECTORS_PATH, mmap_mode="r")
        with open(METADATA_PATH, encoding="utf-8") as f:
            cls.meta = json.load(f)

    def test_metadata_top_level_schema(self):
        """Verify top-level keys in metadata JSON."""
        required_keys = ["schema_version", "build_timestamp", "corpus_fingerprint", "corpus", "embedding", "index", "items"]
        for k in required_keys:
            self.assertIn(k, self.meta, f"Missing key in metadata: {k}")

        self.assertEqual(self.meta["corpus"]["name"], "Project Madurai")
        self.assertEqual(self.meta["corpus"]["database"], "madurai_exact.db")
        self.assertEqual(self.meta["corpus"]["database_sha256"], EXPECTED_DB_SHA256)
        self.assertEqual(self.meta["corpus"]["total_chunks"], EXPECTED_TOTAL_CHUNKS)
        self.assertEqual(self.meta["corpus"]["eligible_chunks"], EXPECTED_ELIGIBLE_CHUNKS)
        self.assertEqual(self.meta["corpus"]["suppressed_chunks"], EXPECTED_SUPPRESSED_CHUNKS)

    def test_embedding_configuration(self):
        """Verify model identity, revision, dimension, and pooling."""
        emb = self.meta["embedding"]
        self.assertEqual(emb["model_id"], PINNED_MODEL_ID)
        self.assertEqual(emb["model_revision"], PINNED_MODEL_REVISION)
        self.assertEqual(emb["dimension"], PINNED_EMBEDDING_DIM)
        self.assertEqual(emb["pooling"], "mean")
        self.assertTrue(emb["normalized"])

    def test_index_configuration(self):
        """Verify index type, metric, and ordering."""
        idx = self.meta["index"]
        self.assertEqual(idx["type"], "numpy_dense")
        self.assertEqual(idx["metric"], "inner_product")
        self.assertEqual(idx["ordering"], "chunk_id_ascending")
        self.assertEqual(idx["vector_count"], EXPECTED_ELIGIBLE_CHUNKS)
        self.assertEqual(idx["dtype"], "float32")

    def test_vector_matrix_properties(self):
        """Verify vector shape, dtype, and lack of NaN / Inf."""
        self.assertEqual(self.vectors.shape, (EXPECTED_ELIGIBLE_CHUNKS, PINNED_EMBEDDING_DIM))
        self.assertEqual(self.vectors.dtype, np.float32)
        self.assertFalse(np.isnan(self.vectors).any(), "Vectors contain NaN")
        self.assertFalse(np.isinf(self.vectors).any(), "Vectors contain Inf")

    def test_vector_normalization(self):
        """Verify all vectors are unit L2-normalized."""
        norms = np.linalg.norm(self.vectors, axis=1)
        self.assertTrue(
            np.allclose(norms, 1.0, atol=1e-4),
            f"Vectors not unit-normalized: min={np.min(norms)}, max={np.max(norms)}",
        )

    def test_metadata_alignment_and_contiguity(self):
        """Verify 1-to-1 alignment between metadata items and vector indices."""
        items = self.meta["items"]
        self.assertEqual(len(items), self.vectors.shape[0])
        self.assertEqual(len(items), EXPECTED_ELIGIBLE_CHUNKS)

        seen_ids = set()
        for i, item in enumerate(items):
            self.assertEqual(item["vector_index"], i, f"Item at index {i} has vector_index {item['vector_index']}")
            cid = item["chunk_id"]
            self.assertNotIn(cid, seen_ids, f"Duplicate chunk_id: {cid}")
            seen_ids.add(cid)

            # Essential provenance keys
            for key in ["chunk_id", "source", "work_id", "work_name"]:
                self.assertIn(key, item, f"Item {cid} missing required key {key}")
                self.assertIsNotNone(item[key], f"Item {cid} key {key} is None")

    def test_ordering_is_strictly_chunk_id_ascending(self):
        """Verify items are deterministically sorted by chunk_id ascending."""
        items = self.meta["items"]
        chunk_ids = [item["chunk_id"] for item in items]
        sorted_chunk_ids = sorted(chunk_ids)
        self.assertEqual(chunk_ids, sorted_chunk_ids, "Metadata items are not sorted strictly by chunk_id ascending")

    def test_suppressed_artifacts_excluded(self):
        """Verify known non-poetic stubs are excluded from semantic vectors."""
        items = self.meta["items"]
        chunk_id_set = {item["chunk_id"] for item in items}

        known_suppressed = [
            "PM-SILAP_MADURAI-0003",   # Webmaster email stub
            "PM-CHINTHAMANI-0003",       # Publication colophon stub
            "PM-THEVARAM_APP-0001",      # Pann metadata stub
            "PM-KURUN-0001",             # Colophon / speaker stub
        ]
        for suppressed_id in known_suppressed:
            self.assertNotIn(
                suppressed_id,
                chunk_id_set,
                f"Suppressed stub {suppressed_id} found in permanent semantic index!",
            )

    def test_didactic_and_classical_passages_retained(self):
        """Verify aphorisms, couplets, and epic verses are fully retained."""
        items = self.meta["items"]
        chunk_id_set = {item["chunk_id"] for item in items}

        known_eligible = [
            "PM-AATHI-0001",       # ஆத்திசூடி invocation
            "PM-AATHI-0002",       # அறம் செய விரும்பு
            "PM-KONRAI-0001",      # கொன்றை வேந்தன் invocation
            "PM-KONRAI-0002",      # அன்னையும் பிதாவும் முன்னறி தெய்வம்
            "PM-TK-0001",          # அகர முதல எழுத்தெல்லாம்
            "PM-TK-0035",          # அறன்வலியுறுத்தல்
            "PM-TK-1330",          # Last Kural
            "PM-SILAP_PUGAR-0178", # சிலப்பதிகாரம் - பாரதி அரங்கத்து
        ]
        for eligible_id in known_eligible:
            self.assertIn(
                eligible_id,
                chunk_id_set,
                f"Eligible passage {eligible_id} missing from permanent semantic index!",
            )

    def test_database_immutability(self):
        """Verify madurai_exact.db has not been modified."""
        self.assertTrue(DB_PATH.exists(), f"Database not found at {DB_PATH}")

        # Verify SHA-256
        sha256 = hashlib.sha256()
        with open(DB_PATH, "rb") as f:
            while chunk := f.read(1024 * 1024):
                sha256.update(chunk)
        current_hash = sha256.hexdigest()
        self.assertEqual(
            current_hash,
            EXPECTED_DB_SHA256,
            f"Database SHA-256 mismatch! DB was mutated: {current_hash} != {EXPECTED_DB_SHA256}",
        )

        # Verify row counts
        conn = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)
        try:
            cur = conn.cursor()
            cur.execute("PRAGMA query_only = ON;")
            cur.execute("SELECT COUNT(*) FROM chunks;")
            chunks_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM chunks_fts;")
            fts_count = cur.fetchone()[0]
        finally:
            conn.close()

        self.assertEqual(chunks_count, EXPECTED_TOTAL_CHUNKS)
        self.assertEqual(fts_count, EXPECTED_TOTAL_CHUNKS)


if __name__ == "__main__":
    unittest.main()
