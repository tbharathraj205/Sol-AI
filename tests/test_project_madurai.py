"""
Comprehensive Test Suite for Project Madurai Exact Retrieval.

Covers:
1. Corpus build (manifest loading, NFC normalization, original text preservation, deterministic IDs, idempotence)
2. FTS5 exact retrieval (Tamil combining marks, diacritics preservation, query safety against syntax injection, deterministic ordering, SQL limit)
3. ProjectMaduraiExactAdapter (Evidence contract, source, evidence_type, provenance, NOT_FOUND/ERROR handling, no fabricated lemmas)
4. End-to-end integration against the real generated corpus with RetrievalEngine (மரம், மரங்களில், அகத்தி, யாழ், மனிதன், செய்)
"""

import os
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from backend.schemas.evidence import Evidence
from backend.resources.project_madurai import ProjectMaduraiExactAdapter, sanitize_fts_query
from backend.retrieval.engine import RetrievalEngine
from scripts.build_madurai_index import (
    normalize_tamil_text,
    clean_html_tags,
    parse_generic_stanzas,
    parse_tirukkural,
    init_database,
    insert_chunks,
    TAMIL_FTS5_TOKENIZER,
)


class TestProjectMaduraiCorpusBuild(unittest.TestCase):
    """Tests for Project Madurai corpus ingestion, parsing, and normalization."""

    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parents[1]
        cls.manifest_path = cls.project_root / "data" / "raw" / "project_madurai" / "manifest.json"

    def test_manifest_loads_and_has_required_fields(self):
        """Manifest loads, contains 30-50 works, and has all required metadata fields."""
        self.assertTrue(self.manifest_path.exists(), f"Manifest file missing: {self.manifest_path}")
        with open(self.manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        self.assertIn("works", manifest)
        works = manifest["works"]
        self.assertGreaterEqual(len(works), 30)
        self.assertLessEqual(len(works), 50)

        required_fields = ["work", "work_id", "release_no", "source_url", "author", "period", "genre", "encoding"]
        for w in works:
            for field in required_fields:
                self.assertIn(field, w, f"Work {w.get('work_id')} missing field: {field}")
                self.assertIsNotNone(w[field], f"Work {w.get('work_id')} field {field} is None")

    def test_nfc_normalization_and_zero_width_filtering(self):
        """NFC normalization handles decomposed characters and removes zero-width artifacts."""
        # Decomposed Tamil text with zero-width characters: \u200B (ZWSP), \u200C (ZWNJ), \u200D (ZWJ), \uFEFF (BOM)
        raw_text = "ம\u200Bர\u200Cம்\u200D \uFEFFவளர்ப்போம்"
        cleaned = normalize_tamil_text(raw_text)
        self.assertNotIn("\u200B", cleaned)
        self.assertNotIn("\u200C", cleaned)
        self.assertNotIn("\u200D", cleaned)
        self.assertNotIn("\uFEFF", cleaned)
        self.assertEqual(cleaned, "மரம் வளர்ப்போம்")

    def test_original_text_preservation(self):
        """Original poetic line breaks and traditional layout are strictly preserved."""
        raw_poem = """
        நிலத்தினும் பெரிதே வானினும் உயர்ந்தன்று
        நீரினும் ஆரள வின்றே சாரல்
        கருங்கோற் குறிஞ்சிப் பூக்கொண்டு
        பெருந்தேன் இழைக்கும் நாடனொடு நட்பே.
        """
        cleaned_lines = clean_html_tags(raw_poem.strip())
        norm_lines = normalize_tamil_text(cleaned_lines)
        # Verify lines are intact (not flattened to a single line)
        self.assertIn("\n", cleaned_lines)
        self.assertEqual(len(cleaned_lines.strip().splitlines()), 4)

    def test_deterministic_chunk_ids(self):
        """Chunk IDs follow the PM-{WORK_ID}-{STANZA:04d} convention and are stable."""
        meta = {
            "work_id": "KURU",
            "work": "குறுந்தொகை",
            "author": "கபிலர்",
            "period": "Sangam",
            "genre": "Sangam Akam Poetry",
            "release_no": "PM0110",
            "source_url": "https://example.com"
        }
        text = "1. குறிஞ்சி\nபாடல் வரிகள் ஒன்று\nபாடல் வரிகள் இரண்டு\n\n2. முல்லை\nமுல்லை வரிகள் ஒன்று\nமுல்லை வரிகள் இரண்டு"
        chunks1 = parse_generic_stanzas(meta, text, "data/test.html")
        chunks2 = parse_generic_stanzas(meta, text, "data/test.html")

        self.assertEqual(len(chunks1), 2)
        self.assertEqual(chunks1[0]["chunk_id"], "PM-KURU-0001")
        self.assertEqual(chunks1[1]["chunk_id"], "PM-KURU-0002")
        # Invariance across repeated runs
        self.assertEqual(chunks1[0]["chunk_id"], chunks2[0]["chunk_id"])
        self.assertEqual(chunks1[1]["chunk_id"], chunks2[1]["chunk_id"])

    def test_malformed_html_handled_gracefully(self):
        """Damaged or malformed HTML tags do not cause parser crashes."""
        damaged_html = "<html><body><h3><font color=blue>Unclosed tags<br><br>பாடலின் முதல் வரி<br>பாடலின் இரண்டாம் வரி<p><div>Broken"
        cleaned = clean_html_tags(damaged_html)
        self.assertIsInstance(cleaned, str)
        self.assertIn("பாடலின் முதல் வரி", cleaned)


class TestProjectMaduraiFTS5(unittest.TestCase):
    """Tests for SQLite FTS5 exact indexing and query safety."""

    @classmethod
    def setUpClass(cls):
        # Create an isolated in-memory or temp SQLite FTS5 index
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.temp_dir.name) / "test_fts.db"
        cls.conn = init_database(cls.db_path)

        sample_chunks = [
            {
                "chunk_id": "PM-TEST-0001",
                "corpus_version": "1.0.0",
                "source": "Project Madurai",
                "release_no": "PM0001",
                "work": "சோதனை நூல்",
                "author": "புலவர்",
                "period": "Classical",
                "genre": "Poetry",
                "canto": None,
                "chapter": None,
                "stanza_number": 1,
                "verse_number": "1",
                "line_range": "1-2",
                "original_text": "மரம் வளர்ப்போம் மழை பெறுவோம்",
                "normalized_text": "மரம் வளர்ப்போம் மழை பெறுவோம்",
                "source_url": None,
                "file_path": "data/test.html"
            },
            {
                "chunk_id": "PM-TEST-0002",
                "corpus_version": "1.0.0",
                "source": "Project Madurai",
                "release_no": "PM0001",
                "work": "சோதனை நூல்",
                "author": "புலவர்",
                "period": "Classical",
                "genre": "Poetry",
                "canto": None,
                "chapter": None,
                "stanza_number": 2,
                "verse_number": "2",
                "line_range": "3-4",
                "original_text": "மரங்கள் அடர்ந்த காடு",
                "normalized_text": "மரங்கள் அடர்ந்த காடு",
                "source_url": None,
                "file_path": "data/test.html"
            },
            {
                "chunk_id": "PM-TEST-0003",
                "corpus_version": "1.0.0",
                "source": "Project Madurai",
                "release_no": "PM0001",
                "work": "சோதனை நூல்",
                "author": "புலவர்",
                "period": "Classical",
                "genre": "Poetry",
                "canto": None,
                "chapter": None,
                "stanza_number": 3,
                "verse_number": "3",
                "line_range": "5-6",
                "original_text": "காட்டில் விலங்குகள் உள்ளன",
                "normalized_text": "காட்டில் விலங்குகள் உள்ளன",
                "source_url": None,
                "file_path": "data/test.html"
            },
        ]
        insert_chunks(cls.conn, sample_chunks)

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        cls.temp_dir.cleanup()

    def test_tamil_combining_marks_preserved_in_fts(self):
        """FTS tokenizer preserves Tamil combining marks and distinguishes exact roots from inflections."""
        cur = self.conn.cursor()
        # Querying exact 'மரம்' matches ONLY 'மரம் வளர்ப்போம்', NOT 'மரங்கள் அடர்ந்த காடு'
        cur.execute("SELECT c.chunk_id FROM chunks c JOIN chunks_fts fts ON c.rowid = fts.rowid WHERE chunks_fts MATCH '\"மரம்\"';")
        rows = cur.fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "PM-TEST-0001")

        # Querying exact 'மரங்கள்' matches ONLY 'மரங்கள் அடர்ந்த காடு'
        cur.execute("SELECT c.chunk_id FROM chunks c JOIN chunks_fts fts ON c.rowid = fts.rowid WHERE chunks_fts MATCH '\"மரங்கள்\"';")
        rows = cur.fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "PM-TEST-0002")

    def test_kaattil_vs_kaadu_exact_distinction(self):
        """Exact 'காட்டில்' does not match 'காடு' and vice versa."""
        cur = self.conn.cursor()
        # 'காட்டில்'
        cur.execute("SELECT c.chunk_id FROM chunks c JOIN chunks_fts fts ON c.rowid = fts.rowid WHERE chunks_fts MATCH '\"காட்டில்\"';")
        rows = cur.fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "PM-TEST-0003")

        # 'காடு'
        cur.execute("SELECT c.chunk_id FROM chunks c JOIN chunks_fts fts ON c.rowid = fts.rowid WHERE chunks_fts MATCH '\"காடு\"';")
        rows = cur.fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "PM-TEST-0002")

    def test_malformed_fts_syntax_does_not_crash(self):
        """Malformed or malicious inputs do not trigger FTS syntax errors."""
        cur = self.conn.cursor()
        malformed_inputs = [
            'மரம்*',
            'மரம் AND காடு',
            'மரம் OR NOT (காட்டில்)',
            '"""""',
            '*:*',
            'col:val',
            'மரம் "test" quote',
            "'; DROP TABLE chunks; --",
            '^மரம்',
            '{மரம்}',
        ]
        for inp in malformed_inputs:
            sanitized = sanitize_fts_query(inp)
            try:
                cur.execute(
                    "SELECT c.chunk_id FROM chunks c JOIN chunks_fts fts ON c.rowid = fts.rowid WHERE chunks_fts MATCH ?;",
                    (sanitized,)
                )
                rows = cur.fetchall()
                self.assertIsInstance(rows, list)
            except sqlite3.OperationalError as e:
                self.fail(f"FTS query crashed on sanitized input {sanitized!r} (raw: {inp!r}): {e}")

    def test_deterministic_ordering_and_sql_limit(self):
        """Results are deterministically ordered by chunk_id and respect SQL LIMIT."""
        cur = self.conn.cursor()
        # Add 30 dummy rows for limit test
        extra = [
            {
                "chunk_id": f"PM-EXTRA-{i:04d}",
                "corpus_version": "1.0.0",
                "source": "Project Madurai",
                "release_no": "PM_EX",
                "work": "Extra",
                "author": "Extra",
                "period": "Extra",
                "genre": "Extra",
                "canto": None,
                "chapter": None,
                "stanza_number": i,
                "verse_number": str(i),
                "line_range": None,
                "original_text": f"பொதுவான சொல் {i}",
                "normalized_text": f"பொதுவான சொல் {i}",
                "source_url": None,
                "file_path": "data/test.html"
            }
            for i in range(1, 35)
        ]
        insert_chunks(self.conn, extra)

        sql = """
        SELECT c.chunk_id
        FROM chunks c
        JOIN chunks_fts fts ON c.rowid = fts.rowid
        WHERE chunks_fts MATCH '"பொதுவான"'
        ORDER BY c.chunk_id ASC
        LIMIT 25;
        """
        rows = cur.execute(sql).fetchall()
        self.assertEqual(len(rows), 25)
        # Check ordering is ascending by chunk_id
        ids = [r[0] for r in rows]
        self.assertEqual(ids, sorted(ids))


