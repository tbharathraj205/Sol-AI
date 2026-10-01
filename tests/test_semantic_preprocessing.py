"""
Comprehensive Test Suite for Semantic Preprocessing & Canonical Embedding-Text Construction.

Step 3A verification:
1. Cleaning:
   - Residual 'Back' navigation removal
   - 'திருச்சிற்றம்பலம் + Back' cleaning
   - Preservation of normal Tamil literary text
   - Email suppression
   - Publication source header suppression
   - Whitespace normalization preserving poetic lines
   - Tamil diacritic and character preservation
   - Zero-width character filtering
2. Eligibility:
   - Aathichudi aphorisms remain eligible
   - Konrai Vendhan aphorisms remain eligible
   - Tirukkural couplets remain eligible
   - Structural speaker attributions are suppressed ('speaker_attribution')
   - Musical stubs are suppressed ('musical_stub')
   - Webmaster contact is suppressed ('webmaster_contact')
   - Publication source header is suppressed ('publication_source_header')
   - Standalone navigation stubs are suppressed ('navigation_artifact')
3. Canonical embedding text:
   - Tirukkural receives chapter context
   - Tirukkural couplets formatted on a single line
   - Aathichudi does not receive author/work metadata
   - Konrai Vendhan does not receive author/work metadata
   - Valid Sangam/epic canto context is included
   - Generic fallback passages use clean passage text
   - No fabricated metadata appears
   - Suppressed chunks have embedding_text = None
4. Database immutability:
   - SQLite database is accessed strictly read-only
   - Database checksum, row count, and FTS tables remain completely untouched
5. Dynamic corpus statistics:
   - Dynamically calculated from madurai_exact.db without hardcoding
"""

import hashlib
import sqlite3
import unittest
from pathlib import Path

from backend.retrieval.semantic_preprocessing import (
    PASSAGE_PREFIX,
    QUERY_PREFIX,
    SemanticPreparation,
    clean_semantic_text,
    construct_canonical_embedding_text,
    get_corpus_statistics,
    is_eligible_for_semantic_index,
    prepare_chunk,
)


