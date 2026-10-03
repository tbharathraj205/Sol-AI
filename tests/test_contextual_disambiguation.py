"""
Unit and Integration tests for P1 Context-Aware Word-Sense Disambiguation (WSD).

Verifies:
TEST 1: Real demo sentence 'அவனுடைய தம்பி கால் கிலோ மாம்பழம் வாங்கி வந்தான்.'
        with query 'கால்' selects fractional / quarter-kilogram sense, NOT physical foot.
TEST 2: Same word 'கால்' with physical-foot context selects physical foot/leg sense.
TEST 3: SAME QUERY, DIFFERENT CONTEXT produces different contextual meanings:
        response_physical.contextual_meaning != response_kilo.contextual_meaning.
TEST 4: General quantity unit generalization: verifies 'கால்' collocated with 'லிட்டர்',
        'மீட்டர்', 'மணி', and 'பகுதி' all select fractional quantity senses.
TEST 5: General meaning ('meaning') remains distinct and contains multiple documented senses,
        not collapsed into or forced identical to 'contextual_meaning'.
TEST 6: Context absent (context=None) leaves contextual_meaning None, retaining general meaning.
TEST 7: Context irrelevant leaves contextual_meaning None and documents ambiguity in uncertainties.
TEST 8: Inflected query 'மரங்களில்' undergoes ThamizhiMorph analysis to 'மரம்' while preserving context.
TEST 9: Direct MockLLMInterpreter execution with EvidencePack verifies contextual meaning synthesis.
"""

import os
import unittest
from pathlib import Path

from backend.retrieval.engine import RetrievalEngine
from backend.interpretation.evidence_pack import build_evidence_pack
from backend.interpretation.interpreter import MockLLMInterpreter
from backend.interpretation.schemas import SOLResponse
from backend.sol_django.api.services import SOLServiceRegistry


