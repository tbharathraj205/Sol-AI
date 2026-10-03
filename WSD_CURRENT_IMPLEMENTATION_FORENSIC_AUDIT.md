# SOL AI — Contextual Word-Sense Disambiguation (WSD) & Interpretation Forensic Audit

**Audit Date:** 2026-10-03  
**Status:** Complete Forensic Audit (Read-Only)  
**Authoritative Basis:** Actual Source Code of `SOL_AI` Repository  

---

## 1. Executive Summary

This forensic audit investigates the exact end-to-end data flow of contextual Word-Sense Disambiguation (WSD) and linguistic interpretation within the SOL AI codebase. Every finding is directly grounded in the repository's source code, concrete database schemas, and client implementations.

### Primary Forensic Findings:
1. **The Disambiguation Layer is Asymmetrically Hybrid:**
   The LLM prompt ([prompts.py](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/prompts.py#L19-L28)) instructs the LLM to perform WSD and return `contextual_meaning`. However, in the application service layer ([services.py](file:///c:/Vishwa/Projects/SOL_AI/backend/sol_django/api/services.py#L170-L186)), `SOLServiceRegistry._apply_post_overrides()` **unconditionally runs deterministic Python WSD (`TamilWSD.disambiguate`) and overwrites `response.contextual_meaning`**. The LLM's choice of `contextual_meaning` is completely discarded at runtime. The LLM only retains ownership of `contextual_interpretation` (explanatory narrative prose).
2. **Double WSD Execution in Mock Mode:**
   When running with `provider="mock"`, `MockLLMInterpreter.interpret()` executes `wsd.disambiguate()` ([interpreter.py](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/interpreter.py#L163-L167)). Immediately thereafter, `SOLServiceRegistry._apply_post_overrides()` executes `wsd.disambiguate()` a second time on the identical data ([services.py](file:///c:/Vishwa/Projects/SOL_AI/backend/sol_django/api/services.py#L175-L180)).
3. **Severe Web App vs. Extension Architectural Discrepancy:**
   - **Extension:** Context is extracted from the webpage DOM by [content.js](file:///c:/Vishwa/Projects/SOL_AI/extension/content/content.js#L61-L114), transmitted via [service-worker.js](file:///c:/Vishwa/Projects/SOL_AI/extension/background/service-worker.js#L64), and rendered in a dedicated card ("In this context / இச்சூழலில்") by [content.js](file:///c:/Vishwa/Projects/SOL_AI/extension/content/content.js#L457-L476). However, the in-page drawer completely ignores `contextual_interpretation`.
   - **Web App:** The Next.js frontend ([frontend/lib/api.js](file:///c:/Vishwa/Projects/SOL_AI/frontend/lib/api.js#L48)) **never sends context** (`context` is omitted from the POST body). Furthermore, the Web App components ([WordExplorer.jsx](file:///c:/Vishwa/Projects/SOL_AI/frontend/components/word/WordExplorer.jsx#L59-L94), [MeaningCard.jsx](file:///c:/Vishwa/Projects/SOL_AI/frontend/components/word/MeaningCard.jsx#L3-L43)) **never inspect or render `contextual_meaning`**.
   - **Extension Popup:** [popup.js](file:///c:/Vishwa/Projects/SOL_AI/extension/popup/popup.js#L63) does not extract or send context, and does not render `contextual_meaning`. It renders only `contextual_interpretation`.
4. **Hardcoded Sense Truncation on Clients:**
   Although the backend retains all candidate senses without truncation in `response.senses`, both the Web App ([MeaningCard.jsx](file:///c:/Vishwa/Projects/SOL_AI/frontend/components/word/MeaningCard.jsx#L7)) and Extension ([content.js](file:///c:/Vishwa/Projects/SOL_AI/extension/content/content.js#L484), [popup.js](file:///c:/Vishwa/Projects/SOL_AI/extension/popup/popup.js#L117)) **hardcode `.slice(0, 2)`**, discarding all lexical senses beyond the first two.
5. **Zero Gloss Contribution from Tamil WordNet:**
   `TamilWordNetAdapter.lookup()` ([wordnet.py](file:///c:/Vishwa/Projects/SOL_AI/backend/resources/wordnet.py#L133)) hardcodes `meaning=None` because the underlying raw dictionary dump lacks definition glosses. Therefore, Tamil WordNet contributes zero candidate senses to WSD. Candidate senses come exclusively from `ThaniThamizhAkarathiAdapter` and `TamilWiktionaryAdapter`.

---

## 2. Current Architecture Diagram

```mermaid
flowchart TD
    subgraph Client ["Client Layer"]
        ExtCtxMenu["Chrome Extension (Context Menu)"]
        ExtPopup["Chrome Extension (Popup)"]
        WebApp["Next.js Web App"]
    end

    subgraph DOMExtraction ["DOM Context Extraction"]
        ContentJS["content.js (DOM Selection & Sentence Splitting)"]
    end

    subgraph APIEntry ["HTTP / API Layer"]
        ServiceWorker["service-worker.js"]
        FrontendAPI["frontend/lib/api.js"]
        DjangoView["query_view() in api/views.py"]
        ServiceReg["SOLServiceRegistry.process_query()"]
    end

    subgraph Retrieval ["Retrieval Engine"]
        Engine["RetrievalEngine.search()"]
        Normalizer["QueryNormalizer.normalize()"]
        Pass1["Pass 1: Exact Surface Lookup (Adapters)"]
        Pass2["Pass 2: Candidate Lemma Lookup"]
        Pass3["Pass 3: Project Madurai Semantic Search"]
        Aggregator["EvidenceAggregator.aggregate()"]
    end

    subgraph AggregatedResult ["Evidence Structuring"]
        UnifiedRes["UnifiedResult"]
        PackBuilder["build_evidence_pack()"]
        EvPack["EvidencePack"]
    end

    subgraph InterpretationLayer ["Interpretation Layer"]
        InterpFactory["interpreter.get_interpreter(provider)"]
        MockInterp["MockLLMInterpreter"]
        GeminiInterp["GeminiLLMInterpreter"]
        GroqInterp["GroqLLMInterpreter"]
        PythonWSD["TamilWSD.disambiguate()"]
        LLMAPICall["External LLM API (Google / Groq)"]
    end

    subgraph Overrides ["Post-LLM Overrides"]
        PostOverrides["SOLServiceRegistry._apply_post_overrides()"]
        DeterministicWSD["TamilWSD.disambiguate() (Forces contextual_meaning)"]
        MorphOverride["parse_structured_morphology()"]
        LitOverride["process_literary_evidence()"]
    end

    subgraph Delivery ["Response & Rendering"]
        SOLResp["Final SOLResponse"]
        ExtPanel["Extension Drawer: In this context + 2 Senses"]
        WebDisplay["Web App: 2 Senses + Interpretation Tab"]
    end

    ExtCtxMenu --> ContentJS
    ContentJS -->|"query + context"| ServiceWorker
    ExtPopup -->|"query only (no context)"| ServiceWorker
    WebApp -->|"query only (no context)"| FrontendAPI

    ServiceWorker -->|"POST /api/query"| DjangoView
    FrontendAPI -->|"POST /api/query"| DjangoView
    DjangoView --> ServiceReg

    ServiceReg --> Engine
    Engine --> Normalizer --> Pass1
    Pass1 --> Pass2 --> Pass3 --> Aggregator --> UnifiedRes
    UnifiedRes --> PackBuilder --> EvPack

    EvPack --> InterpFactory
    InterpFactory -->|mock| MockInterp
    InterpFactory -->|gemini| GeminiInterp
    InterpFactory -->|groq| GroqInterp

    MockInterp -->|Runs WSD (1st time)| PythonWSD
    GeminiInterp --> LLMAPICall
    GroqInterp --> LLMAPICall

    MockInterp --> PostOverrides
    GeminiInterp --> PostOverrides
    GroqInterp --> PostOverrides

    PostOverrides -->|Unconditionally Overwrites contextual_meaning| DeterministicWSD
    PostOverrides --> MorphOverride
    PostOverrides --> LitOverride
    PostOverrides --> SOLResp

    SOLResp --> DjangoView
    DjangoView --> ExtPanel
    DjangoView --> WebDisplay
```

---

## 3. Exact Request Lifecycle

The lifecycle of a contextual request proceeds through 8 sequential phases:

```
[1. User Action]
     ↓ User highlights Tamil word and selects "Explain with சொல் AI"
[2. Client Extraction (extension/content/content.js)]
     ↓ Locates block ancestor, regex splits sentences, isolates surrounding sentence
[3. Client Transport (extension/background/service-worker.js)]
     ↓ Issues HTTP POST to http://localhost:8000/api/query with {query, context}
[4. Django View (backend/sol_django/api/views.py)]
     ↓ Validates JSON payload, extracts query, provider, and context
[5. Service Registry (backend/sol_django/api/services.py)]
     ↓ Orchestrates RetrievalEngine -> EvidencePack -> Interpreter -> _apply_post_overrides
[6. Retrieval & Evidence Pack (backend/retrieval/ & backend/interpretation/)]
     ↓ Multi-pass search across 6 adapters -> UnifiedResult -> unflattened EvidencePack
[7. Interpretation & WSD Override (backend/interpretation/)]
     ↓ LLM generates draft interpretation; _apply_post_overrides runs TamilWSD and overwrites contextual_meaning
[8. JSON Serialization & Client Rendering]
     ↓ Serializes SOLResponse -> Content script renders dedicated contextual card
```

---

## 4. Client Context Extraction

The context extraction logic is implemented in [extension/content/content.js](file:///c:/Vishwa/Projects/SOL_AI/extension/content/content.js#L61-L114).

### Detailed Operation:
1. **Message Listener:**
   `chrome.runtime.onMessage.addListener` listens for `{ action: "GET_CONTEXT" }` ([content.js#L61-L62](file:///c:/Vishwa/Projects/SOL_AI/extension/content/content.js#L61-L62)).
2. **DOM Selection:**
   Calls `window.getSelection()`. If `selection.rangeCount > 0`:
   ```javascript
   let container = selection.getRangeAt(0).commonAncestorContainer;
   if (container.nodeType === 3) container = container.parentNode;
   ```
3. **Block Ancestor Traversal:**
   Traverses upward looking for standard block elements:
   ```javascript
   let current = container;
   while (current && current !== document.body && current.nodeName !== 'P' && current.nodeName !== 'DIV' && current.nodeName !== 'SECTION' && current.nodeName !== 'ARTICLE') {
     current = current.parentNode;
   }
   ```
4. **Text Extraction & Sentence Splitting:**
   Extracts `fullPassage = current.textContent.trim()` and `selectedWord = selection.toString().trim()`.
   Splits text into sentences using the regex:
   ```javascript
   const sentences = fullPassage.match(/[^.?!]+[.?!]*/g) || [];
   ```
5. **Target Sentence Matching:**
   - **Exact match:** `sentences.find(sentence => sentence.includes(selectedWord))`
   - **Loose fallback:** `sentences.find(sentence => sentence.toLowerCase().includes(selectedWord.toLowerCase()))`
   - **Unbounded fallback:** `fullPassage.substring(0, 200)`
6. **Error / Empty Fallback:**
   If empty: `"[FALLBACK] Extracted text was empty."`
   If an exception occurs: `"[FALLBACK] Extraction threw an error: " + e.message`.

### Forensic Answers on Client Extraction:
- **How is selected word obtained?** `selection.toString().trim()` ([content.js#L83](file:///c:/Vishwa/Projects/SOL_AI/extension/content/content.js#L83)).
- **How is surrounding context obtained?** Finds the nearest `<p>`, `<div>`, `<section>`, `<article>`, splits on `[.?!]`, and finds the sentence containing the word ([content.js#L72-L93](file:///c:/Vishwa/Projects/SOL_AI/extension/content/content.js#L72-L93)).
- **What exact string is sent as `context`?** The exact matched sentence string (`targetSentence.trim()`).
- **Is the selected word itself included in context?** **YES.** The entire sentence is extracted, which includes the selected word.
- **Is context truncated?** If matched via sentence regex, **NO**. If sentence matching fails, it is truncated to 200 characters ([content.js#L100](file:///c:/Vishwa/Projects/SOL_AI/extension/content/content.js#L100)).
- **Is context normalized?** Only whitespace is trimmed via `.trim()`. No Unicode normalization (NFC) is applied in client JavaScript.
- **Does the Web App send context?** **NO.** In [frontend/lib/api.js#L48](file:///c:/Vishwa/Projects/SOL_AI/frontend/lib/api.js#L48), `querySolApi()` sends only `{ query: queryText, provider }`.
- **Does Extension Popup send context?** **NO.** In [extension/popup/popup.js#L63](file:///c:/Vishwa/Projects/SOL_AI/extension/popup/popup.js#L63), `performLookup()` sends only `{ action: "QUERY_API", query: queryText }`.

---

## 5. HTTP / API Entry Point

The API entry point is implemented in [backend/sol_django/api/views.py](file:///c:/Vishwa/Projects/SOL_AI/backend/sol_django/api/views.py#L46-L107) and routed via [backend/sol_django/api/urls.py](file:///c:/Vishwa/Projects/SOL_AI/backend/sol_django/api/urls.py#L11-L12).

### Call Chain:
```
Client HTTP POST /api/query
  ↓
query_view(request) [backend/sol_django/api/views.py:47]
  ↓
json.loads(request.body.decode("utf-8")) [views.py:64]
  ↓
SOLServiceRegistry.get_instance().process_query(query, provider, context) [services.py:74]
  ↓
RetrievalEngine.search(clean_query) [engine.py:148]
  ↓
build_evidence_pack(retrieval_result, query_context=context) [evidence_pack.py:42]
  ↓
interpreter.interpret(pack) [interpreter.py]
  ↓
SOLServiceRegistry._apply_post_overrides(pack, response, query) [services.py:142]
  ↓
_json_response(response.model_dump(), status=200) [views.py:96]
```

### Request Payload Schema:
```json
{
  "query": "கால்",
  "provider": "gemini",
  "context": "அவனுடைய தம்பி கால் கிலோ மாம்பழம் வாங்கி வந்தான்."
}
```
Validation in `query_view`:
- Verifies request body is non-empty (`status=400`).
- Verifies valid JSON dict (`status=400`).
- Verifies `query` key exists and is non-empty (`status=400`).
- Context and provider are optional (`payload.get("provider")`, `payload.get("context")`).

---

## 6. Retrieval Flow & Candidate Lexical Senses

The retrieval engine is implemented in [backend/retrieval/engine.py](file:///c:/Vishwa/Projects/SOL_AI/backend/retrieval/engine.py#L24-L361).

### The Multi-Pass Sequence:
1. **Normalization:** [QueryNormalizer.normalize(query)](file:///c:/Vishwa/Projects/SOL_AI/backend/query/normalizer.py#L32) applies Unicode NFC normalization and strips leading/trailing whitespace.
2. **Pass 1 (Surface Lookup):** Iterates over registered adapters in `self.adapters` ([engine.py#L206-L224](file:///c:/Vishwa/Projects/SOL_AI/backend/retrieval/engine.py#L206-L224)):
   - `ThamizhiMorph` ([thamizhimorph.py](file:///c:/Vishwa/Projects/SOL_AI/backend/resources/thamizhimorph.py#L251))
   - `Tamil Wiktionary` ([wiktionary.py](file:///c:/Vishwa/Projects/SOL_AI/backend/resources/wiktionary.py#L43))
   - `Thani Thamizh Akarathi` ([akarathi.py](file:///c:/Vishwa/Projects/SOL_AI/backend/resources/akarathi.py#L46))
   - `Tamil WordNet` ([wordnet.py](file:///c:/Vishwa/Projects/SOL_AI/backend/resources/wordnet.py#L47))
   - `Sentamizh` ([sentamizh.py](file:///c:/Vishwa/Projects/SOL_AI/backend/resources/sentamizh.py#L47))
   - `Project Madurai` ([project_madurai.py](file:///c:/Vishwa/Projects/SOL_AI/backend/resources/project_madurai.py#L70))
3. **Candidate Lemma Extraction:** Scans Pass 1 evidence with `status == "FOUND"` for any `ev.lemma != target` or `root_word != target` ([engine.py#L225-L233](file:///c:/Vishwa/Projects/SOL_AI/backend/retrieval/engine.py#L225-L233)).
   - For `கால்`: `கால்` is an uninflected root form. Both ThamizhiMorph and WordNet report `lemma = "கால்"`. Since `ev.lemma == target`, **no secondary candidate lemmas are discovered**.
4. **Pass 2 (Lemma Lookup):** Since `candidate_lemmas` is empty, **Pass 2 does not execute any queries** ([engine.py#L244](file:///c:/Vishwa/Projects/SOL_AI/backend/retrieval/engine.py#L244)).
5. **Pass 3 (Semantic Retrieval):** Evaluates `_evaluate_semantic_short_circuit()` ([engine.py#L87-L146](file:///c:/Vishwa/Projects/SOL_AI/backend/retrieval/engine.py#L87-L146)). If Project Madurai exact matches $\ge 25$ or literary evidence $\ge 10$ with lexical/morphological support, semantic retrieval is skipped.
6. **Aggregation & Priority Sorting:** [EvidenceAggregator.aggregate()](file:///c:/Vishwa/Projects/SOL_AI/backend/retrieval/aggregator.py#L21-L137) sorts evidence deterministically (core analyses score 10, guesser 5; exact surface matches score 8).

---

### ANSWER TO MANDATORY FORENSIC QUESTION:
> *"Before WSD runs, exactly how many lexical candidate records/senses exist for `கால்`, and from which sources do they come?"*

When WSD runs ([services.py#L171](file:///c:/Vishwa/Projects/SOL_AI/backend/sol_django/api/services.py#L171) & [interpreter.py#L160](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/interpreter.py#L160)), candidate senses are extracted as:
```python
candidate_senses = [ev.meaning for ev in pack.lexical_evidence if ev.meaning]
```
The exact inventory of candidate senses is:

1. **`Tamil WordNet`:** **0 candidate senses.**
   `TamilWordNetAdapter` matches rows in `twn_index`, but line 133 of [wordnet.py](file:///c:/Vishwa/Projects/SOL_AI/backend/resources/wordnet.py#L133) explicitly sets `meaning=None` because the dictionary dump lacks glosses. The `if ev.meaning` filter completely excludes all WordNet records.
2. **`Thani Thamizh Akarathi`:** **Exactly 1 lexical candidate record.**
   Indexed from `data/raw/thani_thamizh_akarathi/agarathi/search/கா/கால்`. In [build_akarathi_index.py#L62-L71](file:///c:/Vishwa/Projects/SOL_AI/scripts/build_akarathi_index.py#L62-L71), all lines of this headword file are collapsed into a single comma-separated gloss:
   `"crus, பாதம், தூண், தாங்குகால், அடிப்பக்கம், தேர்க்கால், ஆரக்கால், வாய்க்கால், காற்பங்கு, இரத்தக் கலப்பாமுறவு, வழி, காற்று, முளை, ..."`.
3. **`Tamil Wiktionary`:** **$N$ distinct candidate senses** (where $N \ge 8$ depending on `wiktionary_index.db`).
   In [build_wiktionary_index.py#L119-L121](file:///c:/Vishwa/Projects/SOL_AI/scripts/build_wiktionary_index.py#L119-L121), every `#` bullet point from the XML dump is inserted as an individual row in the SQLite `definitions` table. [wiktionary.py#L73-L86](file:///c:/Vishwa/Projects/SOL_AI/backend/resources/wiktionary.py#L73-L86) creates an independent `Evidence` object for each row.
   These distinct records include:
   - `பாதம் / உடல் உறுப்பு` (foot/body part)
   - `நான்கில் ஒரு பங்கு / காற்பங்கு` (one quarter)
   - `மேசை, நாற்காலி ஆகியவற்றின் தாங்கும் பகுதி` (furniture leg)
   - `காற்று` (wind)
   - `வாய்க்கால் / நீர் செல்லும் வழி` (water channel)
   - `மரத்தின் அடிப்பகுதி` (base of a tree)

**Conclusion:**
- If `wiktionary_index.db` is loaded: **$1 + N$ lexical candidate strings** enter WSD (1 collapsed gloss from Akarathi, and $N$ individual glosses from Wiktionary).
- If `wiktionary_index.db` is absent: **Exactly 1 lexical candidate record** enters WSD (from Thani Thamizh Akarathi).

> [!CRITICAL]
> **OLD REPORT VS CURRENT CODE DIFFERENCE:**
> An older document claimed that "Thani Thamizh Akarathi preserves distinct senses across dictionaries." In current code, `build_akarathi_index.py` collapses all lines within `search/கா/கால்` into a single `meaning` string. If Wiktionary is omitted, `len(unique_senses) == 1`, causing line 330 of [wsd.py](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/wsd.py#L330) to trigger an immediate early exit: `("Single documented sense.", 1.0)`, bypassing all scoring logic.

---

## 7. UnifiedResult

`UnifiedResult` is defined in [backend/schemas/result.py](file:///c:/Vishwa/Projects/SOL_AI/backend/schemas/result.py#L6-L30).

```python
@dataclass
class UnifiedResult:
    query: str
    normalized_query: str
    lemma_candidates: List[str]
    evidence: List[Evidence]
    resource_summary: Dict[str, Dict[str, Any]]
    cross_resource_support: Dict[str, List[str]]
    errors: Dict[str, str]
```

### Fields Relevant to WSD:
- `evidence`: The raw array of `Evidence` objects containing lexical entries.
- `lemma_candidates`: Used by `build_evidence_pack` to populate `EvidencePack.lemma_candidates`.
- All other fields (`resource_summary`, `cross_resource_support`, `errors`) are telemetry/metadata and do not enter WSD.

---

## 8. EvidencePack

`build_evidence_pack()` is implemented in [backend/interpretation/evidence_pack.py](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/evidence_pack.py#L42-L135).

### Filtering and Assembly Rules:
1. **Filtering:** Filters exclusively for evidence where `metadata.get("status") == "FOUND"` ([evidence_pack.py#L62-L65](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/evidence_pack.py#L62-L65)).
2. **Morphology Categorization:** Directs items from `ThamizhiMorph` or `ev_type == "morphology"` or `"fst_model"` to `morphology_evs`. Core FST evidence is sorted before Guesser FST via `_morphology_sort_key` ([evidence_pack.py#L22-L39](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/evidence_pack.py#L22-L39)).
3. **Lexical Categorization:** Directs items from `Thani Thamizh Akarathi`, `Tamil Wiktionary`, and `Tamil WordNet` (excluding morphtable) to `lexical_evs`.
4. **Literary Categorization & Capping:** Directs Sentamizh and Project Madurai to `raw_literary_evs`. Applies [SentamizhContextSelector.select()](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/context_selector.py#L56-L106) to deterministically score and cap contexts to `max_literary_contexts=5` with work diversity.
5. **Preservation of Senses:** **No lexical sense flattening or deduplication occurs here.** Senses remain unflattened `Evidence` objects in `pack.lexical_evidence`.
6. **Context Retention:** `pack.query_context` stores the exact raw `context` string passed from the HTTP request.

---

## 9. WSD — Detailed Algorithm Trace

The deterministic WSD algorithm is implemented in [backend/interpretation/wsd.py](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/wsd.py#L209-L531).

### A. Inputs
`TamilWSD.disambiguate(query: str, context_sentence: Optional[str], candidate_senses: List[str])`:
- `query`: The highlighted word string.
- `context_sentence`: The surrounding sentence string.
- `candidate_senses`: A raw list of definition strings (`[ev.meaning for ev in pack.lexical_evidence if ev.meaning]`).

### B. Context Preprocessing
1. **Empty Check:** If `not context_sentence or not context_sentence.strip()`, returns `(None, 0.0, ["No query context provided."])` ([wsd.py#L251-L252](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/wsd.py#L251-L252)).
2. **Tokenization:** `tamil_tokens(c_text)` matches `[\u0B80-\u0BFA]+` ([wsd.py#L183-L186](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/wsd.py#L183-L186)).
3. **Stopword & Query Filtering:** Removes tokens matching `query`, items in `TAMIL_STOPWORDS` (42 grammatical particles), and tokens with length $\le 1$ ([wsd.py#L258](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/wsd.py#L258)).
4. **Query Occurrence Locating:** Identifies indices where `w == query` or `tamil_stem(w) == tamil_stem(query)`. Fallback: `query in w` ([wsd.py#L263-L271](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/wsd.py#L263-L271)).
5. **Token Proximity Distance:** For each context token $w$, computes:
   $$\text{dist}(w) = \min_{q \in Q} | \text{idx}(w) - q |$$
6. **Collocations:** Immediate collocates identified where $\text{dist}(w) == 1$ ([wsd.py#L282](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/wsd.py#L282)).

### C. Domain Feature Detections
1. **Quantity / Unit Detection:** Checks context tokens and their stems against `QUANTITY_UNIT_TERMS` (50 units: kilo, liter, meter, hour, part, etc.). Finds closest unit ([wsd.py#L285-L298](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/wsd.py#L285-L298)).
2. **Somatic / Body Detection:** Checks context tokens and stems against `SOMATIC_BODY_TERMS` (pain, injury, walking, slipping, joints, etc.). Finds closest somatic word ([wsd.py#L300-L311](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/wsd.py#L300-L311)).
3. **Furniture / Structure Detection:** Checks context tokens against `FURNITURE_STRUCTURE_TERMS` (chair, table, cot, pillar, etc.). Finds closest furniture word ([wsd.py#L313-L324](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/wsd.py#L313-L324)).

### D. Scoring Signals & Formulas

For each candidate sense $s_i \in \text{unique\_senses}$:

| Signal Name | Code Location | Formula / Logic | Weight / Boost | Activation Condition |
|---|---|---|---|---|
| **Adjacent Unit Boost** | [wsd.py:382](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/wsd.py#L382) | `score += 35.0` | $+35.0$ | Sense has fraction indicator AND closest unit $\text{dist} == 1$ |
| **Collocated Unit Boost** | [wsd.py:387](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/wsd.py#L387) | `score += 20.0 / d` | $+6.67$ to $+10.0$ | Sense has fraction indicator AND closest unit $\text{dist} \in [2, 3]$ |
| **Distant Unit Boost** | [wsd.py:393](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/wsd.py#L393) | `score += 5.0 / d` | $+5.0 / d$ | Sense has fraction indicator AND closest unit $\text{dist} > 3$ |
| **Adjacent Somatic Boost** | [wsd.py:406](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/wsd.py#L406) | `score += 35.0` | $+35.0$ | Sense has anatomy indicator AND closest somatic $\text{dist} == 1$ |
| **Collocated Somatic Boost**| [wsd.py:411](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/wsd.py#L411) | `score += 20.0 / d` | $+6.67$ to $+10.0$ | Sense has anatomy indicator AND closest somatic $\text{dist} \in [2, 3]$ |
| **Distant Somatic Boost** | [wsd.py:415](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/wsd.py#L415) | `score += 5.0 / d` | $+5.0 / d$ | Sense has anatomy indicator AND closest somatic $\text{dist} > 3$ |
| **Adjacent Furniture Boost**| [wsd.py:428](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/wsd.py#L428) | `score += 35.0` | $+35.0$ | Sense has furniture indicator AND closest furniture $\text{dist} == 1$ |
| **Exact Token Overlap** | [wsd.py:453](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/wsd.py#L453) | $4.0 \times \text{IDF}(c) \times \text{pos\_weight} \times \text{genus\_mult}$ | Variable | Context token $c \in s_{\text{toks}}$ |
| **Stemmed Overlap** | [wsd.py:459](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/wsd.py#L459) | $2.5 \times \text{IDF}(c_{\text{stm}}) \times \text{pos\_weight} \times \text{genus\_mult}$ | Variable | Stem of context token $c_{\text{stm}} \in s_{\text{stm}}$ |
| **Synonym Overlap** | [wsd.py:468](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/wsd.py#L468) | $2.0 \times \text{IDF}(\text{syn}) \times \text{pos\_weight}$ | Variable | Akarathi synonyms of $c$ overlap with $s_{\text{toks}}$ |
| **Synonym Stem Overlap** | [wsd.py:476](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/wsd.py#L476) | $1.5 \times \text{IDF}(\text{syn\_stm}) \times \text{pos\_weight}$ | Variable | Stems of Akarathi synonyms overlap with $s_{\text{stm}}$ |

**Positional Multiplier (`pos_weight`):**
- $\text{dist} == 1 \implies 2.5$
- $\text{dist} \in [2, 3] \implies 1.5$
- $\text{dist} > 3 \implies 1.0$

**Genus Multiplier (`genus_mult`):**
- If token is in `GENUS_WORDS` (`{"பகுதி", "வகை", "இடம்", "பொருள்", "ஒன்று", "பெயர்", "நிலை", "முறை"}`), `genus_mult = 0.4`. Prevents generic hypernyms from falsely dominating specific differentiae.

**IDF Formula:**
$$\text{IDF}(t) = \ln\left(\frac{N + 1}{\text{count}(t)}\right) + 1.0$$
where $N$ is the number of candidate senses.

### E. Ambiguity Guards
1. **Low Evidence Floor:** If $\text{top\_score} < 1.0$, returns `(None, top_score, ["Context lacks discriminative evidence to determine intended sense."])` ([wsd.py#L488-L489](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/wsd.py#L488-L489)).
2. **Close Competition Guard:** If $\text{top\_score} - \text{second\_score} < 0.1$ and $\text{top\_score} < 2.0$, returns `(None, top_score, ["Ambiguous between competing senses..."])` ([wsd.py#L491-L492](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/wsd.py#L491-L492)).

---

## 10. Detailed Trace: `கால் கிலோ` vs. Competing Senses

**Sentence:** `அவனுடைய தம்பி கால் கிலோ மாம்பழம் வாங்கி வந்தான்.`  
**Query:** `கால்`

### 1. Token Positions & Distances:
- `raw_c_tokens`: `["அவனுடைய", "தம்பி", "கால்", "கிலோ", "மாம்பழம்", "வாங்கி", "வந்தான்"]`
- `query_indices`: `[2]` (`"கால்"`)
- `c_tokens` (excluding stopwords and query):
  - `அவனுடைய`: index 0, distance $= 2$ (`pos_weight = 1.5`)
  - `தம்பி`: index 1, distance $= 1$ (`pos_weight = 2.5`, collocate)
  - `கிலோ`: index 3, distance $= 1$ (`pos_weight = 2.5`, collocate)
  - `மாம்பழம்`: index 4, distance $= 2$ (`pos_weight = 1.5`)
  - `வாங்கி`: index 5, distance $= 3$ (`pos_weight = 1.5`)
  - `வந்தான்`: index 6, distance $= 4$ (`pos_weight = 1.0`)

### 2. Feature Activations:
- `closest_unit`: `"கிலோ"` at $\text{dist} = 1$ (matches `QUANTITY_UNIT_TERMS`).
- `closest_somatic`: `None` ($\text{dist} = 999$).
- `closest_furniture`: `None` ($\text{dist} = 999$).

### 3. Sense Evaluation Comparison:

```
+-----------------------------------------------------+---------------+---------------+---------------------------------------+
| Candidate Sense                                     | Unit Boost    | Somatic Boost | Token Overlap Contribution & Status   |
+-----------------------------------------------------+---------------+---------------+---------------------------------------+
| Sense 1: Fractional Quarter (நான்கில் ஒரு பங்கு / 1/4)  | +35.0         | +0.0          | Exact match on கிலோ (+w) -> WINNER    |
| Sense 2: Anatomical Foot (உடல் உறுப்பு / பாதம்)     | +0.0          | +0.0          | Overlap = 0.0 -> REJECTED             |
| Sense 3: Furniture Leg (நாற்காலியின் தாங்கும் பகுதி)  | +0.0          | +0.0          | Overlap = 0.0 -> REJECTED             |
| Sense 4: Flowing Channel (வாய்க்கால்)               | +0.0          | +0.0          | Overlap = 0.0 -> REJECTED             |
+-----------------------------------------------------+---------------+---------------+---------------------------------------+
```

### 4. Post-Formatting Triggered:
`win_has_fraction` is True, `closest_unit_name == "கிலோ"`, `closest_unit_dist == 1 <= 2`.
Calls [format_fraction_unit_gloss()](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/wsd.py#L131-L181):
```python
"நான்கில் ஒரு பங்கு — இங்கு 'கால் கிலோ' என்பது ஒரு கிலோவின் நான்கில் ஒரு பங்கு (¼ kg / 250g)."
```

---

## 11. Trace: Anatomical Foot (`கால் வழுக்கி கீழே விழுந்தான்`)

**Sentence:** `அவன் கல்லில் நடக்கும்போது கால் வழுக்கி கீழே விழுந்தான்.`  
**Query:** `கால்`

1. **Tokens:** `["அவன்", "கல்லில்", "நடக்கும்போது", "கால்", "வழுக்கி", "கீழே", "விழுந்தான்"]`
2. **Stopwords Removed:** `"அவன்"` removed.
3. **Proximity:**
   - `"நடக்கும்போது"`: index 2, distance $= 1$ from query (`pos_weight = 2.5`). Matches `SOMATIC_BODY_TERMS`.
   - `"வழுக்கி"`: index 4, distance $= 1$ from query (`pos_weight = 2.5`). Matches `SOMATIC_BODY_TERMS`.
4. **Closest Somatic:** Distance $= 1$.
5. **Scoring:**
   - **Anatomical sense (`உடல் உறுப்பு` / `பாதம்`):** Receives `somatic_boost = 35.0` (adjacent somatic). Total score $\ge 35.0$.
   - **Fractional sense:** No unit present $\implies 0.0$.
6. **Post-Formatting Triggered ([wsd.py:514-518](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/wsd.py#L514-L518)):**
   Prefixes `"உடல் உறுப்பு / பாதம் — "` to the cleaned sense gloss.

---

## 12. Trace: No Context (Null / Absent)

**Sentence:** `null` or `""`  
**Query:** `கால்`

1. In [services.py#L170-L186](file:///c:/Vishwa/Projects/SOL_AI/backend/sol_django/api/services.py#L170-L186):
   ```python
   if pack.query_context and pack.query_context.strip():
       # executes WSD...
   else:
       response.contextual_meaning = None
   ```
2. `response.contextual_meaning` is set directly to `None`.
3. In [prompts.py#L52](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/prompts.py#L52), when `pack.query_context` is None, the `Query Context (User Sentence)` section is **completely omitted from the LLM prompt**.
4. WSD algorithm is never executed.

---

## 13. Trace: Inflected Word (`மரங்களில்`)

**Query:** `மரங்களில்`  
**Context:** Optional or None

1. **Pass 1 Retrieval:**
   - `ThamizhiMorph` analyzes `மரங்களில்` via `noun.fst`. Outputs: `மரம்+noun+pl+loc`.
     `lemma = "மரம்"`, `pos = "noun"`, `morphology = "noun+pl+loc"`.
   - `Tamil WordNet` morphtable resolves root: `மரம்`.
2. **Lemma Discovery:**
   `candidate_lemmas = {"மரம்"}` is populated because `lemma != "மரங்களில்"`.
3. **Pass 2 Retrieval:**
   Queries secondary adapters (`Tamil Wiktionary`, `Thani Thamizh Akarathi`, `Sentamizh`, `Project Madurai`) for candidate lemma `"மரம்"`. Definitions and classical verses for `"மரம்"` are retrieved.
4. **EvidencePack Sorting:**
   Core FST (`noun.fst`) is sorted to index 0 over any guesser models. `pack.lemma_candidates = ["மரம்"]`.
5. **Morphology Resolution:**
   [parse_structured_morphology()](file:///c:/Vishwa/Projects/SOL_AI/backend/resources/thamizhimorph.py#L39-L149) decomposes tags into:
   - `pos`: `"noun"`
   - `case`: `"Locative"` (derived from `+loc`)
   - `number`: `"Plural"` (derived from `+pl`)
   - `analysis_type`: `"core"`
   - `fst_model`: `"noun.fst"`
6. **WSD Execution (if context present):**
   If context is present, WSD runs for query `"மரங்களில்"`.
   In [wsd.py#L265](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/wsd.py#L265), `tamil_stem("மரங்களில்")` matches suffix `"ங்களில்"`, stripping it down to `"மரம்"`. This allows seamless lemma-level matching against candidate senses of `"மரம்"`.
7. **Client Presentation:**
   Because `data.query !== data.lemma`, the Web App renders a gold notification banner ([WordExplorer.jsx#L41-L55](file:///c:/Vishwa/Projects/SOL_AI/frontend/components/word/WordExplorer.jsx#L41-L55)):
   `"Note: Showing available details for the inflected word 'மரங்களில்'. A direct dictionary meaning might not be available. [Look for root word 'மரம்']"`.

---

## 14. What Exactly Does WSD Return?

`TamilWSD.disambiguate()` returns a Python 3-tuple:
```python
Tuple[Optional[str], float, List[str]]
# (winning_sense_text, confidence_score, explanation_reasons)
```

- `winning_sense_text`: A single string containing the winning definition, with contextual prefixes/glosses applied. If ambiguous or no context, `None`.
- `confidence_score`: A float (e.g. `35.0` or `1.0`).
- `explanation_reasons`: A list of debug strings (e.g. `["adjacent_unit:கிலோ(dist=1)->fraction_sense(+35.0)"]`).

> [!NOTE]
> `confidence_score` and `explanation_reasons` are **discarded** by `services.py` line 175 (`sel_sense, score, _ = wsd.disambiguate(...)`). Only `sel_sense` is saved to `response.contextual_meaning`.

---

## 15. Interpreter Flow & Provider Differences

The interpreter flow is implemented in [backend/interpretation/interpreter.py](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/interpreter.py#L26-L334).

### Provider Matrix:

| Feature / Behavior | Mock Provider | Gemini Provider | Groq Provider | Provider Failure Fallback |
|---|---|---|---|---|
| **Runs WSD inside interpreter?** | **YES** ([interpreter.py:163](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/interpreter.py#L163)) | **NO** | **NO** | **YES** (falls back to Mock) |
| **Passes WSD output to LLM?** | N/A (no LLM) | **NO** (LLM prompt has no WSD scores/choice) | **NO** | N/A |
| **LLM receives original context?** | N/A | **YES** (in query section) | **YES** (in query section) | N/A |
| **LLM receives all lexical senses?** | N/A | **YES** (flat text glosses) | **YES** (flat text glosses) | N/A |
| **LLM generates `contextual_meaning`?** | N/A | Prompt asks for it; **immediately overwritten by server** | Prompt asks for it; **immediately overwritten by server** | Nullified on error, then overwritten by server |
| **Who owns `contextual_meaning`?** | `TamilWSD` | `TamilWSD` | `TamilWSD` | `TamilWSD` |
| **Who owns `contextual_interpretation`?** | Deterministic Python string | LLM-generated Tamil prose | LLM-generated Tamil prose | Deterministic Python string |

---

## 16. Exact LLM Input Prompt Structure

Below is the exact text prompt generated by [format_evidence_prompt()](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/prompts.py#L44-L135) for `கால்` with context:

```text
=== QUERY ===
Query: கால்
Normalized Query: கால்
Query Context (User Sentence): அவனுடைய தம்பி கால் கிலோ மாம்பழம் வாங்கி வந்தான்.
Context-Aware Disambiguation Notice: The user highlighted this word within the above sentence. Use this sentence as the primary anchor to disambiguate polysemous senses from the lexical evidence.
Lemma Candidates: None

=== LEMMA / MORPHOLOGY ===
[1] Source: ThamizhiMorph | Model: noun.fst [CORE]
    Lemma: கால்
    POS: noun
    Morphology Components: {'pos': 'noun'}
    Raw Foma Output: கால்	கால்+noun

=== LEXICAL EVIDENCE ===
[1] Source: Thani Thamizh Akarathi | Headword: கால் | POS: N/A | Freq: N/A
    Meaning/Gloss: crus, பாதம், தூண், தாங்குகால், அடிப்பக்கம், தேர்க்கால், ஆரக்கால், வாய்க்கால், காற்பங்கு, இரத்தக் கலப்பாமுறவு, வழி, காற்று, முளை...
[2] Source: Tamil Wiktionary | Headword: கால் | POS: N/A | Freq: N/A
    Meaning/Gloss: பாதம்
[3] Source: Tamil Wiktionary | Headword: கால் | POS: N/A | Freq: N/A
    Meaning/Gloss: நான்கில் ஒரு பங்கு

=== LITERARY EVIDENCE ===
[1] Source: Sentamizh | Work: Kuruntokai | Period: Sangam | Verse #: 120
    Classical Verse: ...
    Modern Tamil Gloss: ...

=== RELATIONSHIPS ===
No explicit lexical relationships available.

=== CONFLICTS ===
No conflicts detected across evidence sources.

=== SOURCE PROVENANCE ===
- ThamizhiMorph: Status=FOUND, Entries=1
- Thani Thamizh Akarathi: Status=FOUND, Entries=1
- Tamil Wiktionary: Status=FOUND, Entries=2
- Sentamizh: Status=FOUND, Entries=5
```

---

## 17. LLM Output Processing & SOLResponse Ownership

The LLM returns JSON parsed into `SOLResponse` ([interpreter.py#L256](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/interpreter.py#L256)). Then `SOLServiceRegistry._apply_post_overrides()` runs ([services.py#L142-L241](file:///c:/Vishwa/Projects/SOL_AI/backend/sol_django/api/services.py#L142-L241)).

### Exhaustive Field Ownership Classification:

```
+---------------------------+-----------------------------------+-------------------------------------------------------------+
| SOLResponse Field         | Classification                    | Authoritative Mechanism in Code                             |
+---------------------------+-----------------------------------+-------------------------------------------------------------+
| query                     | Deterministic backend             | services.py:92 (clean_query)                                |
| normalized_query          | Deterministic backend             | QueryNormalizer.normalize(query)                            |
| lemma                     | Mixed                             | FST/WordNet -> LLM/Mock -> SOLResponse                     |
| meaning                   | Mixed / Server override           | LLM draft; if empty, services.py:159 populates from evidence |
| english_meaning           | Deterministic backend / LLM       | OfflineTranslator in Mock; LLM in API mode                  |
| senses                    | Server override                   | services.py:163 parse_senses_from_meaning_string()          |
| morphology                | Server override                   | services.py:234 parse_structured_morphology() (unconditional)|
| contextual_meaning        | Deterministic WSD                 | services.py:180 TamilWSD.disambiguate() (unconditional)     |
| contextual_interpretation | LLM-generated (API) / Mock string | LLM synthesis; Mock formatted string                        |
| literary_context          | Server override                   | services.py:212 process_literary_evidence() (unconditional)  |
| related_words             | Server override                   | services.py:189-209 extracts from pack / meaning string     |
| sources                   | Mixed                             | Pack source provenance -> LLM/Mock                          |
| uncertainties             | Mixed                             | LLM list + services.py:182 ambiguity append                 |
| evidence_summary          | Deterministic backend             | Copied directly from EvidencePack.evidence_counts           |
+---------------------------+-----------------------------------+-------------------------------------------------------------+
```

---

## 18. Structured Lexical Sense Flow

1. **Creation:** [schemas.py#L77-L132](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/schemas.py#L77-L132) defines `build_lexical_senses()` and `parse_senses_from_meaning_string()`.
2. **Schema:**
   - `sense_number`: 1-based integer index
   - `title`: Extracted before `—`, `-`, or `:`
   - `description`: Text following punctuation separator
   - `english_translation`: Optional English translation
   - `raw_text`: Unsplit raw string
3. **Backend Retention:** The backend retains **all senses** without truncation.
4. **Client Slicing:**
   - **Web App:** [MeaningCard.jsx#L7](file:///c:/Vishwa/Projects/SOL_AI/frontend/components/word/MeaningCard.jsx#L7) hardcodes `propSenses.slice(0, 2)`.
   - **Extension Drawer:** [content.js#L484](file:///c:/Vishwa/Projects/SOL_AI/extension/content/content.js#L484) hardcodes `data.senses.slice(0, 2)`.
   - **Extension Popup:** [popup.js#L117](file:///c:/Vishwa/Projects/SOL_AI/extension/popup/popup.js#L117) hardcodes `data.senses.slice(0, 2)`.
5. **Re-parsing:**
   If `data.senses` is absent, clients re-parse `data.meaning` by splitting on `;` and slicing to 2 ([MeaningCard.jsx#L14](file:///c:/Vishwa/Projects/SOL_AI/frontend/components/word/MeaningCard.jsx#L14), [content.js#L486](file:///c:/Vishwa/Projects/SOL_AI/extension/content/content.js#L486), [popup.js#L120](file:///c:/Vishwa/Projects/SOL_AI/extension/popup/popup.js#L120)).

---

## 19. Extension Display vs. Web App Display

```
+------------------------------------+------------------------------------+------------------------------------+
| UI Feature / Field                 | Chrome Extension (content.js)      | Next.js Web App (frontend/app/)    |
+------------------------------------+------------------------------------+------------------------------------+
| Sends query context to backend?    | YES (via DOM sentence extraction)  | NO (only sends query string)       |
| Displays contextual_meaning?       | YES ("In this context" gold card)  | NO (not referenced in any component)|
| Displays contextual_interpretation?| NO (completely ignored)            | YES (under "meanings" tab)         |
| Displays structured senses?        | YES (hardcoded slice to 2)         | YES (hardcoded slice to 2)         |
| Displays morphology?               | YES (pills for POS, Case, Number)  | YES (detailed table & segment cards)|
| Displays literary context?         | YES (snippets with expand button)  | YES (rich reader cards & metrics)  |
| Displays related words?            | YES (clickable chips, max 3)       | YES (grid with relations)          |
| Displays uncertainties?            | NO                                 | YES (dedicated alert banner)       |
+------------------------------------+------------------------------------+------------------------------------+
```

---

## 20. Source-of-Truth Table

| Linguistic Data | Original Source | Processing Layer | Final Owner | Client Responsibility |
|---|---|---|---|---|
| **Lexical Senses** | `Thani Thamizh Akarathi`, `Tamil Wiktionary` | `RetrievalEngine` $\to$ `build_lexical_senses` | Backend (`services.py`) | Truncates to top 2 (`slice(0, 2)`) |
| **Morphology** | `ThamizhiMorph` (FST models) | `parse_structured_morphology` | Backend (`services.py`) | Renders tags/breakdown pills |
| **Context** | Browser DOM selection | `content.js` sentence matching | Extension Client | Transmits string to `/api/query` |
| **WSD Selection** | Context Sentence + Lexical Evidence | `TamilWSD.disambiguate()` | Backend (`TamilWSD`) | Renders under "In this context" |
| **Literary Passages** | `Sentamizh`, `Project Madurai` | `SentamizhContextSelector` $\to$ `process_literary_evidence` | Backend (`services.py`) | Renders highlighted snippets |
| **Related Words** | `Tamil WordNet`, `Akarathi` | `EvidenceAggregator` $\to$ fallback extraction | Backend (`services.py`) | Renders clickable tags |
| **Semantic Evidence** | `Project Madurai Semantic` (E5-small) | `ProjectMaduraiSemanticAdapter` | Backend (`engine.py`) | Ingested into literary context |

---

## 21. "What Gets Sent to the LLM?" Table

| Item | Sent to LLM? | Source | Rationale / Purpose |
|---|---|---|---|
| **Query** | **YES** | User Request | Primary target word anchor |
| **Normalized Query** | **YES** | `QueryNormalizer` | Canonical NFC representation |
| **Context Sentence** | **YES** (if present) | Client DOM extraction | Polysemy anchor for interpretation |
| **All Lexical Senses** | **YES** | Dictionary adapters | Sole dictionary ground truth |
| **WSD Selected Sense** | **NO** | `TamilWSD` | WSD runs *after* or in parallel; not in prompt |
| **WSD Score** | **NO** | `TamilWSD` | Internal algorithmic score; omitted from prompt |
| **Morphology** | **YES** | `ThamizhiMorph` | Grounded grammatical tags & FOMA output |
| **Literary Evidence** | **YES** (capped at 5) | `SentamizhContextSelector` | Grounded classical usage evidence |
| **Related Words** | **YES** | WordNet synsets | Grounded semantic relationships |
| **Semantic Evidence** | **YES** (if retrieved) | Project Madurai Semantic | Dense thematic literary occurrences |
| **Source Provenance** | **YES** | Aggregated summary | Resource audit and hit transparency |

---

## 22. "Who Owns What?" Table

| System Responsibility | Backend Services | Python WSD | LLM Layer | Web App | Extension Client |
|---|---|---|---|---|---|
| **Resource Retrieval** | **PRIMARY** | NONE | NONE | NONE | NONE |
| **Context Extraction** | NONE | NONE | NONE | NONE | **PRIMARY** |
| **Sense Selection (WSD)** | SECONDARY | **PRIMARY** | NONE | NONE | NONE |
| **Narrative Interpretation** | NONE | NONE | **PRIMARY** | NONE | NONE |
| **Morphological Analysis** | **PRIMARY** | NONE | NONE | NONE | NONE |
| **Literary Selection** | **PRIMARY** | NONE | NONE | NONE | NONE |
| **UI Sense Rendering** | NONE | NONE | NONE | **PRIMARY** | **PRIMARY** |

*Explanations:*
- **Sense Selection:** Python WSD is `PRIMARY` because `_apply_post_overrides` unconditionally forces its result onto the final response. The LLM has `NONE` runtime ownership over the field.
- **Context Extraction:** Extension is `PRIMARY` because it executes the DOM tree traversal. The Web App has `NONE` capability.
- **Narrative Interpretation:** LLM is `PRIMARY` for generating contextual explanatory prose (`contextual_interpretation`).

---

## 23. Potential Architectural Inefficiencies & Duplications

> [!WARNING]
> The following observations represent factual architectural inefficiencies and code duplications identified directly in the source code without speculation:

1. **Redundant WSD Work by LLM & Post-Override Overwrite:**
   The system prompt ([prompts.py#L22-L27](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/prompts.py#L22-L27)) spends significant tokens commanding the LLM to perform WSD and return `contextual_meaning`. However, `services.py#L180` immediately overwrites `response.contextual_meaning` with `sel_sense` from `TamilWSD`. Asking the LLM to perform WSD is token-wasteful because its decision is never preserved.
2. **Double Execution of WSD in Mock Mode:**
   `MockLLMInterpreter.interpret()` executes `wsd.disambiguate()` ([interpreter.py#L163](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/interpreter.py#L163)), and then `SOLServiceRegistry._apply_post_overrides()` executes `wsd.disambiguate()` a second time ([services.py#L175](file:///c:/Vishwa/Projects/SOL_AI/backend/sol_django/api/services.py#L175)).
3. **Double Parsing and Slicing of Lexical Senses:**
   Raw entries in Akarathi are squashed into a single comma-separated text blob in `build_akarathi_index.py`. Then in `_apply_post_overrides()`, they are split and parsed into `LexicalSenseItem`. When delivered to the frontend, both `MeaningCard.jsx` and `content.js` slice them to 2, throwing away any additional senses.
4. **Brute-Force Post-LLM Structural Overwrite:**
   The LLM is prompted to produce `morphology` and `literary_context` in its JSON schema, but `_apply_post_overrides()` unconditionally overwrites both fields with deterministic Python objects ([services.py#L218, L234](file:///c:/Vishwa/Projects/SOL_AI/backend/sol_django/api/services.py#L218)). Prompting the LLM to format these complex nested structures consumes input/output tokens unnecessarily.
5. **Complete Feature Blindspot in Web App:**
   `contextual_meaning` is a core capability of the system, yet the Web App API client cannot send context, and the Web App UI has no component or element capable of rendering it.

---

## 24. Unknowns / Ambiguities

1. **Wiktionary Database Availability:**
   `data/processed/wiktionary_index.db` is an optional binary SQLite database. If it is rebuilt or absent, the number of candidate senses for polysemous words drops to 1 (collapsed Akarathi gloss), which triggers `wsd.py#L330` and bypasses the WSD scoring matrix.
2. **WordNet Gloss Emptiness:**
   Tamil WordNet lexical records have `meaning=None` permanently hardcoded in `wordnet.py`. While intentional due to the raw dump characteristics, it means WordNet provides zero sense candidates to WSD.

---

## 25. Files Inspected

- [backend/sol_django/api/views.py](file:///c:/Vishwa/Projects/SOL_AI/backend/sol_django/api/views.py) (HTTP transport, payload parsing)
- [backend/sol_django/api/services.py](file:///c:/Vishwa/Projects/SOL_AI/backend/sol_django/api/services.py) (Service registry, fallback cascade, `_apply_post_overrides`)
- [backend/sol_django/sol_django/urls.py](file:///c:/Vishwa/Projects/SOL_AI/backend/sol_django/sol_django/urls.py) (Root routing, `/api/query`, aliases)
- [backend/sol_django/sol_django/settings.py](file:///c:/Vishwa/Projects/SOL_AI/backend/sol_django/sol_django/settings.py) (Django configuration)
- [backend/retrieval/engine.py](file:///c:/Vishwa/Projects/SOL_AI/backend/retrieval/engine.py) (Unified retrieval, multi-pass search, semantic short-circuit)
- [backend/retrieval/aggregator.py](file:///c:/Vishwa/Projects/SOL_AI/backend/retrieval/aggregator.py) (Evidence deduplication, candidate extraction, priority ranking)
- [backend/resources/akarathi.py](file:///c:/Vishwa/Projects/SOL_AI/backend/resources/akarathi.py) (Thani Thamizh Akarathi adapter)
- [backend/resources/wiktionary.py](file:///c:/Vishwa/Projects/SOL_AI/backend/resources/wiktionary.py) (Tamil Wiktionary SQLite adapter)
- [backend/resources/wordnet.py](file:///c:/Vishwa/Projects/SOL_AI/backend/resources/wordnet.py) (Tamil WordNet adapter)
- [backend/resources/thamizhimorph.py](file:///c:/Vishwa/Projects/SOL_AI/backend/resources/thamizhimorph.py) (ThamizhiMorph FST adapter & morphology parser)
- [backend/resources/sentamizh.py](file:///c:/Vishwa/Projects/SOL_AI/backend/resources/sentamizh.py) (Sentamizh corpus adapter)
- [backend/resources/project_madurai.py](file:///c:/Vishwa/Projects/SOL_AI/backend/resources/project_madurai.py) (Project Madurai exact FTS5 adapter)
- [backend/resources/project_madurai_semantic.py](file:///c:/Vishwa/Projects/SOL_AI/backend/resources/project_madurai_semantic.py) (Project Madurai dense semantic adapter)
- [backend/interpretation/wsd.py](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/wsd.py) (Tamil WSD scoring engine, collocation, stemming)
- [backend/interpretation/interpreter.py](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/interpreter.py) (Mock, Gemini, and Groq interpreters)
- [backend/interpretation/prompts.py](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/prompts.py) (System prompt, evidence prompt formatter)
- [backend/interpretation/evidence_pack.py](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/evidence_pack.py) (EvidencePack categorizer & builder)
- [backend/interpretation/context_selector.py](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/context_selector.py) (Literary context selection & work diversity)
- [backend/interpretation/literary_processor.py](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/literary_processor.py) (Snippet generation, highlight offsets)
- [backend/interpretation/schemas.py](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/schemas.py) (Pydantic schemas: SOLResponse, EvidencePack, LexicalSenseItem)
- [extension/content/content.js](file:///c:/Vishwa/Projects/SOL_AI/extension/content/content.js) (DOM sentence context extraction, panel rendering)
- [extension/background/service-worker.js](file:///c:/Vishwa/Projects/SOL_AI/extension/background/service-worker.js) (Message routing, HTTP dispatch to backend)
- [extension/popup/popup.js](file:///c:/Vishwa/Projects/SOL_AI/extension/popup/popup.js) (Manual toolbar lookup, response rendering)
- [frontend/lib/api.js](file:///c:/Vishwa/Projects/SOL_AI/frontend/lib/api.js) (Next.js REST client)
- [frontend/app/HomeClient.jsx](file:///c:/Vishwa/Projects/SOL_AI/frontend/app/HomeClient.jsx) (Search query flow, state handling)
- [frontend/components/word/WordExplorer.jsx](file:///c:/Vishwa/Projects/SOL_AI/frontend/components/word/WordExplorer.jsx) (Word presentation orchestrator)
- [frontend/components/word/MeaningCard.jsx](file:///c:/Vishwa/Projects/SOL_AI/frontend/components/word/MeaningCard.jsx) (Sense rendering & slice logic)
- [frontend/components/word/InterpretationCard.jsx](file:///c:/Vishwa/Projects/SOL_AI/frontend/components/word/InterpretationCard.jsx) (Narrative prose interpretation card)

---

## 26. Final Findings

1. **Current Code Authority:** The codebase relies on a **deterministic Python post-override** for disambiguation (`TamilWSD`), morphology (`ThamizhiMorph`), and literary context (`SentamizhContextSelector`). The LLM acts purely as a narrative explanation generator.
2. **Context Delivery Integrity:** The Chrome Extension context-menu path is the only client path currently equipped to supply context sentences to the API and render the resulting contextual sense.
3. **Zero Mutation Compliance:** This forensic audit was executed under strict read-only compliance without altering or refactoring any code, tests, or configurations.
