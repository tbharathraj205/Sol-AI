import unittest
from pathlib import Path
from backend.retrieval.engine import RetrievalEngine
from backend.schemas.result import UnifiedResult
from scripts.run_unified_benchmark import parse_benchmark_cases


class TestUnifiedBenchmark(unittest.TestCase):
    """
    Test suite for the Unified Benchmark execution and result schema integrity.
    """

    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parents[1]
        cls.benchmark_file = cls.project_root / "research" / "BENCHMARK.md"
        cls.cases = parse_benchmark_cases(cls.benchmark_file)
        cls.engine = RetrievalEngine()

    def test_benchmark_cases_parsed(self):
        """1. Verify that benchmark cases are successfully parsed from BENCHMARK.md."""
        self.assertGreater(len(self.cases), 50)
        case_ids = [c["id"] for c in self.cases]
        self.assertIn("L001", case_ids)
        self.assertIn("L038", case_ids)
        self.assertIn("M001", case_ids)

    def test_query_execution_and_schema_validity(self):
        """2. Test a sample of benchmark queries to verify crash-free execution and schema validity."""
        test_queries = ["வீடு", "மரங்களில்", "யாழ்", "அகதி", "கணினி"]
        for q in test_queries:
            result = self.engine.search(q)
            self.assertIsInstance(result, UnifiedResult)
            self.assertIsNotNone(result.query)
            self.assertIsNotNone(result.normalized_query)

            # Every resource attempted
            expected_resources = {
                "ThamizhiMorph",
                "Thani Thamizh Akarathi",
                "Tamil WordNet",
                "Tamil Wiktionary",
                "Sentamizh",
                "Project Madurai",
            }
            for res in expected_resources:
                self.assertIn(res, result.resource_summary)

            # Evidence provenance preserved
            for ev in result.evidence:
                self.assertIn(ev.source, expected_resources)

    def test_inflected_morphology_and_lemma_support(self):
        """3. Test inflected query (மரங்களில்) for lemma candidates and cross-resource support."""
        result = self.engine.search("மரங்களில்")
        self.assertIn("மரம்", result.lemma_candidates)
        self.assertIn("மரம்", result.cross_resource_support)
        self.assertIn("Tamil WordNet", result.cross_resource_support["மரம்"])


if __name__ == "__main__":
    unittest.main()
