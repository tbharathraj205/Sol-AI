"""
Application and Domain Service Registry for SOL AI.

Provides a thread-safe, lazy process-local service registry encapsulating:
- RetrievalEngine lookup orchestration
- EvidencePack construction
- Interpreter execution with multi-stage LLM fallback (Primary -> Groq -> Mock)
- Grounded post-LLM deterministic overrides (related words, literary context, morphology)

Zero domain logic is placed inside Django views; views interact strictly via this service layer.
"""

import os
import re
import logging
from threading import Lock
from typing import Optional, List, Dict, Any

from backend.retrieval.engine import RetrievalEngine
from backend.interpretation.evidence_pack import build_evidence_pack
from backend.interpretation import interpreter as interpreter_module
from backend.interpretation.schemas import (
    EvidencePack,
    SOLResponse,
    LiteraryContextItem,
    LexicalSenseItem,
    parse_senses_from_meaning_string,
)

logger = logging.getLogger(__name__)


class SOLServiceRegistry:
    """
    Process-local, thread-safe service registry for SOL AI.
    Reuses expensive resources (RetrievalEngine, adapters, SQLite connections)
    within the worker process across HTTP requests without global state leakage.
    """

    _instance: Optional["SOLServiceRegistry"] = None
    _lock: Lock = Lock()

    def __init__(self, engine: Optional[RetrievalEngine] = None):
        self._engine: Optional[RetrievalEngine] = engine
        self._engine_lock: Lock = Lock()

    @classmethod
    def get_instance(cls) -> "SOLServiceRegistry":
        """Retrieve or create the process-local singleton service registry."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (useful for test isolation)."""
        with cls._lock:
            cls._instance = None

    def get_engine(self) -> RetrievalEngine:
        """
        Lazily initialize and return the process-local RetrievalEngine.
        Thread-safe to ensure single instantiation under concurrent requests.
        """
        if self._engine is None:
            with self._engine_lock:
                if self._engine is None:
                    logger.info("Initializing SOL AI RetrievalEngine in worker process...")
                    self._engine = RetrievalEngine()
        return self._engine

    def process_query(
        self,
        query: str,
        provider: Optional[str] = None,
        context: Optional[str] = None,
    ) -> SOLResponse:
        """
        Execute the full SOL AI query pipeline:
        1. RetrievalEngine search
        2. EvidencePack aggregation
        3. Interpreter execution with fallback cascade
        4. Deterministic post-processing overrides

        :param query: Raw Tamil query string
        :param provider: Requested LLM provider ('mock', 'gemini', 'groq') or None for env default
        :param context: Optional surrounding contextual text
        :return: Final structured and grounded SOLResponse
        """
        clean_query = str(query).strip()

        # 1. Retrieval
        engine = self.get_engine()
        retrieval_result = engine.search(clean_query)

        # 2. Evidence Pack
        pack = build_evidence_pack(retrieval_result, query_context=context)

        # 3. Interpreter resolution (raises ValueError on bad provider or missing required key)
        interpreter = interpreter_module.get_interpreter(provider)

        # 4. Interpret with fallback cascade
        try:
            response = interpreter.interpret(pack)
        except Exception as primary_err:
            logger.warning("Primary LLM Error: %s", primary_err)

            env_provider = os.environ.get("SOL_LLM_PROVIDER", "mock").lower()

            if env_provider != "groq" and os.environ.get("GROQ_API_KEY"):
                logger.info("Attempting Groq fallback...")
                try:
                    groq_interpreter = interpreter_module.get_interpreter("groq")
                    response = groq_interpreter.interpret(pack)
                except Exception as groq_err:
                    logger.warning(
                        "Groq Fallback Error: %s. Falling back to deterministic mock interpreter.",
                        groq_err,
                    )
                    fallback_interpreter = interpreter_module.get_interpreter("mock")
                    response = fallback_interpreter.interpret(pack)
                    response.contextual_meaning = None
                    response.uncertainties.append(
                        "AI Contextual Interpretation is currently unavailable due to high server load."
                    )
            else:
                logger.info("Falling back to deterministic mock interpreter.")
                fallback_interpreter = interpreter_module.get_interpreter("mock")
                response = fallback_interpreter.interpret(pack)
                response.contextual_meaning = None
                response.uncertainties.append(
                    "AI Contextual Interpretation is currently unavailable due to high server load."
                )

        # 5. Deterministic Structural Overrides
        self._apply_post_overrides(pack=pack, response=response, query=clean_query)

        return response

    def _apply_post_overrides(
        self,
        pack: EvidencePack,
        response: SOLResponse,
        query: str,
    ) -> None:
        """
        Inject deterministic structural evidence from EvidencePack into SOLResponse
        to override any omissions or formatting defects from LLM output.
        """
        # 1. General Meaning: ensure stable lexical meaning inventory from lexical evidence if omitted
        if not response.meaning and pack.lexical_evidence:
            meanings = []
            for ev in pack.lexical_evidence:
                if ev.meaning and ev.meaning not in meanings:
                    meanings.append(ev.meaning)
            if meanings:
                response.meaning = "; ".join(meanings)

        # Ensure structured senses are always populated and synchronized
        if not response.senses and response.meaning:
            response.senses = parse_senses_from_meaning_string(
                response.meaning, response.english_meaning
            )
        elif response.senses and not response.meaning:
            response.meaning = "; ".join(s.raw_text or s.title for s in response.senses)

        # 2. Contextual Meaning Override / Deterministic Disambiguation
        if pack.query_context and pack.query_context.strip():
            candidate_senses = [ev.meaning for ev in pack.lexical_evidence if ev.meaning]
            if candidate_senses:
                from backend.interpretation.wsd import TamilWSD
                wsd = TamilWSD()
                sel_sense, score, _ = wsd.disambiguate(
                    query=query,
                    context_sentence=pack.query_context,
                    candidate_senses=candidate_senses,
                )
                response.contextual_meaning = sel_sense
                if sel_sense is None and not any("ambiguity" in u.lower() or "context" in u.lower() for u in response.uncertainties):
                    response.uncertainties.append(
                        "Contextual sense ambiguity: The provided context does not establish sufficient discriminative evidence to select a unique lexical sense."
                    )
        else:
            response.contextual_meaning = None

        # 3. Related Words Override
        rel_words: List[str] = []
        for ev in pack.related_evidence:
            if hasattr(ev, "relations") and ev.relations:
                for r in ev.relations:
                    if r not in rel_words:
                        rel_words.append(r)

        # Fallback heuristic: extract short words from dictionary meanings if empty
        if not rel_words and response.meaning:
            parts = re.split(r"[,;]\s*", response.meaning)
            for p in parts:
                p = p.strip(" .")
                is_tamil = bool(re.match(r"^[\u0B80-\u0BFF\s]+$", p))
                if p and is_tamil and len(p.split()) <= 2 and len(p) > 2 and p != query:
                    if not any(char in p for char in ["(", ")", "[", "]", '"', "'"]):
                        if p not in rel_words:
                            rel_words.append(p)

        if rel_words:
            response.related_words = rel_words

        # 2. Literary Context Override
        lit_items: List[LiteraryContextItem] = []
        for ev in pack.literary_evidence:
            lit_items.append(
                LiteraryContextItem(
                    work=ev.work or ev.metadata.get("source_text"),
                    author=ev.author,
                    period=ev.period or ev.metadata.get("period"),
                    passage=ev.passage or ev.metadata.get("classical_tamil"),
                    verse_number=str(
                        ev.metadata.get("verse_number", ev.metadata.get("verse_id", ""))
                    ),
                    meaning=ev.meaning or ev.metadata.get("modern_tamil"),
                    source=ev.source or "Sentamizh",
                )
            )
        if lit_items:
            response.literary_context = lit_items

        # 3. Morphology Override
        if pack.morphology_evidence:
            first_morph = pack.morphology_evidence[0]
            fst_model = first_morph.metadata.get("fst_model", "unknown")
            analysis_type = first_morph.metadata.get(
                "analysis_type",
                "guesser" if "guess" in str(fst_model).lower() else "core",
            )
            response.morphology = {
                "pos": getattr(first_morph, "pos", "Unknown"),
                "fst_model": fst_model,
                "analysis_type": analysis_type,
                "raw_morphology": getattr(first_morph, "morphology", None),
            }