class TestProjectMaduraiAdapter(unittest.TestCase):
    """Tests for ProjectMaduraiExactAdapter conforming to ResourceAdapter contract."""

    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parents[1]
        cls.db_path = cls.project_root / "data" / "processed" / "madurai_exact.db"
        cls.adapter = ProjectMaduraiExactAdapter(cls.db_path)

    def test_valid_evidence_contract(self):
        """Adapter emits standard Evidence with source='Project Madurai' and evidence_type='literary_context'."""
        evs = self.adapter.lookup("மரம்")
        self.assertGreater(len(evs), 0)
        for ev in evs:
            self.assertIsInstance(ev, Evidence)
            self.assertEqual(ev.source, "Project Madurai")
            self.assertEqual(ev.evidence_type, "literary_context")
            self.assertIsNotNone(ev.passage)
            self.assertIsNotNone(ev.work)
            self.assertIsNotNone(ev.source_id)
            self.assertEqual(ev.metadata.get("status"), "FOUND")
            self.assertEqual(ev.metadata.get("retrieval_method"), "exact")

    def test_not_found_behavior(self):
        """Query with no matches returns single NOT_FOUND Evidence object without error."""
        evs = self.adapter.lookup("கிடைக்காதசொல்123xyz")
        self.assertEqual(len(evs), 1)
        self.assertEqual(evs[0].source, "Project Madurai")
        self.assertEqual(evs[0].metadata.get("status"), "NOT_FOUND")

    def test_error_behavior_on_missing_db(self):
        """Missing database file returns gracefully with ERROR Evidence object without raising exception."""
        bad_adapter = ProjectMaduraiExactAdapter(Path("non_existent_dir/bad.db"))
        evs = bad_adapter.lookup("மரம்")
        self.assertEqual(len(evs), 1)
        self.assertEqual(evs[0].source, "Project Madurai")
        self.assertEqual(evs[0].metadata.get("status"), "ERROR")
        self.assertIn("error", evs[0].metadata)

    def test_no_fabricated_lemmas(self):
        """Adapter never asserts or invents a lemma; passes through caller lemma or None."""
        evs_no_lemma = self.adapter.lookup("மரங்கள்")
        for ev in evs_no_lemma:
            if ev.metadata.get("status") == "FOUND":
                self.assertIsNone(ev.lemma, "Adapter must not invent a lemma when none provided!")

        evs_with_lemma = self.adapter.lookup("மரம்", lemma="மரம்")
        for ev in evs_with_lemma:
            if ev.metadata.get("status") == "FOUND":
                self.assertEqual(ev.lemma, "மரம்")


