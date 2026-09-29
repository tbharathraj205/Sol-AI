import unittest
from backend.schemas.evidence import Evidence
from backend.resources.akarathi import ThaniThamizhAkarathiAdapter


class TestThaniThamizhAkarathiAdapter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.adapter = ThaniThamizhAkarathiAdapter()

    def test_known_exact_headword(self):
        query = "மனிதன்"
        evidences = self.adapter.lookup(query)
        self.assertIsInstance(evidences, list)
        self.assertGreaterEqual(len(evidences), 2)

        source_files = {e.metadata.get("source_file") for e in evidences}

        self.assertIn("plain_text_dicts/Pav_Words.txt", source_files)
        self.assertIn("search/ம/மனிதன்", source_files)

        ev = evidences[0]
        self.assertIsInstance(ev, Evidence)
        self.assertEqual(ev.surface, query)
        self.assertEqual(ev.lemma, "மனிதன்")
        self.assertEqual(ev.source, "Thani Thamizh Akarathi")
        self.assertEqual(ev.evidence_type, "lexical")
        self.assertEqual(ev.meaning, "மாந்தன்")
        self.assertEqual(ev.metadata.get("status"), "FOUND")

    def test_headword_with_multiple_meanings(self):
        query = "அந்தரங்கம்"
        evidences = self.adapter.lookup(query)
        self.assertGreaterEqual(len(evidences), 1)
        meanings = [ev.meaning for ev in evidences if ev.meaning]
        self.assertTrue(any("மருமம்" in m or "அருமறை" in m for m in meanings))

    def test_repeated_headword_across_dictionaries(self):
        query = "அகதி"
        evidences = self.adapter.lookup(query)
        # Should return entries from both Pav_Words and Neelambigai Ammaiyar dictionaries
        self.assertGreaterEqual(len(evidences), 2)

        source_files = [ev.metadata.get("source_file") for ev in evidences]
        self.assertTrue(any("Pav_Words.txt" in sf for sf in source_files))
        self.assertTrue(any("Neelambigai" in sf for sf in source_files))

        # Check meanings were preserved independently
        meanings = [ev.meaning for ev in evidences]
        self.assertIn("ஏதிலி", meanings)
        self.assertIn("வறியன், யாருமற்றவன்", meanings)

    def test_missing_word_safety(self):
        query = "xyz_missing_word_999"
        evidences = self.adapter.lookup(query)
        self.assertEqual(len(evidences), 1)
        ev = evidences[0]
        self.assertEqual(ev.surface, query)
        self.assertIsNone(ev.lemma)
        self.assertIsNone(ev.meaning)
        self.assertEqual(ev.metadata.get("status"), "NOT_FOUND")

    def test_tamil_unicode_handling(self):
        query = "அக்கினி நட்சத்திரம்"
        evidences = self.adapter.lookup(query)
        self.assertGreaterEqual(len(evidences), 1)
        self.assertEqual(evidences[0].surface, query)
        self.assertIn(evidences[0].meaning, ["எரிநாள்", "தீநாள்"])


if __name__ == "__main__":
    unittest.main()
