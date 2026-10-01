"""
SOL AI — Step 3C: Permanent Semantic Vector Build.

Builds the permanent offline semantic vector representation of the Project Madurai corpus:
- data/processed/madurai_semantic_vectors.npy
- data/processed/madurai_semantic_meta.json

Architectural Tenets:
1. Exact Database Immutability:
   - data/processed/madurai_exact.db is strictly read-only ('file:...mode=ro', PRAGMA query_only = ON).
   - Database checksum, mtime, and row counts are verified before and after build.
2. Canonical Text Source of Truth:
   - Texts are dynamically extracted and prepared via backend.retrieval.semantic_preprocessing.prepare_chunk().
   - Preprocessing logic is NEVER duplicated or altered.
3. Deterministic Vector Alignment:
   - Vector at vectors[i] corresponds exactly to metadata['items'][i].
   - Ordered strictly by chunk_id ASC.
4. Pinned Hugging Face Model:
   - intfloat/multilingual-e5-small @ revision 614241f622f53c4eeff9890bdc4f31cfecc418b3.
   - Mean pooling with attention mask + L2 normalization.
5. In-Depth Validation:
   - Dimensions, normalization, absence of NaN/Inf, unique chunk IDs, exclusion of suppressed stubs.
   - Deterministic sample re-encoding verification.
"""

import argparse
import hashlib
import json
import logging
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.retrieval.semantic_preprocessing import (
    PASSAGE_PREFIX,
    prepare_chunk,
)

# Output encoding and logging
sys.stdout.reconfigure(encoding="utf-8")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("build_madurai_semantic_vectors")

# Pinned Model Configuration
PINNED_MODEL_ID = "intfloat/multilingual-e5-small"
PINNED_MODEL_REVISION = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
PINNED_EMBEDDING_DIM = 384
MAX_SEQUENCE_LENGTH = 512
SCHEMA_VERSION = "1.0.0"


def compute_file_sha256(path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            sha256.update(chunk)
    return sha256.hexdigest()


def get_database_fingerprint(db_path: Path) -> Dict[str, Any]:
    """
    Capture immutable database fingerprint:
    SHA-256, mtime, size, chunks row count, and chunks_fts row count.
    """
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found at: {db_path}")

    sha256_hash = compute_file_sha256(db_path)
    stat = db_path.stat()

    conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True, timeout=10.0)
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA query_only = ON;")
        cur.execute("SELECT COUNT(*) FROM chunks;")
        chunks_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM chunks_fts;")
        chunks_fts_count = cur.fetchone()[0]
    finally:
        conn.close()

    return {
        "path": str(db_path),
        "sha256": sha256_hash,
        "mtime": stat.st_mtime,
        "size_bytes": stat.st_size,
        "chunks_count": chunks_count,
        "chunks_fts_count": chunks_fts_count,
    }


