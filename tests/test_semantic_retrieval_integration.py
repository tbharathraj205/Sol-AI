"""
SOL AI — Step 3E: Semantic Retrieval Integration Tests.

Comprehensive integration test suite covering:
TEST 1 — Exact retrieval preserved ('மரம்')
TEST 2 — Inflectional retrieval preserved ('மரங்களில்')
TEST 3 — Semantic evidence appears (benchmark conceptual query)
TEST 4 — Semantic duplicate handling (deterministic provenance preserved)
TEST 5 — Semantic failure isolation (mocked adapter exception)
TEST 6 — Missing semantic artifacts failure safety
TEST 7 — Health endpoint does NOT trigger semantic initialization
TEST 8 — Full API integration (POST /api/query)
"""

import os
import sys
import json
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Setup path and Django environment
project_root = Path(__file__).resolve().parents[1]
sol_django_dir = project_root / "backend" / "sol_django"
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(sol_django_dir) not in sys.path:
    sys.path.insert(0, str(sol_django_dir))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sol_django.settings")

import django
django.setup()

from django.test import Client, SimpleTestCase
from backend.retrieval.engine import RetrievalEngine, SEMANTIC_CANDIDATE_K
from backend.resources.project_madurai_semantic import ProjectMaduraiSemanticAdapter
from backend.interpretation.schemas import SOLResponse
from backend.sol_django.api.services import SOLServiceRegistry


