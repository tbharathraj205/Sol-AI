import unittest
from backend.schemas.evidence import Evidence
from backend.resources.thamizhimorph import ThamizhiMorphAdapter


class TestThamizhiMorphAdapter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.adapter = ThamizhiMorphAdapter()

    def test_known_noun(self):
        query = "மரங்களில்"
        evidences = self.adapter.lookup(query)
        self.assertIsInstance(evidences, list)
        self.assertGreaterEqual(len(evidences), 1)

        first_ev = evidences[0]
        self.assertIsInstance(first_ev, Evidence)
        self.assertEqual(first_ev.surface, query)
        self.assertEqual(first_ev.source, "ThamizhiMorph")
        self.assertEqual(first_ev.lemma, "மரம்")
        self.assertEqual(first_ev.pos, "noun")
        self.assertIn("raw_foma_output", first_ev.metadata)
        self.assertIn("fst_model", first_ev.metadata)

    def test_inflected_noun(self):
        query = "மரத்தை"
        evidences = self.adapter.lookup(query)
        self.assertGreaterEqual(len(evidences), 1)
        lemmas = [ev.lemma for ev in evidences if ev.lemma]
        self.assertIn("மரம்", lemmas)

    def test_known_verb(self):
        query = "வந்தார்கள்"
        evidences = self.adapter.lookup(query)
        self.assertGreaterEqual(len(evidences), 1)
        lemmas = [ev.lemma for ev in evidences if ev.lemma]
        self.assertIn("வா", lemmas)
        self.assertEqual(evidences[0].pos, "verb")

    def test_complex_verb(self):
        query = "சென்றுகொண்டிருந்தான்"
        evidences = self.adapter.lookup(query)
        self.assertGreaterEqual(len(evidences), 1)
        first_ev = evidences[0]
        self.assertEqual(first_ev.surface, query)
        self.assertEqual(first_ev.source, "ThamizhiMorph")
        self.assertIsNotNone(first_ev.lemma)

    def test_ambiguity_preservation(self):
        query = "வந்தார்கள்"
        evidences = self.adapter.lookup(query)
        # Came (he/she honorific) vs Came (they plural)
        self.assertGreaterEqual(len(evidences), 2)
        raw_outputs = [ev.metadata.get("raw_foma_output") for ev in evidences]
        self.assertEqual(len(raw_outputs), len(set(raw_outputs)))

    def test_unknown_word_safety(self):
        query = "xyz_unknown_nonword_123"
        evidences = self.adapter.lookup(query)
        self.assertEqual(len(evidences), 1)
        ev = evidences[0]
        self.assertEqual(ev.surface, query)
        self.assertIsNone(ev.lemma)
        self.assertEqual(ev.metadata.get("normalization_status"), "UNKNOWN")


    def test_parse_structured_morphology_noun_locative_plural(self):
        from backend.resources.thamizhimorph import parse_structured_morphology
        sm = parse_structured_morphology(
            query="மரங்களில்",
            pos="noun",
            raw_morphology="noun+pl+loc",
            fst_model="noun.fst",
            analysis_type="core",
        )
        self.assertEqual(sm.pos, "noun")
        self.assertEqual(sm.case, "Locative")
        self.assertEqual(sm.number, "Plural")
        self.assertIsNone(sm.tense)
        self.assertEqual(sm.fst_model, "noun.fst")
        self.assertEqual(sm.analysis_type, "core")
        self.assertEqual(sm.raw_morphology, "noun+pl+loc")
        self.assertEqual(len(sm.segments), 1)
        self.assertEqual(sm.segments[0].tamil, "மரங்களில்")
        self.assertEqual(sm.segments[0].role, "noun + pl + loc")

        # Dict access and compatibility checks
        self.assertEqual(sm.get("case"), "Locative")
        self.assertEqual(sm["number"], "Plural")
        self.assertIn("pos", sm)

    def test_parse_structured_morphology_noun_accusative_singular(self):
        from backend.resources.thamizhimorph import parse_structured_morphology
        sm = parse_structured_morphology(
            query="மரத்தை",
            pos="noun",
            raw_morphology="noun+sg+acc",
            fst_model="noun.fst",
        )
        self.assertEqual(sm.pos, "noun")
        self.assertEqual(sm.case, "Accusative")
        self.assertEqual(sm.number, "Singular")
        self.assertIsNone(sm.tense)

    def test_parse_structured_morphology_verb_past_tense(self):
        from backend.resources.thamizhimorph import parse_structured_morphology
        sm = parse_structured_morphology(
            query="வந்தார்கள்",
            pos="verb",
            raw_morphology="verb+fin+sim+strong+past=த்+3sghe=ஆர்கள்",
            fst_model="verb-c12.fst",
        )
        self.assertEqual(sm.pos, "verb")
        self.assertEqual(sm.tense, "Past")
        self.assertEqual(sm.number, "Singular")
        self.assertIsNone(sm.case)

    def test_parse_structured_morphology_empty_or_unknown(self):
        from backend.resources.thamizhimorph import parse_structured_morphology
        sm = parse_structured_morphology(
            query="போலி",
            pos=None,
            raw_morphology=None,
            fst_model=None,
        )
        self.assertIsNone(sm.pos)
        self.assertIsNone(sm.case)
        self.assertIsNone(sm.number)
        self.assertIsNone(sm.tense)
        self.assertEqual(sm.analysis_type, "lexical_mapping")
        self.assertEqual(sm.segments, [])

    def test_parse_structured_morphology_guesser(self):
        from backend.resources.thamizhimorph import parse_structured_morphology
        sm = parse_structured_morphology(
            query="ஏதோ",
            pos=None,
            raw_morphology="noun+sg+nom",
            fst_model="noun-guess.fst",
        )
        self.assertEqual(sm.pos, "noun")
        self.assertEqual(sm.case, "Nominative")
        self.assertEqual(sm.number, "Singular")
        self.assertEqual(sm.analysis_type, "guesser")


if __name__ == "__main__":
    unittest.main()
