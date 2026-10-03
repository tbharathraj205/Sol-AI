"""
System prompts and evidence prompt formatting templates for the SOL AI LLM Interpreter.
"""

from typing import Optional
from backend.interpretation.schemas import EvidencePack, WSDResult

SYSTEM_PROMPT = """You are the interpretation layer of SOL AI, a Tamil Etymological and Morphological Intelligence system.

CRITICAL INSTRUCTIONS & GROUNDING RULES:
1. You are NOT the Tamil knowledge base. The retrieved resource evidence supplied in this prompt IS your sole knowledge base.
2. Your task is to interpret, synthesize, explain, and organize ONLY the supplied EvidencePack.
3. ABSOLUTELY PROHIBITED: Do NOT fabricate or hallucinate any meanings, root lemmas, morphology rules, literary references, authors, works, etymologies, semantic relations, historical claims, citations, translations, or metadata.
4. If evidence is insufficient or empty: state explicitly that SOL AI resources do not currently possess sufficient evidence for this term.
5. If evidence contains conflicts or competing candidates: preserve and explain the conflict. Do NOT force a single lemma choice when the evidence does not support one clearly.
6. Evidence Hierarchy:
   - CORE FST ANALYSIS > LEXICAL MAPPING > GUESSER ANALYSIS.
   - Core analyses take precedence over guesser analyses, but guesser evidence must still be disclosed in uncertainties if present.
7. Distinguish DIRECTLY SUPPORTED facts from CONTEXTUAL INTERPRETATION and UNCERTAINTIES.
8. CONTEXT-AWARE SENSE INTERPRETATION & DETERMINISTIC WSD HANDOFF:
   - The user's highlighted word may be polysemous (பலபொருள் ஒரு சொல்).
   - The deterministic Python WSD layer has already evaluated the user context against all candidate senses and determined the authoritative contextual sense.
   - Treat the deterministic WSD selection as authoritative.
   - For "contextual_meaning": Return the exact selected sense provided by the deterministic WSD layer in the prompt. If WSD abstained or returned null, "contextual_meaning" MUST be null. Do NOT replace it with another candidate.
   - For "contextual_interpretation": Synthesize and explain why the selected sense fits the supplied context sentence and evidence. MUST BE WRITTEN IN TAMIL (தமிழ்). If WSD abstained or found ambiguity, explain the contextual uncertainty rather than inventing a meaning.
   - "meaning" MUST still contain the general documented definitions/senses (separated by semicolons). Do NOT overwrite general meaning with contextual meaning.
   - If no Query Context is provided, "contextual_meaning" MUST be null.

You MUST return valid JSON matching the following SOLResponse JSON schema:
{
  "query": "original query string",
  "normalized_query": "normalized query string",
  "lemma": "primary root lemma or null if unknown",
  "meaning": "primary definition(s) or null if unsupported. MUST BE WRITTEN IN TAMIL (தமிழ்).",
  "contextual_meaning": "The exact selected sense determined by deterministic WSD, or null if WSD abstained or no context provided. MUST BE WRITTEN IN TAMIL (தமிழ்).",
  "contextual_interpretation": "grounded summary explanation synthesizing why the selected sense fits the user context without fabrication. MUST BE WRITTEN IN TAMIL (தமிழ்).",
  "sources": ["ThamizhiMorph", "Sentamizh"],
  "uncertainties": ["explicit notes on missing data, conflicts, guesser analyses, or contextual ambiguity"],
  "evidence_summary": {"total_found": 0, "morphology_count": 0, "lexical_count": 0, "raw_literary_count": 0, "selected_literary_count": 0, "related_count": 0}
}
"""