class SemanticVectorBuilder:
    """
    Builder engine for Project Madurai permanent semantic vectors and metadata.
    """

    def __init__(
        self,
        db_path: Path,
        output_dir: Path,
        batch_size: int = 32,
        num_threads: int = 6,
    ):
        self.db_path = db_path
        self.output_dir = output_dir
        self.batch_size = batch_size
        self.num_threads = num_threads
        self.vectors_path = self.output_dir / "madurai_semantic_vectors.npy"
        self.metadata_path = self.output_dir / "madurai_semantic_meta.json"

        self.tokenizer = None
        self.model = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def load_model(self) -> float:
        """Load pinned E5 tokenizer and model."""
        logger.info("Configuring PyTorch num_threads=%d...", self.num_threads)
        torch.set_num_threads(self.num_threads)

        logger.info(
            "Loading pinned model: %s (revision: %s) on %s...",
            PINNED_MODEL_ID,
            PINNED_MODEL_REVISION,
            self.device,
        )
        t0 = time.perf_counter()
        self.tokenizer = AutoTokenizer.from_pretrained(
            PINNED_MODEL_ID,
            revision=PINNED_MODEL_REVISION,
        )
        self.model = AutoModel.from_pretrained(
            PINNED_MODEL_ID,
            revision=PINNED_MODEL_REVISION,
        )
        self.model.to(self.device)
        self.model.eval()
        load_time = time.perf_counter() - t0
        logger.info("Model loaded successfully in %.2f s.", load_time)
        return load_time

    @staticmethod
    def _average_pool(last_hidden_states: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        """Mean pooling over token embeddings respecting attention mask."""
        last_hidden = last_hidden_states.masked_fill(~attention_mask[..., None].bool(), 0.0)
        return last_hidden.sum(dim=1) / attention_mask.sum(dim=1)[..., None]

    def encode_batch(self, texts: List[str]) -> np.ndarray:
        """
        Encode a batch of texts into L2-normalized float32 embeddings.
        Returns NumPy array of shape (len(texts), PINNED_EMBEDDING_DIM).
        """
        if not texts:
            return np.empty((0, PINNED_EMBEDDING_DIM), dtype=np.float32)

        inputs = self.tokenizer(
            texts,
            max_length=MAX_SEQUENCE_LENGTH,
            padding=True,
            truncation=True,
            return_tensors="pt",
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.inference_mode():
            outputs = self.model(**inputs)
            embeddings = self._average_pool(outputs.last_hidden_state, inputs["attention_mask"])
            embeddings = F.normalize(embeddings, p=2, dim=1)

        return embeddings.cpu().float().numpy()

    def fetch_and_prepare_corpus(self) -> Tuple[List[Dict[str, Any]], List[str], Dict[str, Any]]:
        """
        Open database in read-only mode, extract chunks in deterministic chunk_id order,
        evaluate eligibility via prepare_chunk(), and build metadata item dictionaries.
        """
        logger.info("Opening database read-only: %s", self.db_path)
        uri = f"file:{self.db_path.as_posix()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=10.0)
        conn.row_factory = sqlite3.Row

        try:
            cur = conn.cursor()
            cur.execute("PRAGMA query_only = ON;")
            cur.execute("SELECT * FROM chunks ORDER BY chunk_id ASC;")
            rows = cur.fetchall()
        finally:
            conn.close()

        total_chunks = len(rows)
        eligible_items: List[Dict[str, Any]] = []
        eligible_passages: List[str] = []
        suppressed_reasons: Dict[str, int] = {}

        logger.info("Processing %d total canonical chunks via prepare_chunk()...", total_chunks)

        for row in rows:
            prep = prepare_chunk(row)
            if prep.eligible:
                vector_idx = len(eligible_items)
                item_meta = {
                    "vector_index": vector_idx,
                    "chunk_id": str(row["chunk_id"]),
                    "source": str(row["source"] or "Project Madurai"),
                    "work_id": str(row["release_no"] or row["work"]),
                    "work_name": str(row["work"]),
                    "author": row["author"],
                    "period": row["period"],
                    "genre": row["genre"],
                    "section": row["canto"],
                    "sub_section": row["chapter"],
                    "stanza_number": row["stanza_number"],
                    "source_url": row["source_url"],
                }
                eligible_items.append(item_meta)
                eligible_passages.append(prep.embedding_text)
            else:
                reason = prep.suppression_reason or "unknown"
                suppressed_reasons[reason] = suppressed_reasons.get(reason, 0) + 1

        eligible_chunks = len(eligible_items)
        suppressed_chunks = sum(suppressed_reasons.values())

        if eligible_chunks + suppressed_chunks != total_chunks:
            raise ValueError(
                f"Corpus partition mismatch: eligible ({eligible_chunks}) + "
                f"suppressed ({suppressed_chunks}) != total ({total_chunks})"
            )

        logger.info(
            "Corpus preparation summary: total=%d, eligible=%d, suppressed=%d",
            total_chunks,
            eligible_chunks,
            suppressed_chunks,
        )
        logger.info("Suppression breakdown: %s", suppressed_reasons)

        stats = {
            "total_chunks": total_chunks,
            "eligible_chunks": eligible_chunks,
            "suppressed_chunks": suppressed_chunks,
            "suppression_reasons": suppressed_reasons,
        }
        return eligible_items, eligible_passages, stats

    def build_vectors(self, eligible_passages: List[str]) -> Tuple[np.ndarray, float]:
        """
        Encode all eligible passages in controlled batches.
        """
        n_passages = len(eligible_passages)
        logger.info(
            "Encoding %d passages with batch_size=%d, max_sequence_length=%d...",
            n_passages,
            self.batch_size,
            MAX_SEQUENCE_LENGTH,
        )

        batches: List[np.ndarray] = []
        t0 = time.perf_counter()

        for start_idx in range(0, n_passages, self.batch_size):
            end_idx = min(start_idx + self.batch_size, n_passages)
            batch_texts = eligible_passages[start_idx:end_idx]

            try:
                batch_vecs = self.encode_batch(batch_texts)
            except RuntimeError as e:
                if "out of memory" in str(e).lower() and self.batch_size > 8:
                    logger.warning("OOM detected with batch_size=%d. Falling back to smaller batch...", self.batch_size)
                    self.batch_size = max(8, self.batch_size // 2)
                    logger.info("Resuming with batch_size=%d...", self.batch_size)
                    batch_vecs = self.encode_batch(batch_texts)
                else:
                    raise

            batches.append(batch_vecs)

            if (start_idx // self.batch_size) % 50 == 0 or end_idx >= n_passages:
                elapsed = time.perf_counter() - t0
                rate = end_idx / elapsed if elapsed > 0 else 0
                pct = (end_idx / n_passages) * 100
                logger.info(
                    "   Progress: %5d / %5d (%.1f%%) — %.1f texts/sec — elapsed: %.1fs",
                    end_idx,
                    n_passages,
                    pct,
                    rate,
                    elapsed,
                )

        vectors = np.vstack(batches)
        build_duration = time.perf_counter() - t0
        logger.info("Vector matrix built: shape=%s, dtype=%s in %.2fs", vectors.shape, vectors.dtype, build_duration)
        return vectors, build_duration

    def validate_vectors(self, vectors: np.ndarray, eligible_count: int) -> Dict[str, Any]:
        """
        Validate numerical properties, dimensions, and L2 normalization of vectors.
        """
        logger.info("Validating vector matrix properties...")
        if vectors.shape != (eligible_count, PINNED_EMBEDDING_DIM):
            raise ValueError(f"Unexpected vector shape: {vectors.shape}, expected ({eligible_count}, {PINNED_EMBEDDING_DIM})")

        if vectors.dtype != np.float32:
            raise TypeError(f"Unexpected vector dtype: {vectors.dtype}, expected float32")

        if np.isnan(vectors).any():
            raise ValueError("Vector matrix contains NaN values!")

        if np.isinf(vectors).any():
            raise ValueError("Vector matrix contains Inf values!")

        # Norm verification
        norms = np.linalg.norm(vectors, axis=1)
        min_norm = float(np.min(norms))
        max_norm = float(np.max(norms))
        mean_norm = float(np.mean(norms))

        logger.info("Vector norms: min=%.6f, max=%.6f, mean=%.6f", min_norm, max_norm, mean_norm)
        if not np.allclose(norms, 1.0, atol=1e-4):
            raise ValueError(f"Vector normalization failed: min={min_norm}, max={max_norm}")

        return {
            "shape": list(vectors.shape),
            "dtype": str(vectors.dtype),
            "min_norm": min_norm,
            "max_norm": max_norm,
            "mean_norm": mean_norm,
        }

    def validate_metadata_alignment(
        self,
        metadata_items: List[Dict[str, Any]],
        vectors: np.ndarray,
    ):
        """
        Verify 1-to-1 alignment between metadata items and vector rows.
        """
        logger.info("Validating metadata / vector alignment...")
        if len(metadata_items) != vectors.shape[0]:
            raise ValueError(f"Count mismatch: {len(metadata_items)} metadata items vs {vectors.shape[0]} vectors")

        seen_chunk_ids = set()
        for idx, item in enumerate(metadata_items):
            if item["vector_index"] != idx:
                raise ValueError(f"Vector index mismatch at {idx}: metadata has {item['vector_index']}")
            cid = item["chunk_id"]
            if cid in seen_chunk_ids:
                raise ValueError(f"Duplicate chunk_id found in metadata: {cid}")
            seen_chunk_ids.add(cid)

        # Verification of known suppressed chunks
        suppressed_check_ids = ["PM-SILAP_MADURAI-0003", "PM-CHINTHAMANI-0003"]
        for bad_id in suppressed_check_ids:
            if bad_id in seen_chunk_ids:
                raise ValueError(f"Suppressed artifact {bad_id} illegally present in metadata!")

        # Verification of known eligible examples
        eligible_check_ids = [
            "PM-AATHI-0001",
            "PM-AATHI-0002",
            "PM-KONRAI-0001",
            "PM-TK-0001",
            "PM-TK-0035",
            "PM-SILAP_PUGAR-0178",
        ]
        for good_id in eligible_check_ids:
            if good_id not in seen_chunk_ids:
                raise ValueError(f"Eligible chunk {good_id} missing from metadata!")

        logger.info("Metadata / vector alignment verified successfully.")

    def verify_sample_determinism(
        self,
        vectors: np.ndarray,
        metadata_items: List[Dict[str, Any]],
        eligible_passages: List[str],
    ) -> Dict[str, Any]:
        """
        Select a deterministic sample of vectors, re-encode their passages,
        and verify numerical consistency against the built vectors matrix.
        """
        logger.info("Running deterministic sample re-encoding verification...")
        sample_indices = [
            0,
            len(metadata_items) // 4,
            len(metadata_items) // 2,
            (3 * len(metadata_items)) // 4,
            len(metadata_items) - 1,
        ]

        # Add fixed known benchmark chunk indices
        id_to_idx = {item["chunk_id"]: idx for idx, item in enumerate(metadata_items)}
        fixed_benchmark_cids = [
            "PM-TK-0001",
            "PM-TK-0035",
            "PM-TK-0066",
            "PM-TK-0216",
            "PM-TK-0279",
            "PM-AATHI-0002",
            "PM-SILAP_PUGAR-0178",
        ]
        for cid in fixed_benchmark_cids:
            if cid in id_to_idx:
                sample_indices.append(id_to_idx[cid])

        # Deduplicate and sort
        sample_indices = sorted(set(sample_indices))

        max_sample_diff = 0.0
        sample_results = []

        for idx in sample_indices:
            cid = metadata_items[idx]["chunk_id"]
            passage_text = eligible_passages[idx]
            original_vec = vectors[idx]

            # Re-encode isolated text
            re_encoded_vec = self.encode_batch([passage_text])[0]

            diff = float(np.max(np.abs(original_vec - re_encoded_vec)))
            cos_sim = float(np.dot(original_vec, re_encoded_vec))

            if diff > max_sample_diff:
                max_sample_diff = diff

            if diff > 1e-5:
                raise ValueError(f"Determinism verification failed at index {idx} ({cid}): max diff {diff} > 1e-5")

            sample_results.append({
                "index": idx,
                "chunk_id": cid,
                "max_abs_diff": diff,
                "cosine_similarity": cos_sim,
            })

        logger.info(
            "Determinism verified across %d sample passages (max absolute element difference: %.2e).",
            len(sample_indices),
            max_sample_diff,
        )
        return {
            "samples_checked": len(sample_indices),
            "max_abs_diff": max_sample_diff,
            "sample_details": sample_results,
        }

    def execute_build(self) -> Dict[str, Any]:
        """
        Execute full permanent vector build pipeline.
        """
        logger.info("================================================================")
        logger.info("SOL AI — STEP 3C: PERMANENT SEMANTIC VECTOR BUILD")
        logger.info("================================================================")

        # 1. Pre-build database immutability capture
        logger.info("Step 1: Capturing pre-build database fingerprint...")
        db_before = get_database_fingerprint(self.db_path)
        logger.info("Pre-build DB SHA-256: %s", db_before["sha256"])
        logger.info("Pre-build DB row count: %d chunks, %d FTS rows", db_before["chunks_count"], db_before["chunks_fts_count"])

        # 2. Model loading
        logger.info("Step 2: Loading pinned E5 model...")
        cold_load_time = self.load_model()

        # 3. Dynamic corpus extraction and preparation
        logger.info("Step 3: Extracting and preparing corpus chunks...")
        items, passages, corpus_stats = self.fetch_and_prepare_corpus()

        # 4. Batch vector encoding
        logger.info("Step 4: Building permanent vector matrix...")
        vectors, build_duration = self.build_vectors(passages)

        # 5. Numerical and structural validation
        logger.info("Step 5: Validating vector matrix and metadata alignment...")
        vector_stats = self.validate_vectors(vectors, len(items))
        self.validate_metadata_alignment(items, vectors)

        # 6. Deterministic sample verification
        logger.info("Step 6: Verifying deterministic rebuild consistency...")
        sample_det = self.verify_sample_determinism(vectors, items, passages)

        # 7. Construct permanent metadata object
        logger.info("Step 7: Assembling metadata schema...")
        build_timestamp = datetime.now(timezone.utc).isoformat()
        corpus_fingerprint = hashlib.sha256(
            f"{db_before['sha256']}_{PINNED_MODEL_ID}_{PINNED_MODEL_REVISION}_{len(items)}_{PINNED_EMBEDDING_DIM}".encode("utf-8")
        ).hexdigest()

        metadata_payload = {
            "schema_version": SCHEMA_VERSION,
            "build_timestamp": build_timestamp,
            "corpus_fingerprint": corpus_fingerprint,
            "corpus": {
                "name": "Project Madurai",
                "database": self.db_path.name,
                "database_sha256": db_before["sha256"],
                "total_chunks": corpus_stats["total_chunks"],
                "eligible_chunks": corpus_stats["eligible_chunks"],
                "suppressed_chunks": corpus_stats["suppressed_chunks"],
                "suppression_reasons": corpus_stats["suppression_reasons"],
            },
            "embedding": {
                "model_id": PINNED_MODEL_ID,
                "model_revision": PINNED_MODEL_REVISION,
                "dimension": PINNED_EMBEDDING_DIM,
                "max_sequence_length": MAX_SEQUENCE_LENGTH,
                "pooling": "mean",
                "normalized": True,
            },
            "index": {
                "type": "numpy_dense",
                "metric": "inner_product",
                "ordering": "chunk_id_ascending",
                "vector_count": len(items),
                "dtype": "float32",
            },
            "items": items,
        }

        # 8. Save output artifacts
        logger.info("Step 8: Writing permanent artifacts to disk...")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Saving vector matrix to %s...", self.vectors_path)
        np.save(self.vectors_path, vectors)

        logger.info("Saving metadata JSON to %s...", self.metadata_path)
        with open(self.metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata_payload, f, ensure_ascii=False, indent=2)

        # Compute output artifacts hashes and sizes
        vectors_size = self.vectors_path.stat().st_size
        vectors_sha256 = compute_file_sha256(self.vectors_path)
        metadata_size = self.metadata_path.stat().st_size
        metadata_sha256 = compute_file_sha256(self.metadata_path)

        logger.info("Vector file: %s (%.2f MB, SHA256: %s)", self.vectors_path, vectors_size / (1024 * 1024), vectors_sha256)
        logger.info("Metadata file: %s (%.2f MB, SHA256: %s)", self.metadata_path, metadata_size / (1024 * 1024), metadata_sha256)

        # 9. Post-build database immutability verification
        logger.info("Step 9: Verifying database immutability...")
        db_after = get_database_fingerprint(self.db_path)
        logger.info("Post-build DB SHA-256: %s", db_after["sha256"])

        db_unchanged = (
            db_before["sha256"] == db_after["sha256"]
            and db_before["mtime"] == db_after["mtime"]
            and db_before["size_bytes"] == db_after["size_bytes"]
            and db_before["chunks_count"] == db_after["chunks_count"]
            and db_before["chunks_fts_count"] == db_after["chunks_fts_count"]
        )

        if not db_unchanged:
            raise RuntimeError(
                f"DATABASE MUTATION DETECTED! Before: {db_before} vs After: {db_after}"
            )
        logger.info("Database immutability strictly confirmed: 100% bit-for-bit unchanged.")

        # Performance calculations
        enc_throughput = len(items) / build_duration if build_duration > 0 else 0
        expected_matrix_bytes = len(items) * PINNED_EMBEDDING_DIM * 4

        summary = {
            "status": "SUCCESS",
            "db_fingerprint": db_after,
            "cold_load_time_sec": cold_load_time,
            "build_duration_sec": build_duration,
            "encoding_throughput_texts_per_sec": enc_throughput,
            "corpus_stats": corpus_stats,
            "vector_stats": vector_stats,
            "determinism": sample_det,
            "expected_matrix_bytes": expected_matrix_bytes,
            "artifacts": {
                "vectors": {
                    "path": str(self.vectors_path),
                    "size_bytes": vectors_size,
                    "sha256": vectors_sha256,
                    "shape": list(vectors.shape),
                    "dtype": str(vectors.dtype),
                },
                "metadata": {
                    "path": str(self.metadata_path),
                    "size_bytes": metadata_size,
                    "sha256": metadata_sha256,
                    "item_count": len(items),
                },
            },
        }

        logger.info("================================================================")
        logger.info("STEP 3C PERMANENT SEMANTIC VECTOR BUILD COMPLETED SUCCESSFULLY")
        logger.info("================================================================")
        return summary


def main():
    parser = argparse.ArgumentParser(description="Build Project Madurai permanent semantic vectors.")
    parser.add_argument(
        "--db-path",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "madurai_exact.db",
        help="Path to madurai_exact.db",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed",
        help="Directory to save semantic vector and metadata artifacts",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Batch size for vector encoding (default: 32)",
    )
    parser.add_argument(
        "--num-threads",
        type=int,
        default=6,
        help="PyTorch intraop CPU thread count (default: 6)",
    )

    args = parser.parse_args()

    builder = SemanticVectorBuilder(
        db_path=args.db_path,
        output_dir=args.output_dir,
        batch_size=args.batch_size,
        num_threads=args.num_threads,
    )

    summary = builder.execute_build()
    print("\n--- BUILD SUMMARY JSON ---")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