class TestSemanticTextCleaning(unittest.TestCase):
    """Unit tests for semantic passage cleaning and normalization."""

    def test_back_removal_alone(self):
        """Standalone 'Back' string cleans to empty text."""
        self.assertEqual(clean_semantic_text("Back"), "")
        self.assertEqual(clean_semantic_text("  Back  "), "")
        self.assertEqual(clean_semantic_text("[Back]"), "")
        self.assertEqual(clean_semantic_text("Back\n"), "")

    def test_thiruchitrambalam_and_back(self):
        """Thiruvasagam trailing 'திருச்சிற்றம்பலம் Back' preserves Tamil text and strips Back."""
        raw = "திருச்சிற்றம்பலம்\nBack"
        cleaned = clean_semantic_text(raw)
        self.assertEqual(cleaned, "திருச்சிற்றம்பலம்")

    def test_thiruchitrambalam_and_back_crlf(self):
        """Trailing Back with CRLF line endings is stripped correctly."""
        raw = "திருச்சிற்றம்பலம்\r\nBack"
        cleaned = clean_semantic_text(raw)
        self.assertEqual(cleaned, "திருச்சிற்றம்பலம்")

    def test_thiruchitrambalam_and_bracketed_back(self):
        """Trailing bracketed [Back] is stripped correctly."""
        raw = "திருச்சிற்றம்பலம்\n[Back]"
        cleaned = clean_semantic_text(raw)
        self.assertEqual(cleaned, "திருச்சிற்றம்பலம்")

    def test_poetic_passage_with_trailing_back(self):
        """Poetic verse ending in Back has only Back removed."""
        raw = "வான் வந்து மண் புகுந்து\nதிருச்சிற்றம்பலம்\nBack"
        cleaned = clean_semantic_text(raw)
        self.assertEqual(cleaned, "வான் வந்து மண் புகுந்து\nதிருச்சிற்றம்பலம்")

    def test_normal_english_back_preserved(self):
        """The word 'back' in the middle of arbitrary prose is NOT deleted."""
        prose = "He stepped back slowly and smiled."
        cleaned = clean_semantic_text(prose)
        self.assertEqual(cleaned, prose)

    def test_preservation_of_normal_tamil_poetry(self):
        """Meaningful poetic line breaks are preserved."""
        poem = (
            "நிலத்தினும் பெரிதே வானினும் உயர்ந்தன்று\n"
            "நீரினும் ஆரள வின்றே சாரல்\n"
            "கருங்கோற் குறிஞ்சிப் பூக்கொண்டு\n"
            "பெருந்தேன் இழைக்கும் நாடனொடு நட்பே."
        )
        cleaned = clean_semantic_text(poem)
        self.assertEqual(cleaned, poem)
        self.assertEqual(len(cleaned.splitlines()), 4)

    def test_whitespace_normalization(self):
        """Repeated spaces and tabs within lines are condensed; empty lines omitted."""
        raw = "அறம்   செய\t\tவிரும்பு.\n\n\nஆறுவது   சினம்."
        cleaned = clean_semantic_text(raw)
        self.assertEqual(cleaned, "அறம் செய விரும்பு.\nஆறுவது சினம்.")

    def test_zero_width_character_filtering(self):
        """Zero-width Unicode characters (ZWSP, ZWNJ, ZWJ, BOM) are completely removed."""
        raw = "ம\u200Bர\u200Cம்\u200D \uFEFFவளர்ப்போம்"
        cleaned = clean_semantic_text(raw)
        self.assertEqual(cleaned, "மரம் வளர்ப்போம்")
        self.assertNotIn("\u200B", cleaned)
        self.assertNotIn("\u200C", cleaned)
        self.assertNotIn("\u200D", cleaned)
        self.assertNotIn("\uFEFF", cleaned)

    def test_tamil_diacritics_preservation(self):
        """Tamil vowels, consonants, combining marks, and aytham are preserved."""
        chars = "அஆஇஈஉஊஎஏஐஒஓஔ ஃ க் கா கி கீ கு கூ கெ கே கை கொ கோ கௌ"
        cleaned = clean_semantic_text(chars)
        self.assertEqual(cleaned, chars)

    def test_none_and_empty_handling(self):
        """None, empty string, and whitespace-only strings return empty string."""
        self.assertEqual(clean_semantic_text(None), "")
        self.assertEqual(clean_semantic_text(""), "")
        self.assertEqual(clean_semantic_text("   \n\t  "), "")


