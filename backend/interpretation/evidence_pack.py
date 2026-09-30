"""
Evidence Pack Builder for SOL AI.
Assembles raw Evidence objects from UnifiedResult into structured, unflattened
EvidencePack categories for the LLM Interpreter.
"""

from typing import List, Dict, Any, Optional
from backend.schemas.result import UnifiedResult
from backend.schemas.evidence import Evidence
from backend.interpretation.schemas import EvidencePack
from backend.interpretation.context_selector import SentamizhContextSelector


LITERARY_EVIDENCE_TYPES = {
    "literary",
    "corpus",
    "citation",
    "literary_context",
}


def _morphology_sort_key(ev: Evidence) -> int:
    """
    Priority order for morphology evidence:
    0: Core FST analysis (analysis_type == 'core' and fst_model present)
    1: Standard/lexical core morphology map (e.g. WordNet morphtable)
    2: Guesser FST analysis (analysis_type == 'guesser')
    """
    atype = (ev.metadata.get("analysis_type") or "").lower()
    fst = ev.metadata.get("fst_model")
    has_morph = bool(ev.morphology)

    if atype == "core" and fst and has_morph:
        return 0
    elif atype == "guesser" and has_morph:
        return 1
    elif atype != "guesser" and not fst:
        return 2
    return 3


def build_evidence_pack(
    unified_result: UnifiedResult,
    max_literary_contexts: int = 5,
    context_selector: Optional[SentamizhContextSelector] = None,
    query_context: Optional[str] = None,
) -> EvidencePack:
    """
    Categorizes raw Evidence objects from UnifiedResult into an EvidencePack.
    Applies SentamizhContextSelector to literary evidence to limit context size.
    Preserves original Evidence objects and source provenance without flattening.
    Ensures Core FST evidence takes priority over Guesser FST evidence while preserving both.
    """
    if context_selector is None:
        context_selector = SentamizhContextSelector(max_contexts=max_literary_contexts)

    query = unified_result.query
    normalized_query = unified_result.normalized_query
    candidates = unified_result.lemma_candidates or [normalized_query]

    # Filter strictly for FOUND status evidence objects
    found_evidences = [
        ev for ev in unified_result.evidence
        if ev.metadata.get("status") == "FOUND" or ev.metadata.get("status") is None
    ]

    morphology_evs: List[Evidence] = []
    lexical_evs: List[Evidence] = []
    raw_literary_evs: List[Evidence] = []
    related_evs: List[Evidence] = []

    for ev in found_evidences:
        ev_type = (ev.evidence_type or "").lower()
        src = ev.source or ""

        # Categorize
        if src == "ThamizhiMorph" or ev_type == "morphology" or "fst_model" in ev.metadata:
            morphology_evs.append(ev)
        elif ev_type in LITERARY_EVIDENCE_TYPES:
            raw_literary_evs.append(ev)
        elif src in ["Thani Thamizh Akarathi", "Tamil WordNet"] or ev_type in ["lexical", "gloss", "sense"]:
            if ev.metadata.get("type") == "morphtable":
                # WordNet morphology root mapping
                morphology_evs.append(ev)
            else:
                lexical_evs.append(ev)
            if ev.relations or "synset_id" in ev.metadata:
                related_evs.append(ev)
        else:
            lexical_evs.append(ev)

    # Sort morphology evidence so CORE FST > GUESSER FST while preserving both
    morphology_evs.sort(key=_morphology_sort_key)

    # Apply deterministic context selection on literary evidence
    selected_literary_evs = context_selector.select(
        evidence_list=raw_literary_evs,
        query=normalized_query,
        lemma_candidates=candidates,
        max_contexts=max_literary_contexts,
    )

    # Detect conflicts (e.g. multiple distinct candidate lemmas or competing definitions)
    conflicts: List[Dict[str, Any]] = []
    unique_lemmas = set(candidates)
    if len(unique_lemmas) > 1:
        conflicts.append({
            "type": "competing_lemmas",
            "candidates": list(unique_lemmas),
            "description": f"Multiple lemma candidates derived from morphology: {', '.join(unique_lemmas)}"
        })

    # Evidence counts summary
    counts = {
        "total_found": len(found_evidences),
        "morphology_count": len(morphology_evs),
        "lexical_count": len(lexical_evs),
        "raw_literary_count": len(raw_literary_evs),
        "selected_literary_count": len(selected_literary_evs),
        "related_count": len(related_evs),
    }

    return EvidencePack(
        query=query,
        normalized_query=normalized_query,
        query_context=query_context,
        lemma_candidates=candidates,
        morphology_evidence=morphology_evs,
        lexical_evidence=lexical_evs,
        literary_evidence=selected_literary_evs,
        related_evidence=related_evs,
        conflicts=conflicts,
        source_provenance=unified_result.resource_summary or {},
        evidence_counts=counts,
    )
