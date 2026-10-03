"""
Unit tests for the centralized literary context processor (Phase 3).
Validates line extraction, context window truncation, highlight offsets,
metadata handling, and edge cases including Tamil Unicode.
"""

import pytest
from backend.interpretation.literary_processor import (
    extract_relevant_line,
    build_context_window,
    compute_highlight_offsets,
    process_literary_evidence,
)
from backend.interpretation.schemas import HighlightOffset, LiteraryContextItem
from backend.schemas.evidence import Evidence


class TestLiteraryProcessor:
    """Test suite covering the 10 core edge cases and functional requirements of literary_processor."""

    # Case 1: Single occurrence in passage
    def test_single_occurrence_in_passage(self):
        text = "அகர முதல எழுத்தெல்லாம் ஆதி பகவன் முதற்றே உலகு"
        query = "அகர"
        offsets = compute_highlight_offsets(text, [query])
        assert len(offsets) == 1
        assert offsets[0].start == 0
        assert offsets[0].end == len("அகர")
        assert text[offsets[0].start:offsets[0].end] == "அகர"

    # Case 2: Multiple occurrences in same line
    def test_multiple_occurrences_in_same_line(self):
        text = "செயற்கரிய செய்வார் பெரியர் சிறியர் செயற்கரிய செய்கலாதார்."
        query = "செயற்கரிய"
        offsets = compute_highlight_offsets(text, [query])
        assert len(offsets) == 2
        for off in offsets:
            assert text[off.start:off.end] == query
            assert off.start < off.end
        assert offsets[0].start == 0
        assert offsets[1].start > offsets[0].end

    # Case 3: Multiple occurrences in different lines
    def test_multiple_occurrences_in_different_lines(self):
        passage = "அறம் செய விரும்பு.\nஅறன் எனப்பட்டதே இல்வாழ்க்கை.\nஅறத்தினூங்கு ஆக்கமும் இல்லை."
        query = "அறம்"
        lemma = "அறன்"
        line = extract_relevant_line(passage, [query, lemma])
        assert line == "அறம் செய விரும்பு."
        # Full passage offsets should find occurrences across lines
        passage_offsets = compute_highlight_offsets(passage, [query, lemma])
        assert len(passage_offsets) >= 2
        matched_words = [passage[off.start:off.end] for off in passage_offsets]
        assert "அறம்" in matched_words
        assert "அறன்" in matched_words

    # Case 4: Query match at beginning of line
    def test_query_match_at_beginning_of_line(self):
        line = "வானோர்க்கும் உயர்ந்த உலகம்"
        offsets = compute_highlight_offsets(line, ["வானோர்க்கும்"])
        assert len(offsets) == 1
        assert offsets[0].start == 0
        assert offsets[0].end == len("வானோர்க்கும்")
        assert line[offsets[0].start:offsets[0].end] == "வானோர்க்கும்"

    # Case 5: Query match at end of line
    def test_query_match_at_end_of_line(self):
        line = "உலகத்தோடு ஒட்ட ஒழுகல் பலகற்றும் கல்லார் அறிவிலா தார்"
        offsets = compute_highlight_offsets(line, ["தார்"])
        assert len(offsets) == 1
        assert offsets[0].end == len(line)
        assert line[offsets[0].start:offsets[0].end] == "தார்"

    # Case 6: Unicode characters (Tamil diacritics / combining marks)
    def test_tamil_unicode_combining_characters(self):
        text = "கற்க கசடறக் கற்பவை கற்றபின் நிற்க அதற்குத் தக"
        query = "கசடறக்"
        offsets = compute_highlight_offsets(text, [query])
        assert len(offsets) == 1
        sub = text[offsets[0].start:offsets[0].end]
        assert sub == query
        assert len(sub) == len(query)

    # Case 7: Surrounding lines present vs single-line passage
    def test_surrounding_lines_vs_single_line(self):
        single_line = "துப்பார்க்குத் துப்பாய துப்பாக்கித் துப்பார்க்குத் துப்பாய தூஉம் மழை"
        multi_line = "வான்நின்று உலகம் வழங்கி வருதலால்\nதான்அமிழ்தம் என்றுணரற் பாற்று."

        item_single = process_literary_evidence(
            [{"passage": single_line, "work": "Tirukkural"}],
            query="துப்பார்க்குத்",
        )[0]
        # In single_line, length is <= 120 and no newline, so can_expand should be False
        assert not item_single.can_expand
        assert item_single.matched_line == single_line

        item_multi = process_literary_evidence(
            [{"passage": multi_line, "work": "Tirukkural"}],
            query="உலகம்",
        )[0]
        # multi_line has newline, can_expand should be True
        assert item_multi.can_expand
        assert item_multi.matched_line == "வான்நின்று உலகம் வழங்கி வருதலால்"
        assert "\n" not in item_multi.snippet

    # Case 8: Truncated window vs untruncated window (length < 120 vs length > 120)
    def test_context_window_truncation(self):
        short_line = "அன்பும் அறனும் உடைத்தாயின் இல்வாழ்க்கை பண்பும் பயனும் அது"
        window_short = build_context_window(short_line, ["அன்பும்"], max_chars=120)
        assert window_short == short_line
        assert "..." not in window_short

        # Line longer than 120 chars
        long_line = (
            "பல்லாயிரக்கணக்கான ஆண்டுகளாய் தொடரும் தொன்மையான தமிழ் இலக்கிய மரபில் "
            "மனித வாழ்க்கையின் நுட்பமான உணர்வுகளையும் அறநெறிகளையும் எடுத்துரைக்கும் "
            "பாடல்கள் பல உள்ளன."
        )
        assert len(long_line) > 120
        window_long = build_context_window(long_line, ["அறநெறிகளையும்"], max_chars=120)
        assert len(window_long) <= 125  # With prefix/suffix
        assert "அறநெறிகளையும்" in window_long
        assert "..." in window_long

    # Case 9: Missing metadata (no work/author/era)
    def test_missing_metadata_handled_gracefully(self):
        raw_evidence = [
            {
                "passage": "அகர முதல எழுத்தெல்லாம்",
                # No work, author, period, verse_number
            }
        ]
        items = process_literary_evidence(raw_evidence, query="அகர")
        assert len(items) == 1
        it = items[0]
        assert it.work is None
        assert it.author is None
        assert it.period is None
        assert it.verse_number == ""
        assert it.passage == "அகர முதல எழுத்தெல்லாம்"
        assert it.snippet == "அகர முதல எழுத்தெல்லாம்"
        assert it.is_featured is True

    # Case 10: Empty or whitespace-only passage
    def test_empty_or_whitespace_passage(self):
        raw_evidence = [
            {"passage": "   ", "work": "Test"},
            {"passage": "", "work": "Test2"},
        ]
        items = process_literary_evidence(raw_evidence, query="சொல்")
        assert len(items) == 2
        assert items[0].passage == ""
        assert items[0].snippet == ""
        assert items[0].matched_line == ""
        assert items[0].highlight_offsets == []
        assert items[0].can_expand is False

    # Additional test: Polymorphic input (Evidence object vs Dict vs LiteraryContextItem)
    def test_polymorphic_input_handling(self):
        ev_obj = Evidence(
            surface="பெரியர்",
            source="Sentamizh",
            passage="செயற்கரிய செய்வார் பெரியர் சிறியர் செயற்கரிய செய்கலாதார்.",
            author="திருவள்ளுவர்",
            work="திருக்குறள்",
            period="சங்க காலம்",
            metadata={"verse_number": 26, "modern_tamil": "அரிய செயல்களைச் செய்வோர் பெரியோர்."},
        )
        dict_obj = {
            "passage": "அன்பிலார் எல்லாம் தமக்குரியர் அன்புடையார் என்பும் உரியர் பிறர்க்கு.",
            "work": "திருக்குறள்",
            "verse_number": "72",
        }
        item_obj = LiteraryContextItem(
            work="புறநானூறு",
            passage="உண்டி கொடுத்தோர் உயிர் கொடுத்தோரே.",
            author="குடபுலவியனார்",
        )

        results = process_literary_evidence([ev_obj, dict_obj, item_obj], query="பெரியர்")
        assert len(results) == 3
        # First item is featured
        assert results[0].is_featured is True
        assert results[0].author == "திருவள்ளுவர்"
        assert results[0].verse_number == "26"
        assert results[0].meaning == "அரிய செயல்களைச் செய்வோர் பெரியோர்."

        # Second item is not featured
        assert results[1].is_featured is False
        assert results[1].work == "திருக்குறள்"
        assert results[1].verse_number == "72"

        # Third item
        assert results[2].is_featured is False
        assert results[2].work == "புறநானூறு"
        assert results[2].author == "குடபுலவியனார்"