class TestSemanticEligibility(unittest.TestCase):
    """Unit tests for semantic index eligibility classification."""

    def test_aathichudi_aphorisms_remain_eligible(self):
        """Autonomous didactic aphorisms in Aathichudi must be eligible."""
        chunk = {
            "chunk_id": "PM-AATHI-0002",
            "work": "ஆத்திசூடி",
            "author": "ஔவையார்",
            "genre": "Didactic",
            "original_text": "அறம் செய விரும்பு.",
        }
        prep = prepare_chunk(chunk)
        self.assertTrue(prep.eligible)
        self.assertIsNone(prep.suppression_reason)
        self.assertEqual(prep.cleaned_text, "அறம் செய விரும்பு.")
        self.assertEqual(prep.embedding_text, "passage: அறம் செய விரும்பு.")

    def test_konrai_vendhan_aphorisms_remain_eligible(self):
        """Autonomous didactic aphorisms in Konrai Vendhan must be eligible."""
        chunk = {
            "chunk_id": "PM-KONRAI-0002",
            "work": "கொன்றை வேந்தன்",
            "author": "ஔவையார்",
            "genre": "Didactic",
            "original_text": "அன்னையும் பிதாவும் முன்னறி தெய்வம்.",
        }
        prep = prepare_chunk(chunk)
        self.assertTrue(prep.eligible)
        self.assertIsNone(prep.suppression_reason)
        self.assertEqual(prep.cleaned_text, "அன்னையும் பிதாவும் முன்னறி தெய்வம்.")
        self.assertEqual(prep.embedding_text, "passage: அன்னையும் பிதாவும் முன்னறி தெய்வம்.")

    def test_tirukkural_couplets_remain_eligible(self):
        """Tirukkural couplets must remain eligible."""
        chunk = {
            "chunk_id": "PM-TK-0001",
            "work": "திருக்குறள்",
            "author": "திருவள்ளுவர்",
            "genre": "Didactic",
            "chapter": "கடவுள் வாழ்த்து",
            "original_text": "அகர முதல எழுத்தெல்லாம் ஆதி\nபகவன் முதற்றே உலகு.",
        }
        prep = prepare_chunk(chunk)
        self.assertTrue(prep.eligible)
        self.assertIsNone(prep.suppression_reason)
        self.assertIsNotNone(prep.embedding_text)

    def test_webmaster_contact_suppressed(self):
        """Webmaster contact chunk PM-SILAP_MADURAI-0003 is suppressed."""
        chunk = {
            "chunk_id": "PM-SILAP_MADURAI-0003",
            "work": "சிலப்பதிகாரம் - மதுரைக்காண்டம்",
            "original_text": "மேலதிக உதவிக்குத் தொடர்புகொள்ள வேண்டிய முகவரி  kalyan@geocities.com",
        }
        prep = prepare_chunk(chunk)
        self.assertFalse(prep.eligible)
        self.assertEqual(prep.suppression_reason, "webmaster_contact")
        self.assertIsNone(prep.embedding_text)

    def test_publication_source_header_suppressed(self):
        """Publication source header chunk PM-CHINTHAMANI-0003 is suppressed."""
        chunk = {
            "chunk_id": "PM-CHINTHAMANI-0003",
            "work": "சீவக சிந்தாமணி - சுருக்கம்",
            "original_text": 'Source:\n"சீவகசிந்தாமணி - சுருக்கம்"\nPublished by: The South India Saiva Siddhanta Works',
        }
        prep = prepare_chunk(chunk)
        self.assertFalse(prep.eligible)
        self.assertEqual(prep.suppression_reason, "publication_source_header")
        self.assertIsNone(prep.embedding_text)

    def test_speaker_attribution_kootru_suppressed(self):
        """Colophons / speaker attributions like 'குறிஞ்சி - தோழி கூற்று' are suppressed."""
        chunk = {
            "chunk_id": "PM-KURU-0003",
            "work": "குறுந்தொகை",
            "original_text": "குறிஞ்சி - தோழி கூற்று",
        }
        prep = prepare_chunk(chunk)
        self.assertFalse(prep.eligible)
        self.assertEqual(prep.suppression_reason, "speaker_attribution")
        self.assertIsNone(prep.embedding_text)

    def test_speaker_attribution_solliyathu_suppressed(self):
        """Colophons ending in 'சொல்லியது' are suppressed."""
        chunk = {
            "chunk_id": "PM-NATR-0007",
            "work": "நற்றிணை",
            "original_text": "பிரிவு உணர்த்திய தோழிக்குத் தலைவி சொல்லியது",
        }
        prep = prepare_chunk(chunk)
        self.assertFalse(prep.eligible)
        self.assertEqual(prep.suppression_reason, "speaker_attribution")
        self.assertIsNone(prep.embedding_text)

    def test_musical_stub_suppressed(self):
        """Musical mode metadata stubs like 'பண் - நட்டபாடை' are suppressed."""
        chunk = {
            "chunk_id": "PM-THEVARAM_1-0306",
            "work": "தேவாரம் - முதல் திருமுறை (பாகம் 1)",
            "original_text": "பண் - நட்டபாடை",
        }
        prep = prepare_chunk(chunk)
        self.assertFalse(prep.eligible)
        self.assertEqual(prep.suppression_reason, "musical_stub")
        self.assertIsNone(prep.embedding_text)

    def test_musical_stub_thakkaragam_suppressed(self):
        """Musical mode metadata stubs like 'பண் - தக்கராகம்' are suppressed."""
        chunk = {
            "chunk_id": "PM-THEVARAM_1-0378",
            "work": "தேவாரம் - முதல் திருமுறை (பாகம் 1)",
            "original_text": "பண் - தக்கராகம்",
        }
        prep = prepare_chunk(chunk)
        self.assertFalse(prep.eligible)
        self.assertEqual(prep.suppression_reason, "musical_stub")

    def test_structural_metadata_thinai_poet_suppressed(self):
        """Thinai - poet stubs in Natrinai are suppressed."""
        chunk = {
            "chunk_id": "PM-NATR-0005",
            "work": "நற்றிணை",
            "original_text": "1 குறிஞ்சி - கபிலர்",
        }
        prep = prepare_chunk(chunk)
        self.assertFalse(prep.eligible)
        self.assertEqual(prep.suppression_reason, "structural_metadata")

    def test_structural_metadata_toc_etext_suppressed(self):
        """TOC entries with e-text publication labels are suppressed."""
        chunk = {
            "chunk_id": "PM-THEVARAM_1-0003",
            "work": "தேவாரம் - முதல் திருமுறை (பாகம் 1)",
            "original_text": "1    திருப்பிரமபுரம்   (1-11)   மின்பதிப்பு",
        }
        prep = prepare_chunk(chunk)
        self.assertFalse(prep.eligible)
        self.assertEqual(prep.suppression_reason, "structural_metadata")

    def test_standalone_back_navigation_suppressed(self):
        """A chunk consisting solely of a navigation anchor is suppressed."""
        chunk = {
            "chunk_id": "PM-TEST-BACK",
            "work": "சோதனை",
            "original_text": "Back",
        }
        prep = prepare_chunk(chunk)
        self.assertFalse(prep.eligible)
        self.assertEqual(prep.suppression_reason, "navigation_artifact")
        self.assertIsNone(prep.embedding_text)


