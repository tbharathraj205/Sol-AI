"""
SOL AI — Tests for P2 Semantic Short-Circuit and Retrieval Performance.

Verifies:
TEST 1 — Exact lexical query skips semantic ('கால்' mock semantic adapter NOT called)
TEST 2 — Conceptual query invokes semantic ('கல்வியின் பெருமையும் கற்கும் முறையும்' mock semantic adapter IS called)
TEST 3 — Inflectional query remains deterministic ('மரங்களில்' -> 'மரம்' preserved)
TEST 4 — Semantic disabled explicitly (enable_semantic=False never invokes semantic)
TEST 5 — Semantic failure isolation (mocked semantic failure preserves deterministic results)
TEST 6 — Exact evidence preservation (metadata, retrieval_mode, source, lemma, passage unchanged)
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

# Setup path
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.retrieval.engine import RetrievalEngine
from backend.resources.project_madurai_semantic import ProjectMaduraiSemanticAdapter
from backend.schemas.evidence import Evidence


class TestSemanticShortCircuit(unittest.TestCase):
    """
    Test suite for P2 Semantic Retrieval Short-Circuit optimization.
    """

    def test_01_exact_lexical_query_skips_semantic(self):
        """
        TEST 1 — Exact lexical query skips semantic:
        Using high-frequency query 'கால்':
        - Deterministic retrieval produces saturated exact evidence (>=25 PM items)
        - Mocked semantic adapter is NOT called
        - UnifiedResult contains strong deterministic evidence
        """
        mock_semantic = MagicMock(spec=ProjectMaduraiSemanticAdapter)
        engine = RetrievalEngine(project_madurai_semantic=mock_semantic, enable_semantic=True)

        res = engine.search("கால்")

        # Semantic adapter MUST NOT be invoked
        mock_semantic.lookup.assert_not_called()

        # Deterministic evidence must be present
        self.assertEqual(res.normalized_query, "கால்")
        pm_evs = [
            e for e in res.evidence
            if e.source == "Project Madurai"
            and e.metadata.get("status") == "FOUND"
            and e.metadata.get("retrieval_method") == "exact"
        ]
        self.assertGreaterEqual(len(pm_evs), 25, "Project Madurai exact evidence should be saturated")

    def test_02_conceptual_query_invokes_semantic(self):
        """
        TEST 2 — Conceptual query invokes semantic:
        Using benchmark conceptual query 'கல்வியின் பெருமையும் கற்கும் முறையும்':
        - Deterministic evidence is insufficient (no exact stanzas)
        - Semantic adapter IS called
        """
        mock_semantic = MagicMock(spec=ProjectMaduraiSemanticAdapter)
        # Setup mock to return a valid semantic evidence object
        mock_semantic.lookup.return_value = [
            Evidence(
                surface="கல்வியின் பெருமையும் கற்கும் முறையும்",
                lemma=None,
                source="Project Madurai",
                evidence_type="literary_context",
                passage="கற்க கசடறக் கற்பவை கற்றபின்...",
                work="திருக்குறள்",
                author="திருவள்ளுவர்",
                source_id="PM-TK-391",
                metadata={
                    "status": "FOUND",
                    "retrieval_mode": "semantic",
                    "similarity_score": 0.88,
                    "chunk_id": "PM-TK-391",
                },
            )
        ]

        engine = RetrievalEngine(project_madurai_semantic=mock_semantic, enable_semantic=True)
        res = engine.search("கல்வியின் பெருமையும் கற்கும் முறையும்")

        # Semantic adapter MUST be invoked for conceptual query
        mock_semantic.lookup.assert_called_once()

        # Semantic evidence must be incorporated
        sem_evs = [
            e for e in res.evidence
            if e.source == "Project Madurai"
            and e.metadata.get("status") == "FOUND"
            and e.metadata.get("retrieval_mode") == "semantic"
        ]
        self.assertEqual(len(sem_evs), 1)
        self.assertAlmostEqual(sem_evs[0].metadata["similarity_score"], 0.88)

    def test_03_inflectional_query_remains_deterministic(self):
        """
        TEST 3 — Inflectional query remains deterministic:
        Query 'மரங்களில்':
        - ThamizhiMorph generates lemma 'மரம்'
        - Pass 2 resolves exact lemma evidence for 'மரம்'
        - Morphology is preserved and short-circuit does not interfere
        """
        mock_semantic = MagicMock(spec=ProjectMaduraiSemanticAdapter)
        engine = RetrievalEngine(project_madurai_semantic=mock_semantic, enable_semantic=True)

        res = engine.search("மரங்களில்")

        # Lemma 'மரம்' must be discovered
        self.assertIn("மரம்", res.lemma_candidates)

        # ThamizhiMorph evidence must be present
        tm_evs = [
            e for e in res.evidence
            if e.source == "ThamizhiMorph" and e.metadata.get("status") == "FOUND"
        ]
        self.assertGreater(len(tm_evs), 0, "ThamizhiMorph evidence missing")

        # Due to saturated exact matches for 'மரம்', semantic retrieval is skipped
        mock_semantic.lookup.assert_not_called()

    def test_04_semantic_disabled_explicitly(self):
        """
        TEST 4 — Semantic disabled explicitly:
        When enable_semantic=False:
        - Semantic lookup is NEVER executed even for conceptual query
        """
        mock_semantic = MagicMock(spec=ProjectMaduraiSemanticAdapter)
        engine = RetrievalEngine(project_madurai_semantic=mock_semantic, enable_semantic=False)

        res = engine.search("கல்வியின் பெருமையும் கற்கும் முறையும்")
        mock_semantic.lookup.assert_not_called()

        # Also test with per-call override enable_semantic=False
        engine2 = RetrievalEngine(project_madurai_semantic=mock_semantic, enable_semantic=True)
        res2 = engine2.search("கல்வியின் பெருமையும் கற்கும் முறையும்", enable_semantic=False)
        mock_semantic.lookup.assert_not_called()

    def test_05_semantic_failure_isolation(self):
        """
        TEST 5 — Semantic failure:
        Force semantic adapter failure (exception) on an unresolved query:
        - Deterministic retrieval continues without crashing
        - Engine gracefully returns valid UnifiedResult
        """
        mock_semantic = MagicMock(spec=ProjectMaduraiSemanticAdapter)
        mock_semantic.lookup.side_effect = RuntimeError("Simulated semantic pipeline failure")

        engine = RetrievalEngine(project_madurai_semantic=mock_semantic, enable_semantic=True)

        # Use an unresolved query where semantic lookup would be triggered
        res = engine.search("அரியவகைசொல்வேறுபாடற்றது")
        self.assertIsNotNone(res)
        self.assertEqual(res.normalized_query, "அரியவகைசொல்வேறுபாடற்றது")
        # Should not crash and semantic error is contained
        mock_semantic.lookup.assert_called_once()

    def test_06_exact_evidence_preservation(self):
        """
        TEST 6 — Exact evidence preservation:
        Verify the short-circuit does NOT alter:
        - retrieval_mode / retrieval_method
        - source
        - lemma
        - passage
        - metadata
        of deterministic evidence.
        """
        engine = RetrievalEngine(enable_semantic=True)
        res = engine.search("கால்")

        exact_pm_evs = [
            e for e in res.evidence
            if e.source == "Project Madurai"
            and e.metadata.get("status") == "FOUND"
        ]
        self.assertGreater(len(exact_pm_evs), 0)

        for ev in exact_pm_evs:
            self.assertEqual(ev.source, "Project Madurai")
            self.assertEqual(ev.evidence_type, "literary_context")
            self.assertIsNotNone(ev.passage)
            self.assertIsNotNone(ev.source_id)
            self.assertEqual(ev.metadata.get("retrieval_method"), "exact")
            self.assertNotEqual(ev.metadata.get("retrieval_mode"), "semantic")
            self.assertEqual(ev.metadata.get("status"), "FOUND")


if __name__ == "__main__":
    unittest.main()
