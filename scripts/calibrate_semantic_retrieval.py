"""
SOL AI — Step 3F: Semantic Retrieval Calibration Script.

Empirically evaluates:
1. K sweep (K = 5, 10, 15, 20, 25)
2. Threshold sweep across observed score distribution
3. Positive vs Negative similarity score distributions (min, median, max, overlap)
4. Query-level breakdown across all 23 benchmark queries
5. Sensitivity analysis (including vs excluding questionable 'பாரதி' query)
6. Precision, Recall, MRR, Rejection Rate, False Positive Rate

Uses:
- Frozen Model: intfloat/multilingual-e5-small @ 614241f622f53c4eeff9890bdc4f31cfecc418b3
- Permanent Vectors: data/processed/madurai_semantic_vectors.npy
- Metadata: data/processed/madurai_semantic_meta.json
- Benchmark: tests/data/semantic_benchmark.json
"""

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Force UTF-8 stdout
sys.stdout.reconfigure(encoding="utf-8")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("calibrate_semantic")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.resources.project_madurai_semantic import ProjectMaduraiSemanticAdapter


def load_benchmark(benchmark_path: Path) -> List[Dict[str, Any]]:
    with open(benchmark_path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_calibration():
    adapter = ProjectMaduraiSemanticAdapter()
    logger.info("Ensuring semantic adapter is loaded...")
    t0 = time.perf_counter()
    adapter.ensure_loaded()
    load_time = time.perf_counter() - t0
    logger.info("Adapter loaded in %.2f seconds.", load_time)

    benchmark_path = PROJECT_ROOT / "tests" / "data" / "semantic_benchmark.json"
    benchmark = load_benchmark(benchmark_path)
    logger.info("Loaded %d queries from %s", len(benchmark), benchmark_path)

    # 1. Run top-50 retrieval for all 23 queries to gather candidate pools
    MAX_CANDIDATES = 50
    query_results = []

    for item in benchmark:
        q = item["query"]
        category = item["category"]
        gold_cids = set(item["gold_chunk_ids"])
        
        t_q0 = time.perf_counter()
        evs = adapter.lookup(q, top_k=MAX_CANDIDATES)
        latency_ms = (time.perf_counter() - t_q0) * 1000.0

        candidates = []
        for rank, ev in enumerate(evs, start=1):
            cid = ev.source_id or ev.metadata.get("chunk_id")
            score = ev.metadata.get("similarity_score", 0.0)
            is_relevant = cid in gold_cids
            candidates.append({
                "rank": rank,
                "chunk_id": cid,
                "similarity_score": score,
                "is_relevant": is_relevant,
                "work": ev.work,
                "passage": ev.passage[:60] if ev.passage else "",
            })

        # Rank of first relevant
        first_rel_rank = None
        highest_rel_sim = None
        highest_irrel_sim = None

        for c in candidates:
            if c["is_relevant"]:
                if first_rel_rank is None:
                    first_rel_rank = c["rank"]
                if highest_rel_sim is None or c["similarity_score"] > highest_rel_sim:
                    highest_rel_sim = c["similarity_score"]
            else:
                if highest_irrel_sim is None or c["similarity_score"] > highest_irrel_sim:
                    highest_irrel_sim = c["similarity_score"]

        query_results.append({
            "query": q,
            "category": category,
            "gold_chunk_ids": list(item["gold_chunk_ids"]),
            "candidates": candidates,
            "first_rel_rank": first_rel_rank,
            "highest_rel_sim": highest_rel_sim,
            "highest_irrel_sim": highest_irrel_sim,
            "latency_ms": latency_ms,
        })

    # Save raw evaluation
    out_dir = PROJECT_ROOT / "scratch"
    out_dir.mkdir(exist_ok=True)
    
    # -------------------------------------------------------------
    # 2. Score Distribution Analysis (Positive vs Negative)
    # -------------------------------------------------------------
    positive_gold_scores = []  # scores of actual gold matches retrieved
    positive_top1_scores = []  # top-1 candidate score for positive queries
    all_positive_candidate_scores = [] # all candidate scores for positive queries (top 25)

    negative_top1_scores = []  # top-1 score for negative queries
    negative_candidate_scores = []  # all candidate scores for negative queries (top 25)

    for qr in query_results:
        cat = qr["category"]
        if cat == "negative_out_of_domain":
            for c in qr["candidates"][:25]:
                negative_candidate_scores.append(c["similarity_score"])
            negative_top1_scores.append(qr["candidates"][0]["similarity_score"])
        else:
            # Positive query
            for c in qr["candidates"][:25]:
                all_positive_candidate_scores.append(c["similarity_score"])
                if c["is_relevant"]:
                    positive_gold_scores.append(c["similarity_score"])
            if qr["candidates"]:
                positive_top1_scores.append(qr["candidates"][0]["similarity_score"])

    dist_stats = {
        "positive_gold_scores": {
            "count": len(positive_gold_scores),
            "min": float(np.min(positive_gold_scores)) if positive_gold_scores else None,
            "median": float(np.median(positive_gold_scores)) if positive_gold_scores else None,
            "mean": float(np.mean(positive_gold_scores)) if positive_gold_scores else None,
            "max": float(np.max(positive_gold_scores)) if positive_gold_scores else None,
        },
        "positive_top1_scores": {
            "count": len(positive_top1_scores),
            "min": float(np.min(positive_top1_scores)),
            "median": float(np.median(positive_top1_scores)),
            "mean": float(np.mean(positive_top1_scores)),
            "max": float(np.max(positive_top1_scores)),
        },
        "negative_top1_scores": {
            "count": len(negative_top1_scores),
            "min": float(np.min(negative_top1_scores)),
            "median": float(np.median(negative_top1_scores)),
            "mean": float(np.mean(negative_top1_scores)),
            "max": float(np.max(negative_top1_scores)),
        },
        "negative_candidate_scores_top25": {
            "count": len(negative_candidate_scores),
            "min": float(np.min(negative_candidate_scores)),
            "median": float(np.median(negative_candidate_scores)),
            "mean": float(np.mean(negative_candidate_scores)),
            "max": float(np.max(negative_candidate_scores)),
        },
    }

    # -------------------------------------------------------------
    # 3. K Sweep Evaluation (No Threshold)
    # -------------------------------------------------------------
    k_values = [5, 10, 15, 20, 25]

    def eval_k(k: int, exclude_questionable: bool = False):
        recalls = []
        precisions = []
        mrrs = []

        pos_queries = [
            qr for qr in query_results
            if qr["category"] != "negative_out_of_domain"
            and (not exclude_questionable or qr["query"] != "பாரதி")
        ]

        for qr in pos_queries:
            gold = set(qr["gold_chunk_ids"])
            top_k_cands = qr["candidates"][:k]
            retrieved_cids = set(c["chunk_id"] for c in top_k_cands)
            hits = len(gold.intersection(retrieved_cids))

            recall = hits / len(gold) if gold else 0.0
            precision = hits / k
            
            # Reciprocal rank
            rr = 0.0
            for rank_idx, c in enumerate(top_k_cands, start=1):
                if c["chunk_id"] in gold:
                    rr = 1.0 / rank_idx
                    break

            recalls.append(recall)
            precisions.append(precision)
            mrrs.append(rr)

        # Negative query false positive rate at K (no threshold)
        neg_queries = [qr for qr in query_results if qr["category"] == "negative_out_of_domain"]
        neg_fpr_no_thresh = 1.0  # without threshold, all negative queries return K results

        return {
            "K": k,
            "recall": float(np.mean(recalls)),
            "precision": float(np.mean(precisions)),
            "mrr": float(np.mean(mrrs)),
            "neg_fpr": neg_fpr_no_thresh,
        }

    k_results = [eval_k(k, exclude_questionable=False) for k in k_values]
    k_results_no_quest = [eval_k(k, exclude_questionable=True) for k in k_values]

    # -------------------------------------------------------------
    # 4. Threshold Sweep
    # -------------------------------------------------------------
    # Let's inspect thresholds covering observed range:
    # 0.70 to 0.90 in steps of 0.01
    thresholds = [round(t, 2) for t in np.arange(0.70, 0.91, 0.01)]

    def eval_threshold(tau: float, candidate_k: int = 25, exclude_questionable: bool = False):
        pos_queries = [
            qr for qr in query_results
            if qr["category"] != "negative_out_of_domain"
            and (not exclude_questionable or qr["query"] != "பாரதி")
        ]
        neg_queries = [qr for qr in query_results if qr["category"] == "negative_out_of_domain"]

        recalls = []
        precisions = []
        pos_queries_with_retention = 0
        total_gold_items = sum(len(qr["gold_chunk_ids"]) for qr in pos_queries)
        total_gold_retained = 0

        for qr in pos_queries:
            gold = set(qr["gold_chunk_ids"])
            # Filter candidates within top candidate_k by threshold tau
            filtered_cands = [c for c in qr["candidates"][:candidate_k] if c["similarity_score"] >= tau]
            retrieved_cids = set(c["chunk_id"] for c in filtered_cands)
            hits = len(gold.intersection(retrieved_cids))

            total_gold_retained += hits
            if hits > 0:
                pos_queries_with_retention += 1

            recall = hits / len(gold) if gold else 0.0
            precision = hits / len(filtered_cands) if filtered_cands else 0.0

            recalls.append(recall)
            precisions.append(precision)

        # Negative queries behavior under threshold tau
        # A negative query is suppressed (True Negative) if 0 candidates pass tau
        # False Positive if >= 1 candidate passes tau
        neg_rejected = 0
        for qr in neg_queries:
            filtered_cands = [c for c in qr["candidates"][:candidate_k] if c["similarity_score"] >= tau]
            if len(filtered_cands) == 0:
                neg_rejected += 1

        neg_rejection_rate = neg_rejected / len(neg_queries) if neg_queries else 1.0
        neg_fpr = 1.0 - neg_rejection_rate
        gold_retention_rate = total_gold_retained / total_gold_items if total_gold_items else 0.0
        query_retention_rate = pos_queries_with_retention / len(pos_queries) if pos_queries else 0.0

        return {
            "threshold": tau,
            "candidate_k": candidate_k,
            "recall": float(np.mean(recalls)),
            "precision": float(np.mean(precisions)),
            "gold_retention_rate": gold_retention_rate,
            "query_retention_rate": query_retention_rate,
            "neg_rejection_rate": neg_rejection_rate,
            "neg_fpr": neg_fpr,
        }

    threshold_results_k25 = [eval_threshold(t, candidate_k=25) for t in thresholds]
    threshold_results_k10 = [eval_threshold(t, candidate_k=10) for t in thresholds]
    threshold_results_k25_no_quest = [eval_threshold(t, candidate_k=25, exclude_questionable=True) for t in thresholds]

    output_data = {
        "load_time_s": load_time,
        "dist_stats": dist_stats,
        "k_sweep": k_results,
        "k_sweep_excluding_questionable": k_results_no_quest,
        "threshold_sweep_k25": threshold_results_k25,
        "threshold_sweep_k10": threshold_results_k10,
        "threshold_sweep_k25_excluding_questionable": threshold_results_k25_no_quest,
        "query_results": query_results,
    }

    with open(out_dir / "calibration_data.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    # Print summary to stdout
    print("\n" + "="*80)
    print("STEP 3F: CALIBRATION SUMMARY")
    print("="*80)
    print("\n--- DISTRIBUTIONS ---")
    for k, v in dist_stats.items():
        print(f"{k}: {v}")

    print("\n--- K SWEEP (Full Benchmark, no threshold) ---")
    print(f"{'K':<5} | {'Recall@K':<10} | {'Precision@K':<12} | {'MRR':<10} | {'Negative FPR':<12}")
    print("-" * 55)
    for r in k_results:
        print(f"{r['K']:<5} | {r['recall']:<10.4f} | {r['precision']:<12.4f} | {r['mrr']:<10.4f} | {r['neg_fpr']:<12.4f}")

    print("\n--- K SWEEP (Excluding Questionable 'பாரதி') ---")
    print(f"{'K':<5} | {'Recall@K':<10} | {'Precision@K':<12} | {'MRR':<10} | {'Negative FPR':<12}")
    print("-" * 55)
    for r in k_results_no_quest:
        print(f"{r['K']:<5} | {r['recall']:<10.4f} | {r['precision']:<12.4f} | {r['mrr']:<10.4f} | {r['neg_fpr']:<12.4f}")

    print("\n--- THRESHOLD SWEEP (Candidate K=25) ---")
    print(f"{'Threshold':<10} | {'Recall':<8} | {'Precision':<10} | {'Gold Ret%':<10} | {'Neg Rejection%':<15} | {'Neg FPR%':<10}")
    print("-" * 75)
    for r in threshold_results_k25:
        print(f"{r['threshold']:<10.2f} | {r['recall']:<8.4f} | {r['precision']:<10.4f} | {r['gold_retention_rate']*100:<10.1f} | {r['neg_rejection_rate']*100:<15.1f} | {r['neg_fpr']*100:<10.1f}")

    print("\n--- QUERY LEVEL BREAKDOWN ---")
    for qr in query_results:
        print(f"[{qr['category']}] Query: '{qr['query']}'")
        print(f"  Gold: {qr['gold_chunk_ids']}")
        print(f"  First Rel Rank: {qr['first_rel_rank']}, Highest Rel Sim: {qr['highest_rel_sim']}, Highest Irrel Sim: {qr['highest_irrel_sim']}")
        for c in qr["candidates"][:5]:
            rel_flag = "✓ REL" if c["is_relevant"] else "✗"
            print(f"    Rank {c['rank']}: {c['chunk_id']} ({c['similarity_score']:.4f}) {rel_flag} - {c['work']} - {c['passage'][:40]}")


if __name__ == "__main__":
    run_calibration()
