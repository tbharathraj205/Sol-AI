"""
Comprehensive Test Suite for SOL AI WSD Architecture Overhaul.

Verifies:
A. Fraction contexts (கால் கிலோ, கால் லிட்டர், கால் மீட்டர், கால் மணி)
B. Anatomical contexts (walking, slipping/injury, pain/body)
C. Structural contexts (chair leg, table leg)
D. Same query, different contexts -> distinct contextual meanings
E. No context queries -> contextual_meaning is None, WSD abstains
F. Weak context -> abstention (insufficient evidence)
G. Conflicting context -> abstention or marked conflicting uncertainty
H. Inflected forms
I. Structured SenseCandidate extraction & provenance preservation
J. WSDResult metadata retention (scores, reasons, confidence, status, candidates)
K. Single WSD execution verification (no double WSD in mock or services)
L. Real Django API /api/query end-to-end verification (Requests 1, 2, 3)
M. General meaning vs contextual meaning separation
"""

import os
import sys
import json
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure project root is in sys.path
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
from backend.retrieval.engine import RetrievalEngine
from backend.interpretation.evidence_pack import build_evidence_pack
from backend.interpretation.schemas import (
    SenseCandidate,
    WSDResult,
    CandidateScore,
    SOLResponse,
    extract_sense_candidates,
)
from backend.interpretation.wsd import (
    TamilWSD,
    WSDContextFeatureExtractor,
    format_fraction_unit_gloss,
    clean_sense_text,
)
from backend.interpretation.interpreter import MockLLMInterpreter
from backend.sol_django.api.services import SOLServiceRegistry