class TestProjectMaduraiIntegration(unittest.TestCase):
    """
    Integration tests against the real generated Project Madurai corpus with RetrievalEngine.
    Verifies multi-pass resolution and coexistence with Sentamizh.
    """

    @classmethod
    def setUpClass(cls):
        cls.engine = RetrievalEngine()

    def test_real_corpus_exact_maram(self):
        """Real corpus lookup for 'மரம்' retrieves Project Madurai and Sentamizh evidence."""
        res = self.engine.search("மரம்")
        self.assertEqual(res.normalized_query, "மரம்")
        self.assertIn("Project Madurai", res.resource_summary)
        self.assertEqual(res.resource_summary["Project Madurai"]["status"], "FOUND")
        self.assertGreaterEqual(res.resource_summary["Project Madurai"]["total_entries"], 1)

        pm_evs = [e for e in res.evidence if e.source == "Project Madurai" and e.metadata.get("status") == "FOUND"]
        self.assertGreater(len(pm_evs), 0)
        # Every PM evidence has valid provenance
        for ev in pm_evs:
            self.assertIn("PM-", ev.source_id)
            self.assertIsNotNone(ev.work)
            self.assertIsNotNone(ev.passage)

    def test_real_corpus_inflected_marangalil_multipass(self):
        """
        For inflected word 'மரங்களில்':
        Pass 1 surface misses or provides candidate lemma 'மரம்'.
        Pass 2 uses candidate lemma 'மரம்' to retrieve Project Madurai evidence.
        """
        res = self.engine.search("மரங்களில்")
        self.assertEqual(res.normalized_query, "மரங்களில்")
        self.assertIn("மரம்", res.lemma_candidates)

        pm_evs = [e for e in res.evidence if e.source == "Project Madurai" and e.metadata.get("status") == "FOUND"]
        self.assertGreater(len(pm_evs), 0)
        # At least one PM evidence has lemma == "மரம்" from Pass 2
        pm_with_lemma = [e for e in pm_evs if e.lemma == "மரம்"]
        self.assertGreater(len(pm_with_lemma), 0)

    def test_real_corpus_representative_terms(self):
        """Test representative Tamil queries: அகத்தி, யாழ், மனிதன், செய்."""
        terms = ["அகத்தி", "யாழ்", "மனிதன்", "செய்"]
        for term in terms:
            res = self.engine.search(term)
            pm_evs = [e for e in res.evidence if e.source == "Project Madurai" and e.metadata.get("status") == "FOUND"]
            self.assertGreater(
                len(pm_evs), 0,
                f"Expected Project Madurai to find evidence for term '{term}' in the real corpus"
            )

    def test_coexistence_with_sentamizh(self):
        """Both Sentamizh and Project Madurai coexist and emit literary evidence simultaneously."""
        res = self.engine.search("மரம்")
        sources = {e.source for e in res.evidence if e.metadata.get("status") == "FOUND"}
        self.assertIn("Sentamizh", sources)
        self.assertIn("Project Madurai", sources)
        self.assertIn("ThamizhiMorph", sources)


