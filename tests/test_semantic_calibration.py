"""
SOL AI — Step 3F: Semantic Retrieval Calibration & Production Policy Tests.

Tests:
- Test 1: Production K equals calibrated value (25)
- Test 2: Production threshold equals calibrated value (0.845)
- Test 3: Below-threshold suppression (candidates < 0.845 are discarded)
- Test 4: Above-threshold retention (benchmark relevant result >= 0.845 remains)
- Test 5: Exact preservation ('மரம்' retains deterministic exact evidence)
- Test 6: Morphology preservation ('மரங்களில்' -> 'மரம்' via ThamizhiMorph)
- Test 7: Conceptual retrieval ('கல்வியின் பெருமையும் கற்கும் முறையும்' retrieves PM-TK-0391)
- Test 8: Negative query suppression (out-of-domain modern queries suppressed below threshold)
- Test 9: Duplicate preservation (exact provenance authoritative when chunk coincides)
- Test 10: Semantic failure isolation (exception in semantic pass fails closed safely)
"""

import os
import sys
import json
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Setup path and Django environment
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOL_DJANGO_DIR = PROJECT_ROOT / "backend" / "sol_django"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SOL_DJANGO_DIR) not in sys.path:
    sys.path.insert(0, str(SOL_DJANGO_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sol_django.settings")

import django
django.setup()

from django.test import Client
from backend.retrieval.engine import (
    RetrievalEngine,
    SEMANTIC_CANDIDATE_K,
    SEMANTIC_SIMILARITY_THRESHOLD,
)
from backend.resources.project_madurai_semantic import (
    ProjectMaduraiSemanticAdapter,
    CALIBRATED_CANDIDATE_K,
    CALIBRATED_SIMILARITY_THRESHOLD,
)
from backend.schemas.evidence import Evidence
from backend.interpretation.schemas import SOLResponse


class TestSemanticCalibrationPolicy(unittest.TestCase):
    """
    Verification test suite for Step 3F calibrated production policy.
    """

    @classmethod
    def setUpClass(cls):
        cls.engine = RetrievalEngine()
        cls.adapter = cls.engine.project_madurai_semantic or ProjectMaduraiSemanticAdapter()
        cls.adapter.ensure_loaded()

    # -------------------------------------------------------------------------
    # Test 1 — Final K
    # -------------------------------------------------------------------------
    def test_01_final_production_k(self):
        """Production candidate K equals the empirically calibrated value (25)."""
        self.assertEqual(SEMANTIC_CANDIDATE_K, 25)
        self.assertEqual(CALIBRATED_CANDIDATE_K, 25)
        self.assertEqual(self.engine.semantic_candidate_k, 25)

    # -------------------------------------------------------------------------
    # Test 2 — Threshold
    # -------------------------------------------------------------------------
    def test_02_final_production_threshold(self):
        """Production similarity threshold equals the empirically calibrated value (0.845)."""
        self.assertEqual(SEMANTIC_SIMILARITY_THRESHOLD, 0.845)
        self.assertEqual(CALIBRATED_SIMILARITY_THRESHOLD, 0.845)
        self.assertEqual(self.engine.semantic_similarity_threshold, 0.845)

    # -------------------------------------------------------------------------
    # Test 3 — Below-threshold suppression
    # -------------------------------------------------------------------------
    def test_03_below_threshold_suppression(self):
        """A semantic result below the calibrated threshold is not returned as accepted evidence."""
        # Query with low candidate similarities: verify adapter with threshold=0.845 suppresses below-threshold items
        res_unfiltered = self.adapter.lookup("குவாண்டம் கணினி மற்றும் செயற்கை நுண்ணறிவு வழிமுறைகள்", top_k=5, threshold=None)
        self.assertGreater(len(res_unfiltered), 0)
        for r in res_unfiltered:
            self.assertLess(r.metadata["similarity_score"], 0.845)

        # Now query with threshold=0.845: all must be suppressed
        res_filtered = self.adapter.lookup("குவாண்டம் கணினி மற்றும் செயற்கை நுண்ணறிவு வழிமுறைகள்", top_k=5, threshold=0.845)
        self.assertEqual(len(res_filtered), 0, "Below-threshold results were not suppressed")

        # Also verify via engine: mocked candidate with similarity 0.830 (< 0.845) is discarded
        mock_ev = Evidence(
            surface="சோதனை",
            lemma=None,
            source="Project Madurai",
            evidence_type="literary_context",
            source_id="PM-MOCK-001",
            metadata={
                "chunk_id": "PM-MOCK-001",
                "similarity_score": 0.8300,
                "retrieval_mode": "semantic",
                "retrieval_method": "semantic",
                "status": "FOUND",
            }
        )
        with patch.object(self.engine.project_madurai_semantic, "lookup", return_value=[mock_ev]):
            search_res = self.engine.search("சோதனை")
            accepted_sem = [
                e for e in search_res.evidence
                if e.metadata.get("chunk_id") == "PM-MOCK-001"
            ]
            self.assertEqual(len(accepted_sem), 0, "Candidate below threshold was accepted into evidence")

    # -------------------------------------------------------------------------
    # Test 4 — Above-threshold retention
    # -------------------------------------------------------------------------
    def test_04_above_threshold_retention(self):
        """A benchmark-supported relevant result above the threshold remains available."""
        # 'யாழ்' has PM-TK-0066 with similarity 0.8635 >= 0.845
        res = self.adapter.lookup("யாழ்", top_k=5, threshold=0.845)
        self.assertGreater(len(res), 0)
        cids = [r.source_id for r in res]
        self.assertIn("PM-TK-0066", cids)
        score = [r.metadata["similarity_score"] for r in res if r.source_id == "PM-TK-0066"][0]
        self.assertGreaterEqual(score, 0.845)

    # -------------------------------------------------------------------------
    # Test 5 — Exact preservation
    # -------------------------------------------------------------------------
    def test_05_exact_preservation(self):
        """Query 'மரம்' produces authoritative deterministic exact evidence."""
        res = self.engine.search("மரம்")
        self.assertEqual(res.normalized_query, "மரம்")

        exact_evs = [
            e for e in res.evidence
            if e.source == "Project Madurai"
            and e.metadata.get("retrieval_method") == "exact"
            and e.metadata.get("status") == "FOUND"
        ]
        self.assertGreater(len(exact_evs), 0, "Deterministic exact evidence missing for 'மரம்'")
        for ev in exact_evs:
            self.assertEqual(ev.metadata.get("retrieval_method"), "exact")
            self.assertIsNotNone(ev.passage)

    # -------------------------------------------------------------------------
    # Test 6 — Morphology preservation
    # -------------------------------------------------------------------------
    def test_06_morphology_preservation(self):
        """Query 'மரங்களில்' resolves through deterministic morphology (ThamizhiMorph -> 'மரம்')."""
        res = self.engine.search("மரங்களில்")
        self.assertEqual(res.normalized_query, "மரங்களில்")

        # Must identify candidate lemma 'மரம்' via morphology
        self.assertIn("மரம்", res.lemma_candidates)

        # Lexical evidence for lemma must be present
        lemma_evs = [
            e for e in res.evidence
            if e.lemma == "மரம்"
            and e.metadata.get("status") == "FOUND"
        ]
        self.assertGreater(len(lemma_evs), 0, "Morphology-discovered lemma evidence missing")

    # -------------------------------------------------------------------------
    # Test 7 — Conceptual retrieval
    # -------------------------------------------------------------------------
    def test_07_conceptual_retrieval(self):
        """Conceptual benchmark query survives calibration with relevant semantic evidence."""
        query = "கல்வியின் பெருமையும் கற்கும் முறையும்"
        res = self.engine.search(query)

        # Check semantic evidence survived thresholding
        semantic_evs = [
            e for e in res.evidence
            if e.source == "Project Madurai"
            and e.metadata.get("retrieval_mode") == "semantic"
            and e.metadata.get("status") == "FOUND"
        ]
        self.assertGreater(len(semantic_evs), 0, "No semantic evidence survived threshold")

        # Verify gold chunk PM-TK-0391 (Tirukkural verse 391 on learning) is present
        cids = [e.source_id or e.metadata.get("chunk_id") for e in semantic_evs]
        self.assertIn("PM-TK-0391", cids, "Gold conceptual passage PM-TK-0391 missing")

        hit = [e for e in semantic_evs if (e.source_id or e.metadata.get("chunk_id")) == "PM-TK-0391"][0]
        self.assertGreaterEqual(hit.metadata["similarity_score"], 0.845)
        self.assertIn("கற்க கசடறக்", hit.passage)

    # -------------------------------------------------------------------------
    # Test 8 — Negative query suppression
    # -------------------------------------------------------------------------
    def test_08_negative_query_suppression(self):
        """Negative/out-of-domain queries below threshold have semantic evidence suppressed."""
        # 1. Quantum computing & AI query (top score 0.8170 < 0.845)
        res_quantum = self.engine.search("குவாண்டம் கணினி மற்றும் செயற்கை நுண்ணறிவு வழிமுறைகள்")
        sem_quantum = [
            e for e in res_quantum.evidence
            if e.source == "Project Madurai"
            and e.metadata.get("retrieval_mode") == "semantic"
            and e.metadata.get("status") == "FOUND"
        ]
        self.assertEqual(len(sem_quantum), 0, "Negative query 'குவாண்டம்...' was not suppressed")

        # 2. Airport security query (top score 0.8423 < 0.845)
        res_airport = self.engine.search("விமான நிலைய பாதுகாப்பு மற்றும் மின்னணு கடவுச்சீட்டு")
        sem_airport = [
            e for e in res_airport.evidence
            if e.source == "Project Madurai"
            and e.metadata.get("retrieval_mode") == "semantic"
            and e.metadata.get("status") == "FOUND"
        ]
        self.assertEqual(len(sem_airport), 0, "Negative query 'விமான நிலைய...' was not suppressed")

        # 3. Stock market query (top score 0.8410 < 0.845)
        res_stock = self.engine.search("பங்குச் சந்தை முதலீடு மற்றும் பணவீக்க விகிதம்")
        sem_stock = [
            e for e in res_stock.evidence
            if e.source == "Project Madurai"
            and e.metadata.get("retrieval_mode") == "semantic"
            and e.metadata.get("status") == "FOUND"
        ]
        self.assertEqual(len(sem_stock), 0, "Negative query 'பங்குச் சந்தை...' was not suppressed")

    # -------------------------------------------------------------------------
    # Test 9 — Duplicate preservation
    # -------------------------------------------------------------------------
    def test_09_duplicate_preservation(self):
        """Deterministic evidence remains authoritative when semantic chunk matches exact chunk."""
        # Query 'மரம்': exact passes retrieve PM-CHINTHAMANI-0939 as exact match,
        # Pass force_semantic=True so that both exact and semantic passes run
        # despite deterministic short-circuit, allowing deduplication logic to be tested
        res = self.engine.search("மரம்", force_semantic=True)

        all_pm_evs = [
            e for e in res.evidence
            if e.source == "Project Madurai" and e.metadata.get("status") == "FOUND"
        ]
        self.assertGreater(len(all_pm_evs), 0)

        # Invariant 1: zero duplicate chunks across all Project Madurai evidence
        pm_cids = [e.source_id for e in all_pm_evs if e.source_id]
        self.assertEqual(len(pm_cids), len(set(pm_cids)), "Duplicate chunk IDs present in evidence")

        # Invariant 2: PM-CHINTHAMANI-0939 was deduplicated and retains exact provenance
        matched_evs = [
            e for e in all_pm_evs
            if e.source_id == "PM-CHINTHAMANI-0939"
        ]
        self.assertEqual(len(matched_evs), 1)
        ev = matched_evs[0]
        self.assertEqual(ev.metadata.get("retrieval_method"), "exact")
        self.assertNotEqual(ev.metadata.get("retrieval_mode"), "semantic")
        # Semantic similarity is attached as metadata without altering exact provenance
        self.assertIn("similarity_score", ev.metadata)
        self.assertGreaterEqual(ev.metadata["similarity_score"], 0.845)

    # -------------------------------------------------------------------------
    # Test 10 — Semantic failure isolation
    # -------------------------------------------------------------------------
    def test_10_semantic_failure_isolation(self):
        """Semantic failure fails closed and leaves deterministic retrieval fully operational."""
        with patch.object(self.engine.project_madurai_semantic, "lookup", side_effect=RuntimeError("Simulated OOM")):
            res = self.engine.search("மரம்")
            # Deterministic retrieval must still succeed
            self.assertEqual(res.normalized_query, "மரம்")
            exact_evs = [
                e for e in res.evidence
                if e.source == "Project Madurai"
                and e.metadata.get("retrieval_method") == "exact"
            ]
            self.assertGreater(len(exact_evs), 0)
            self.assertEqual(res.resource_summary["Project Madurai"]["status"], "FOUND")


class TestSemanticCalibrationAPI(unittest.TestCase):
    """
    Verification of REST API endpoints under calibrated policy.
    """

    @classmethod
    def setUpClass(cls):
        cls.client = Client()

    def test_api_health(self):
        """GET /api/health returns 200 OK."""
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"status": "ok"})

    def test_api_query_exact(self):
        """POST /api/query for exact query 'மரம்'."""
        resp = self.client.post(
            "/api/query",
            data=json.dumps({"query": "மரம்", "provider": "mock"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        sol = SOLResponse(**resp.json())
        self.assertEqual(sol.query, "மரம்")
        self.assertIn("Project Madurai", sol.sources)

    def test_api_query_inflectional(self):
        """POST /api/query for inflected query 'மரங்களில்'."""
        resp = self.client.post(
            "/api/query",
            data=json.dumps({"query": "மரங்களில்", "provider": "mock"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        sol = SOLResponse(**resp.json())
        self.assertEqual(sol.lemma, "மரம்")

    def test_api_query_conceptual(self):
        """POST /api/query for conceptual query 'கல்வியின் பெருமையும் கற்கும் முறையும்'."""
        resp = self.client.post(
            "/api/query",
            data=json.dumps({"query": "கல்வியின் பெருமையும் கற்கும் முறையும்", "provider": "mock"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        sol = SOLResponse(**resp.json())
        self.assertIn("Project Madurai", sol.sources)
        self.assertGreater(len(sol.literary_context), 0)

    def test_api_query_negative(self):
        """POST /api/query for negative query 'குவாண்டம் கணினி மற்றும் செயற்கை நுண்ணறிவு வழிமுறைகள்'."""
        resp = self.client.post(
            "/api/query",
            data=json.dumps({"query": "குவாண்டம் கணினி மற்றும் செயற்கை நுண்ணறிவு வழிமுறைகள்", "provider": "mock"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        sol = SOLResponse(**data)
        # Suppressed: no literary context should be falsely claimed
        pm_items = [item for item in sol.literary_context if item.source == "Project Madurai"]
        self.assertEqual(len(pm_items), 0, "Negative query produced ungrounded literary context")


if __name__ == "__main__":
    unittest.main()