class TestCanonicalEmbeddingText(unittest.TestCase):
    """Unit tests for canonical embedding passage construction."""

    def test_tirukkural_receives_chapter_context(self):
        """Tirukkural receives 'passage: அதிகாரம்: {chapter}. {couplet}' with single line."""
        chunk = {
            "chunk_id": "PM-TK-0001",
            "work": "திருக்குறள்",
            "chapter": "கடவுள் வாழ்த்து",
            "original_text": "அகர முதல எழுத்தெல்லாம் ஆதி\nபகவன் முதற்றே உலகு.",
        }
        prep = prepare_chunk(chunk)
        expected = (
            "passage: அதிகாரம்: கடவுள் வாழ்த்து. "
            "அகர முதல எழுத்தெல்லாம் ஆதி பகவன் முதற்றே உலகு."
        )
        self.assertEqual(prep.embedding_text, expected)

    def test_tirukkural_without_chapter_falls_back_gracefully(self):
        """Tirukkural with missing chapter does not invent chapter context."""
        chunk = {
            "chunk_id": "PM-TK-0001",
            "work": "திருக்குறள்",
            "chapter": None,
            "original_text": "அகர முதல எழுத்தெல்லாம் ஆதி\nபகவன் முதற்றே உலகு.",
        }
        prep = prepare_chunk(chunk)
        expected = "passage: அகர முதல எழுத்தெல்லாம் ஆதி பகவன் முதற்றே உலகு."
        self.assertEqual(prep.embedding_text, expected)

    def test_aathichudi_does_not_receive_author_or_work_metadata(self):
        """Aathichudi embeds the aphorism directly with no author/work prefix."""
        chunk = {
            "chunk_id": "PM-AATHI-0002",
            "work": "ஆத்திசூடி",
            "author": "ஔவையார்",
            "genre": "Didactic",
            "original_text": "அறம் செய விரும்பு.",
        }
        prep = prepare_chunk(chunk)
        self.assertEqual(prep.embedding_text, "passage: அறம் செய விரும்பு.")
        self.assertNotIn("ஔவையார்", prep.embedding_text)
        self.assertNotIn("ஆத்திசூடி", prep.embedding_text)

    def test_konrai_does_not_receive_author_or_work_metadata(self):
        """Konrai Vendhan embeds the aphorism directly with no author/work prefix."""
        chunk = {
            "chunk_id": "PM-KONRAI-0002",
            "work": "கொன்றை வேந்தன்",
            "author": "ஔவையார்",
            "genre": "Didactic",
            "original_text": "அன்னையும் பிதாவும் முன்னறி தெய்வம்.",
        }
        prep = prepare_chunk(chunk)
        self.assertEqual(prep.embedding_text, "passage: அன்னையும் பிதாவும் முன்னறி தெய்வம்.")
        self.assertNotIn("ஔவையார்", prep.embedding_text)
        self.assertNotIn("கொன்றை", prep.embedding_text)

    def test_sangam_epic_with_valid_canto_includes_context(self):
        """Sangam / Epic passage with valid canto prepends 'passage: {canto}: {cleaned_text}'."""
        chunk = {
            "chunk_id": "PM-SILAP_VANJI-0037",
            "work": "சிலப்பதிகாரம் - வஞ்சிக்காண்டம்",
            "period": "Epic",
            "genre": "Epic Poetry",
            "canto": "25. காட்சிக் காதை",
            "original_text": "மாநீர் வேலிக் கடம்பெறிந்து இமயத்து\nவானவர் மருள மலைவிற் பூட்டிய",
        }
        prep = prepare_chunk(chunk)
        expected = (
            "passage: 25. காட்சிக் காதை: மாநீர் வேலிக் கடம்பெறிந்து இமயத்து\n"
            "வானவர் மருள மலைவிற் பூட்டிய"
        )
        self.assertEqual(prep.embedding_text, expected)

    def test_sangam_epic_without_canto_uses_clean_passage(self):
        """Sangam / Epic passage without canto does not invent context."""
        chunk = {
            "chunk_id": "PM-KURU-0004",
            "work": "குறுந்தொகை",
            "period": "Sangam",
            "genre": "Sangam Akam Poetry",
            "canto": None,
            "original_text": "செங்களம் படக்கொன் றவுணர்த் தேய்த்த\nசெங்கோ லம்பிற் செங்கோட்டி யானை",
        }
        prep = prepare_chunk(chunk)
        expected = "passage: செங்களம் படக்கொன் றவுணர்த் தேய்த்த\nசெங்கோ லம்பிற் செங்கோட்டி யானை"
        self.assertEqual(prep.embedding_text, expected)

    def test_generic_fallback_passage(self):
        """Generic passage uses 'passage: {cleaned_text}' without fabricated metadata."""
        chunk = {
            "chunk_id": "PM-NALADI-0009",
            "work": "நாலடியார்",
            "author": "சமண முனிவர்கள்",
            "period": "Post-Sangam / Didactic",
            "genre": "Didactic",
            "canto": None,
            "chapter": "1 செல்வம் நிலையாமை",
            "original_text": "அறுசுவை யுண்டி அமர்ந்தில்லாள் ஊட்ட\nமறுசிகை நீக்கியுண் டாரும்",
        }
        prep = prepare_chunk(chunk)
        expected = "passage: அறுசுவை யுண்டி அமர்ந்தில்லாள் ஊட்ட\nமறுசிகை நீக்கியுண் டாரும்"
        self.assertEqual(prep.embedding_text, expected)
        self.assertNotIn("சமண முனிவர்கள்", prep.embedding_text)
        self.assertNotIn("நாலடியார்", prep.embedding_text)

    def test_constants_definitions(self):
        """Verify constant definitions for future compatibility."""
        self.assertEqual(PASSAGE_PREFIX, "passage: ")
        self.assertEqual(QUERY_PREFIX, "query: ")


