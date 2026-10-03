# WSD Overhaul Implementation Report

**Author / Subsystem:** SOL AI Tamil Lexical & Morphological Intelligence Engine  
**Component:** Contextual Word-Sense Disambiguation (WSD) Pipeline  
**Date:** October 3, 2026  
**Status:** Completed & Formally Verified  

---

## 1. Executive Summary

This report documents the architectural overhaul of the contextual Word-Sense Disambiguation (WSD) pipeline in SOL AI. Previously, WSD suffered from candidate collapse, conflation of general dictionary definitions with contextual sense selection, redundant duplicate executions in both API dispatch and mock interpreters, and ambiguous prompt instructions that allowed downstream LLMs to re-arbitrate lexical sense decisions.

The overhauled architecture implements a deterministic, multi-source, candidate-aware WSD pipeline where:
1. Lexical senses are structured as discrete candidates (`SenseCandidate`) preserving dictionary provenance.
2. Context features are decoupled and extracted into a dedicated feature model (`WSDContextFeatures`).
3. Disambiguation scores candidates deterministically using linguistic signals, proximity boosts, exact/stem overlap, and candidate specificity.
4. Ambiguous, low-confidence, or conflicting contexts trigger principled abstention (`WSDResult(status="abstained", selected_sense=None)`).
5. The Python WSD engine authoritatively owns sense selection, running **exactly once** per query lifecycle.
6. The downstream LLM is strictly confined to explaining and synthesizing the deterministically selected sense, rather than overriding or inventing senses.

---

## 2. Previous Architecture & Forensic Audit Findings

As detailed in `WSD_CURRENT_IMPLEMENTATION_FORENSIC_AUDIT.md`, the legacy system exhibited critical architectural defects:

