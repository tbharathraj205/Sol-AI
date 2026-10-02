from typing import List, Dict, Any, Set
from collections import defaultdict

from backend.schemas.evidence import Evidence
from backend.schemas.result import UnifiedResult

try:
    from deep_translator import GoogleTranslator
except ImportError:
    GoogleTranslator = None


class EvidenceAggregator:
    """
    Evidence Aggregator & Priority Ranker for SOL AI.
    Groups evidence by candidate lemma and source, detects genuine cross-resource support,
    preserves conflicting/guesser analyses, and applies deterministic priority sorting.
    """

    @staticmethod
    def aggregate(
        query: str,
        normalized_query: str,
        all_evidence: List[Evidence],
        errors: Dict[str, str]
    ) -> UnifiedResult:
        """
        Aggregate raw Evidence objects from resource adapters into a UnifiedResult.
        
        :param query: Raw user query
        :param normalized_query: Normalized query string
        :param all_evidence: Combined list of Evidence objects across all adapters
        :param errors: Dictionary of resource errors if any adapter failed
        :return: UnifiedResult object
        """
        # 1. Filter ONLY valid FOUND evidence for candidate extraction and support mapping
        found_evidence = [ev for ev in all_evidence if ev.metadata.get("status") == "FOUND"]

        # 2. Extract unique candidate lemmas from FOUND evidence
        lemma_candidates: Set[str] = set()
        for ev in found_evidence:
            if ev.lemma and ev.lemma.strip():
                lemma_candidates.add(ev.lemma.strip())
            if ev.metadata.get("root_word") and ev.metadata.get("root_word").strip():
                lemma_candidates.add(ev.metadata.get("root_word").strip())
            if ev.metadata.get("headword") and ev.metadata.get("headword").strip():
                lemma_candidates.add(ev.metadata.get("headword").strip())

        sorted_lemmas = sorted(list(lemma_candidates))

        # 3. Compute Strict Cross-Resource Support
        # A resource R supports candidate C iff R returned actual FOUND evidence for C
        cross_support: Dict[str, Set[str]] = defaultdict(set)

        # All target strings to check for support (surface query + discovered lemmas)
        all_targets = set([normalized_query] + sorted_lemmas)

        for target_str in all_targets:
            for ev in found_evidence:
                source = ev.source
                if not source:
                    continue

                # Semantic retrieval provides thematic literary context, not lexical verification
                if ev.metadata.get("retrieval_mode") == "semantic":
                    continue

                # Check if this evidence object matches target_str
                matches_surface = (ev.surface == target_str)
                matches_lemma = (ev.lemma == target_str)
                matches_root = (ev.metadata.get("root_word") == target_str)
                matches_headword = (ev.metadata.get("headword") == target_str)

                if matches_surface or matches_lemma or matches_root or matches_headword:
                    cross_support[target_str].add(source)

        cross_resource_support_dict = {
            target_str: sorted(list(sources))
            for target_str, sources in cross_support.items()
            if sources
        }

        # 4. Deterministic Priority Sorting
        def get_priority_key(ev: Evidence):
            status = ev.metadata.get("status", "")
            if status != "FOUND":
                return (0, 0, 0)
            
            analysis_score = 10
            if ev.metadata.get("analysis_type") == "guesser":
                analysis_score = 5

            match_score = 8
            if ev.surface != normalized_query and ev.lemma == normalized_query:
                match_score = 6
            elif ev.surface != normalized_query:
                match_score = 4

            type_score = 8
            if ev.evidence_type == "frequency":
                type_score = 2

            return (analysis_score, match_score, type_score)

        sorted_evidence = sorted(all_evidence, key=get_priority_key, reverse=True)

        # 5. Resource Summary Statistics
        resource_summary: Dict[str, Dict[str, Any]] = {}
        resources_list = ["ThamizhiMorph", "Thani Thamizh Akarathi", "Tamil WordNet", "Tamil Wiktionary", "Sentamizh", "Project Madurai"]

        for res in resources_list:
            res_evs = [e for e in sorted_evidence if e.source == res]
            found_evs = [e for e in res_evs if e.metadata.get("status") == "FOUND"]
            has_error = res in errors

            status = "FOUND" if found_evs else ("ERROR" if has_error else "NOT_FOUND")

            core_count = sum(1 for e in found_evs if e.metadata.get("analysis_type") == "core")
            guesser_count = sum(1 for e in found_evs if e.metadata.get("analysis_type") == "guesser")

            resource_summary[res] = {
                "status": status,
                "total_entries": len(found_evs),
                "core_analyses": core_count if res == "ThamizhiMorph" else None,
                "guesser_analyses": guesser_count if res == "ThamizhiMorph" else None
            }

        return UnifiedResult(
            query=query,
            normalized_query=normalized_query,
            lemma_candidates=sorted_lemmas,
            evidence=sorted_evidence,
            resource_summary=resource_summary,
            cross_resource_support=cross_resource_support_dict,
            errors=errors
        )
