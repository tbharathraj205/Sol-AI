"""
LLM Interpreter module for SOL AI.
Defines abstract BaseLLMInterpreter interface, MockLLMInterpreter (offline/deterministic),
and GeminiLLMInterpreter (REST API integration).
"""

import os
import json
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from backend.interpretation.schemas import (
    EvidencePack,
    SOLResponse,
    LiteraryContextItem,
    LexicalSenseItem,
    build_lexical_senses,
    SenseCandidate,
    WSDResult,
    extract_sense_candidates,
)
from backend.interpretation.prompts import SYSTEM_PROMPT, format_evidence_prompt

OfflineTranslator = None


class BaseLLMInterpreter(ABC):
    """
    Abstract interface for SOL AI LLM Interpreters.
    """

    @abstractmethod
    def interpret(
        self,
        pack: EvidencePack,
        wsd_result: Optional[WSDResult] = None
    ) -> SOLResponse:
        """
        Receives an EvidencePack and returns a structured SOLResponse.
        Consumes the authoritative deterministic WSDResult if available.
        """
        pass


class MockLLMInterpreter(BaseLLMInterpreter):
    """
    Deterministic, grounded interpreter that synthesizes SOLResponse directly
    from EvidencePack without external API calls. Used for unit testing and offline execution.
    """

    def __init__(self, wsd: Optional[Any] = None):
        self._wsd = wsd

    def _get_wsd(self):
        if self._wsd is None:
            from backend.interpretation.wsd import TamilWSD
            self._wsd = TamilWSD()
        return self._wsd

    def interpret(
        self,
        pack: EvidencePack,
        wsd_result: Optional[WSDResult] = None
    ) -> SOLResponse:
        query = pack.query
        norm_query = pack.normalized_query

        # Determine lemma only if evidence is found
        lemma = None
        if pack.evidence_counts.get("total_found", 0) > 0:
            if pack.morphology_evidence:
                lemma = pack.morphology_evidence[0].lemma
            elif pack.lexical_evidence:
                lemma = pack.lexical_evidence[0].lemma
            elif pack.lemma_candidates:
                lemma = pack.lemma_candidates[0]

        # Determine meanings
        meanings = []
        for ev in pack.lexical_evidence:
            if ev.meaning and ev.meaning not in meanings:
                meanings.append(ev.meaning)
        
        meaning_str = "; ".join(meanings) if meanings else None
        
        english_meaning_str = None
        eng_meanings = []
        if meanings and OfflineTranslator is not None:
            try:
                translator = OfflineTranslator.get_instance()
                for m in meanings:
                    # Max length truncation per meaning
                    text_to_translate = m[:400]
                    res = translator.translate(text_to_translate)
                    eng_meanings.append(res)
                english_meaning_str = "; ".join(eng_meanings)
            except Exception as e:
                print(f"[Offline Translation Error] {e}")

        senses_list = build_lexical_senses(meanings, eng_meanings if eng_meanings else None)

        # Determine morphology
        morph_dict = None
        if pack.morphology_evidence:
            first_morph = pack.morphology_evidence[0]
            fst_model = first_morph.metadata.get("fst_model") if hasattr(first_morph, "metadata") else None
            analysis_type = first_morph.metadata.get("analysis_type") if hasattr(first_morph, "metadata") else None
            from backend.resources.thamizhimorph import parse_structured_morphology
            morph_dict = parse_structured_morphology(
                query=pack.query,
                pos=getattr(first_morph, "pos", None),
                raw_morphology=getattr(first_morph, "morphology", None),
                fst_model=fst_model,
                analysis_type=analysis_type,
            )

        # Build literary context items
        from backend.interpretation.literary_processor import process_literary_evidence
        lit_items = process_literary_evidence(
            pack.literary_evidence,
            query=pack.query,
            lemma=lemma,
        )

        # Related words
        rel_words: List[str] = []
        for ev in pack.related_evidence:
            if ev.relations:
                for r in ev.relations:
                    if r not in rel_words:
                        rel_words.append(r)
        
        # Fallback heuristic: extract short words from dictionary meanings if empty
        if not rel_words and meaning_str:
            import re
            parts = re.split(r'[,;]\s*', meaning_str)
            for p in parts:
                p = p.strip(' .')
                is_tamil = bool(re.match(r'^[\u0B80-\u0BFF\s]+$', p))
                if p and is_tamil and len(p.split()) <= 2 and len(p) > 2 and p != query:
                    if not any(char in p for char in ['(', ')', '[', ']', '"', "'"]):
                        if p not in rel_words:
                            rel_words.append(p)

        # Sources
        sources = [
            src for src, info in pack.source_provenance.items()
            if info.get("status") == "FOUND"
        ]

        # Uncertainties & conflicts
        uncertainties: List[str] = []
        if pack.evidence_counts.get("total_found", 0) == 0:
            uncertainties.append("No evidence found in available SOL AI resources.")

        # Check if ONLY guesser analyses are available for morphology
        has_core_morph = any(ev.metadata.get("analysis_type") == "core" for ev in pack.morphology_evidence)
        guesser_morphs = [ev for ev in pack.morphology_evidence if ev.metadata.get("analysis_type") == "guesser"]
        
        if not has_core_morph and guesser_morphs:
            fst_name = guesser_morphs[0].metadata.get("fst_model", "guesser")
            uncertainties.append(f"Morphological analysis derived from guesser model ({fst_name}).")

        for conf in pack.conflicts:
            uncertainties.append(f"Conflict: {conf.get('description')}")

        # Contextual interpretation synthesis via deterministic Tamil WSD (authoritative single execution)
        wsd_res = wsd_result or getattr(pack, "wsd_result", None)
        if wsd_res is None and pack.query_context and pack.query_context.strip():
            # If wsd_result was not passed from service layer, execute WSD once as fallback
            candidate_objects = extract_sense_candidates(pack)
            if candidate_objects:
                wsd = self._get_wsd()
                wsd_res = wsd.disambiguate(
                    query=query,
                    context_sentence=pack.query_context,
                    candidate_senses=candidate_objects,
                )

        contextual_meaning_mock = None
        if wsd_res:
            if wsd_res.selected_sense:
                contextual_meaning_mock = wsd_res.selected_sense
            elif pack.query_context and pack.query_context.strip():
                contextual_meaning_mock = None
                if wsd_res.status in ("ambiguous", "insufficient_evidence", "conflicting_signals"):
                    amb_reason = (
                        f"Contextual sense ambiguity: {wsd_res.reasons[0]}"
                        if wsd_res.reasons
                        else "Contextual sense ambiguity: The provided context does not establish sufficient discriminative evidence to select a unique lexical sense."
                    )
                    if not any("ambiguity" in u.lower() or "context" in u.lower() for u in uncertainties):
                        uncertainties.append(amb_reason)

        if pack.evidence_counts.get("total_found", 0) == 0:
            interpretation = (
                f"No evidence was retrieved from SOL AI resource adapters for query '{query}'. "
                "The system cannot verify or interpret this term without external fabrication."
            )
        else:
            parts = []
            if lemma:
                parts.append(f"The query '{query}' resolves to root/lemma '{lemma}'.")
            if morph_dict and morph_dict.get("pos"):
                parts.append(f"Morphology indicates part-of-speech '{morph_dict['pos']}'.")
            if contextual_meaning_mock:
                parts.append(
                    f"In the user's context ('{pack.query_context}'), the word reflects the specific sense: '{contextual_meaning_mock}'."
                )
            elif meaning_str:
                parts.append(f"Lexical resources define the term as: {meaning_str}.")
            if lit_items:
                works = list(set([item.work for item in lit_items if item.work]))
                parts.append(
                    f"Selected {len(lit_items)} classical literary occurrences across works: {', '.join(works)}."
                )
            interpretation = " ".join(parts)

        return SOLResponse(
            query=query,
            normalized_query=norm_query,
            lemma=lemma,
            meaning=meaning_str,
            english_meaning=english_meaning_str,
            senses=senses_list,
            morphology=morph_dict,
            contextual_meaning=contextual_meaning_mock,
            contextual_interpretation=interpretation,
            wsd_result=wsd_res,
            literary_context=lit_items,
            related_words=rel_words,
            sources=sources,
            uncertainties=uncertainties,
            evidence_summary=pack.evidence_counts,
        )