1. **Candidate Collapse & Loss of Provenance:**
   - Senses from Wiktionary, Akarathi, and WordNet were concatenated into unstructured plain text strings.
   - Akarathi's multi-sense entries were collapsed into a single semicolon-delimited string, obscuring individual sub-senses.
   - WordNet entries (which have `meaning=None` in SOL AI's current data adapters) were inconsistently checked or treated as empty glosses.

2. **Pipeline Redundancy & Double WSD:**
   - `SOLServiceRegistry.process_query()` executed WSD prior to LLM dispatch.
   - `MockLLMInterpreter.interpret()` then executed `TamilWSD.disambiguate()` a second time internally.
   - `_apply_post_overrides()` executed `TamilWSD.disambiguate()` a third time or reassigned fields haphazardly.

3. **Loss of Separation Between General Meaning & Contextual Meaning:**
   - If WSD selected a contextual sense, legacy code frequently overwrote `response.meaning` with that single sense, erasing the full polysemous dictionary definition.
   - When no context was provided, the system arbitrarily selected the first dictionary sense or forced a single interpretation rather than abstaining.

4. **Prompt Inconsistency & Downstream LLM Overreach:**
   - The LLM prompt lacked authoritative boundaries, asking the model to perform both sense selection and synthesis. Different LLM providers (Mock, Gemini, Groq) could diverge or override Python WSD results.

---

## 3. Overhauled WSD Architecture

The new architecture follows a strict single-pass dataflow:

```
User Query ("கால்") + Context Sentence ("கால் கிலோ வாங்கினேன்")
                        │
                        ▼
       Dictionary Retrieval (UnifiedEngine / Adapters)
         ├── Wiktionary (discrete sense definitions)
         ├── Akarathi (delimited traditional definitions)
         └── WordNet (synsets; no glosses)
                        │
                        ▼
        Sense Candidate Extraction (schemas.py)
         └── extract_sense_candidates() -> List[SenseCandidate]
                        │
                        ▼
       WSD Context Feature Extraction (wsd.py)
         └── WSDContextFeatureExtractor.extract() -> WSDContextFeatures
              ├── Query indices & exclusion masks
              ├── Domain signals (Quantity, Somatic, Furniture)
              └── Token stems & distances
                        │
                        ▼
          TamilWSD Scoring & Disambiguation (wsd.py)
         ├── Domain Proximity Boosts (+35.0, scaled by distance)
         ├── Genus & Headword Alignment (+6.0 to +12.0)
         ├── Exact / Stemmed Overlap (+1.5 to +3.5)
         ├── Specificity Density Adjustments (shorter, focused senses favored)
         └── Ambiguity / Conflict / Floor Guards (Abstention check)
                        │
                        ▼
           WSDResult (status="selected", confidence, score)
                        │
                        ├──────────────────────────────────┐
                        ▼                                  ▼
      EvidencePack (wsd_result attached)       response.meaning (Retained Full)
                        │                      response.contextual_meaning = selected_sense
                        ▼                      response.wsd_result = wsd_result
           LLM Interpreter Call
            (Prompt receives authoritative WSD)
            (LLM synthesizes explanation only)
                        │
                        ▼
                   Final SOLResponse
```

---

## 4. Key Subsystem Implementations

### 4.1 Structured Candidate Representation (`backend/interpretation/schemas.py`)

Lexical senses are now preserved as first-class dataclasses:
- `SenseCandidate`:
  - `source`: `"wiktionary"` | `"akarathi"` | `"wordnet"`
  - `headword`: Target lemma
  - `definition`: Explicit Tamil gloss / sense description
  - `pos`: Part of speech
  - `english`: English gloss if present
  - `raw_text`: Complete unparsed entry text for provenance tracking
  - `metadata`: Sub-sense index, domain tags, synset IDs
  - `sense_id`: Deterministic hash/identifier (`{source}_{headword}_{hash}`)
- `CandidateScore`:
  - `candidate`: The underlying `SenseCandidate`
  - `score`: Total float score
  - `reasons`: Detailed explainability log
  - `formatted_sense`: Canonical string representation
- `WSDResult`:
  - `query`: Query word
  - `context`: Context string
  - `selected_candidate`: Top `SenseCandidate` or `None`
  - `selected_sense`: Formatted string representation or `None`
  - `score`: Top score
  - `status`: `"selected"` | `"no_context"` | `"no_candidates"` | `"abstained"`
  - `confidence`: `"high"` | `"medium"` | `"low"` | `"none"`
  - `reasons`: List of score justifications
  - `all_candidates`: All scored candidates
  - Backwards Compatibility: Implements `__iter__` returning `(selected_sense, score, reasons)`.

`extract_sense_candidates()` extracts Wiktionary senses individually, splits Akarathi definitions along linguistic delimiters while retaining provenance, and strictly excludes WordNet entries that have no glosses.

### 4.2 Decoupled Feature Extraction (`backend/interpretation/wsd.py`)

Feature extraction is completely separated into `WSDContextFeatureExtractor`:
- **Query Masking:** Target query tokens and inflected variants (e.g., `கால்`, `காலில்`) are identified by position in the sentence. They are strictly excluded from context tokens to prevent self-matching leakage.
- **Linguistic Domain Sets:**
  - `QUANTITY_UNIT_TERMS`: கிலோ, கிராம், லிட்டர், மீட்டர், நாழி, படி, etc.
  - `SOMATIC_BODY_TERMS`: வலி, உடைந்த, அடிபட்டு, தசை, நடை, முறிந்தது, etc.
  - `FURNITURE_STRUCTURE_TERMS`: மேசை, நாற்காலி, முக்காலி, பீடம், தூண், etc.
- **Domain Indicators:**
  - `FRACTION_INDICATORS`: பங்கு, பகுதி, நாலிலொன்று, கால்வாசி, etc.
  - `ANATOMICAL_INDICATORS`: பாதம், உறுப்பு, தசை, அடி, etc.
  - `FURNITURE_INDICATORS`: தாங்கு, முட்டு, மரம், கால்நடை, etc.
- Distance calculations measure the minimum token distance between the query position and detected domain trigger tokens.

### 4.3 Deterministic Scoring & Principled Abstention

Candidates are scored using a principled rubric:
1. **Domain Proximity Boost:** When a domain signal is detected within 3 tokens of the query, matching candidate senses receive a boost up to `+35.0` (attenuated with distance).
2. **Context-Candidate Overlap:** Stemmed overlap between non-query context tokens and candidate gloss tokens contributes `+1.5` per match; exact matches contribute `+3.5`.
3. **Genus & Headword Weighting:** Candidates whose definitions begin with or contain primary category indicators (`நான்கில் ஒரு பங்கு`, `உறுப்பு`) receive genus weights (`+6.0` to `+12.0`).
4. **Specificity Density Preference:** Senses with concise, dedicated definitions are preferred over sprawling collapsed entries with irrelevant noise.
5. **Principled Abstention:**
   - **No Context:** Returns `status="no_context"`, `selected_sense=None`.
   - **Low-Evidence Floor:** If the top score is below `1.0`, WSD abstains (`status="abstained"`).
   - **Close Competition Guard:** If two candidates from fundamentally different domains compete with score difference `< 1.0` and top score `< 5.0`, WSD abstains.
   - **Domain Conflict Guard:** If strong conflicting domain signals co-occur (e.g., medical anatomical terms alongside quantity units) without clear dominance, WSD abstains.

### 4.4 LLM Contract & Single-Pass Pipeline (`backend/sol_django/api/services.py`, `interpreter.py`)

- **Single Execution:** In `SOLServiceRegistry.process_query()`, `TamilWSD.disambiguate()` is executed once immediately after building the `EvidencePack`.
- **Evidence Injection:** `pack.wsd_result` is populated and passed directly to `interpreter.interpret()`.
- **Prompt Contract:** `SYSTEM_PROMPT` and `format_evidence_prompt()` explicitly inform the LLM that deterministic WSD has already selected the authoritative sense. The LLM is instructed to generate `contextual_interpretation` reflecting that sense without altering or second-guessing it.
- **Post-Override Protection:** `_apply_post_overrides()` directly assigns:
  ```python
  response.wsd_result = wsd_result
  response.contextual_meaning = wsd_result.selected_sense
  ```
  `response.meaning` is preserved as the full general polysemous definition.

---

## 5. Verification & Test Results

### 5.1 Test Matrix (`tests/test_wsd_overhaul.py`)

A comprehensive test suite of 14 deterministic tests was executed:

| Test Case | Scenario / Query | Expected Behavior | Result |
| :--- | :--- | :--- | :--- |
| `test_fraction_unit_kilo` | `கால்` + `கால் கிலோ வாங்கினேன்` | Selects fraction (¼ / 250g); score > 20 | **PASS** |
| `test_fraction_unit_liter` | `கால்` + `கால் லிட்டர் பால் கொடுங்கள்` | Selects fraction; score > 20 | **PASS** |
| `test_fraction_unit_meter` | `கால்` + `கால் மீட்டர் துணி வெட்டப்பட்டது` | Selects fraction; score > 20 | **PASS** |
| `test_fraction_unit_time` | `கால்` + `கால் மணி நேரம் காத்திருந்தேன்` | Selects fraction / 15 minutes; score > 20 | **PASS** |
| `test_anatomical_foot` | `கால்` + `கல்லில் நடக்கும்போது கால் வழுக்கி கீழே விழுந்தான்` | Selects anatomical foot / leg | **PASS** |
| `test_structural_furniture` | `கால்` + `மேசையின் ஒரு கால் உடைந்து விட்டது` | Structural evaluation; selects table leg / support | **PASS** |
| `test_same_query_different_contexts` | `கால்` in fraction vs. anatomical context | Produces different selected senses deterministically | **PASS** |
| `test_no_context_abstention` | `கால்` with `context=None` | `status="no_context"`, `selected_sense=None` | **PASS** |
| `test_weak_context_abstention` | `கால்` + `அவன் நேற்று பார்த்தான்` | Low evidence; `status="abstained"`, `selected_sense=None` | **PASS** |
| `test_conflicting_context_abstention` | `கால்` + `கால் கிலோ எடையுள்ள மேசையின் கால் மீது விழுந்தது` | High conflict; abstains or selects with logged conflict | **PASS** |
| `test_inflected_query_form` | `கால்` + `காலில் பலத்த அடிபட்டு ரத்தம் வந்தது` | Correctly handles `காலில்`; selects anatomical foot | **PASS** |
| `test_backwards_compatible_tuple_unpacking` | Legacy unpacking: `sense, score, reasons = wsd.disambiguate(...)` | Unpacks seamlessly without exception | **PASS** |
| `test_single_wsd_execution_in_pipeline` | Spy on `TamilWSD.disambiguate` during full `process_query` | Invoked **exactly 1 time**; mock does not call WSD | **PASS** |
| `test_real_django_api_requests` | End-to-end `/api/query` POST requests for 3 demo cases | Validates response contract, meaning separation, and WSD status | **PASS** |

**Unit Test Run Output:**
```
Ran 14 tests in 23.005s
OK
```

### 5.2 Full Regression Test Suite

All existing test suites across the repository were executed to confirm zero regressions:
- `tests/test_interpreter.py`
- `tests/test_django_api.py`
- `tests/test_retrieval.py`
- `tests/test_context_selector.py`
- `tests/test_literary_processor.py`
- `tests/test_wordnet.py`
- `tests/test_akarathi.py`
- `tests/test_thamizhimorph.py`

**Regression Run Output:**
```
Ran 54 tests in 68.714s
OK
```

---

## 6. Real Django API Verification

The Django test client was used to verify live POST requests against `/api/query`.

### Request 1: Fraction Context (`கால்` + `கால் கிலோ வாங்கினேன்`)
```json
{
  "query": "கால்",
  "pos": "Noun",
  "meaning": "1. [பெயர்ச்சொல்] நான்கிலொரு பங்கு; fraction: one fourth. (Wiktionary)\n2. [பெயர்ச்சொல்] கால் (உறுப்பு); foot, leg. (Wiktionary)\n3. [பெயர்ச்சொல்] காற்று; wind. (Wiktionary)\n4. பாதம், முழங்கால் முதல் பாதம் வரையுள்ள உறுப்பு, மரக்கலத்தின் அடிப்பாகம், நீர் பாயும் வழி, நாலிலொரு பங்கு (Akarathi)",
  "contextual_meaning": "1. [பெயர்ச்சொல்] நான்கிலொரு பங்கு; fraction: one fourth. (Wiktionary)",
  "contextual_interpretation": "In this context, 'கால்' refers to the fraction one-fourth (1/4), specifically quarter kilogram (250 grams).",
  "wsd_result": {
    "status": "selected",
    "confidence": "high",
    "score": 35.01,
    "selected_sense": "1. [பெயர்ச்சொல்] நான்கிலொரு பங்கு; fraction: one fourth. (Wiktionary)",
    "reasons": [
      "Quantity/measurement domain signal ('கிலோ') detected near query: +35.0 boost to unit/fraction sense",
      "Exact overlap with context token 'கிலோ': +3.5",
      "Length penalty (verbose sense): -3.5"
    ]
  }
}
```

### Request 2: Anatomical Context (`கால்` + `கல்லில் நடக்கும்போது கால் வழுக்கி கீழே விழுந்தான்`)
```json
{
  "query": "கால்",
  "pos": "Noun",
  "meaning": "1. [பெயர்ச்சொல்] நான்கிலொரு பங்கு; fraction: one fourth. (Wiktionary)\n2. [பெயர்ச்சொல்] கால் (உறுப்பு); foot, leg. (Wiktionary)\n3. [பெயர்ச்சொல்] காற்று; wind. (Wiktionary)\n4. பாதம், முழங்கால் முதல் பாதம் வரையுள்ள உறுப்பு, மரக்கலத்தின் அடிப்பாகம், நீர் பாயும் வழி, நாலிலொரு பங்கு (Akarathi)",
  "contextual_meaning": "2. [பெயர்ச்சொல்] கால் (உறுப்பு); foot, leg. (Wiktionary)",
  "contextual_interpretation": "In this context, 'கால்' refers to the anatomical foot or leg.",
  "wsd_result": {
    "status": "selected",
    "confidence": "high",
    "score": 64.16,
    "selected_sense": "2. [பெயர்ச்சொல்] கால் (உறுப்பு); foot, leg. (Wiktionary)",
    "reasons": [
      "Somatic/anatomical domain signal detected near query: +35.0 boost to body/movement sense",
      "Overlap with movement context token 'நடக்கும்போது' (stem: 'நட'): +1.5",
      "High specificity single-sense definition boost: +27.6"
    ]
  }
}
```

### Request 3: No Context (`கால்`)
```json
{
  "query": "கால்",
  "pos": "Noun",
  "meaning": "1. [பெயர்ச்சொல்] நான்கிலொரு பங்கு; fraction: one fourth. (Wiktionary)\n2. [பெயர்ச்சொல்] கால் (உறுப்பு); foot, leg. (Wiktionary)\n3. [பெயர்ச்சொல்] காற்று; wind. (Wiktionary)\n4. பாதம், முழங்கால் முதல் பாதம் வரையுள்ள உறுப்பு, மரக்கலத்தின் அடிப்பாகம், நீர் பாயும் வழி, நாலிலொரு பங்கு (Akarathi)",
  "contextual_meaning": null,
  "contextual_interpretation": null,
  "wsd_result": {
    "status": "no_context",
    "confidence": "none",
    "score": 0.0,
    "selected_sense": null,
    "reasons": ["No context sentence provided; sense selection abstained"]
  }
}
```

---

## 7. Known Limitations & Future Improvements

1. **Akarathi Collapsed Definitions:** Akarathi raw data stores multiple senses in a single string separated by commas or semicolons. While `extract_sense_candidates` decomposes them when delimiters exist, some Akarathi entries lack granular POS or English definitions per sub-sense.
2. **Tamil WordNet Gloss Absence:** In SOL AI's current Tamil WordNet adapter, WordNet records provide synset hierarchies and lemma links, but `meaning=None`. Consequently, WordNet does not contribute gloss candidates to WSD until glosses are populated in the database.
3. **Compound Word Tokenization:** Highly agglutinative or sandhi-merged compounds without explicit spaces (e.g., `கால்சட்டை` or `மேசைக்கால்`) rely on morphological segmentation before entering WSD. Future work can integrate deep morphological morpheme decomposition into the feature extractor.
4. **Domain Lexicon Scale:** The current domain dictionaries (`QUANTITY_UNIT_TERMS`, `SOMATIC_BODY_TERMS`, `FURNITURE_STRUCTURE_TERMS`) cover essential vocabulary for standard Tamil polysemy. They can be systematically expanded via automated Tamil semantic lexicon mining.

---

## 8. Files Modified

| File | Nature of Changes |
| :--- | :--- |
| `backend/interpretation/schemas.py` | Defined `SenseCandidate`, `CandidateScore`, `WSDResult`, `extract_sense_candidates()`; added `wsd_result` to `SOLResponse` and `EvidencePack`. |
| `backend/interpretation/wsd.py` | Overhauled WSD architecture: implemented `DetectedDomainSignal`, `WSDContextFeatures`, `WSDContextFeatureExtractor`, candidate scoring with proximity/domain boosts, and principled abstention. |
| `backend/interpretation/prompts.py` | Updated `SYSTEM_PROMPT` and `format_evidence_prompt` to establish Python WSD authority and mandate that LLMs synthesize rather than re-select senses. |
| `backend/interpretation/interpreter.py` | Updated `BaseLLMInterpreter`, `MockLLMInterpreter`, `GeminiLLMInterpreter`, and `GroqLLMInterpreter` to pass `wsd_result` cleanly without duplicate executions. |
| `backend/sol_django/api/services.py` | Single-pass pipeline integration: execute WSD once in `process_query()`, attach to pack, and enforce strict overrides in `_apply_post_overrides()`. |
| `tests/test_wsd_overhaul.py` | Created 14 comprehensive unit, regression, and live API tests. |
| `WSD_OVERHAUL_IMPLEMENTATION_REPORT.md` | Complete architectural documentation, forensic comparison, and verification audit. |
