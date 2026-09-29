import unittest
from backend.retrieval.engine import RetrievalEngine
from backend.schemas.result import UnifiedResult


class TestUnifiedRetrieval(unittest.TestCase):
    """
    Integration & Regression test suite for SOL AI Unified Retrieval Engine & Evidence Aggregator.
    Verifies strict status filtering, zero false cross-resource attributions, and candidate-only data handling.
    """

    @classmethod
    def setUpClass(cls):
        cls.engine = RetrievalEngine()

    def test_inflected_word_marangalil(self):
        """1. Test inflected word (மரங்களில்)."""
        result = self.engine.search("மரங்களில்")
        self.assertIsInstance(result, UnifiedResult)
        self.assertEqual(result.normalized_query, "மரங்களில்")

        # Candidate lemmas must contain 'மரம்'
        self.assertIn("மரம்", result.lemma_candidates)

        # ThamizhiMorph and WordNet must return FOUND status evidence
        tm_evs = [e for e in result.evidence if e.source == "ThamizhiMorph" and e.metadata.get("status") == "FOUND"]
        wn_evs = [e for e in result.evidence if e.source == "Tamil WordNet" and e.metadata.get("status") == "FOUND"]
        self.assertGreater(len(tm_evs), 0)
        self.assertGreater(len(wn_evs), 0)

        # Cross-resource support for lemma 'மரம்' must include ThamizhiMorph, Tamil WordNet, and Sentamizh
        self.assertIn("மரம்", result.cross_resource_support)
        sources = result.cross_resource_support["மரம்"]
        self.assertIn("ThamizhiMorph", sources)
        self.assertIn("Tamil WordNet", sources)
        self.assertIn("Sentamizh", sources)

        # Akarathi does not directly match the inflected surface form,
        # but it now provides evidence for the resolved lemma 'மரம்'.
        self.assertNotIn(
            "Thani Thamizh Akarathi",
            result.cross_resource_support.get("மரங்களில்", [])
        )
        self.assertIn(
            "Thani Thamizh Akarathi",
            result.cross_resource_support.get("மரம்", [])
        )
        
    def test_literary_word_yaazh(self):
        """2. Test classical literary word (யாழ்)."""
        result = self.engine.search("யாழ்")
        self.assertEqual(result.normalized_query, "யாழ்")

        # Sentamizh and ThamizhiMorph return FOUND evidence
        sentamizh_evs = [e for e in result.evidence if e.source == "Sentamizh" and e.metadata.get("status") == "FOUND"]
        tm_evs = [e for e in result.evidence if e.source == "ThamizhiMorph" and e.metadata.get("status") == "FOUND"]
        self.assertGreater(len(sentamizh_evs), 0)
        self.assertGreater(len(tm_evs), 0)

        sources = result.cross_resource_support.get("யாழ்", [])
        self.assertIn("Sentamizh", sources)
        self.assertIn("ThamizhiMorph", sources)

        # WordNet is still not expected, but Akarathi now provides evidence.
        self.assertNotIn("Tamil WordNet", sources)
        self.assertIn("Thani Thamizh Akarathi", sources)

    def test_purist_dictionary_word_agathi(self):
        """3. Test purist dictionary word (அகதி)."""
        result = self.engine.search("அகதி")
        self.assertEqual(result.normalized_query, "அகதி")

        akarathi_evs = [e for e in result.evidence if e.source == "Thani Thamizh Akarathi" and e.metadata.get("status") == "FOUND"]
        wn_evs = [e for e in result.evidence if e.source == "Tamil WordNet" and e.metadata.get("status") == "FOUND"]
        self.assertGreaterEqual(len(akarathi_evs), 2)
        self.assertGreaterEqual(len(wn_evs), 1)

        sources = result.cross_resource_support.get("அகதி", [])
        self.assertIn("Thani Thamizh Akarathi", sources)
        self.assertIn("Tamil WordNet", sources)

        # Sentamizh returned NOT_FOUND and MUST NOT appear in cross_resource_support
        self.assertNotIn("Sentamizh", sources)

    def test_unknown_word_no_false_support(self):
        """4. Test unknown word to ensure no false cross-resource support attributions."""
        query = "போலிசொல்வார்த்தை123"
        result = self.engine.search(query)
        self.assertIsInstance(result, UnifiedResult)

        # All resources attempted and in summary with NOT_FOUND status
        for res in ["ThamizhiMorph", "Tamil WordNet", "Thani Thamizh Akarathi", "Sentamizh"]:
            self.assertEqual(result.resource_summary[res]["status"], "NOT_FOUND")

        # cross_resource_support MUST be completely empty for unknown query
        self.assertEqual(len(result.cross_resource_support), 0)

    def test_candidate_only_not_counted_as_evidence(self):
        """5. Test that candidate-only information without FOUND evidence is not counted."""
        query = "போலிசொல்வார்த்தை123"
        result = self.engine.search(query)
        found_evs = [e for e in result.evidence if e.metadata.get("status") == "FOUND"]
        self.assertEqual(len(found_evs), 0)


if __name__ == "__main__":
    unittest.main()
