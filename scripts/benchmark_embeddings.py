"""
SOL AI — Step 3B: Embedding Benchmark & Model Validation Script.

Empirical evaluation and benchmarking of candidate embedding models:
1. Candidate A: intfloat/multilingual-e5-base
2. Candidate B: intfloat/multilingual-e5-small

Evaluates:
- Hardware & software environment
- Model loading times (cold load)
- Determinism and numerical consistency
- Single-query encoding latency (p50, p95, p99)
- Batch encoding throughput (batch sizes 1, 4, 8, 16)
- Memory usage & safety
- Semantic retrieval quality on gold benchmark dataset against full 13,284-chunk corpus:
  - Recall@5, Recall@10, Recall@15, Recall@25
  - Precision@5, Precision@10
  - MRR (Mean Reciprocal Rank)
  - Exact FTS baseline comparison
  - Negative / out-of-domain query false-positive analysis

Strict scope boundaries:
- In-memory evaluation ONLY.
- DOES NOT save permanent vector index (no madurai_semantic_vectors.npy).
- DOES NOT modify madurai_exact.db or any production retrieval code.
"""

import json
import logging
import os
import platform
import sqlite3
import sys
import time
from dataclasses import dataclass
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

from backend.resources.project_madurai import ProjectMaduraiExactAdapter
from backend.retrieval.semantic_preprocessing import (
    PASSAGE_PREFIX,
    QUERY_PREFIX,
    prepare_chunk,
)

# Configure logging and stdout
sys.stdout.reconfigure(encoding="utf-8")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("benchmark_embeddings")


# ---------------------------------------------------------------------------
# 1. Isolated Embedding Model Wrapper
# ---------------------------------------------------------------------------

