"""
Unit tests for EvidencePack classification.
Verifies that literary evidence classification is resource-agnostic and relies
on evidence_type rather than source name (e.g., Sentamizh vs Project Madurai).
"""

import unittest
from backend.schemas.evidence import Evidence
from backend.schemas.result import UnifiedResult
from backend.interpretation.evidence_pack import (
    build_evidence_pack,
    LITERARY_EVIDENCE_TYPES,
)


class TestEvidencePackClassification(unittest.TestCase):
    """
    Test suite verifying resource-agnostic literary classification in build_evidence_pack.
    """

    def test_literary_evidence_types_constant(self):
        """Verify LITERARY_EVIDENCE_TYPES contains all canonical literary types."""
        self.assertIn("literary", LITERARY_EVIDENCE_TYPES)
        self.assertIn("corpus", LITERARY_EVIDENCE_TYPES)
        self.assertIn("citation", LITERARY_EVIDENCE_TYPES)
        self.assertIn("literary_context", LITERARY_EVIDENCE_TYPES)

    def test_sentamizh_literary_context_classified_as_literary(self):
        """Sentamizh with evidence_type='literary_context' must be classified as literary evidence."""
        ev = Evidence(
            surface="மரம்",
            source="Sentamizh",
            evidence_type="literary_context",
            passage="மரம் பயில் இறும்பின்",
            work="குறுந்தொகை",
            metadata={"status": "FOUND", "source_text": "குறுந்தொகை"},
        )
        result = UnifiedResult(
            query="மரம்",
            normalized_query="மரம்",
            lemma_candidates=["மரம்"],
            evidence=[ev],
        )
        pack = build_evidence_pack(result)
        self.assertEqual(len(pack.literary_evidence), 1)
        self.assertEqual(pack.literary_evidence[0].source, "Sentamizh")
        self.assertEqual(len(pack.lexical_evidence), 0)

    def test_project_madurai_literary_context_classified_as_literary(self):
        """Project Madurai with evidence_type='literary_context' must be classified as literary evidence."""
        ev = Evidence(
            surface="மரம்",
            source="Project Madurai",
            evidence_type="literary_context",
            passage="அறவாழி அந்தணன் தாள்சேர்ந்தார்க் கல்லால்",
            work="திருக்குறள்",
            metadata={"status": "FOUND", "chunk_id": "PM-TK-0008"},
        )
        result = UnifiedResult(
            query="மரம்",
            normalized_query="மரம்",
            lemma_candidates=["மரம்"],
            evidence=[ev],
        )
        pack = build_evidence_pack(result)
        self.assertEqual(len(pack.literary_evidence), 1)
        self.assertEqual(pack.literary_evidence[0].source, "Project Madurai")
        self.assertEqual(len(pack.lexical_evidence), 0)

    def test_arbitrary_future_literary_resource_classified_as_literary(self):
        """Any future resource with evidence_type in LITERARY_EVIDENCE_TYPES is classified as literary."""
        ev = Evidence(
            surface="மரம்",
            source="FutureTamilCorpus",
            evidence_type="literary_context",
            passage="மரமும் மலரும்",
            work="நற்றிணை",
            metadata={"status": "FOUND"},
        )
        result = UnifiedResult(
            query="மரம்",
            normalized_query="மரம்",
            lemma_candidates=["மரம்"],
            evidence=[ev],
        )
        pack = build_evidence_pack(result)
        self.assertEqual(len(pack.literary_evidence), 1)
        self.assertEqual(pack.literary_evidence[0].source, "FutureTamilCorpus")
        self.assertEqual(len(pack.lexical_evidence), 0)


if __name__ == "__main__":
    unittest.main()