class TestContextualDisambiguation(unittest.TestCase):
    """
    Test suite verifying Context-Aware Word-Sense Disambiguation for Tamil polysemy.
    """

    @classmethod
    def setUpClass(cls):
        cls.engine = RetrievalEngine()
        cls.interpreter = MockLLMInterpreter()
        cls.service = SOLServiceRegistry.get_instance()

        cls.CONTEXT_REAL_DEMO_KILO = "அவனுடைய தம்பி கால் கிலோ மாம்பழம் வாங்கி வந்தான்."
        cls.CONTEXT_PHYSICAL = "அவன் கல்லில் நடக்கும்போது கால் வழுக்கி கீழே விழுந்தான்."
        cls.CONTEXT_FRACTION = "இந்த நிலத்தின் கால் பகுதி மட்டுமே பயிரிடப்பட்டுள்ளது."
        cls.CONTEXT_LITER = "கால் லிட்டர் பால் வாங்கினேன்."
        cls.CONTEXT_METER = "கால் மீட்டர் துணி வாங்கினான்."
        cls.CONTEXT_TIME = "கால் மணி நேரம் காத்திருந்தேன்."
        cls.CONTEXT_IRRELEVANT = "அவர் கால் என்று சொன்னார்."

    def test_01_real_demo_kaal_kilo(self):
        """
        TEST 1 — CRITICAL REAL DEMO SENTENCE:
        'அவனுடைய தம்பி கால் கிலோ மாம்பழம் வாங்கி வந்தான்.' with query 'கால்'
        MUST return the fractional / one-fourth kilogram sense (நான்கில் ஒரு பங்கு / ¼ kg),
        and MUST NOT return the physical foot/leg sense (உடல் உறுப்பு).
        """
        response = self.service.process_query(
            query="கால்",
            provider="mock",
            context=self.CONTEXT_REAL_DEMO_KILO,
        )

        self.assertIsInstance(response, SOLResponse)
        self.assertIsNotNone(
            response.contextual_meaning,
            "CRITICAL DEMO FAILURE: contextual_meaning must not be None for real demo sentence!"
        )

        # Contextual meaning must unambiguously reflect one-fourth / quarter
        self.assertIn(
            "நான்கில் ஒரு பங்கு",
            response.contextual_meaning,
            f"Expected 'நான்கில் ஒரு பங்கு' in contextual_meaning, got: {response.contextual_meaning}"
        )
        self.assertTrue(
            "கிலோ" in response.contextual_meaning or "¼" in response.contextual_meaning or "1/4" in response.contextual_meaning,
            f"Expected unit/fraction reference in contextual_meaning, got: {response.contextual_meaning}"
        )

        # MUST NOT identify physical body organ
        self.assertNotIn(
            "உடல் உறுப்பு",
            response.contextual_meaning,
            f"CRITICAL DEMO REGRESSION: contextual_meaning must not refer to body organ! Got: {response.contextual_meaning}"
        )

    def test_02_physical_foot_meaning(self):
        """
        TEST 2 — Physical foot context selects physical foot/leg sense.
        """
        response = self.service.process_query(
            query="கால்",
            provider="mock",
            context=self.CONTEXT_PHYSICAL,
        )

        self.assertIsInstance(response, SOLResponse)
        self.assertIsNotNone(response.contextual_meaning)
        # Verify the contextual meaning corresponds to the physical foot/body organ sense
        self.assertTrue(
            "உடல் உறுப்பு" in response.contextual_meaning or
            "பாதம்" in response.contextual_meaning or
            "நடக்கவோ" in response.contextual_meaning,
            f"Expected physical foot/leg sense, got: {response.contextual_meaning}"
        )
        # Ensure it did NOT incorrectly choose the fractional sense
        self.assertNotIn("நான்கில் ஒரு பங்கு", response.contextual_meaning)

    def test_03_same_query_different_context_different_senses(self):
        """
        TEST 3 — PRIMARY DEMO REQUIREMENT:
        The SAME query 'கால்' with different surrounding sentences MUST produce
        different contextual meanings.
        """
        response_phys = self.service.process_query(
            query="கால்",
            provider="mock",
            context=self.CONTEXT_PHYSICAL,
        )
        response_kilo = self.service.process_query(
            query="கால்",
            provider="mock",
            context=self.CONTEXT_REAL_DEMO_KILO,
        )

        self.assertIsNotNone(response_phys.contextual_meaning)
        self.assertIsNotNone(response_kilo.contextual_meaning)

        # Core assertion: Different contexts MUST produce different contextual meanings
        self.assertNotEqual(
            response_phys.contextual_meaning,
            response_kilo.contextual_meaning,
            "CRITICAL FAILURE: Both contexts produced identical contextual meaning!"
        )

        # Verify sense semantics
        self.assertIn("உடல் உறுப்பு", response_phys.contextual_meaning)
        self.assertIn("நான்கில் ஒரு பங்கு", response_kilo.contextual_meaning)

    def test_04_quantity_unit_generalization(self):
        """
        TEST 4 — Generic quantity / unit / classifier generalization:
        Verifies that any quantity unit collocated with 'கால்' correctly selects
        fractional quantity sense without word-specific hardcoding.
        """
        cases = [
            ("liter", self.CONTEXT_LITER, "லிட்டர்"),
            ("meter", self.CONTEXT_METER, "மீட்டர்"),
            ("time", self.CONTEXT_TIME, "மணி"),
            ("partition", self.CONTEXT_FRACTION, "பகுதி"),
        ]

        for label, context, expected_token in cases:
            with self.subTest(unit=label):
                resp = self.service.process_query(
                    query="கால்",
                    provider="mock",
                    context=context,
                )
                self.assertIsNotNone(resp.contextual_meaning, f"Failed for {label}")
                self.assertIn(
                    "நான்கில் ஒரு பங்கு",
                    resp.contextual_meaning,
                    f"Expected fractional sense for {label}, got: {resp.contextual_meaning}"
                )
                self.assertIn(
                    expected_token,
                    resp.contextual_meaning,
                    f"Expected {expected_token} in gloss for {label}, got: {resp.contextual_meaning}"
                )
                self.assertNotIn(
                    "உடல் உறுப்பு",
                    resp.contextual_meaning,
                    f"Physical foot sense incorrectly selected for {label}"
                )

    def test_05_general_meaning_remains_separate(self):
        """
        TEST 5 — General meaning ('meaning') retains all documented dictionary senses
        and is NOT collapsed into or forced identical to 'contextual_meaning'.
        """
        response = self.service.process_query(
            query="கால்",
            provider="mock",
            context=self.CONTEXT_REAL_DEMO_KILO,
        )

        self.assertIsNotNone(response.meaning)
        self.assertIsNotNone(response.contextual_meaning)

        # General meaning contains multiple documented senses separated by semicolons
        self.assertIn(";", response.meaning)
        self.assertIn("உடல் உறுப்பு", response.meaning)
        self.assertIn("நான்கில் ஒரு பங்கு", response.meaning)

        # General meaning must NOT be identical to the selected single contextual meaning
        self.assertNotEqual(response.meaning, response.contextual_meaning)

    def test_06_context_absent_leaves_contextual_meaning_none(self):
        """
        TEST 6 — When context is absent (context=None), the system must NOT invent certainty.
        contextual_meaning must be None while general documented meaning is preserved.
        """
        response = self.service.process_query(
            query="கால்",
            provider="mock",
            context=None,
        )

        self.assertIsNone(response.contextual_meaning)
        self.assertIsNotNone(response.meaning)
        self.assertIn("உடல் உறுப்பு", response.meaning)

    def test_07_context_irrelevant_handles_ambiguity(self):
        """
        TEST 7 — When context contains the word but does not provide sufficient discriminative
        clues, the system must NOT pretend certainty.
        """
        response = self.service.process_query(
            query="கால்",
            provider="mock",
            context=self.CONTEXT_IRRELEVANT,
        )

        # contextual_meaning should be None when context lacks discriminative evidence
        self.assertIsNone(response.contextual_meaning)
        # Explicit ambiguity notice should be documented in uncertainties
        ambiguity_noted = any("ambiguity" in u.lower() or "context" in u.lower() for u in response.uncertainties)
        self.assertTrue(ambiguity_noted, f"Expected ambiguity note in uncertainties, got: {response.uncertainties}")

    def test_08_inflected_word_thamizhimorph_and_context(self):
        """
        TEST 8 — Inflected word 'மரங்களில்' resolves to lemma 'மரம்' via ThamizhiMorph,
        and user context is preserved through EvidencePack.
        """
        context = "தோட்டத்தில் உள்ள மரங்களில் பறவைகள் அமர்ந்துள்ளன."
        response = self.service.process_query(
            query="மரங்களில்",
            provider="mock",
            context=context,
        )

        self.assertEqual(response.query, "மரங்களில்")
        self.assertEqual(response.lemma, "மரம்")
        self.assertIsNotNone(response.morphology)
        self.assertEqual(response.morphology.get("pos"), "noun")
        self.assertTrue(len(response.sources) > 0)

    def test_09_direct_mock_interpreter_wsd(self):
        """
        TEST 9 — Direct MockLLMInterpreter execution with EvidencePack verifies
        contextual meaning and interpretation synthesis.
        """
        retrieval_res = self.engine.search("கால்")
        pack_phys = build_evidence_pack(retrieval_res, query_context=self.CONTEXT_PHYSICAL)
        pack_kilo = build_evidence_pack(retrieval_res, query_context=self.CONTEXT_REAL_DEMO_KILO)

        resp_phys = self.interpreter.interpret(pack_phys)
        resp_kilo = self.interpreter.interpret(pack_kilo)

        self.assertNotEqual(resp_phys.contextual_meaning, resp_kilo.contextual_meaning)
        self.assertIn("உடல் உறுப்பு", resp_phys.contextual_meaning)
        self.assertIn("நான்கில் ஒரு பங்கு", resp_kilo.contextual_meaning)

        # Contextual interpretation synthesizes the specific context
        self.assertIn(self.CONTEXT_PHYSICAL, resp_phys.contextual_interpretation)
        self.assertIn(self.CONTEXT_REAL_DEMO_KILO, resp_kilo.contextual_interpretation)

    def test_10_general_meaning_matches_web_app_and_is_context_independent(self):
        """
        TEST 10 — REGRESSION TEST:
        General Meaning matches the web app's existing meaning representation:
        - Web app consumes `data.meaning.split(';').map(s => s.trim()).filter(Boolean)`
        - Web app preserves the top 2 senses (displayed as '2 Senses Preserved' for 'கால்'):
          Sense 1: 'மாந்தர்கள் உட்பட விலங்குகளின் ஓர் உடல் உறுப்பு. இது தரையில் ஊன்றி நடக்கவோ, நகரவோ பயன்படுவது.'
          Sense 2: 'ஒன்றை ஈடாகப் பங்கிட்ட நான்கில் ஒரு பங்கு (அரையில் பாதி)' (with \frac{1}{4})
        - General Meaning is 100% stable and context-independent across all sentences:
          changing the sentence does NOT alter General Meaning.
        """
        context_a = "அவள் கால் கிலோ சர்க்கரை வாங்கினாள்."
        context_b = "அவனுடைய கால் வலிக்கிறது."
        context_c = "நாற்காலியின் கால் உடைந்தது."

        resp_a = self.service.process_query(query="கால்", provider="mock", context=context_a)
        resp_b = self.service.process_query(query="கால்", provider="mock", context=context_b)
        resp_c = self.service.process_query(query="கால்", provider="mock", context=context_c)
        resp_none = self.service.process_query(query="கால்", provider="mock", context=None)

        for label, resp in [("Context A", resp_a), ("Context B", resp_b), ("Context C", resp_c), ("No Context", resp_none)]:
            self.assertIsNotNone(resp.meaning, f"{label} returned empty meaning")
            raw_senses = [s.strip() for s in resp.meaning.split(";") if s.strip()]
            preserved_senses = raw_senses[:2]  # Web app MeaningCard.jsx slice(0, 2)
            self.assertEqual(
                len(preserved_senses),
                2,
                f"Expected exactly 2 preserved senses for 'கால்' matching web app, got: {len(preserved_senses)}"
            )
            # Sense 1: Physical foot/leg definition
            self.assertIn("உடல் உறுப்பு", preserved_senses[0])
            self.assertIn("நடக்கவோ", preserved_senses[0])
            # Sense 2: Quarter / fractional definition
            self.assertIn("நான்கில் ஒரு பங்கு", preserved_senses[1])

        # Identity across all contexts: changing sentence does not alter General Meaning
        self.assertEqual(resp_a.meaning, resp_b.meaning)
        self.assertEqual(resp_b.meaning, resp_c.meaning)
        self.assertEqual(resp_c.meaning, resp_none.meaning)

    def test_11_three_distinct_contexts_disambiguate_accurately(self):
        """
        TEST 11 — ACCURATE CONTEXTUAL DISAMBIGUATION ACROSS THREE CONTEXTS:
        - Context A ('அவள் கால் கிலோ சர்க்கரை வாங்கினாள்.') -> நான்கில் ஒரு பங்கு / 1/4
        - Context B ('அவனுடைய கால் வலிக்கிறது.') -> உடல் உறுப்பு / பாதம்
        - Context C ('நாற்காலியின் கால் உடைந்தது.') -> நாற்காலியைத் தாங்கும் பகுதி
        """
        context_a = "அவள் கால் கிலோ சர்க்கரை வாங்கினாள்."
        context_b = "அவனுடைய கால் வலிக்கிறது."
        context_c = "நாற்காலியின் கால் உடைந்தது."

        resp_a = self.service.process_query(query="கால்", provider="mock", context=context_a)
        resp_b = self.service.process_query(query="கால்", provider="mock", context=context_b)
        resp_c = self.service.process_query(query="கால்", provider="mock", context=context_c)

        # All three must produce non-None contextual meaning
        self.assertIsNotNone(resp_a.contextual_meaning)
        self.assertIsNotNone(resp_b.contextual_meaning)
        self.assertIsNotNone(resp_c.contextual_meaning)

        # Context A: fractional / quarter
        self.assertIn("நான்கில் ஒரு பங்கு", resp_a.contextual_meaning)
        self.assertNotIn("உடல் உறுப்பு", resp_a.contextual_meaning)

        # Context B: somatic / physical body organ
        self.assertTrue(
            "உடல் உறுப்பு" in resp_b.contextual_meaning or "பாதம்" in resp_b.contextual_meaning,
            f"Expected anatomical sense for Context B, got: {resp_b.contextual_meaning}"
        )
        self.assertNotIn("நான்கில் ஒரு பங்கு", resp_b.contextual_meaning)

        # Context C: furniture / structural support
        self.assertTrue(
            "நாற்காலி" in resp_c.contextual_meaning or "தாங்கும் பகுதி" in resp_c.contextual_meaning,
            f"Expected furniture sense for Context C, got: {resp_c.contextual_meaning}"
        )
        self.assertNotIn("நான்கில் ஒரு பங்கு", resp_c.contextual_meaning)

        # All three contextual meanings must be mutually distinct
        self.assertNotEqual(resp_a.contextual_meaning, resp_b.contextual_meaning)
        self.assertNotEqual(resp_b.contextual_meaning, resp_c.contextual_meaning)
        self.assertNotEqual(resp_a.contextual_meaning, resp_c.contextual_meaning)


if __name__ == "__main__":
    unittest.main()
