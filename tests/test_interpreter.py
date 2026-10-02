"""
Unit and Integration tests for SOL AI LLM Interpreter and EvidencePack builder.
Uses RetrievalEngine to fetch real deterministic evidence and verifies SOLResponse generation.
Includes mocked Gemini API network calls and exception assertions.
"""

import os
import json
import unittest
from unittest.mock import patch, MagicMock

from backend.retrieval.engine import RetrievalEngine
from backend.interpretation.evidence_pack import build_evidence_pack
from backend.interpretation.interpreter import (
    MockLLMInterpreter,
    GeminiLLMInterpreter,
    get_interpreter,
)
from backend.interpretation.schemas import SOLResponse


class TestInterpreter(unittest.TestCase):
    """
    Integration test suite for EvidencePack and LLM Interpreters.
    """

    @classmethod
    def setUpClass(cls):
        cls.engine = RetrievalEngine()
        cls.interpreter = MockLLMInterpreter()

    def test_marangalil_interpretation(self):
        """1. Test inflected word (மரங்களில்)."""
        retrieval_result = self.engine.search("மரங்களில்")
        pack = build_evidence_pack(retrieval_result, max_literary_contexts=5)

        self.assertIn("மரம்", pack.lemma_candidates)
        self.assertGreater(len(pack.morphology_evidence), 0)
        self.assertGreater(len(pack.literary_evidence), 0)

        response = self.interpreter.interpret(pack)
        self.assertIsInstance(response, SOLResponse)
        self.assertEqual(response.query, "மரங்களில்")
        self.assertEqual(response.lemma, "மரம்")
        self.assertIsNotNone(response.morphology)
        self.assertGreater(len(response.literary_context), 0)

        works = set(item.work for item in response.literary_context if item.work)
        self.assertGreater(len(works), 1)

    def test_marangalil_core_fst_priority(self):
        """1b. Regression test: CORE FST evidence must take priority over GUESSER evidence for மரங்களில்."""
        retrieval_result = self.engine.search("மரங்களில்")
        pack = build_evidence_pack(retrieval_result)

        first_ev = pack.morphology_evidence[0]
        self.assertEqual(first_ev.metadata.get("analysis_type"), "core")
        self.assertEqual(first_ev.metadata.get("fst_model"), "noun.fst")

        response = self.interpreter.interpret(pack)
        self.assertEqual(response.morphology.get("fst_model"), "noun.fst")
        self.assertEqual(response.morphology.get("analysis_type"), "core")

        guesser_items = [e for e in pack.morphology_evidence if e.metadata.get("analysis_type") == "guesser"]
        self.assertGreater(len(guesser_items), 0)

    def test_yaazh_interpretation(self):
        """2. Test classical literary word (யாழ்)."""
        retrieval_result = self.engine.search("யாழ்")
        pack = build_evidence_pack(retrieval_result, max_literary_contexts=5)

        self.assertGreater(len(pack.literary_evidence), 0)

        response = self.interpreter.interpret(pack)
        self.assertIsInstance(response, SOLResponse)
        self.assertEqual(response.query, "யாழ்")
        self.assertGreater(len(response.literary_context), 0)

        works = set(item.work for item in response.literary_context if item.work)
        self.assertGreater(len(works), 1)

    def test_agathi_interpretation(self):
        """3. Test purist dictionary word (அகதி)."""
        retrieval_result = self.engine.search("அகதி")
        pack = build_evidence_pack(retrieval_result, max_literary_contexts=5)

        self.assertGreater(len(pack.lexical_evidence), 0)

        response = self.interpreter.interpret(pack)
        self.assertIsInstance(response, SOLResponse)
        self.assertEqual(response.query, "அகதி")
        self.assertIsNotNone(response.meaning)
        self.assertIn(";", response.meaning)

    def test_agathi_no_false_core_provenance(self):
        """3b. Regression test: அகதி must never synthesize 'core' when no core FST model analyzed it."""
        retrieval_result = self.engine.search("அகதி")
        pack = build_evidence_pack(retrieval_result)
        response = self.interpreter.interpret(pack)

        if response.morphology:
            fst_model = response.morphology.get("fst_model")
            atype = response.morphology.get("analysis_type")
            if fst_model is None:
                self.assertNotEqual(atype, "core")
                self.assertEqual(atype, "lexical_mapping")

    def test_unknown_word_interpretation(self):
        """4. Test unknown word handling without fabrication (deterministic mode)."""
        query = "போலிசொல்வார்த்தை123"
        retrieval_result = self.engine.search(query, enable_semantic=False)
        pack = build_evidence_pack(retrieval_result)

        self.assertEqual(len(pack.morphology_evidence), 0)
        self.assertEqual(len(pack.lexical_evidence), 0)
        self.assertEqual(len(pack.literary_evidence), 0)

        response = self.interpreter.interpret(pack)
        self.assertIsInstance(response, SOLResponse)
        self.assertIsNone(response.lemma)
        self.assertIsNone(response.meaning)
        self.assertGreater(len(response.uncertainties), 0)
        self.assertIn("No evidence found", response.uncertainties[0])

    def test_conflicting_candidates_interpretation(self):
        """5. Test conflicting candidates visibility."""
        retrieval_result = self.engine.search("மரங்களில்")
        pack = build_evidence_pack(retrieval_result)

        if len(set(pack.lemma_candidates)) > 1:
            self.assertGreater(len(pack.conflicts), 0)
            response = self.interpreter.interpret(pack)
            conf_uncertainties = [u for u in response.uncertainties if "Conflict" in u]
            self.assertGreater(len(conf_uncertainties), 0)

    def test_missing_gemini_api_key_raises_value_error(self):
        """6. Test that missing GEMINI_API_KEY raises ValueError when Gemini provider is selected."""
        old_key = os.environ.pop("GEMINI_API_KEY", None)
        try:
            with self.assertRaises(ValueError):
                get_interpreter("gemini")
        finally:
            if old_key:
                os.environ["GEMINI_API_KEY"] = old_key

    @patch("urllib.request.urlopen")
    def test_gemini_interpreter_mocked_success(self, mock_urlopen):
        """7. Test GeminiLLMInterpreter with mocked successful HTTP response."""
        mock_resp_json = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": json.dumps({
                                    "query": "மரங்களில்",
                                    "normalized_query": "மரங்களில்",
                                    "lemma": "மரம்",
                                    "meaning": "மரங்களின் திரள்",
                                    "morphology": {"pos": "noun", "fst_model": "noun.fst", "analysis_type": "core"},
                                    "contextual_interpretation": "Mocked Gemini Response",
                                    "literary_context": [],
                                    "related_words": [],
                                    "sources": ["ThamizhiMorph"],
                                    "uncertainties": [],
                                    "evidence_summary": {"total_found": 1}
                                })
                            }
                        ]
                    }
                }
            ]
        }

        mock_cm = MagicMock()
        mock_cm.read.return_value = json.dumps(mock_resp_json).encode("utf-8")
        mock_cm.__enter__.return_value = mock_cm
        mock_urlopen.return_value = mock_cm

        gemini_interp = GeminiLLMInterpreter(api_key="test_dummy_key_12345")
        retrieval_result = self.engine.search("மரங்களில்")
        pack = build_evidence_pack(retrieval_result)
        response = gemini_interp.interpret(pack)

        self.assertIsInstance(response, SOLResponse)
        self.assertEqual(response.contextual_interpretation, "Mocked Gemini Response")
        self.assertEqual(response.lemma, "மரம்")

    @patch("urllib.request.urlopen")
    def test_gemini_interpreter_malformed_json_handling(self, mock_urlopen):
        """8. Test GeminiLLMInterpreter error handling when API returns malformed JSON."""
        mock_resp_json = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "Invalid non-json text"}]
                    }
                }
            ]
        }
        mock_cm = MagicMock()
        mock_cm.read.return_value = json.dumps(mock_resp_json).encode("utf-8")
        mock_cm.__enter__.return_value = mock_cm
        mock_urlopen.return_value = mock_cm

        gemini_interp = GeminiLLMInterpreter(api_key="test_dummy_key_12345")
        retrieval_result = self.engine.search("மரங்களில்")
        pack = build_evidence_pack(retrieval_result)

        with self.assertRaises(RuntimeError):
            gemini_interp.interpret(pack)


if __name__ == "__main__":
    unittest.main()