class TestProjectMaduraiRebuildCorrections(unittest.TestCase):
    """
    Regression Test Suite A through J for Step 2F Rebuild & Ingestion Corrections.
    """

    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parents[1]
        cls.db_path = cls.project_root / "data" / "processed" / "madurai_exact.db"
        cls.engine = RetrievalEngine()
        cls.conn = sqlite3.connect(cls.db_path)

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    def test_a_iniyavai_mapping(self):
        """Test A: INIYAVAI maps to Iniyavai Narpathu (PM0025) by Boothanchendanar, not Bharathiyar."""
        cur = self.conn.cursor()
        cur.execute("SELECT chunk_id, release_no, author, work, original_text FROM chunks WHERE chunk_id LIKE 'PM-INIYAVAI%'")
        rows = cur.fetchall()

        self.assertGreater(len(rows), 0, "No chunks found for INIYAVAI")
        self.assertLessEqual(len(rows), 50, f"Expected ~44 chunks for INIYAVAI, found {len(rows)}")

        for chunk_id, release_no, author, work, original_text in rows:
            self.assertEqual(release_no, "PM0025", f"Expected PM0025, got {release_no} in {chunk_id}")
            self.assertIn("பூதஞ்சேந்தனார்", author, f"Unexpected author {author} in {chunk_id}")
            self.assertEqual(work, "இனியவை நாற்பது", f"Unexpected work {work} in {chunk_id}")
            self.assertNotIn("பாரதியார்", original_text)
            self.assertNotIn("சுப்பிரமணிய", original_text)
            self.assertNotIn("ஞானப் பாடல்கள்", original_text)

        all_text = " ".join(r[4] for r in rows)
        self.assertIn("கண்மூன் றுடையான்தாள் சேர்தல் கடிதினிதே", all_text)
        self.assertIn("பிச்சைபுக் காயினுங் கற்றல் மிகஇனிதே", all_text)

    def test_b_bharathiyar_mapping(self):
        """Test B: BHARATHI_2 maps to PM0021 (Gnanap Padalkal) and BHARATHI maps to PM0049."""
        cur = self.conn.cursor()
        # Verify BHARATHI_2
        cur.execute("SELECT chunk_id, release_no, author, work FROM chunks WHERE chunk_id LIKE 'PM-BHARATHI_2%'")
        rows2 = cur.fetchall()
        self.assertGreater(len(rows2), 400)
        for chunk_id, release_no, author, work in rows2:
            self.assertEqual(release_no, "PM0021")
            self.assertEqual(author, "சி. சுப்பிரமணிய பாரதியார்")
            self.assertEqual(work, "பாரதியார் பாடல்கள் (பாகம் 2)")

        # Verify BHARATHI
        cur.execute("SELECT chunk_id, release_no, author, work FROM chunks WHERE chunk_id LIKE 'PM-BHARATHI-%'")
        rows1 = cur.fetchall()
        self.assertGreater(len(rows1), 400)
        for chunk_id, release_no, author, work in rows1:
            self.assertEqual(release_no, "PM0049")
            self.assertEqual(author, "சி. சுப்பிரமணிய பாரதியார்")
            self.assertEqual(work, "பாரதியார் பாடல்கள்")

    def test_c_tirukkural_verses_and_zero_english_boilerplate(self):
        """Test C: Tirukkural has 1330 canonical couplets with zero shift and no English header boilerplate."""
        cur = self.conn.cursor()
        cur.execute("SELECT chunk_id, stanza_number, original_text FROM chunks WHERE chunk_id LIKE 'PM-TK-%' ORDER BY stanza_number ASC")
        rows = cur.fetchall()

        self.assertEqual(len(rows), 1330, f"Expected exactly 1330 Tirukkural chunks, got {len(rows)}")

        tk_dict = {r[1]: r[2] for r in rows}

        # Kural 1
        self.assertIn("அகர முதல எழுத்தெல்லாம் ஆதி", tk_dict[1])
        self.assertIn("பகவன் முதற்றே உலகு.", tk_dict[1])

        # Kural 2
        self.assertIn("கற்றதனால் ஆய பயனென்கொல் வாலறிவன்", tk_dict[2])
        self.assertIn("நற்றாள் தொழாஅர் எனின்.", tk_dict[2])

        # Kural 10
        self.assertIn("பிறவிப் பெருங்கடல் நீந்துவர் நீந்தார்", tk_dict[10])
        self.assertIn("இறைவன் அடிசேரா தார்.", tk_dict[10])

        # Kural 100
        self.assertIn("இனிய உளவாக இன்னாத கூறல்", tk_dict[100])
        self.assertIn("கனிஇருப்பக் காய்கவர்ந் தற்று.", tk_dict[100])

        # Kural 500
        self.assertIn("காலாழ் களரில் நரியடும் கண்ணஞ்சா", tk_dict[500])

        # Kural 1000
        self.assertIn("பண்பிலான் பெற்ற பெருஞ்செல்வம் நன்பால்", tk_dict[1000])

        # Kural 1330
        self.assertIn("ஊடுதல் காமத்திற்கு இன்பம் அதற்கின்பம்", tk_dict[1330])
        self.assertIn("கூடி முயங்கப் பெறின்.", tk_dict[1330])

        # Zero English boilerplate in TK chunks
        for st_num, text in tk_dict.items():
            self.assertNotIn("Project Madurai", text)
            self.assertNotIn("In Tamil script", text)
            self.assertNotIn("unicode format", text)
            self.assertNotIn("Prepared by", text)

    def test_d_aathichudi_full_inventory(self):
        """Test D: Aathichudi has full inventory (1 invocation + 109 aphorisms = 110 chunks)."""
        cur = self.conn.cursor()
        cur.execute("SELECT chunk_id, stanza_number, original_text FROM chunks WHERE chunk_id LIKE 'PM-AATHI-%' ORDER BY stanza_number ASC")
        rows = cur.fetchall()

        self.assertEqual(len(rows), 110, f"Expected 110 Aathichudi chunks, got {len(rows)}")

        # First aphorism (PM-AATHI-0002)
        self.assertIn("அறம் செய விரும்பு.", rows[1][2])

        # Middle aphorisms
        all_text = " ".join(r[2] for r in rows)
        self.assertIn("தீவினை அகற்று", all_text)
        self.assertIn("நூல் பல கல்", all_text)

        # Last aphorism (PM-AATHI-0110)
        self.assertIn("ஓரம் சொல்லேல்.", rows[109][2])

    def test_e_konrai_vendhan_full_inventory(self):
        """Test E: Konrai Vendhan has full inventory (1 invocation + 91 aphorisms = 92 chunks)."""
        cur = self.conn.cursor()
        cur.execute("SELECT chunk_id, stanza_number, original_text FROM chunks WHERE chunk_id LIKE 'PM-KONRAI-%' ORDER BY stanza_number ASC")
        rows = cur.fetchall()

        self.assertEqual(len(rows), 92, f"Expected 92 Konrai Vendhan chunks, got {len(rows)}")

        # First aphorism (PM-KONRAI-0002)
        self.assertIn("அன்னையும் பிதாவும் முன்னறி தெய்வம்.", rows[1][2])

        # Last aphorism (PM-KONRAI-0092)
        self.assertIn("ஓதாதார்க்கு இல்லை உணர்வொடும் ஒழுக்கம்.", rows[91][2])

    def test_f_canto_heading_false_positives(self):
        """Test F: General Tamil words like இயல்பானான், இயல்வது, பகுதி are not falsely parsed as cantos."""
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM chunks WHERE canto LIKE '%இயல்பானான்%' OR canto LIKE '%இயல்வது%' OR canto LIKE '%பகுதியைக்%'")
        count = cur.fetchone()[0]
        self.assertEqual(count, 0, f"Found {count} chunks with false canto headings")

    def test_g_boilerplate_filtering(self):
        """Test G: Web navigation links, donor/volunteer acknowledgements are excluded from chunks."""
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM chunks WHERE original_text LIKE '%உள்ளுறை அட்டவணைக்குத் திரும்ப%' OR original_text LIKE '%Project Madurai is an open%'")
        count = cur.fetchone()[0]
        self.assertEqual(count, 0, f"Found {count} chunks with boilerplate")

    def test_h_literary_units_preservation(self):
        """Test H: Multi-line poetic forms (Naladiyar venbas, Tiruppavai pasurams) are preserved as cohesive stanzas."""
        cur = self.conn.cursor()

        # Naladiyar quatrain venba
        cur.execute("SELECT original_text FROM chunks WHERE chunk_id = 'PM-NALADI-0009'")
        naladi_text = cur.fetchone()[0]
        self.assertEqual(len(naladi_text.splitlines()), 4, "Naladiyar venba should be preserved as 4 lines")

        # Tiruppavai 8-line pasuram
        cur.execute("SELECT original_text FROM chunks WHERE chunk_id = 'PM-THIRUPPAVAI-0005'")
        tiruppavai_text = cur.fetchone()[0]
        self.assertGreaterEqual(len(tiruppavai_text.splitlines()), 8, "Tiruppavai pasuram should be preserved as 8+ lines")

    def test_i_fts_parity_and_count(self):
        """Test I: Chunks table and FTS5 index have exact parity, and corpus contains 35 works."""
        cur = self.conn.cursor()
        cur.execute("SELECT count(*) FROM chunks")
        chunks_count = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM chunks_fts")
        fts_count = cur.fetchone()[0]
        cur.execute("SELECT count(DISTINCT work) FROM chunks")
        works_count = cur.fetchone()[0]

        self.assertEqual(chunks_count, fts_count, "Chunks and FTS5 row counts must match")
        self.assertEqual(works_count, 35, "Corpus must contain 35 distinct works")
        self.assertGreaterEqual(chunks_count, 14000)

    def test_j_retrieval_integrity(self):
        """Test J: End-to-end exact retrieval works for representative queries across repaired works."""
        # Query 1: Aathichudi / Dharma
        res_aram = self.engine.search("அறம்")
        pm_aram = [e for e in res_aram.evidence if e.source == "Project Madurai" and e.metadata.get("status") == "FOUND"]
        self.assertGreater(len(pm_aram), 0)
        works_aram = {e.work for e in pm_aram}
        self.assertTrue(any("ஆத்திசூடி" in w or "திருக்குறள்" in w for w in works_aram))

        # Query 2: Iniyavai Narpathu
        res_iniya = self.engine.search("இனிது")
        pm_iniya = [e for e in res_iniya.evidence if e.source == "Project Madurai" and e.metadata.get("status") == "FOUND"]
        self.assertGreater(len(pm_iniya), 0)
        works_iniya = {e.work for e in pm_iniya}
        self.assertIn("இனியவை நாற்பது", works_iniya)

        # Query 3: Bharathiyar
        res_bharathi = self.engine.search("பாரதி")
        pm_bharathi = [e for e in res_bharathi.evidence if e.source == "Project Madurai" and e.metadata.get("status") == "FOUND"]
        self.assertGreater(len(pm_bharathi), 0)


if __name__ == "__main__":
    unittest.main()