class TestDatabaseImmutabilityAndStatistics(unittest.TestCase):
    """Tests ensuring database read-only immutability and accurate statistics."""

    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parents[1]
        cls.db_path = cls.project_root / "data" / "processed" / "madurai_exact.db"
        if not cls.db_path.exists():
            raise unittest.SkipTest(f"Database file missing: {cls.db_path}")

        # Compute initial hash
        with open(cls.db_path, "rb") as f:
            cls.initial_hash = hashlib.sha256(f.read()).hexdigest()
        cls.initial_mtime = cls.db_path.stat().st_mtime

    def test_database_is_not_modified_by_statistics(self):
        """Calculating corpus statistics leaves madurai_exact.db bit-for-bit identical."""
        stats = get_corpus_statistics(self.db_path)

        # Re-check file hash and mtime
        with open(self.db_path, "rb") as f:
            final_hash = hashlib.sha256(f.read()).hexdigest()
        final_mtime = self.db_path.stat().st_mtime

        self.assertEqual(self.initial_hash, final_hash, "Database SHA-256 changed!")
        self.assertEqual(self.initial_mtime, final_mtime, "Database mtime changed!")

        # Verify statistics return expected structure
        self.assertIn("total_chunks", stats)
        self.assertIn("eligible_chunks", stats)
        self.assertIn("suppressed_chunks", stats)
        self.assertIn("length_distribution", stats)
        self.assertIn("suppression_reasons", stats)

        self.assertEqual(stats["total_chunks"], stats["eligible_chunks"] + stats["suppressed_chunks"])
        self.assertGreater(stats["total_chunks"], 10000)
        self.assertGreater(stats["eligible_chunks"], 10000)
        self.assertGreater(stats["suppressed_chunks"], 0)

    def test_all_51_thiruvasagam_back_chunks_cleaned_in_db(self):
        """All 51 Thiruvasagam chunks with Back in the real DB clean perfectly."""
        uri = f"file:{self.db_path.as_posix()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.cursor()
            cur.execute("SELECT chunk_id, original_text FROM chunks WHERE original_text LIKE '%Back%';")
            back_rows = cur.fetchall()
        finally:
            conn.close()

        self.assertEqual(len(back_rows), 51, f"Expected 51 chunks with Back, found {len(back_rows)}")
        for r in back_rows:
            cleaned = clean_semantic_text(r["original_text"])
            self.assertNotIn("Back", cleaned)
            self.assertTrue(cleaned.endswith("திருச்சிற்றம்பலம்"))

    def test_real_db_webmaster_chunk_is_suppressed(self):
        """PM-SILAP_MADURAI-0003 in the real database is suppressed for webmaster contact."""
        uri = f"file:{self.db_path.as_posix()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM chunks WHERE chunk_id = 'PM-SILAP_MADURAI-0003';")
            row = cur.fetchone()
        finally:
            conn.close()

        self.assertIsNotNone(row)
        prep = prepare_chunk(row)
        self.assertFalse(prep.eligible)
        self.assertEqual(prep.suppression_reason, "webmaster_contact")
        self.assertIsNone(prep.embedding_text)

    def test_real_db_publication_source_chunk_is_suppressed(self):
        """PM-CHINTHAMANI-0003 in the real database is suppressed for publication header."""
        uri = f"file:{self.db_path.as_posix()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM chunks WHERE chunk_id = 'PM-CHINTHAMANI-0003';")
            row = cur.fetchone()
        finally:
            conn.close()

        self.assertIsNotNone(row)
        prep = prepare_chunk(row)
        self.assertFalse(prep.eligible)
        self.assertEqual(prep.suppression_reason, "publication_source_header")
        self.assertIsNone(prep.embedding_text)


if __name__ == "__main__":
    unittest.main()
