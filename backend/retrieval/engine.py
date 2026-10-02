import sys
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from backend.query.normalizer import QueryNormalizer
from backend.schemas.evidence import Evidence
from backend.schemas.result import UnifiedResult
from backend.resources.thamizhimorph import ThamizhiMorphAdapter
from backend.resources.akarathi import ThaniThamizhAkarathiAdapter
from backend.resources.wordnet import TamilWordNetAdapter
from backend.resources.sentamizh import SentamizhAdapter
from backend.resources.project_madurai import ProjectMaduraiExactAdapter
from backend.resources.project_madurai_semantic import ProjectMaduraiSemanticAdapter
from backend.retrieval.aggregator import EvidenceAggregator

logger = logging.getLogger(__name__)

# Step 3F: Empirically calibrated semantic candidate pool and similarity threshold.
SEMANTIC_CANDIDATE_K = 25
SEMANTIC_SIMILARITY_THRESHOLD = 0.845


class RetrievalEngine:
    """
    Unified Retrieval Engine for SOL AI.
    Coordinates multi-stage retrieval across ThamizhiMorph, Thani Thamizh Akarathi,
    Tamil WordNet, Sentamizh, and Project Madurai adapters:
      Pass 1: Exact surface retrieval
      Pass 2: Lemma / root retrieval
      Pass 3: Semantic retrieval (Project Madurai)
    with stable deduplication and fault-tolerant error boundaries.
    """

    def __init__(
        self,
        thamizhimorph: Optional[ThamizhiMorphAdapter] = None,
        akarathi: Optional[ThaniThamizhAkarathiAdapter] = None,
        wordnet: Optional[TamilWordNetAdapter] = None,
        sentamizh: Optional[SentamizhAdapter] = None,
        project_madurai: Optional[ProjectMaduraiExactAdapter] = None,
        project_madurai_semantic: Optional[ProjectMaduraiSemanticAdapter] = None,
        enable_semantic: bool = True,
        semantic_candidate_k: int = SEMANTIC_CANDIDATE_K,
        semantic_similarity_threshold: float = SEMANTIC_SIMILARITY_THRESHOLD,
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
        self.enable_semantic = enable_semantic
        self.semantic_candidate_k = semantic_candidate_k
        self.semantic_similarity_threshold = semantic_similarity_threshold

        # Lazy load Wiktionary so it doesn't fail if the db is still building
        try:
            from backend.resources.wiktionary import TamilWiktionaryAdapter
            self.wiktionary = TamilWiktionaryAdapter()
        except ImportError:
            self.wiktionary = None

        # Pass 1 deterministic adapters
        self.adapters = {
            "ThamizhiMorph": self.thamizhimorph,
            "Tamil Wiktionary": self.wiktionary,
            "Thani Thamizh Akarathi": self.akarathi,
            "Tamil WordNet": self.wordnet,
            "Sentamizh": self.sentamizh,
            "Project Madurai": self.project_madurai,
        }
        # Remove any None adapters
        self.adapters = {k: v for k, v in self.adapters.items() if v is not None}

        # Pass 3 semantic adapter (lazy initialization preserved)
        if not self.enable_semantic:
            self.project_madurai_semantic = None
        elif project_madurai_semantic is not None:
            self.project_madurai_semantic = project_madurai_semantic
        else:
            self.project_madurai_semantic = ProjectMaduraiSemanticAdapter()

    def _evaluate_semantic_short_circuit(
        self,
        query: str,
        all_evidence: List[Evidence],
    ) -> Tuple[bool, str]:
        """
        Evaluate whether semantic escalation is necessary based on deterministic evidence.

        Short-circuit heuristic:
        - Condition A (Project Madurai exact saturation): If Project Madurai exact retrieval
          already returns its configured deterministic evidence limit (25 results),
          semantic retrieval is redundant.
        - Condition B (Strong deterministic literary evidence): If exact/lemma retrieval
          already provides substantial Project Madurai/Sentamizh literary evidence (>= 10)
          supported by lexical or morphological evidence.
        - Condition C (Conceptual query protection): Queries with weak or no deterministic
          evidence must NOT be skipped, ensuring conceptual/thematic queries reach semantic search.

        :param query: Normalized query string
        :param all_evidence: Accumulated deterministic evidence from Pass 1 and Pass 2
        :return: (should_skip: bool, reason: str)
        """
        pm_exact_evs = [
            e for e in all_evidence
            if e.source == "Project Madurai"
            and e.metadata.get("status") == "FOUND"
            and e.metadata.get("retrieval_method") == "exact"
        ]

        # Condition A: Project Madurai exact retrieval reached deterministic limit (25)
        if len(pm_exact_evs) >= 25:
            return True, f"Project Madurai exact evidence saturated ({len(pm_exact_evs)} >= 25 exact matches)"

        literary_evs = [
            e for e in all_evidence
            if e.source in ("Project Madurai", "Sentamizh")
            and e.metadata.get("status") == "FOUND"
            and e.evidence_type == "literary_context"
        ]
        lexical_evs = [
            e for e in all_evidence
            if e.source in ("Tamil Wiktionary", "Thani Thamizh Akarathi", "Tamil WordNet")
            and e.metadata.get("status") == "FOUND"
        ]
        morph_evs = [
            e for e in all_evidence
            if e.source == "ThamizhiMorph"
            and e.metadata.get("status") == "FOUND"
        ]

        # Condition B: Strong deterministic literary evidence supported by lexical/morphology
        if len(literary_evs) >= 10 and (len(lexical_evs) > 0 or len(morph_evs) > 0):
            return True, (
                f"Substantial deterministic literary evidence ({len(literary_evs)} passages) "
                f"with lexical/morphological support ({len(lexical_evs)} lexical, {len(morph_evs)} morph)"
            )

        # Condition C: Weak/no deterministic evidence -> run semantic
        return False, "Deterministic evidence insufficient"

    def search(
        self,
        query: str,
        lemma: Optional[str] = None,
        enable_semantic: Optional[bool] = None,
        force_semantic: bool = False,
    ) -> UnifiedResult:
        """
        Perform a unified evidence search for a Tamil input query.

        Retrieval Sequence:
          Pass 1: Surface / exact retrieval across deterministic adapters
          Pass 2: Lemma / root retrieval across lexical and literary resources
          Pass 3: Semantic retrieval across Project Madurai corpus
          Deduplication: Stable chunk identity deduplication (preserving deterministic evidence)
          Evidence Aggregation: Priority sorting and cross-resource support mapping

        :param query: Surface query string
        :param lemma: Optional caller-supplied lemma
        :param enable_semantic: Optional override to toggle semantic retrieval per call
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
                errors={},
            )

        all_evidence: List[Evidence] = []
        errors: Dict[str, str] = {}
        seen_evidence_keys = set()
        seen_madurai_chunks: Dict[str, Evidence] = {}

        # Helper to safely append deduplicated evidence
        def add_evidence(ev_list: List[Evidence]):
            for ev in ev_list:
                cid = ev.source_id or ev.metadata.get("chunk_id")
                if ev.source == "Project Madurai" and cid:
                    if cid in seen_madurai_chunks:
                        # Existing chunk already recorded; preserve earlier (deterministic) evidence
                        continue
                    seen_madurai_chunks[cid] = ev

                key = (ev.source, ev.evidence_type, ev.surface, ev.lemma, ev.passage, ev.source_id)
                if key not in seen_evidence_keys:
                    seen_evidence_keys.add(key)
                    all_evidence.append(ev)

        # 2. Pass 1: Surface Lookup across deterministic adapters
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
                            "status": "ERROR",
                        },
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
            "Project Madurai": self.project_madurai,
        }
        secondary_adapters = {k: v for k, v in secondary_adapters.items() if v is not None}

        for c_lemma in sorted(candidate_lemmas):
            for name, adapter in secondary_adapters.items():
                if name in errors:
                    continue
                try:
                    evs = adapter.lookup(c_lemma)
                    # Filter out NOT_FOUND responses for secondary candidate lemma queries
                    found_evs = [e for e in evs if e.metadata.get("status") == "FOUND"]
                    for e in found_evs:
                        if e.lemma is None:
                            e.lemma = c_lemma
                    add_evidence(found_evs)
                except Exception as e:
                    # Do not overwrite primary error if secondary lookup fails
                    pass

        # 5. Pass 3: Semantic Retrieval (Project Madurai)
        run_semantic = self.enable_semantic if enable_semantic is None else enable_semantic
        if run_semantic and self.project_madurai_semantic is not None:
            should_skip, reason = self._evaluate_semantic_short_circuit(target, all_evidence)
            if should_skip and not force_semantic:
                logger.info(
                    "Semantic retrieval skipped: sufficient deterministic evidence\nquery=%s\nreason=%s",
                    target,
                    reason,
                )
            else:
                if force_semantic:
                    logger.info(
                        "Semantic retrieval enabled: forced by caller\nquery=%s",
                        target,
                    )
                else:
                    logger.info(
                        "Semantic retrieval enabled: deterministic evidence insufficient\nquery=%s",
                        target,
                    )
                # Determine appropriate lemma: caller-supplied takes precedence,
                # otherwise single discovered candidate lemma if available.
                semantic_lemma = lemma
                if semantic_lemma is None and candidate_lemmas:
                    sorted_cands = sorted(candidate_lemmas)
                    if len(sorted_cands) == 1:
                        semantic_lemma = sorted_cands[0]

                try:
                    semantic_evs = self.project_madurai_semantic.lookup(
                        query=target,
                        lemma=semantic_lemma,
                        top_k=self.semantic_candidate_k,
                        threshold=self.semantic_similarity_threshold,
                    )

                    # Defensive check: if adapter returned an ERROR evidence item,
                    # isolate it so it does not contaminate user-facing evidence or errors dict.
                    has_error_ev = any(e.metadata.get("status") == "ERROR" for e in semantic_evs)
                    if has_error_ev:
                        err_msgs = [e.metadata.get("error") for e in semantic_evs if e.metadata.get("status") == "ERROR"]
                        logger.warning(
                            "Project Madurai semantic retrieval returned ERROR for query %r: %s",
                            target,
                            err_msgs,
                        )
                        semantic_evs = []

                    # Filter strictly for FOUND evidence passing calibrated similarity threshold
                    found_semantic = [
                        e for e in semantic_evs
                        if e.metadata.get("status") == "FOUND"
                        and e.metadata.get("similarity_score", 0.0) >= self.semantic_similarity_threshold
                    ]

                    for sem_ev in found_semantic:
                        cid = sem_ev.source_id or sem_ev.metadata.get("chunk_id")
                        if cid and cid in seen_madurai_chunks:
                            # Chunk already retrieved via deterministic Pass 1 (exact) or Pass 2 (lemma).
                            # Preserve deterministic evidence and provenance. Do NOT downgrade or overwrite.
                            existing_ev = seen_madurai_chunks[cid]
                            if "similarity_score" in sem_ev.metadata:
                                existing_ev.metadata.setdefault(
                                    "similarity_score",
                                    sem_ev.metadata["similarity_score"],
                                )
                            continue

                        # Novel semantic evidence
                        if cid:
                            seen_madurai_chunks[cid] = sem_ev
                        key = (
                            sem_ev.source,
                            sem_ev.evidence_type,
                            sem_ev.surface,
                            sem_ev.lemma,
                            sem_ev.passage,
                            sem_ev.source_id,
                        )
                        if key not in seen_evidence_keys:
                            seen_evidence_keys.add(key)
                            all_evidence.append(sem_ev)

                except Exception as e:
                    # Semantic failure isolation: log warning and continue without crashing engine
                    logger.warning(
                        "Project Madurai semantic retrieval failed with exception for query %r: %s",
                        target,
                        e,
                    )

        # 6. Aggregate and Rank Evidence
        result = EvidenceAggregator.aggregate(
            query=query,
            normalized_query=target,
            all_evidence=all_evidence,
            errors=errors,
        )

        return result