class GeminiLLMInterpreter(BaseLLMInterpreter):
    """
    LLM Interpreter using Google Gemini API endpoint via standard library REST requests.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not configured. Set GEMINI_API_KEY or use SOL_LLM_PROVIDER=mock.")
        self.model = model or os.environ.get("SOL_GEMINI_MODEL", "gemini-3.6-flash")

    def interpret(
        self,
        pack: EvidencePack,
        wsd_result: Optional[WSDResult] = None
    ) -> SOLResponse:
        wsd_res = wsd_result or getattr(pack, "wsd_result", None)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        prompt_text = format_evidence_prompt(pack, wsd_result=wsd_res)

        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": prompt_text}]}
            ],
            "systemInstruction": {
                "parts": [{"text": SYSTEM_PROMPT}]
            },
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.1
            }
        }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text_content = data["candidates"][0]["content"]["parts"][0]["text"]
                json_data = json.loads(text_content)
                sol_resp = SOLResponse(**json_data)
                if wsd_res:
                    sol_resp.wsd_result = wsd_res
                    if wsd_res.selected_sense:
                        sol_resp.contextual_meaning = wsd_res.selected_sense
                return sol_resp
        except urllib.error.HTTPError as err:
            err_msg = err.read().decode("utf-8") if err.fp else str(err)
            raise RuntimeError(f"Gemini API Error (HTTP {err.code}): {err_msg[:200]}")
        except json.JSONDecodeError as err:
            raise RuntimeError(f"Malformed JSON response from Gemini API: {str(err)}")
        except Exception as err:
            raise RuntimeError(f"Gemini API request failed: {str(err)}")


class GroqLLMInterpreter(BaseLLMInterpreter):
    """
    LLM Interpreter using Groq API endpoint via standard library REST requests.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable is not configured. Set GROQ_API_KEY or use SOL_LLM_PROVIDER=mock.")
        self.model = model or os.environ.get("SOL_GROQ_MODEL", "qwen/qwen3.8-27b")

    def interpret(
        self,
        pack: EvidencePack,
        wsd_result: Optional[WSDResult] = None
    ) -> SOLResponse:
        wsd_res = wsd_result or getattr(pack, "wsd_result", None)
        url = "https://api.groq.com/openai/v1/chat/completions"
        prompt_text = format_evidence_prompt(pack, wsd_result=wsd_res)

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt_text}
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                    "User-Agent": "SOL-AI/1.0"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text_content = data["choices"][0]["message"]["content"]
                json_data = json.loads(text_content)
                sol_resp = SOLResponse(**json_data)
                if wsd_res:
                    sol_resp.wsd_result = wsd_res
                    if wsd_res.selected_sense:
                        sol_resp.contextual_meaning = wsd_res.selected_sense
                return sol_resp
        except urllib.error.HTTPError as err:
            err_msg = err.read().decode("utf-8") if err.fp else str(err)
            raise RuntimeError(f"Groq API Error (HTTP {err.code}): {err_msg[:200]}")
        except json.JSONDecodeError as err:
            raise RuntimeError(f"Malformed JSON response from Groq API: {str(err)}")
        except Exception as err:
            raise RuntimeError(f"Groq API request failed: {str(err)}")



def get_interpreter(provider: Optional[str] = None) -> BaseLLMInterpreter:
    """
    Factory function to instantiate configured BaseLLMInterpreter.
    Provider option read from SOL_LLM_PROVIDER env variable if not passed.
    """
    if provider is None:
        provider = os.environ.get("SOL_LLM_PROVIDER", "mock").lower()

    if provider == "gemini":
        return GeminiLLMInterpreter()
    elif provider == "groq":
        return GroqLLMInterpreter()
    elif provider == "mock":
        return MockLLMInterpreter()
    else:
        raise ValueError(f"Unknown SOL_LLM_PROVIDER '{provider}'. Supported options: 'gemini', 'groq', 'mock'.")
