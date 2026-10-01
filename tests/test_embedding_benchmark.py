"""
Unit tests for Step 3B Embedding Benchmark & Model Wrapper.

Verifies:
1. Gold benchmark dataset schema and DB integrity
2. E5EmbeddingModel initialization and pooling logic
3. Vector L2-normalization and float32 dtype
4. Determinism of embedding generation
5. Output dimensionality
"""

import json
import sqlite3
import unittest
from pathlib import Path

import numpy as np
import torch

from scripts.benchmark_embeddings import E5EmbeddingModel


class TestSemanticBenchmarkData(unittest.TestCase):
    """Verify integrity of tests/data/semantic_benchmark.json."""

    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parents[1]
        cls.json_path = cls.project_root / "tests" / "data" / "semantic_benchmark.json"
        cls.db_path = cls.project_root / "data" / "processed" / "madurai_exact.db"
        with open(cls.json_path, encoding="utf-8") as f:
            cls.data = json.load(f)

    def test_benchmark_data_structure(self):
        """Verify each benchmark entry contains required keys and valid categories."""
        valid_categories = {
            "exact_lexical",
            "morphological_inflection",
            "conceptual_paraphrastic",
            "negative_out_of_domain"
        }
        self.assertGreaterEqual(len(self.data), 20, "Benchmark must contain at least 20 queries")
        for item in self.data:
            self.assertIn("query", item)
            self.assertIn("category", item)
            self.assertIn("gold_chunk_ids", item)
            self.assertIn("relevance_rationale", item)
            self.assertIn(item["category"], valid_categories)
            self.assertTrue(isinstance(item["gold_chunk_ids"], list))
            if item["category"] == "negative_out_of_domain":
                self.assertEqual(len(item["gold_chunk_ids"]), 0)
            else:
                self.assertGreater(len(item["gold_chunk_ids"]), 0)

    def test_gold_chunk_ids_exist_in_db(self):
        """Verify all gold chunk IDs exist in madurai_exact.db."""
        conn = sqlite3.connect(f"file:{self.db_path.as_posix()}?mode=ro", uri=True)
        cur = conn.cursor()
        cur.execute("PRAGMA query_only = ON;")
        try:
            for item in self.data:
                for cid in item["gold_chunk_ids"]:
                    cur.execute("SELECT count(*) FROM chunks WHERE chunk_id = ?", (cid,))
                    count = cur.fetchone()[0]
                    self.assertEqual(count, 1, f"Gold chunk {cid} not found in madurai_exact.db")
        finally:
            conn.close()


class TestE5EmbeddingWrapper(unittest.TestCase):
    """Test isolated benchmark wrapper on e5-small (lightweight test)."""

    @classmethod
    def setUpClass(cls):
        cls.model = E5EmbeddingModel(
            model_id="intfloat/multilingual-e5-small",
            revision="614241f622f53c4eeff9890bdc4f31cfecc418b3",
            num_threads=2
        )
        cls.model.load_model()

    def test_embedding_dimension(self):
        """Verify output dimension is 384 for e5-small."""
        self.assertEqual(self.model.get_embedding_dim(), 384)

    def test_single_encode_dtype_and_norm(self):
        """Verify encode_text returns 1D float32 L2-normalized vector."""
        vec = self.model.encode_text("query: அறம்")
        self.assertEqual(vec.ndim, 1)
        self.assertEqual(vec.shape[0], 384)
        self.assertEqual(vec.dtype, np.float32)
        norm = np.linalg.norm(vec)
        self.assertAlmostEqual(norm, 1.0, places=5)

    def test_batch_encode_shape(self):
        """Verify encode_batch returns 2D matrix matching batch size."""
        texts = [
            "passage: அறம் செய விரும்பு.",
            "passage: ஆறுவது சினம்.",
            "passage: இயல்வது கரவேல்."
        ]
        matrix = self.model.encode_batch(texts)
        self.assertEqual(matrix.shape, (3, 384))
        self.assertEqual(matrix.dtype, np.float32)
        for i in range(3):
            norm = np.linalg.norm(matrix[i])
            self.assertAlmostEqual(norm, 1.0, places=5)

    def test_pooling_with_mask(self):
        """Verify manual pooling matches expected attention-mask weighting."""
        hidden_states = torch.tensor([
            [[1.0, 2.0], [3.0, 4.0], [0.0, 0.0]],
            [[5.0, 6.0], [0.0, 0.0], [0.0, 0.0]]
        ])
        attention_mask = torch.tensor([
            [1, 1, 0],
            [1, 0, 0]
        ])
        pooled = E5EmbeddingModel._average_pool(hidden_states, attention_mask)
        expected = torch.tensor([
            [2.0, 3.0],
            [5.0, 6.0]
        ])
        self.assertTrue(torch.allclose(pooled, expected))

    def test_determinism(self):
        """Verify vector generation is bit-for-bit or numerically identical across calls."""
        text = "query: கல்வியின் பெருமை"
        v1 = self.model.encode_text(text)
        v2 = self.model.encode_text(text)
        self.assertTrue(np.allclose(v1, v2, atol=1e-6))
        self.assertEqual(float(np.max(np.abs(v1 - v2))), 0.0)


if __name__ == "__main__":
    unittest.main()
