import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

from backend.query.normalizer import QueryNormalizer
from backend.schemas.evidence import Evidence
from backend.schemas.result import UnifiedResult
from backend.resources.thamizhimorph import ThamizhiMorphAdapter
from backend.resources.akarathi import ThaniThamizhAkarathiAdapter
from backend.resources.wordnet import TamilWordNetAdapter
from backend.resources.sentamizh import SentamizhAdapter
from backend.resources.project_madurai import ProjectMaduraiExactAdapter
from backend.retrieval.aggregator import EvidenceAggregator


class RetrievalEngine:
    """
    Unified Retrieval Engine for SOL AI.
    Coordinates multi-stage deterministic lookup across ThamizhiMorph, Thani Thamizh Akarathi,
    Tamil WordNet, Sentamizh, and Project Madurai adapters with fault-tolerant error boundaries.
    """

    def __init__(
        self,
        thamizhimorph: Optional[ThamizhiMorphAdapter] = None,
        akarathi: Optional[ThaniThamizhAkarathiAdapter] = None,
        wordnet: Optional[TamilWordNetAdapter] = None,
        sentamizh: Optional[SentamizhAdapter] = None,
        project_madurai: Optional[ProjectMaduraiExactAdapter] = None
    ):
        """
        Initialize the Retrieval Engine with resource adapters.
        Instantiates default adapters if not explicitly provided.
        """
        self.thamizhimorph = thamizhimorph or ThamizhiMorphAdapter()
        self.akarathi = akarathi or ThaniThamizhAkarathiAdapter()
        self.wordnet = wordnet or TamilWordNetAdapter()
        self.sentamizh = sentamizh or SentamizhAdapter()
        self.project_madurai = project_madurai or ProjectMaduraiExactAdapter()
        
        # Lazy load Wiktionary so it doesn't fail if the db is still building
        try:
            from backend.resources.wiktionary import TamilWiktionaryAdapter
            self.wiktionary = TamilWiktionaryAdapter()
        except ImportError:
            self.wiktionary = None

        self.adapters = {
            "ThamizhiMorph": self.thamizhimorph,
            "Tamil Wiktionary": self.wiktionary,
            "Thani Thamizh Akarathi": self.akarathi,
            "Tamil WordNet": self.wordnet,
            "Sentamizh": self.sentamizh,
            "Project Madurai": self.project_madurai
        }
        # Remove any None adapters
        self.adapters = {k: v for k, v in self.adapters.items() if v is not None}

    def search(self, query: str) -> UnifiedResult:
        """
        Perform a unified evidence search for a Tamil input query.
        
        :param query: Surface query string
        :return: UnifiedResult containing aggregated evidence, candidate lemmas,
                 cross-resource support mapping, and resource status.
        """
        # 1. Normalize Query
        norm_query = QueryNormalizer.normalize(query)
        target = norm_query.normalized_query

        if not target:
            return UnifiedResult(
                query=query,
                normalized_query="",
                lemma_candidates=[],
                evidence=[],
                resource_summary={},
                cross_resource_support={},
                errors={}
            )

        all_evidence: List[Evidence] = []
        errors: Dict[str, str] = {}
        seen_evidence_keys = set()

        # Helper to safely append deduplicated evidence
        def add_evidence(ev_list: List[Evidence]):
            for ev in ev_list:
                key = (ev.source, ev.evidence_type, ev.surface, ev.lemma, ev.passage, ev.source_id)
                if key not in seen_evidence_keys:
                    seen_evidence_keys.add(key)
                    all_evidence.append(ev)

        # 2. Pass 1: Surface Lookup across all adapters
        for name, adapter in self.adapters.items():
            try:
                evs = adapter.lookup(target)
                add_evidence(evs)
            except Exception as e:
                errors[name] = str(e)
                # Ensure a graceful error evidence object is attached
                add_evidence([
                    Evidence(
                        surface=target,
                        lemma=None,
                        source=name,
                        metadata={
                            "error": str(e),
                            "status": "ERROR"
                        }
                    )
                ])

        # 3. Extract Candidate Lemmas from Pass 1 morphological / WordNet evidence
        candidate_lemmas = set()
        for ev in all_evidence:
            if ev.metadata.get("status") == "FOUND":
                if ev.lemma and ev.lemma != target:
                    candidate_lemmas.add(ev.lemma.strip())
                if ev.metadata.get("root_word") and ev.metadata.get("root_word") != target:
                    candidate_lemmas.add(ev.metadata.get("root_word").strip())

        # 4. Pass 2: Secondary Lookup for Candidate Lemmas in Lexical / Literary Resources
        secondary_adapters = {
            "Tamil Wiktionary": self.wiktionary,
            "Thani Thamizh Akarathi": self.akarathi,
            "Tamil WordNet": self.wordnet,
            "Sentamizh": self.sentamizh,
            "Project Madurai": self.project_madurai
        }
        secondary_adapters = {k: v for k, v in secondary_adapters.items() if v is not None}

        for lemma in candidate_lemmas:
            for name, adapter in secondary_adapters.items():
                if name in errors:
                    continue
                try:
                    evs = adapter.lookup(lemma)
                    # Filter out NOT_FOUND responses for secondary candidate lemma queries
                    found_evs = [e for e in evs if e.metadata.get("status") == "FOUND"]
                    for e in found_evs:
                        if e.lemma is None:
                            e.lemma = lemma
                    add_evidence(found_evs)
                except Exception as e:
                    # Do not overwrite primary error if secondary lookup fails
                    pass

        # 5. Aggregate and Rank Evidence
        result = EvidenceAggregator.aggregate(
            query=query,
            normalized_query=target,
            all_evidence=all_evidence,
            errors=errors
        )

        return result