class TestSemanticRetrievalIntegration(unittest.TestCase):
    """
    Step 3E Integration and Verification Test Suite for SOL AI Semantic Retrieval.
    """

    @classmethod
    def setUpClass(cls):
        """Instantiate canonical RetrievalEngine."""
        cls.engine = RetrievalEngine()

    # -------------------------------------------------------------------------
    # TEST 1 — Exact retrieval preserved
    # -------------------------------------------------------------------------
    def test_01_exact_retrieval_preserved(self):
        """
        Query 'மரம்':
        - exact retrieval still works
        - Project Madurai exact evidence exists
        - semantic integration does not remove exact evidence
        """
        res = self.engine.search("மரம்")
        self.assertEqual(res.normalized_query, "மரம்")

        # Project Madurai must report FOUND in resource summary
        self.assertIn("Project Madurai", res.resource_summary)
        self.assertEqual(res.resource_summary["Project Madurai"]["status"], "FOUND")

        # Exact evidence must be present with retrieval_method == 'exact'
        exact_evs = [
            e for e in res.evidence
            if e.source == "Project Madurai"
            and e.metadata.get("status") == "FOUND"
            and e.metadata.get("retrieval_method") == "exact"
        ]
        self.assertGreater(len(exact_evs), 0, "Exact Project Madurai evidence missing for 'மரம்'")

        # Validate canonical properties of exact evidence
        for ev in exact_evs:
            self.assertIn("PM-", ev.source_id)
            self.assertIsNotNone(ev.passage)
            self.assertIsNotNone(ev.work)
            self.assertEqual(ev.evidence_type, "literary_context")

    # -------------------------------------------------------------------------
    # TEST 2 — Inflectional retrieval preserved
    # -------------------------------------------------------------------------
    def test_02_inflectional_retrieval_preserved(self):
        """
        Query 'மரங்களில்':
        - ThamizhiMorph -> 'மரம்' still works
        - Verify lemma/exact evidence remains present
        - Semantic retrieval must not replace the deterministic path
        """
        res = self.engine.search("மரங்களில்")
        self.assertEqual(res.normalized_query, "மரங்களில்")

        # ThamizhiMorph must produce candidate lemma 'மரம்'
        self.assertIn("மரம்", res.lemma_candidates)

        # ThamizhiMorph morphological evidence must be present
        tm_evs = [
            e for e in res.evidence
            if e.source == "ThamizhiMorph" and e.metadata.get("status") == "FOUND"
        ]
        self.assertGreater(len(tm_evs), 0, "ThamizhiMorph evidence missing for 'மரங்களில்'")

        # Pass 2 lemma lookup must retrieve Project Madurai exact evidence with lemma == 'மரம்'
        pm_lemma_evs = [
            e for e in res.evidence
            if e.source == "Project Madurai"
            and e.metadata.get("status") == "FOUND"
            and e.lemma == "மரம்"
        ]
        self.assertGreater(len(pm_lemma_evs), 0, "Pass 2 lemma evidence for 'மரம்' missing")

    # -------------------------------------------------------------------------
    # TEST 3 — Semantic evidence appears
    # -------------------------------------------------------------------------
    def test_03_semantic_evidence_appears(self):
        """
        Query conceptual benchmark 'கல்வியின் பெருமையும் கற்கும் முறையும்':
        - semantic evidence is returned
        - source == 'Project Madurai'
        - evidence_type == 'literary_context'
        - retrieval_mode == 'semantic'
        - similarity_score exists and is numeric within valid cosine range
        - original passage metadata is populated
        """
        query = "கல்வியின் பெருமையும் கற்கும் முறையும்"
        res = self.engine.search(query)

        # Filter for semantic Project Madurai evidence
        sem_evs = [
            e for e in res.evidence
            if e.source == "Project Madurai"
            and e.metadata.get("status") == "FOUND"
            and e.metadata.get("retrieval_mode") == "semantic"
        ]
        self.assertGreater(len(sem_evs), 0, f"No semantic evidence returned for '{query}'")

        for ev in sem_evs:
            self.assertEqual(ev.source, "Project Madurai")
            self.assertEqual(ev.evidence_type, "literary_context")
            self.assertIsNotNone(ev.passage, f"Passage missing for semantic chunk {ev.source_id}")
            self.assertGreater(len(ev.passage), 0)
            self.assertIsNotNone(ev.work, f"Work missing for semantic chunk {ev.source_id}")
            self.assertIn("PM-", ev.source_id)

            score = ev.metadata.get("similarity_score")
            self.assertIsInstance(score, float)
            self.assertGreaterEqual(score, -1.0)
            self.assertLessEqual(score, 1.0)
            # High semantic similarity expected for this Tirukkural education benchmark
            self.assertGreater(score, 0.70)

    # -------------------------------------------------------------------------
    # TEST 4 — Semantic duplicate handling
    # -------------------------------------------------------------------------
    def test_04_semantic_duplicate_handling(self):
        """
        Query 'மரம்' where semantic candidates overlap exact candidates:
        - no duplicate Project Madurai chunks (each chunk_id appears only once)
        - deterministic evidence is preserved
        - semantic evidence does not overwrite exact provenance
        """
        res = self.engine.search("மரம்")

        pm_evs = [
            e for e in res.evidence
            if e.source == "Project Madurai" and e.metadata.get("status") == "FOUND"
        ]
        self.assertGreater(len(pm_evs), 0)

        # Stable chunk ID deduplication check
        chunk_ids = [e.source_id for e in pm_evs if e.source_id]
        self.assertEqual(
            len(chunk_ids),
            len(set(chunk_ids)),
            "Duplicate Project Madurai chunk IDs detected in evidence set"
        )

        # Chunks retrieved by exact match MUST retain exact retrieval provenance
        for ev in pm_evs:
            if ev.metadata.get("retrieval_method") == "exact":
                self.assertNotEqual(
                    ev.metadata.get("retrieval_mode"),
                    "semantic",
                    f"Exact evidence {ev.source_id} was improperly overwritten with semantic mode"
                )

    # -------------------------------------------------------------------------
    # TEST 5 — Semantic failure isolation
    # -------------------------------------------------------------------------
    def test_05_semantic_failure_isolation(self):
        """
        Simulate semantic adapter failure (exception raised).
        Verify:
        - exact retrieval succeeds
        - lemma retrieval succeeds
        - API/retrieval response remains valid
        - semantic failure does not crash RetrievalEngine
        """
        failing_semantic_adapter = MagicMock(spec=ProjectMaduraiSemanticAdapter)
        failing_semantic_adapter.lookup.side_effect = RuntimeError(
            "Simulated PyTorch CUDA out of memory / corrupted vector array"
        )

        engine = RetrievalEngine(project_madurai_semantic=failing_semantic_adapter)

        # Exact query
        res = engine.search("மரம்")
        self.assertIsNotNone(res)
        self.assertEqual(res.normalized_query, "மரம்")
        exact_evs = [
            e for e in res.evidence
            if e.source == "Project Madurai"
            and e.metadata.get("status") == "FOUND"
            and e.metadata.get("retrieval_method") == "exact"
        ]
        self.assertGreater(len(exact_evs), 0, "Exact retrieval failed when semantic crashed")
        self.assertNotIn("Project Madurai", res.errors)

        # Inflected query
        res_inf = engine.search("மரங்களில்")
        self.assertIn("மரம்", res_inf.lemma_candidates)
        lemma_evs = [
            e for e in res_inf.evidence
            if e.source == "Project Madurai"
            and e.metadata.get("status") == "FOUND"
            and e.lemma == "மரம்"
        ]
        self.assertGreater(len(lemma_evs), 0, "Lemma retrieval failed when semantic crashed")

    # -------------------------------------------------------------------------
    # TEST 6 — Missing semantic artifacts failure safety
    # -------------------------------------------------------------------------
    def test_06_missing_semantic_artifacts_fail_safe(self):
        """
        Simulate missing vector file or metadata:
        - adapter returns error evidence safely
        - engine isolates the error and prevents evidence contamination
        - deterministic retrieval continues unimpeded
        """
        missing_artifacts_adapter = ProjectMaduraiSemanticAdapter(
            vectors_path=Path("nonexistent_path/fake_vectors.npy"),
            metadata_path=Path("nonexistent_path/fake_meta.json"),
        )
        engine = RetrievalEngine(project_madurai_semantic=missing_artifacts_adapter)

        res = engine.search("மரம்")
        self.assertEqual(res.normalized_query, "மரம்")

        # Exact evidence present
        exact_evs = [
            e for e in res.evidence
            if e.source == "Project Madurai"
            and e.metadata.get("status") == "FOUND"
        ]
        self.assertGreater(len(exact_evs), 0)

        # No error contamination in evidence list
        error_evs = [
            e for e in res.evidence
            if e.metadata.get("status") == "ERROR" and e.source == "Project Madurai"
        ]
        self.assertEqual(len(error_evs), 0, "Semantic error leaked into user-facing evidence")

    # -------------------------------------------------------------------------
    # TEST 7 — Health endpoint lazy lifecycle
    # -------------------------------------------------------------------------
    def test_07_health_endpoint_no_semantic_init(self):
        """
        Verify:
        GET /api/health and GET /health
        do NOT trigger semantic model or vector matrix initialization.
        """
        SOLServiceRegistry.reset_instance()
        client = Client()

        # Call health check
        for path in ["/api/health", "/health"]:
            resp = client.get(path)
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json().get("status"), "ok")

        # Service registry engine must NOT have been instantiated
        reg = SOLServiceRegistry.get_instance()
        self.assertIsNone(reg._engine, "Health endpoint eagerly instantiated RetrievalEngine")

        # Independent fresh adapter instance verification
        fresh_adapter = ProjectMaduraiSemanticAdapter()
        self.assertFalse(fresh_adapter.is_loaded, "Fresh adapter should not be loaded eagerly")

    # -------------------------------------------------------------------------
    # TEST 8 — API integration (POST /api/query)
    # -------------------------------------------------------------------------
    def test_08_api_integration_deterministic_and_semantic(self):
        """
        Call POST /api/query:
        1. Exact query 'மரம்':
           - HTTP 200
           - response conforms strictly to SOLResponse
           - deterministic sources present
        2. Semantic benchmark 'கல்வியின் பெருமையும் கற்கும் முறையும்':
           - HTTP 200
           - response conforms strictly to SOLResponse
           - semantic Project Madurai literary context appears
        """
        client = Client()

        # 1. Deterministic query
        payload_exact = {"query": "மரம்", "provider": "mock"}
        resp_exact = client.post(
            "/api/query",
            data=json.dumps(payload_exact),
            content_type="application/json",
        )
        self.assertEqual(resp_exact.status_code, 200)
        data_exact = resp_exact.json()
        sol_exact = SOLResponse(**data_exact)
        self.assertEqual(sol_exact.query, "மரம்")
        self.assertEqual(sol_exact.lemma, "மரம்")
        self.assertIn("Project Madurai", sol_exact.sources)
        self.assertGreater(len(sol_exact.literary_context), 0)

        # 2. Semantic benchmark query
        payload_sem = {
            "query": "கல்வியின் பெருமையும் கற்கும் முறையும்",
            "provider": "mock"
        }
        resp_sem = client.post(
            "/api/query",
            data=json.dumps(payload_sem),
            content_type="application/json",
        )
        self.assertEqual(resp_sem.status_code, 200)
        data_sem = resp_sem.json()
        sol_sem = SOLResponse(**data_sem)
        self.assertEqual(sol_sem.query, "கல்வியின் பெருமையும் கற்கும் முறையும்")
        self.assertIn("Project Madurai", sol_sem.sources)
        self.assertGreater(len(sol_sem.literary_context), 0)

        # Verify literary context contains valid Tirukkural passage retrieved semantically
        pm_items = [item for item in sol_sem.literary_context if item.source == "Project Madurai"]
        self.assertGreater(len(pm_items), 0)
        for item in pm_items:
            self.assertIsNotNone(item.passage)
            self.assertIsNotNone(item.work)

    # -------------------------------------------------------------------------
    # Integration Candidate K constant verification
    # -------------------------------------------------------------------------
    def test_09_semantic_candidate_k_constant(self):
        """Verify candidate pool constant SEMANTIC_CANDIDATE_K == 25 is configured."""
        self.assertEqual(SEMANTIC_CANDIDATE_K, 25)
        self.assertEqual(self.engine.semantic_candidate_k, 25)


if __name__ == "__main__":
    unittest.main()