def format_evidence_prompt(pack: EvidencePack, wsd_result: Optional[WSDResult] = None) -> str:
    """
    Formats the EvidencePack into structured text sections for LLM input.
    Injects authoritative deterministic WSD result when context is present.
    """
    wsd = wsd_result or getattr(pack, "wsd_result", None)

    lines = []
    lines.append("=== QUERY ===")
    lines.append(f"Query: {pack.query}")
    lines.append(f"Normalized Query: {pack.normalized_query}")
    if pack.query_context:
        lines.append(f"Query Context (User Sentence): {pack.query_context}")
    lines.append(f"Lemma Candidates: {', '.join(pack.lemma_candidates) if pack.lemma_candidates else 'None'}")
    lines.append("")

    if pack.query_context and wsd:
        lines.append("=== CONTEXTUAL WORD-SENSE DISAMBIGUATION (DETERMINISTIC WSD SELECTION) ===")
        lines.append(f"WSD Status: {wsd.status}")
        lines.append(f"WSD Confidence: {wsd.confidence}")
        lines.append(f"WSD Evidence Strength (Score): {wsd.score:.1f}")
        selected_text = wsd.selected_sense or "None (Abstained / Insufficient Evidence / Ambiguous)"
        lines.append(f"Authoritative Selected Sense: {selected_text}")
        if wsd.reasons:
            lines.append(f"Selection Reasons: {'; '.join(wsd.reasons)}")
        if wsd.candidates:
            lines.append("Evaluated Candidate Senses:")
            for idx, c_score in enumerate(wsd.candidates, 1):
                c = c_score.candidate
                lines.append(f"  [{idx}] Source: {c.source} | Sense: {c.definition} | Score: {c_score.score:.1f}")
        lines.append("Notice: The deterministic WSD layer has selected the contextual sense. Treat that selection as authoritative. Explain why it fits the supplied context in 'contextual_interpretation'. Do not replace it with another candidate. If WSD abstained, explain the uncertainty rather than inventing a contextual meaning.")
        lines.append("")

    lines.append("=== LEMMA / MORPHOLOGY ===")
    if pack.morphology_evidence:
        for idx, ev in enumerate(pack.morphology_evidence, 1):
            src = ev.source
            model = ev.metadata.get("fst_model", ev.metadata.get("type", "unknown"))
            analysis_type = (ev.metadata.get("analysis_type") or "core").upper()
            raw_foma = ev.metadata.get("raw_foma_output", "")
            morph_dict = ev.morphology or {}
            lines.append(f"[{idx}] Source: {src} | Model: {model} [{analysis_type}]")
            lines.append(f"    Lemma: {ev.lemma}")
            lines.append(f"    POS: {ev.pos or morph_dict.get('pos', 'N/A')}")
            lines.append(f"    Morphology Components: {morph_dict}")
            if raw_foma:
                lines.append(f"    Raw Foma Output: {raw_foma}")
    else:
        lines.append("No morphological evidence available.")
    lines.append("")

    lines.append("=== LEXICAL EVIDENCE ===")
    if pack.lexical_evidence:
        for idx, ev in enumerate(pack.lexical_evidence, 1):
            src = ev.source
            lemma = ev.lemma
            meaning = ev.meaning or "N/A"
            pos = ev.pos or (ev.morphology or {}).get("pos", "N/A")
            freq = ev.metadata.get("frequency", "N/A")
            lines.append(f"[{idx}] Source: {src} | Headword: {lemma} | POS: {pos} | Freq: {freq}")
            lines.append(f"    Meaning/Gloss: {meaning}")
            if ev.passage:
                lines.append(f"    Example/Passage: {ev.passage}")
    else:
        lines.append("No lexical dictionary evidence available.")
    lines.append("")

    lines.append("=== LITERARY EVIDENCE ===")
    if pack.literary_evidence:
        for idx, ev in enumerate(pack.literary_evidence, 1):
            src = ev.source
            work = ev.work or ev.metadata.get("source_text", "Unknown Work")
            period = ev.period or ev.metadata.get("period", "Unknown Period")
            verse_num = ev.metadata.get("verse_number", ev.metadata.get("verse_id", "N/A"))
            passage = ev.passage or ev.metadata.get("classical_tamil", "N/A")
            modern = ev.meaning or ev.metadata.get("modern_tamil", "N/A")

            lines.append(f"[{idx}] Source: {src} | Work: {work} | Period: {period} | Verse #: {verse_num}")
            lines.append(f"    Classical Verse: {passage}")
            if modern and modern != "N/A":
                lines.append(f"    Modern Tamil Gloss: {modern}")
    else:
        lines.append("No classical literary evidence available.")
    lines.append("")

    lines.append("=== RELATIONSHIPS ===")
    if pack.related_evidence:
        for idx, ev in enumerate(pack.related_evidence, 1):
            rel_str = ", ".join(ev.relations) if ev.relations else str(ev.metadata.get("synset_id", ""))
            lines.append(f"[{idx}] Source: {ev.source} | Headword: {ev.lemma} | Relations: {rel_str}")
    else:
        lines.append("No explicit lexical relationships available.")
    lines.append("")

    lines.append("=== CONFLICTS ===")
    if pack.conflicts:
        for idx, conf in enumerate(pack.conflicts, 1):
            lines.append(f"[{idx}] Type: {conf.get('type')} | Description: {conf.get('description')}")
    else:
        lines.append("No conflicts detected across evidence sources.")
    lines.append("")

    lines.append("=== SOURCE PROVENANCE ===")
    for src, summary in pack.source_provenance.items():
        status = summary.get("status", "NOT_ATTEMPTED")
        count = summary.get("count", 0)
        lines.append(f"- {src}: Status={status}, Entries={count}")
    lines.append("")

    return "\n".join(lines)