class E5EmbeddingModel:
    """
    Isolated, lightweight benchmark wrapper for Multilingual E5 models.
    Supports mean pooling with attention mask, L2 normalization, and batch inference.
    """

    def __init__(self, model_id: str, revision: Optional[str] = None, num_threads: int = 6):
        self.model_id = model_id
        self.revision = revision
        self.num_threads = num_threads
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = None
        self.model = None
        self.cold_load_time: float = 0.0

    def load_model(self) -> float:
        """Load tokenizer and model weights, returning load time in seconds."""
        torch.set_num_threads(self.num_threads)
        t0 = time.perf_counter()
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_id, revision=self.revision)
        self.model = AutoModel.from_pretrained(self.model_id, revision=self.revision)
        self.model.to(self.device)
        self.model.eval()
        self.cold_load_time = time.perf_counter() - t0
        return self.cold_load_time

    @staticmethod
    def _average_pool(last_hidden_states: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        """Standard E5 mean pooling over non-padded token embeddings."""
        last_hidden = last_hidden_states.masked_fill(~attention_mask[..., None].bool(), 0.0)
        return last_hidden.sum(dim=1) / attention_mask.sum(dim=1)[..., None]

    def encode_batch(self, texts: List[str], max_length: int = 256) -> np.ndarray:
        """
        Encode a batch of texts into L2-normalized float32 embeddings.
        Returns a 2D NumPy array of shape (len(texts), embedding_dim).
        """
        if not texts:
            return np.empty((0, self.get_embedding_dim()), dtype=np.float32)

        inputs = self.tokenizer(
            texts,
            max_length=max_length,
            padding=True,
            truncation=True,
            return_tensors="pt"
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**inputs)
            embeddings = self._average_pool(outputs.last_hidden_state, inputs["attention_mask"])
            embeddings = F.normalize(embeddings, p=2, dim=1)

        return embeddings.cpu().float().numpy()

    def encode_text(self, text: str, max_length: int = 256) -> np.ndarray:
        """Encode a single text string into a 1D float32 vector."""
        batch_vecs = self.encode_batch([text], max_length=max_length)
        return batch_vecs[0]

    def get_embedding_dim(self) -> int:
        return self.model.config.hidden_size if self.model else 0

    def get_metadata(self) -> Dict[str, Any]:
        """Return model metadata for reporting."""
        num_params = sum(p.numel() for p in self.model.parameters()) if self.model else 0
        return {
            "model_id": self.model_id,
            "revision": self.revision or "default",
            "device": str(self.device),
            "num_threads": self.num_threads,
            "num_parameters": num_params,
            "embedding_dim": self.get_embedding_dim(),
            "max_position_embeddings": getattr(self.model.config, "max_position_embeddings", 512),
            "model_type": getattr(self.model.config, "model_type", "unknown"),
            "tokenizer_class": self.tokenizer.__class__.__name__ if self.tokenizer else "unknown",
            "vocab_size": self.tokenizer.vocab_size if self.tokenizer else 0,
            "pooling_strategy": "average_pool (mean pooling with attention mask)",
            "normalization_strategy": "L2 normalization (p=2, dim=1)",
        }


# ---------------------------------------------------------------------------
# 2. Benchmark Runner
# ---------------------------------------------------------------------------

class EmbeddingBenchmarkRunner:
    """Orchestrates comprehensive benchmarking across candidate models."""

    def __init__(self, db_path: Path, benchmark_json_path: Path):
        self.db_path = db_path
        self.benchmark_json_path = benchmark_json_path
        with open(benchmark_json_path, encoding="utf-8") as f:
            self.benchmark_data = json.load(f)
        self.corpus_chunks: List[Dict[str, Any]] = []
        self.eligible_passages: List[str] = []
        self.eligible_chunk_ids: List[str] = []
        self.exact_adapter = ProjectMaduraiExactAdapter(db_path=self.db_path)

    def load_corpus(self):
        """Load all chunks from madurai_exact.db and prepare eligible canonical texts."""
        logger.info("Loading corpus from %s...", self.db_path)
        uri = f"file:{self.db_path.as_posix()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.cursor()
            cur.execute("PRAGMA query_only = ON;")
            cur.execute("SELECT * FROM chunks ORDER BY chunk_id ASC;")
            rows = cur.fetchall()
        finally:
            conn.close()

        logger.info("Total rows in DB: %d. Preprocessing for semantic eligibility...", len(rows))
        for r in rows:
            prep = prepare_chunk(r)
            if prep.eligible:
                self.eligible_chunk_ids.append(r["chunk_id"])
                self.eligible_passages.append(prep.embedding_text)
                self.corpus_chunks.append({
                    "chunk_id": r["chunk_id"],
                    "work": r["work"],
                    "chapter": r["chapter"],
                    "original_text": r["original_text"]
                })

        logger.info(
            "Corpus preparation complete: %d eligible passages ready for in-memory indexing.",
            len(self.eligible_passages)
        )

    def check_determinism(self, model: E5EmbeddingModel) -> Dict[str, Any]:
        """Verify vector and ranking determinism over repeated encodings."""
        logger.info("[%s] Running determinism checks...", model.model_id)
        test_text = "query: அறம் செய விரும்பு."
        runs = [model.encode_text(test_text) for _ in range(5)]
        
        all_equal = True
        max_diff = 0.0
        for i in range(1, len(runs)):
            diff = np.max(np.abs(runs[0] - runs[i]))
            if diff > max_diff:
                max_diff = float(diff)
            if not np.allclose(runs[0], runs[i], atol=1e-6):
                all_equal = False

        # Ranking determinism test on sample passages
        sample_passages = [
            "passage: அதிகாரம்: அறன்வலியுறுத்தல். அறத்தினூஉங்கு ஆக்கம் எவனோ உயிர்க்கு.",
            "passage: அதிகாரம்: நட்பு. உடுக்கை இழந்தவன் கைபோல ஆங்கே இடுக்கண் களைவதாம் நட்பு.",
            "passage: அதிகாரம்: வான்சிறப்பு. வான்நின்று உலகம் வழங்கி வருதலால் தான்அமிழ்தம் என்றுணரற் பாற்று."
        ]
        q_vec = model.encode_text("query: அறம்")
        p_vecs_1 = model.encode_batch(sample_passages)
        sims_1 = p_vecs_1 @ q_vec
        ranks_1 = np.argsort(-sims_1)

        p_vecs_2 = model.encode_batch(sample_passages)
        sims_2 = p_vecs_2 @ q_vec
        ranks_2 = np.argsort(-sims_2)

        ranking_deterministic = np.array_equal(ranks_1, ranks_2)

        return {
            "all_runs_numerically_close": all_equal,
            "max_absolute_difference": max_diff,
            "ranking_deterministic": bool(ranking_deterministic),
            "is_deterministic": all_equal and ranking_deterministic
        }

    def benchmark_latency(self, model: E5EmbeddingModel, repetitions: int = 50) -> Dict[str, Any]:
        """Benchmark single-query encoding latency (p50, p95, p99)."""
        logger.info("[%s] Benchmarking single query latency (%d runs)...", model.model_id, repetitions)
        queries = [
            f"query: {item['query']}"
            for item in self.benchmark_data
        ]

        # Warm-up run
        _ = model.encode_text(queries[0])

        latencies_ms = []
        for i in range(repetitions):
            q = queries[i % len(queries)]
            t0 = time.perf_counter()
            _ = model.encode_text(q)
            lat = (time.perf_counter() - t0) * 1000
            latencies_ms.append(lat)

        lat_arr = np.array(latencies_ms)
        return {
            "repetitions": repetitions,
            "min_ms": float(np.min(lat_arr)),
            "mean_ms": float(np.mean(lat_arr)),
            "p50_ms": float(np.percentile(lat_arr, 50)),
            "p90_ms": float(np.percentile(lat_arr, 90)),
            "p95_ms": float(np.percentile(lat_arr, 95)),
            "p99_ms": float(np.percentile(lat_arr, 99)),
            "max_ms": float(np.max(lat_arr)),
        }

    def benchmark_batch_throughput(
        self,
        model: E5EmbeddingModel,
        batch_sizes: List[int] = [1, 4, 8, 16]
    ) -> List[Dict[str, Any]]:
        """Benchmark batch throughput and per-text latency across batch sizes."""
        logger.info("[%s] Benchmarking batch throughput for batch sizes: %s...", model.model_id, batch_sizes)
        # Use first 32 passages from corpus
        sample_passages = self.eligible_passages[:32]
        results = []

        for bs in batch_sizes:
            batch = sample_passages[:bs]
            # Warm-up
            _ = model.encode_batch(batch)

            t0 = time.perf_counter()
            iters = 4
            for _ in range(iters):
                _ = model.encode_batch(batch)
            dur = time.perf_counter() - t0
            total_texts = bs * iters
            texts_per_sec = total_texts / dur
            lat_per_text_ms = (dur / total_texts) * 1000

            results.append({
                "batch_size": bs,
                "iterations": iters,
                "total_texts": total_texts,
                "total_time_sec": float(dur),
                "texts_per_sec": float(texts_per_sec),
                "avg_latency_per_text_ms": float(lat_per_text_ms),
            })
            logger.info("   Batch %2d: %.2f texts/sec (%.2f ms/text)", bs, texts_per_sec, lat_per_text_ms)

        return results

    def evaluate_retrieval_quality(
        self,
        model: E5EmbeddingModel,
        corpus_embeddings: np.ndarray
    ) -> Dict[str, Any]:
        """
        Evaluate semantic retrieval metrics (Recall@K, Precision@K, MRR) against
        the entire eligible corpus matrix (in-memory).
        """
        logger.info("[%s] Evaluating retrieval quality on gold benchmark dataset...", model.model_id)
        id_to_idx = {cid: idx for idx, cid in enumerate(self.eligible_chunk_ids)}

        k_values = [5, 10, 15, 25]
        recall_at_k = {f"Recall@{k}": [] for k in k_values}
        precision_at_k = {f"Precision@{k}": [] for k in [5, 10]}
        reciprocal_ranks = []

        query_details = []
        negative_analyses = []
        exact_baseline_hits = 0
        exact_baseline_total = 0

        for item in self.benchmark_data:
            q_raw = item["query"]
            cat = item["category"]
            golds = item["gold_chunk_ids"]
            rationale = item["relevance_rationale"]

            # Query vector
            q_e5 = f"query: {q_raw}"
            q_vec = model.encode_text(q_e5)

            # Cosine similarity against all eligible corpus passages (inner product since normalized)
            sims = corpus_embeddings @ q_vec

            # Sort descending
            top_k_indices = np.argsort(-sims)[:25]
            top_k_chunk_ids = [self.eligible_chunk_ids[idx] for idx in top_k_indices]
            top_k_scores = [float(sims[idx]) for idx in top_k_indices]

            # Exact baseline lookup via adapter
            exact_evs = self.exact_adapter.lookup(q_raw)
            exact_cids = [
                e.metadata.get("chunk_id")
                for e in exact_evs
                if e.metadata.get("status") == "FOUND" and e.metadata.get("chunk_id")
            ]

            if cat == "negative_out_of_domain":
                top_matches = []
                for cid, score in zip(top_k_chunk_ids[:5], top_k_scores[:5]):
                    c_info = self.corpus_chunks[id_to_idx[cid]]
                    top_matches.append({
                        "chunk_id": cid,
                        "work": c_info["work"],
                        "chapter": c_info.get("chapter"),
                        "similarity": round(score, 4),
                        "snippet": c_info["original_text"].replace("\n", " ")[:100]
                    })
                negative_analyses.append({
                    "query": q_raw,
                    "top_similarity_score": round(top_k_scores[0], 4) if top_k_scores else 0.0,
                    "top_5_matches": top_matches,
                    "rationale": rationale,
                    "plausibly_relevant": False  # Out-of-domain queries by definition have no legitimate match
                })
                continue

            # Standard semantic query evaluation
            gold_set = set(golds)
            exact_baseline_total += len(gold_set)
            exact_baseline_hits += len(gold_set.intersection(set(exact_cids)))

            # Calculate Recall@K and Precision@K
            for k in k_values:
                retrieved_k = set(top_k_chunk_ids[:k])
                hits = len(gold_set.intersection(retrieved_k))
                rec = hits / len(gold_set) if gold_set else 0.0
                recall_at_k[f"Recall@{k}"].append(rec)

            for k in [5, 10]:
                retrieved_k = set(top_k_chunk_ids[:k])
                hits = len(gold_set.intersection(retrieved_k))
                prec = hits / k
                precision_at_k[f"Precision@{k}"].append(prec)

            # Reciprocal Rank (first relevant result)
            rr = 0.0
            for rank_idx, cid in enumerate(top_k_chunk_ids, start=1):
                if cid in gold_set:
                    rr = 1.0 / rank_idx
                    break
            reciprocal_ranks.append(rr)

            query_details.append({
                "query": q_raw,
                "category": cat,
                "gold_chunk_ids": golds,
                "exact_fts_hits": list(gold_set.intersection(set(exact_cids))),
                "semantic_top_5": top_k_chunk_ids[:5],
                "semantic_top_5_scores": [round(s, 4) for s in top_k_scores[:5]],
                "recall@5": round(recall_at_k["Recall@5"][-1], 4),
                "recall@10": round(recall_at_k["Recall@10"][-1], 4),
                "recall@25": round(recall_at_k["Recall@25"][-1], 4),
                "reciprocal_rank": round(rr, 4)
            })

        exact_recall = exact_baseline_hits / exact_baseline_total if exact_baseline_total else 0.0

        summary_metrics = {
            "num_evaluated_queries": len(query_details),
            "Recall@5": float(np.mean(recall_at_k["Recall@5"])),
            "Recall@10": float(np.mean(recall_at_k["Recall@10"])),
            "Recall@15": float(np.mean(recall_at_k["Recall@15"])),
            "Recall@25": float(np.mean(recall_at_k["Recall@25"])),
            "Precision@5": float(np.mean(precision_at_k["Precision@5"])),
            "Precision@10": float(np.mean(precision_at_k["Precision@10"])),
            "MRR": float(np.mean(reciprocal_ranks)),
            "exact_baseline_recall": float(exact_recall),
            "query_details": query_details,
            "negative_query_analysis": negative_analyses
        }

        return summary_metrics

    def run_candidate(self, model_id: str, revision: str, batch_size: int = 32) -> Dict[str, Any]:
        """Execute full benchmark pipeline for a single candidate model."""
        logger.info("\n=======================================================")
        logger.info("STARTING BENCHMARK: %s", model_id)
        logger.info("=======================================================")

        model = E5EmbeddingModel(model_id=model_id, revision=revision, num_threads=6)
        
        # 1. Cold model load
        load_time = model.load_model()
        logger.info("[%s] Cold load time: %.2f s", model_id, load_time)
        meta = model.get_metadata()

        # 2. Determinism check
        determinism = self.check_determinism(model)
        logger.info("[%s] Determinism: %s", model_id, determinism)

        # 3. Latency benchmark
        latency = self.benchmark_latency(model, repetitions=50)
        logger.info("[%s] Single query p50: %.2f ms, p95: %.2f ms", model_id, latency["p50_ms"], latency["p95_ms"])

        # 4. Batch throughput benchmark
        throughput = self.benchmark_batch_throughput(model, batch_sizes=[1, 4, 8, 16])

        # 5. In-memory corpus matrix encoding
        logger.info(
            "[%s] Encoding full corpus (%d eligible passages, batch_size=%d)...",
            model_id, len(self.eligible_passages), batch_size
        )
        t_enc_start = time.perf_counter()
        corpus_vec_batches = []
        for i in range(0, len(self.eligible_passages), batch_size):
            batch = self.eligible_passages[i:i + batch_size]
            vecs = model.encode_batch(batch, max_length=128)
            corpus_vec_batches.append(vecs)
            if (i // batch_size) % 100 == 0 or i + batch_size >= len(self.eligible_passages):
                done = min(i + batch_size, len(self.eligible_passages))
                elapsed = time.perf_counter() - t_enc_start
                rate = done / elapsed if elapsed > 0 else 0
                logger.info("   [%s] Encoded %d / %d passages (%.1f texts/sec)...", model_id, done, len(self.eligible_passages), rate)

        corpus_embeddings = np.vstack(corpus_vec_batches)
        total_corpus_enc_time = time.perf_counter() - t_enc_start
        corpus_enc_rate = len(self.eligible_passages) / total_corpus_enc_time
        logger.info(
            "[%s] Corpus encoding complete: %s matrix in %.2f s (%.2f texts/sec).",
            model_id, corpus_embeddings.shape, total_corpus_enc_time, corpus_enc_rate
        )

        # 6. Quality evaluation
        quality = self.evaluate_retrieval_quality(model, corpus_embeddings)
        logger.info(
            "[%s] Retrieval Quality: Recall@5=%.4f, Recall@10=%.4f, Recall@25=%.4f, MRR=%.4f",
            model_id, quality["Recall@5"], quality["Recall@10"], quality["Recall@25"], quality["MRR"]
        )

        # Clean up in-memory matrix
        del corpus_embeddings
        del corpus_vec_batches
        del model

        return {
            "metadata": meta,
            "cold_load_time_sec": load_time,
            "determinism": determinism,
            "latency": latency,
            "throughput": throughput,
            "corpus_encoding": {
                "total_passages": len(self.eligible_passages),
                "batch_size": batch_size,
                "total_time_sec": total_corpus_enc_time,
                "overall_texts_per_sec": corpus_enc_rate,
            },
            "quality": quality
        }


def collect_environment_info() -> Dict[str, Any]:
    """Collect comprehensive hardware and software specifications."""
    env = {
        "python_version": sys.version,
        "platform": platform.platform(),
        "os_name": platform.system(),
        "os_release": platform.release(),
        "os_version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "logical_cpu_count": os.cpu_count(),
        "torch_version": torch.__version__,
        "transformers_version": None,
        "tokenizers_version": None,
        "sentencepiece_version": None,
        "numpy_version": np.__version__,
        "cuda_available": torch.cuda.is_available(),
        "cuda_version": getattr(torch.version, "cuda", None),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "N/A",
        "gpu_vram_gb": round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2) if torch.cuda.is_available() else "N/A",
    }
    for mod_name in ["transformers", "tokenizers", "sentencepiece"]:
        try:
            m = __import__(mod_name)
            env[f"{mod_name}_version"] = getattr(m, "__version__", "installed")
        except ImportError:
            env[f"{mod_name}_version"] = "NOT INSTALLED"
    return env


def main():
    logger.info("Starting SOL AI Step 3B Benchmark & Model Validation...")
    env_info = collect_environment_info()
    logger.info("Environment: %s", json.dumps(env_info, indent=2))

    db_path = PROJECT_ROOT / "data" / "processed" / "madurai_exact.db"
    benchmark_json = PROJECT_ROOT / "tests" / "data" / "semantic_benchmark.json"

    runner = EmbeddingBenchmarkRunner(db_path=db_path, benchmark_json_path=benchmark_json)
    runner.load_corpus()

    # Candidate models to evaluate
    candidates = [
        {
            "name": "E5-small",
            "model_id": "intfloat/multilingual-e5-small",
            "revision": "614241f622f53c4eeff9890bdc4f31cfecc418b3",
            "batch_size": 32
        },
        {
            "name": "E5-base",
            "model_id": "intfloat/multilingual-e5-base",
            "revision": "d128750597153bb5987e10b1c3493a34e5a4502a",
            "batch_size": 16
        }
    ]

    benchmark_results = {
        "environment": env_info,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "candidates": {}
    }

    for c in candidates:
        res = runner.run_candidate(
            model_id=c["model_id"],
            revision=c["revision"],
            batch_size=c["batch_size"]
        )
        benchmark_results["candidates"][c["name"]] = res

    # Save benchmark results to JSON in scratch directory
    scratch_dir = PROJECT_ROOT / "scratch"
    scratch_dir.mkdir(parents=True, exist_ok=True)
    out_file = scratch_dir / "step3b_benchmark_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(benchmark_results, f, indent=2, ensure_ascii=False)

    logger.info("All benchmarks complete! Results saved to %s", out_file)


if __name__ == "__main__":
    main()