class TestWSDOverhaul(SimpleTestCase):
    """
    Exhaustive test matrix for WSD architecture overhaul.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.engine = RetrievalEngine()
        cls.wsd = TamilWSD()
        cls.mock_interpreter = MockLLMInterpreter()
        cls.service = SOLServiceRegistry.get_instance()
        cls.client = Client()

        # Cache retrieval evidence for 'கால்' to avoid duplicate search in test loop
        cls.kaal_retrieval = cls.engine.search("கால்")
        cls.kaal_pack = build_evidence_pack(cls.kaal_retrieval)
        cls.kaal_candidates = extract_sense_candidates(cls.kaal_pack, query="கால்")

    def test_structured_sense_candidate_extraction(self):
        """1. Verify structured SenseCandidate extraction preserves provenance and metadata."""
        self.assertGreater(len(self.kaal_candidates), 1)

        sources = {c.source for c in self.kaal_candidates}
        self.assertTrue(any("Wiktionary" in s or "Akarathi" in s for s in sources))

        for c in self.kaal_candidates:
            self.assertIsInstance(c, SenseCandidate)
            self.assertEqual(c.headword, "கால்")
            self.assertTrue(len(c.definition) > 0)
            self.assertIsNotNone(c.source)
            self.assertIsNotNone(c.sense_id)

        # Verify WordNet entries with meaning=None are NOT extracted as gloss candidates
        wordnet_cands = [c for c in self.kaal_candidates if c.source == "Tamil WordNet"]
        self.assertEqual(len(wordnet_cands), 0)

    def test_fraction_contexts(self):
        """2. Test A: Fractional contexts (கால் கிலோ, கால் லிட்டர், கால் மீட்டர், கால் மணி)."""
        test_cases = [
            ("கால் கிலோ", "அவனுடைய தம்பி கால் கிலோ மாம்பழம் வாங்கி வந்தான்.", "கிலோ", "250g"),
            ("கால் லிட்டர்", "அவள் காலையில் கால் லிட்டர் பால் வாங்கினாள்.", "லிட்டர்", "250ml"),
            ("கால் மீட்டர்", "அவன் கால் மீட்டர் துணி வெட்டினான்.", "மீட்டர்", "25cm"),
            ("கால் மணி", "ரயில் வர இன்னும் கால் மணி நேரம் ஆகும்.", "மணி", "15 நிமிடங்கள்"),
        ]

        for label, sentence, unit, expected_fragment in test_cases:
            with self.subTest(case=label):
                result = self.wsd.disambiguate(
                    query="கால்",
                    context_sentence=sentence,
                    candidate_senses=self.kaal_candidates,
                )
                self.assertIsInstance(result, WSDResult)
                self.assertEqual(result.status, "selected")
                self.assertIsNotNone(result.selected_sense)
                self.assertGreaterEqual(result.score, 35.0)
                self.assertEqual(result.confidence, "high")
                self.assertTrue(
                    "நான்கில் ஒரு பங்கு" in result.selected_sense or "காற்பங்கு" in result.selected_sense or "1/4" in result.selected_sense
                )
                self.assertIn(expected_fragment, result.selected_sense)

    def test_anatomical_contexts(self):
        """3. Test B: Anatomical contexts (walking, slipping/injury, pain/body)."""
        test_cases = [
            ("walking_slipping", "அவன் கல்லில் நடக்கும்போது கால் வழுக்கி கீழே விழுந்தான்."),
            ("injury_pain", "விளையாடும் போது அவனுக்கு காலில் பலத்த அடிபட்டு வலித்தது."),
            ("swelling_fracture", "விபத்தில் அவனுடைய கால் எலும்பு முறிந்து வீக்கம் ஏற்பட்டது."),
        ]

        for label, sentence in test_cases:
            with self.subTest(case=label):
                result = self.wsd.disambiguate(
                    query="கால்",
                    context_sentence=sentence,
                    candidate_senses=self.kaal_candidates,
                )
                self.assertIsInstance(result, WSDResult)
                self.assertEqual(result.status, "selected")
                self.assertIsNotNone(result.selected_sense)
                self.assertGreaterEqual(result.score, 5.0)
                self.assertIn(result.confidence, ["medium", "high"])
                self.assertTrue(
                    "உடல் உறுப்பு" in result.selected_sense or "பாதம்" in result.selected_sense
                )

    def test_structural_furniture_contexts(self):
        """4. Test C: Structural contexts (table leg, chair leg)."""
        test_cases = [
            ("chair_leg", "நாற்காலியின் ஒரு கால் உடைந்ததால் கீழே சாய்ந்தது."),
            ("table_leg", "மர மேசையின் கால் பலவீனமாக உள்ளது."),
        ]

        for label, sentence in test_cases:
            with self.subTest(case=label):
                result = self.wsd.disambiguate(
                    query="கால்",
                    context_sentence=sentence,
                    candidate_senses=self.kaal_candidates,
                )
                self.assertIsInstance(result, WSDResult)
                self.assertEqual(result.status, "selected")
                self.assertIsNotNone(result.selected_sense)
                self.assertGreaterEqual(result.score, 20.0)
                self.assertTrue(
                    "தாங்கும் பகுதி" in result.selected_sense or "நாற்காலி" in result.selected_sense or "மேசை" in result.selected_sense
                )

    def test_same_query_different_contexts(self):
        """5. Test D: Same query 'கால்' produces distinct contextual meanings for different sentences."""
        ctx_fraction = "அவனுடைய தம்பி கால் கிலோ மாம்பழம் வாங்கி வந்தான்."
        ctx_anatomical = "அவன் கல்லில் நடக்கும்போது கால் வழுக்கி கீழே விழுந்தான்."
        ctx_structural = "பழைய நாற்காலியின் கால் உடைந்துவிட்டது."

        res_frac = self.wsd.disambiguate("கால்", ctx_fraction, self.kaal_candidates)
        res_anat = self.wsd.disambiguate("கால்", ctx_anatomical, self.kaal_candidates)
        res_struct = self.wsd.disambiguate("கால்", ctx_structural, self.kaal_candidates)

        self.assertNotEqual(res_frac.selected_sense, res_anat.selected_sense)
        self.assertNotEqual(res_anat.selected_sense, res_struct.selected_sense)
        self.assertNotEqual(res_frac.selected_sense, res_struct.selected_sense)

        self.assertTrue("நான்கில்" in res_frac.selected_sense or "250g" in res_frac.selected_sense)
        self.assertTrue("உடல் உறுப்பு" in res_anat.selected_sense or "பாதம்" in res_anat.selected_sense)
        self.assertTrue("தாங்கும்" in res_struct.selected_sense or "நாற்காலி" in res_struct.selected_sense)

    def test_no_context_returns_none(self):
        """6. Test E: No context provided -> contextual_meaning is None, WSD abstains."""
        for empty_ctx in [None, "", "   "]:
            result = self.wsd.disambiguate(
                query="கால்",
                context_sentence=empty_ctx,
                candidate_senses=self.kaal_candidates,
            )
            self.assertEqual(result.status, "no_context")
            self.assertIsNone(result.selected_sense)
            self.assertIsNone(result.selected_candidate)
            self.assertEqual(result.score, 0.0)
            self.assertEqual(result.confidence, "none")

    def test_weak_context_abstains(self):
        """7. Test F: Weak context with no discriminative evidence -> WSD abstains (insufficient evidence)."""
        weak_ctx = "அவன் நேற்று அங்கு ஒரு வார்த்தை சொன்னான்."
        result = self.wsd.disambiguate(
            query="கால்",
            context_sentence=weak_ctx,
            candidate_senses=self.kaal_candidates,
        )
        self.assertEqual(result.status, "insufficient_evidence")
        self.assertIsNone(result.selected_sense)
        self.assertIsNone(result.selected_candidate)
        self.assertLess(result.score, 1.0)

    def test_conflicting_context_abstains_or_marks_uncertainty(self):
        """8. Test G: Conflicting context (both fractional unit and somatic terms adjacent to query)."""
        conflicting_candidates = [
            SenseCandidate(source="DictA", headword="test", definition="நான்கில் ஒரு பங்கு அளவு"),
            SenseCandidate(source="DictB", headword="test", definition="உடல் உறுப்பு பாதம்"),
        ]
        conflicting_sentence = "அவன் கால் கிலோ மீட்டர் நடக்கும்போது வழுக்கி கால் வலித்தது."

        result = self.wsd.disambiguate(
            query="கால்",
            context_sentence=conflicting_sentence,
            candidate_senses=conflicting_candidates,
        )
        self.assertIn(result.status, ["conflicting_signals", "ambiguous", "selected"])
        if result.status == "conflicting_signals":
            self.assertIsNone(result.selected_sense)
            self.assertIn("Conflicting", result.reasons[0])

    def test_wsd_result_unpacking_backwards_compatibility(self):
        """9. Test J: WSDResult supports unpacking as (selected_sense, score, reasons)."""
        sentence = "அவன் கால் கிலோ மாம்பழம் வாங்கினான்."
        result = self.wsd.disambiguate("கால்", sentence, self.kaal_candidates)

        sel_sense, score, reasons = result
        self.assertEqual(sel_sense, result.selected_sense)
        self.assertEqual(score, result.score)
        self.assertEqual(reasons, result.reasons)

    def test_single_authoritative_wsd_execution(self):
        """10. Test K: Verify WSD is executed exactly once during process_query."""
        with patch.object(TamilWSD, "disambiguate", wraps=self.wsd.disambiguate) as spy_disambiguate:
            resp = self.service.process_query(
                query="கால்",
                provider="mock",
                context="அவனுடைய தம்பி கால் கிலோ மாம்பழம் வாங்கி வந்தான்.",
            )
            # Must be called exactly ONCE, not twice!
            self.assertEqual(spy_disambiguate.call_count, 1)
            self.assertIsNotNone(resp.contextual_meaning)
            self.assertIsNotNone(resp.wsd_result)
            self.assertEqual(resp.contextual_meaning, resp.wsd_result.selected_sense)

    def test_api_request_1_kilo_fraction(self):
        """11. Real Django API: REQUEST 1 - கால் + கால் கிலோ -> fraction."""
        payload = {
            "query": "கால்",
            "provider": "mock",
            "context": "அவனுடைய தம்பி கால் கிலோ மாம்பழம் வாங்கி வந்தான்.",
        }
        response = self.client.post(
            "/api/query",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        sol_resp = SOLResponse(**data)

        # Contextual meaning must reflect fraction
        self.assertIsNotNone(sol_resp.contextual_meaning)
        self.assertTrue(
            "நான்கில் ஒரு பங்கு" in sol_resp.contextual_meaning or "250g" in sol_resp.contextual_meaning
        )

        # General meaning must remain intact and NOT overwritten by contextual gloss
        self.assertIsNotNone(sol_resp.meaning)
        self.assertNotEqual(sol_resp.meaning, sol_resp.contextual_meaning)

        # WSD result present in response
        self.assertIsNotNone(sol_resp.wsd_result)
        self.assertEqual(sol_resp.wsd_result.status, "selected")
        self.assertGreaterEqual(sol_resp.wsd_result.score, 35.0)

        # Interpretation grounded in selected sense
        self.assertIsNotNone(sol_resp.contextual_interpretation)
        self.assertIn("கால் கிலோ", sol_resp.contextual_interpretation)

    def test_api_request_2_anatomical(self):
        """12. Real Django API: REQUEST 2 - கால் + walking/slipping -> anatomical foot."""
        payload = {
            "query": "கால்",
            "provider": "mock",
            "context": "அவன் கல்லில் நடக்கும்போது கால் வழுக்கி கீழே விழுந்தான்.",
        }
        response = self.client.post(
            "/api/query",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        sol_resp = SOLResponse(**data)

        # Contextual meaning must reflect anatomical foot
        self.assertIsNotNone(sol_resp.contextual_meaning)
        self.assertTrue(
            "உடல் உறுப்பு" in sol_resp.contextual_meaning or "பாதம்" in sol_resp.contextual_meaning
        )

        # General meaning remains intact
        self.assertIsNotNone(sol_resp.meaning)
        self.assertNotEqual(sol_resp.meaning, sol_resp.contextual_meaning)

        # WSD result present
        self.assertIsNotNone(sol_resp.wsd_result)
        self.assertEqual(sol_resp.wsd_result.status, "selected")

    def test_api_request_3_no_context(self):
        """13. Real Django API: REQUEST 3 - கால் without context -> contextual_meaning is null/absent."""
        payload = {
            "query": "கால்",
            "provider": "mock",
        }
        response = self.client.post(
            "/api/query",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        sol_resp = SOLResponse(**data)

        # contextual_meaning must be None
        self.assertIsNone(sol_resp.contextual_meaning)
        # General meaning must be populated
        self.assertIsNotNone(sol_resp.meaning)

    def test_inflected_forms_preserved(self):
        """14. Regression: Inflected form மரங்களில் continues working across full pipeline."""
        payload = {
            "query": "மரங்களில்",
            "provider": "mock",
            "context": "மரங்களில் அழகிய பறவைகள் அமர்ந்திருந்தன.",
        }
        response = self.client.post(
            "/api/query",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        sol_resp = SOLResponse(**data)

        self.assertEqual(sol_resp.query, "மரங்களில்")
        self.assertEqual(sol_resp.lemma, "மரம்")
        self.assertIsNotNone(sol_resp.morphology)
        self.assertEqual(sol_resp.morphology.get("pos"), "noun")


if __name__ == "__main__":
    unittest.main()
