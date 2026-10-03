# SOL AI

SOL AI is a Tamil lexical intelligence system engineered to unite deterministic linguistic resources, finite-state morphology, multi-dictionary retrieval, classical literary corpus evidence, dense semantic vector retrieval, and deterministic contextual word-sense disambiguation (WSD). Rather than functioning as an unconstrained generative chatbot or speculative large language model, SOL AI operates on strict evidence grounding: authoritative linguistic databases establish lexical facts and morphological structures, while an integrated Large Language Model (LLM) layer is strictly confined to synthesizing, explaining, and translating that verified evidence.

---

## Overview

### The Problem
Looking up words in Tamil is fundamentally more complex than in isolating or mildly inflected languages. Modern digital search interfaces frequently fail because:

1. **Pervasive Agglutinative Morphology (ஒட்டுநிலை மொழி):** Tamil words in running text are rarely dictionary headwords. Verbs, nouns, and adjectives accumulate case markers, plural suffixes, postpositions, tense infixes, and euphonic glides (sandhi). For example, the surface form `மரங்களில்` cannot be resolved by an exact dictionary headword query; it must be decomposed into its root lemma `மரம்`, plural marker `-ங்கள்`, and locative case suffix `-இல்`.
2. **Deep Polysemy (பலபொருள் ஒரு சொல்):** High-frequency Tamil words carry divergent senses across semantic domains. A single word like `கால்` can signify a mathematical fraction ($\frac{1}{4}$), an anatomical foot or leg, physical movement, atmospheric wind, or a furniture support beam.
3. **Fragmented Lexical Resources:** No single comprehensive dictionary covers the full spectrum of Tamil. Classical purist lexicons (*Thani Thamizh Akarathi*), modern crowdsourced dictionaries (*Tamil Wiktionary*), and lexical-semantic relational databases (*Tamil WordNet*) exist in disparate formats, conflicting taxonomies, and varying coverage depths.
4. **Classical Literary Attestation:** Tamil boasts an unbroken 2,000+ year literary continuum. Scholarly and educational research requires verifying not just abstract definitions, but attested usages across Sangam poetry (*Ettuthokai*, *Pattuppattu*), didactic literature (*Tirukkural*, *Naladiyar*), and classical epics.
5. **Contextual Meaning in Running Text:** While dictionaries catalog all historical senses, readers and browser users require disambiguation for the specific sense active in the sentence they are reading.

### Central Design Principle

> **"Deterministic retrieval is the source of truth; the LLM synthesizes and explains from evidence."**

In SOL AI, the LLM is never the knowledge base. It is never permitted to invent root lemmas, fabricate grammatical rules, halluncinate literary verses, or arbitrate word senses. The deterministic Python retrieval pipeline and rule-based WSD engine extract and select the evidence; the LLM acts solely as a structured interpretation layer translating and explaining that evidence.

---

## Key Features

- **Multi-Stage Retrieval Pipeline:**
  - **Pass 1 (Surface Lookup):** Exact full-text and headword lookup across all deterministic resources.
  - **Pass 2 (Lemma / Root Lookup):** Rule-based FST morphology isolates candidate lemmas and roots, triggering secondary lookups across lexical and literary databases.
  - **Pass 3 (Dense Semantic Retrieval):** Supplements exact retrieval for abstract, thematic, or paraphrastic queries against the canonical Project Madurai literary corpus.
- **Rule-Based Morphological Parsing:** Integrates `ThamizhiMorph` Finite-State Transducers (FST) running on `flookup` (native or WSL) to analyze parts of speech, noun cases, grammatical number, and verbal tenses, distinguishing Core FST from Guesser models.
- **Multi-Resource Lexical Integration:** Queries *Tamil Wiktionary*, *Thani Thamizh Akarathi*, and *Tamil WordNet*, normalizing definitions into discrete senses without collapsing distinct entries.
- **Classical Literary Evidence:** Queries *Sentamizh Corpus* and *Project Madurai* (35 canonical works across 14,383 stanzas), surfacing original classical verses alongside modern Tamil glosses.
- **Project Madurai Exact FTS5 Search:** Full-text SQLite FTS5 search with custom diacritic-preserving Tamil tokenization.
- **Project Madurai Dense Semantic Search:** Precomputed 384-dimensional dense vectors using a pinned revision of `intfloat/multilingual-e5-small` over 13,284 poetic passages, operating at a calibrated threshold ($\tau = 0.845, K = 25$).
- **Contextual Word-Sense Disambiguation (TamilWSD):** Deterministic, multi-source sense selection using structured `SenseCandidate` representation, positional distance weighting, and generalized semantic domain detectors (Quantity/Units, Somatic/Anatomy, Structural/Furniture).
- **Principled WSD Abstention:** When context is missing, evidence is below threshold, or domain signals conflict, the system cleanly abstains rather than forcing an arbitrary sense.
- **Separation of General Meaning and Contextual Meaning:** `meaning` preserves the full polysemous dictionary definition inventory; `contextual_meaning` specifies the sense dynamically selected for the user's supplied sentence.
- **Contextual Disambiguation in Action:**
  The same surface word dynamically yields different contextual meanings based on surrounding text:
  - `கால்` in a quantity context (`அவனுடைய தம்பி கால் கிலோ மாம்பழம் வாங்கி வந்தான்.`):
    $\rightarrow$ **நான்கில் ஒரு பங்கு (¼ kg / 250g)**
  - `கால்` in an anatomical context (`அவன் கல்லில் நடக்கும்போது கால் வழுக்கி கீழே விழுந்தான்.`):
    $\rightarrow$ **உடல் உறுப்பு / பாதம் (Foot / Leg)**
  - `கால்` in a structural context (`நாற்காலியின் ஒரு கால் உடைந்ததால் கீழே சாய்ந்தது.`):
    $\rightarrow$ **நாற்காலியைத் தாங்கும் பகுதி (Furniture leg / Structural support)**
  - `கால்` without context:
    $\rightarrow$ `contextual_meaning: null` (Abstention; full polysemous definition preserved in `meaning`).
  *(Note: These are calculated dynamically from extracted context tokens and domain cues, not hardcoded single-word translations).*
- **Multi-Provider LLM Integration:** Supports Google Gemini (`gemini-3.6-flash`), Groq (`qwen/qwen3.8-27b`), and a fully offline deterministic Mock interpreter.
- **Automatic Fallback Cascade:** Primary LLM $\rightarrow$ Groq fallback $\rightarrow$ Deterministic Mock interpreter ensures zero downtime during API outages or rate limits.
- **Stateless Django REST API:** High-throughput HTTP backend (`/api/health`, `/api/query`) with CORS support and thread-safe process-local service registries.
- **Browser Extension (Manifest V3):** Text-selection listener with automated DOM sentence context extraction, shadow DOM overlay, and dark-mode UI.
- **Modern Web Application (Next.js 16):** Modular interface featuring Keyman Tamil typing support, `WordExplorer`, morphological inspection, and literary passage exploration.

---

## Why SOL AI?

A simple dictionary lookup or standard generative LLM prompt is insufficient for scholarly Tamil research:

| Challenge | Simple Dictionary | Pure Generative LLM | SOL AI Architecture |
|---|---|---|---|
| **Inflected Words** (`மரங்களில்`, `வந்தார்கள்`) | **Fails (404 / Not Found):** Dictionaries index base lemmas, not inflected surface variants. | Hallucinates or guesses grammatical properties without formal verification. | **ThamizhiMorph FST:** Deconstructs inflections into root lemma + grammatical tags; triggers Pass 2 secondary lookup. |
| **Polysemy Resolution** (`கால்`, `ஆறு`) | Displays a flat list of 10+ definitions; reader must manually parse. | Often picks the most common sense in internet text regardless of the actual context. | **Deterministic WSD:** Extracts domain cues, positional collocates, and scores candidate senses; abstains on ambiguity. |
| **Resource Coverage** | Restricted to a single dictionary's bias or era. | Obscures where definitions originate; mixes modern colloquialisms with classical terms. | **Unified Evidence Aggregator:** Synthesizes Wiktionary, Akarathi, WordNet, Sentamizh, and Project Madurai with full provenance. |
| **Literary Grounding** | Rare or absent in general-purpose dictionaries. | Hallucinates verses, attributes poems to the wrong poets, or fabricates lines. | **SQLite FTS5 + Dense Vectors:** Verifies real stanzas from 35 canonical Project Madurai works and Sangam poetry. |
| **Thematic / Conceptual Queries** | Fails unless user inputs the exact classical vocabulary. | Answers fluently but lacks verifiable citations. | **Calibrated Semantic Retrieval:** Connects modern conceptual queries (`கல்வியின் பெருமை...`) to classical couplets (`கற்க கசடற...`). |

---

## Architecture

The diagram below illustrates the end-to-end data flow from user interaction to structured response generation:

```mermaid
flowchart TD
    subgraph Clients["Clients"]
        WebApp["Next.js Web App (localhost:3000)"]
        Extension["Chrome Extension (Manifest V3)"]
    end

    subgraph APILayer["Django REST API Layer (backend/sol_django)"]
        Views["views.py (/api/query, /api/health)"]
        Services["services.py (SOLServiceRegistry)"]
    end

    subgraph RetrievalEngineSub["Retrieval Engine (backend/retrieval/engine.py)"]
        Normalizer["QueryNormalizer (Unicode NFC)"]
        Pass1["Pass 1: Exact Surface Retrieval"]
        Pass2["Pass 2: Lemma / Root Retrieval"]
        ShortCircuit{"Evaluate Semantic Short-Circuit"}
        Pass3["Pass 3: Dense Semantic Retrieval"]
        Deduplication["Stable Project Madurai Chunk Deduplication"]
        Aggregator["EvidenceAggregator (Support Mapping & Ranking)"]
        ContextSelector["SentamizhContextSelector (Work Diversity)"]
    end

    subgraph Adapters["Linguistic & Literary Resource Adapters"]
        MorphAdapter["ThamizhiMorph (FST flookup)"]
        WikiAdapter["Tamil Wiktionary (SQLite)"]
        AkarathiAdapter["Thani Thamizh Akarathi (JSON Index)"]
        WordNetAdapter["Tamil WordNet (SQLite)"]
        SentamizhAdapter["Sentamizh Corpus (SQLite)"]
        PMAExact["Project Madurai Exact (SQLite FTS5)"]
        PMASemantic["Project Madurai Semantic (E5-small + .npy)"]
    end

    subgraph WSDStage["Contextual WSD Stage (backend/interpretation/wsd.py)"]
        ExtractCands["extract_sense_candidates() -> List[SenseCandidate]"]
        ExtractFeatures["WSDContextFeatureExtractor -> WSDContextFeatures"]
        ScoreWSD["TamilWSD Scoring & Abstention Guards"]
        WSDRes["Authoritative WSDResult"]
    end

    subgraph InterpretationStage["Interpretation & Synthesis Stage"]
        Pack["EvidencePack (wsd_result attached)"]
        InterpreterSelect["get_interpreter() (Gemini / Groq / Mock)"]
        LLMExecution["LLM Synthesis (Strict Evidence Prompt)"]
        PostOverrides["_apply_post_overrides() (Structural Injection)"]
        FinalResponse["Final SOLResponse (Pydantic Validated JSON)"]
    end

    WebApp -->|POST /api/query| Views
    Extension -->|POST /api/query (with context)| Views
    Views --> Services
    Services --> Normalizer
    Normalizer --> Pass1

    Pass1 <--> MorphAdapter
    Pass1 <--> WikiAdapter
    Pass1 <--> AkarathiAdapter
    Pass1 <--> WordNetAdapter
    Pass1 <--> SentamizhAdapter
    Pass1 <--> PMAExact

    Pass1 --> Pass2
    Pass2 <--> WikiAdapter
    Pass2 <--> AkarathiAdapter
    Pass2 <--> WordNetAdapter
    Pass2 <--> SentamizhAdapter
    Pass2 <--> PMAExact

    Pass2 --> ShortCircuit
    ShortCircuit -->|Insufficient Evidence| Pass3
    ShortCircuit -->|Sufficient Exact Evidence| Deduplication
    Pass3 <--> PMASemantic
    Pass3 --> Deduplication

    Deduplication --> Aggregator
    Aggregator --> ContextSelector
    ContextSelector --> Pack

    Pack --> ExtractCands
    Pack --> ExtractFeatures
    ExtractCands --> ScoreWSD
    ExtractFeatures --> ScoreWSD
    ScoreWSD --> WSDRes

    WSDRes --> Pack
    Pack --> InterpreterSelect
    InterpreterSelect --> LLMExecution
    LLMExecution --> PostOverrides
    WSDRes --> PostOverrides
    PostOverrides --> FinalResponse
    FinalResponse --> Views
```

---

## Retrieval Pipeline

SOL AI executes a multi-pass retrieval pipeline coordinated by `RetrievalEngine`:

### 1. Query Normalization
Every query string is processed by [`QueryNormalizer`](file:///c:/Vishwa/Projects/SOL_AI/backend/query/normalizer.py):
- Canonical Unicode NFC normalization.
- Trimming leading/trailing whitespace and punctuation.
- Filtering out zero-width characters (`\u200B`–`\u200D`, `\uFEFF`).
- Empty queries fail fast before triggering resource lookups.

### 2. Pass 1: Surface Retrieval
The normalized query is dispatched simultaneously to deterministic resource adapters:
- **ThamizhiMorph:** Evaluates surface form for morphological analyses.
- **Tamil Wiktionary:** Exact lookup on `definitions` table by `headword`.
- **Thani Thamizh Akarathi:** Exact key lookup in the in-memory headword index.
- **Tamil WordNet:** Lookup across `twn_index`, `sense_index`, `morphtable_index`, and `frequency_index`.
- **Sentamizh Corpus:** Exact token matching across indexed verse tokens.
- **Project Madurai Exact:** Exact token and phrase search in `chunks_fts` via SQLite FTS5.

### 3. Morphological Analysis
If the surface form is inflected, [`ThamizhiMorphAdapter`](file:///c:/Vishwa/Projects/SOL_AI/backend/resources/thamizhimorph.py) runs the query through FOMA Finite-State Transducers:
- **Core FST Models:** `noun.fst`, `verb.fst`, `adj.fst`, `adv.fst`.
- **Guesser FST Models:** `noun-guess.fst`, `verb-guess.fst`, `adj-guess.fst`, `adv-guess.fst`.
- **Output Decomposition Example:**
  ```text
  Query: "மரங்களில்"
  FOMA Tag: "மரம்+noun+pl+loc"
  Structured Morphology:
    - Lemma: "மரம்"
    - POS: "noun"
    - Case: "Locative"
    - Number: "Plural"
    - Segments: [
        {"tamil": "மரம்", "role": "root"},
        {"tamil": "ங்கள்", "role": "plural"},
        {"tamil": "இல்", "role": "case_locative"}
      ]
  ```
- **Analysis Priority:** Core FST models take precedence over Guesser models. Guesser analyses are explicitly flagged in `uncertainties`.

### 4. Pass 2: Lemma / Root Expansion
Candidate lemmas and root words discovered in Pass 1 morphology (such as `மரம்` extracted from `மரங்களில்`) are dispatched to a secondary lookup pass across lexical and literary adapters (*Wiktionary*, *Akarathi*, *WordNet*, *Sentamizh*, *Project Madurai*). This guarantees that inflected words receive the complete lexical definitions and literary verses of their base lemma.

### 5. Pass 3: Dense Semantic Retrieval
When enabled, Pass 3 supplements exact retrieval using dense vector similarity over the canonical Project Madurai corpus:
- **Short-Circuit Evaluation:** Semantic retrieval is skipped if Pass 1 and Pass 2 already establish strong deterministic proof:
  - *Condition A:* Project Madurai exact retrieval returned $\ge 25$ matches (exact saturation).
  - *Condition B:* Literary evidence $\ge 10$ passages supported by lexical or morphological hits.
  - *Condition C:* Weak or zero deterministic evidence bypasses short-circuiting to ensure conceptual queries reach semantic search.
- **Model & Configuration:** Pinned `intfloat/multilingual-e5-small` (revision `614241f622f53c4eeff9890bdc4f31cfecc418b3`, 384 dimensions).
- **Asymmetric Query Prefix:** Queries are prefixed with `query: ` (e.g., `query: கல்வியின் பெருமை`).
- **Precomputed Artifacts:** Matrix dot-product against `madurai_semantic_vectors.npy` (13,284 passages, 20.4 MB) and `madurai_semantic_meta.json` (7.3 MB).
- **Calibrated Operating Point:** Internal candidate pool $K = 25$, cosine similarity threshold $\tau = 0.845$.
- **Exact Preservation:** If a chunk was already retrieved by Pass 1 or Pass 2, exact provenance is preserved and never overwritten by semantic metadata.

### 6. Evidence Aggregation & Context Selection
- [`EvidenceAggregator`](file:///c:/Vishwa/Projects/SOL_AI/backend/retrieval/aggregator.py) groups evidence by candidate lemma, compiles source provenance, and computes cross-resource support mapping. Semantic evidence is strictly excluded from lexical verification counts.
- [`SentamizhContextSelector`](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/context_selector.py) filters raw literary matches down to a representative, diverse subset (maximum 5 contexts), ensuring work diversity across classical anthologies.

---

## Contextual Word-Sense Disambiguation (WSD)

Following the architectural overhaul in [`backend/interpretation/wsd.py`](file:///c:/Vishwa/Projects/SOL_AI/backend/interpretation/wsd.py), WSD is structured into a deterministic, single-pass pipeline:

```text
User Query + Surrounding Context
            │
            ▼
Sense Candidate Extraction (extract_sense_candidates)
  ├── Wiktionary (discrete sub-senses)
  ├── Akarathi (delimited traditional definitions)
  └── Excludes records with meaning=None (WordNet)
            │
            ▼
Context Feature Extraction (WSDContextFeatureExtractor)
  ├── Query position masking (prevents self-match leakage)
  ├── Content token isolation & Tamil suffix stemming
  └── Domain Cue Detectors (Quantity, Somatic, Furniture)
            │
            ▼
Deterministic Candidate Scoring (TamilWSD)
  ├── Domain Proximity Boosts (+35.0 adjacent, scaled by distance)
  ├── Exact & Stem Overlap (+3.5 / +1.5)
  ├── Synonym & Related Expansion via Akarathi (+2.0)
  ├── Genus Headword Downweighting (0.4x)
  └── Specificity Density Preference
            │
            ▼
Abstention & Competition Guards
  ├── Missing Context -> status="no_context", selected_sense=None
  ├── Low Evidence Floor (< 1.0) -> status="insufficient_evidence"
  ├── Close Competition (< 0.2 diff) -> status="ambiguous"
  └── Domain Conflict (>= 10.0 in distinct domains) -> status="conflicting_signals"
            │
            ▼
Authoritative WSDResult Attached to EvidencePack
            │
            ▼
LLM Interpretation Layer (Synthesizes explanation ONLY; cannot override sense)
```

### Core Architectural Invariants

1. **Python WSD Authoritatively Owns Sense Selection:**
   The deterministic Python WSD layer selects the winning sense. The downstream LLM is strictly prohibited from re-arbitrating or selecting alternative senses.
2. **LLM Explains, Does Not Decide:**
   The prompt instructs the LLM: *"The deterministic WSD layer has already selected the authoritative sense. Synthesize and explain why this sense fits the sentence in Tamil. If WSD abstained, explain the ambiguity rather than inventing a sense."*
3. **Strict Separation of Meaning Fields:**
   - `meaning`: Always retains the full inventory of documented dictionary definitions (separated by semicolons). It is never overwritten by contextual selection.
   - `contextual_meaning`: Contains only the specific sense selected for the supplied sentence (or `null` if WSD abstained or no context was given).
4. **Principled Abstention:**
   If a user supplies a sentence that lacks discriminative evidence (e.g., `அவன் நேற்று அங்கு ஒரு வார்த்தை சொன்னான்`), WSD abstains (`status: "insufficient_evidence"`) rather than picking an arbitrary definition.

### Verified WSD Demonstration Cases

| Query | Context Sentence | WSD Status | Selected Sense | Explanatory Signals |
|---|---|:---:|---|---|
| `கால்` | அவனுடைய தம்பி **கால் கிலோ** மாம்பழம் வாங்கி வந்தான். | `selected` | **நான்கில் ஒரு பங்கு — ஒரு கிலோவின் நான்கில் ஒரு பங்கு (¼ kg / 250g)** | Adjacent quantity collocate (`கிலோ`, dist=1); $+35.0$ domain boost. |
| `கால்` | அவன் கல்லில் நடக்கும்போது **கால் வழுக்கி** கீழே விழுந்தான். | `selected` | **உடல் உறுப்பு / பாதம் — கால் (உறுப்பு); foot, leg.** | Somatic collocate (`வழுக்கி`, `நடக்கும்போது`); $+35.0$ somatic boost. |
| `கால்` | நாற்காலியின் ஒரு **கால் உடைந்ததால்** கீழே சாய்ந்தது. | `selected` | **நாற்காலியைத் தாங்கும் பகுதி — மேசை, நாற்காலி ஆகியவற்றின் தாங்கும் பகுதி** | Structural collocate (`நாற்காலி`, `உடைந்ததால்`); $+35.0$ structural boost. |
| `கால்` | *(None / Empty)* | `no_context` | `null` | Context absent; full dictionary senses preserved in `meaning`. |
| `கால்` | அவன் நேற்று அங்கு ஒரு வார்த்தை சொன்னான். | `insufficient_evidence` | `null` | Top score $< 1.0$; discriminative context absent. |

---

## Linguistic Resources

SOL AI integrates six verified linguistic resources:

| Resource | Role in SOL AI | Retrieval / Usage | Dataset Size & Format | Attribution & Licensing |
|---|---|---|---|---|
| **ThamizhiMorph** | Rule-based morphological analyzer | FOMA Finite-State Transducers queried via `flookup` (Core + Guesser models) | 8 `.fst` binary models | Sarveswaran et al. (University of Jaffna). Open-source academic resource; consult upstream repository for specific license terms. |
| **Tamil Wiktionary** | Modern & historical lexical definitions | Exact headword queries on SQLite database (`wiktionary_index.db`) | 75.8 MB SQLite DB; extracted from offline XML dump | Wikimedia Foundation / Wiktionary contributors. CC BY-SA 3.0 / GFDL. |
| **Thani Thamizh Akarathi** | Purist Tamil lexicon & synonym expansion | In-memory JSON headword index (`akarathi_index.json`); powers WSD synonyms | 140.8 MB JSON index; 11,540+ entries | Kaviyarasan N. Creative Commons / open dictionary license; upstream provenance applies. |
| **Tamil WordNet** | Lexical-semantic network & morphtable mappings | SQLite queries on `wordnet_index.db` (`twn_index`, `sense_index`, `morphtable_index`) | 109.0 MB SQLite DB; 50,497 synset nodes, 434,849 morphtables | AU-KBC Research Centre, Chennai & Tamil University, Thanjavur. CC BY-SA 2.5 (`tvudump.sql`) / GPL. |
| **Sentamizh Corpus** | Classical Sangam poetry & epic literature | SQLite queries on `sentamizh_index.db` joining `verse_tokens` and `verses` | 65.9 MB SQLite DB; 10,393 verse records | e-thamil / Open Tamil community. Apache License 2.0 with upstream source notices. |
| **Project Madurai (Exact)** | Authoritative canonical literary corpus | SQLite FTS5 full-text queries on `madurai_exact.db` (`chunks_fts`) | 25.7 MB SQLite DB; 14,383 stanzas across 35 works | Project Madurai (projectmadurai.org). Freely distributed open electronic texts. |
| **Project Madurai (Semantic)** | Dense semantic literary retrieval | Precomputed L2-normalized float32 matrix dot-product search | 20.4 MB `.npy` vector matrix + 7.3 MB `.json` metadata (13,284 passages) | Embeddings generated using `intfloat/multilingual-e5-small` (Microsoft/Hugging Face). |

---

## Project Madurai Integration

The Project Madurai integration was audited and rebuilt to provide an authoritative literary corpus:

### Canonical Corpus Statistics
- **Canonical Works:** 35 works across 31 Project Madurai releases.
- **Relational Schema:** `chunks` table in `data/processed/madurai_exact.db` (24.54 MB).
- **Total Relational Rows:** Exactly **14,383 rows**.
- **FTS5 Virtual Table:** Exactly **14,383 rows** in `chunks_fts` (100% parity).
- **Diacritic-Preserving Tokenizer:**
  ```sql
  CREATE VIRTUAL TABLE chunks_fts USING fts5(
      normalized_text,
      content='chunks',
      content_rowid='rowid',
      tokenize="unicode61 remove_diacritics 0 tokenchars 'ஂாிீுூெேைொோௌ்ௗ'"
  );
  ```
- **Tirukkural Integrity:** Contains exactly **1,330 couplets** (stanzas 1 to 1330) with zero off-by-one shifting and zero boilerplate.
- **Didactic Aphorisms:** *Aathichudi* has all **110 chunks**; *Konrai Vendhan* has all **92 chunks**.
- **Dense Semantic Pool:** 13,284 poetic passages indexed into `madurai_semantic_vectors.npy` (1,099 non-poetic structural stubs, speaker attributions, and TOC stubs cleanly suppressed).

### Documented Residual Observations
Audits identified minor residual data artifacts that do not affect exact lexical retrieval:
- 51 chunks in *Thiruvasagam* (Parts 1 & 2) contain a trailing `\nBack` navigation link artifact from raw HTML files.
- Chunk `PM-SILAP_MADURAI-0003` contains an unstripped webmaster contact line.
- Chunk `PM-CHINTHAMANI-0003` contains a publication source credit line.
*(Note: These artifacts are suppressed during semantic preprocessing via `backend/retrieval/semantic_preprocessing.py`).*

---

## LLM Layer

The interpretation layer bridges deterministic evidence with natural language synthesis:

### Supported Providers
- **Google Gemini:** `gemini-3.6-flash` via REST API endpoint.
- **Groq:** `qwen/qwen3.8-27b` via OpenAI-compatible chat completion REST API.
- **Mock Interpreter:** Fully offline, deterministic interpreter for local testing and zero-API execution.

### Multi-Stage Fallback Cascade
When executing queries through `SOLServiceRegistry`:
1. Attempts the configured primary provider (e.g. Gemini).
2. If the primary provider fails (e.g., HTTP 429, invalid credentials, or network timeout), attempts Groq fallback if `GROQ_API_KEY` is present.
3. If Groq fails or is unconfigured, falls back to `MockLLMInterpreter`, injecting an uncertainty note: *"AI Contextual Interpretation is currently unavailable due to high server load."*
4. All structural fields (`morphology`, `literary_context`, `related_words`, `wsd_result`) are deterministically injected post-LLM to guarantee 100% structural reliability.

---

## REST API Reference

The primary API backend is a stateless Django REST service running at `http://localhost:8000`.

### Endpoints

#### 1. Health Check
- **Route:** `GET /api/health` *(alias: `GET /health`)*
- **Response (`200 OK`):**
  ```json
  {
    "status": "ok"
  }
  ```

#### 2. Linguistic Query
- **Route:** `POST /api/query` *(alias: `POST /query`)*
- **Headers:** `Content-Type: application/json`

**Request Payload:**
```json
{
  "query": "கால்",
  "provider": "mock",
  "context": "அவனுடைய தம்பி கால் கிலோ மாம்பழம் வாங்கி வந்தான்."
}
```

| Field | Type | Required | Description |
|---|---|:---:|---|
| `query` | string | **Yes** | Tamil word or phrase to look up. |
| `provider` | string | No | LLM provider: `"mock"` (default), `"gemini"`, or `"groq"`. |
| `context` | string | No | Surrounding sentence from webpage or user text for WSD. |

**Response Payload (`200 OK`):**
```json
{
  "query": "கால்",
  "normalized_query": "கால்",
  "lemma": "கால்",
  "meaning": "1. [பெயர்ச்சொல்] நான்கிலொரு பங்கு; fraction: one fourth. (Wiktionary)\n2. [பெயர்ச்சொல்] கால் (உறுப்பு); foot, leg. (Wiktionary)\n3. [பெயர்ச்சொல்] காற்று; wind. (Wiktionary)\n4. பாதம், முழங்கால் முதல் பாதம் வரையுள்ள உறுப்பு, மரக்கலத்தின் அடிப்பாகம், நீர் பாயும் வழி, நாலிலொரு பங்கு (Akarathi)",
  "english_meaning": null,
  "senses": [
    {
      "sense_number": 1,
      "title": "1. [பெயர்ச்சொல்] நான்கிலொரு பங்கு",
      "description": "fraction: one fourth. (Wiktionary)",
      "english_translation": null,
      "raw_text": "1. [பெயர்ச்சொல்] நான்கிலொரு பங்கு; fraction: one fourth. (Wiktionary)"
    },
    {
      "sense_number": 2,
      "title": "2. [பெயர்ச்சொல்] கால் (உறுப்பு)",
      "description": "foot, leg. (Wiktionary)",
      "english_translation": null,
      "raw_text": "2. [பெயர்ச்சொல்] கால் (உறுப்பு); foot, leg. (Wiktionary)"
    }
  ],
  "morphology": {
    "pos": "noun",
    "case": null,
    "number": "Singular",
    "tense": null,
    "analysis_type": "core",
    "fst_model": "noun.fst",
    "raw_morphology": "noun+sg",
    "segments": [
      {
        "tamil": "கால்",
        "latin": "",
        "role": "noun"
      }
    ]
  },
  "contextual_meaning": "நான்கில் ஒரு பங்கு — அவனுடைய தம்பி கால் கிலோ மாம்பழம் வாங்கி வந்தான். இங்கு 'கால் கிலோ' என்பது ஒரு கிலோவின் நான்கில் ஒரு பங்கு (¼ kg / 250g).",
  "contextual_interpretation": "In the user's context ('அவனுடைய தம்பி கால் கிலோ மாம்பழம் வாங்கி வந்தான்.'), the word reflects the specific sense: 'நான்கில் ஒரு பங்கு — ஒரு கிலோவின் நான்கில் ஒரு பங்கு (¼ kg / 250g)'.",
  "wsd_result": {
    "query": "கால்",
    "context": "அவனுடைய தம்பி கால் கிலோ மாம்பழம் வாங்கி வந்தான்.",
    "selected_candidate": {
      "source": "Tamil Wiktionary",
      "headword": "கால்",
      "definition": "நான்கிலொரு பங்கு; fraction: one fourth.",
      "english_meaning": null,
      "pos": "Noun",
      "raw_text": "நான்கிலொரு பங்கு; fraction: one fourth.",
      "metadata": {"status": "FOUND"},
      "sense_id": "tamil_wiktionary:கால்:0"
    },
    "selected_sense": "நான்கில் ஒரு பங்கு — இங்கு 'கால் கிலோ' என்பது ஒரு கிலோவின் நான்கில் ஒரு பங்கு (¼ kg / 250g).",
    "score": 35.0,
    "status": "selected",
    "confidence": "high",
    "reasons": [
      "adjacent_unit:கிலோ(dist=1)->fraction_sense(+35.0)",
      "exact:கிலோ(14.0)"
    ],
    "candidates": [
      {
        "candidate": {
          "source": "Tamil Wiktionary",
          "headword": "கால்",
          "definition": "நான்கிலொரு பங்கு; fraction: one fourth."
        },
        "score": 49.0,
        "reasons": ["adjacent_unit:கிலோ(dist=1)->fraction_sense(+35.0)"],
        "formatted_text": null
      }
    ]
  },
  "literary_context": [
    {
      "work": "குறுந்தொகை",
      "author": "கபிலர்",
      "period": "சங்க காலம்",
      "passage": "தினைத்தா ளன்ன சிறுபசுங் கால...",
      "verse_number": "42",
      "meaning": "சிறிய கால்களையுடைய கொக்கு...",
      "source": "Sentamizh",
      "matched_line": "தினைத்தா ளன்ன சிறுபசுங் கால",
      "snippet": "தினைத்தா ளன்ன சிறுபசுங் கால",
      "highlight_offsets": [{"start": 21, "end": 25}],
      "is_featured": true,
      "can_expand": true
    }
  ],
  "related_words": ["அடி", "பாதம்", "முழங்கால்", "காற்று"],
  "sources": [
    "ThamizhiMorph",
    "Tamil Wiktionary",
    "Thani Thamizh Akarathi",
    "Tamil WordNet",
    "Sentamizh",
    "Project Madurai"
  ],
  "uncertainties": [],
  "evidence_summary": {
    "total_found": 18,
    "morphology_count": 1,
    "lexical_count": 6,
    "raw_literary_count": 11,
    "selected_literary_count": 5,
    "related_count": 4
  }
}
```

---

## User Interfaces

### 1. Browser Extension (Manifest V3)
Located in [`extension/`](file:///c:/Vishwa/Projects/SOL_AI/extension/):
- **Right-Click Context Menu:** Highlight any Tamil word or phrase on any webpage $\rightarrow$ right-click $\rightarrow$ select **"Explain with SOL AI"**.
- **Automated Context Extraction:** Traversing the DOM tree to locate the enclosing sentence boundary (`[^.?!]+[.?!]*`), dispatching both `query` and `context` to `/api/query`.
- **Isolated Shadow DOM Overlay:** Injects a floating side panel inside an open Shadow DOM root to prevent host-page CSS stylesheet contamination.
- **Zero API Key Leakage:** The extension communicates exclusively with the local backend; LLM API keys remain strictly server-side.

### 2. Web Application (Next.js 16)
Located in [`frontend/`](file:///c:/Vishwa/Projects/SOL_AI/frontend/):
- **Tamil Typing Integration:** KeymanWeb integration for phonetic Tamil input in the search bar.
- **Component Architecture:**
  - `WordExplorer`: Main search exploration coordinator.
  - `WordHeader` & `QuickInfoCard`: Primary lemma, POS, and pronunciation overview.
  - `MeaningCard`: Discrete lexical senses and source provenance.
  - `MorphologyCard`: FST root and morpheme segment decomposition.
  - `UsageContextCard`: In-context WSD sense and contextual interpretation.
  - `LiteraryContextCard`: Classical Sangam/Madurai passages with keyword highlights.
  - `RelatedWordsCard`: Synsets and related concepts.
  - `EvidencePanel`: Complete transparent audit of contributing databases.
- **Dedicated Routes:**
  - `/`: Search landing and interactive explorer.
  - `/read`: Classical Tamil verse reading room.
  - `/sources`: Data source provenance and licensing audit.
  - `/about`: System architecture and scholarly design principles.

---

## Installation & Setup

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm
- *(Optional for FST parsing)* `foma` / `flookup` installed natively or via Windows Subsystem for Linux (WSL).

### 1. Backend Setup

```bash
# 1. Clone repository
git clone https://github.com/vishwavel05/SOL_AI.git
cd SOL_AI

# 2. Set up Python virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

Create a `.env` file in the repository root (see `.env.example`):

```env
# Server Configuration
DJANGO_SECRET_KEY=your-secure-secret-key
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=*
CORS_ALLOW_ALL=True

# LLM Provider Configuration ('mock', 'gemini', or 'groq')
SOL_LLM_PROVIDER=mock

# Google Gemini API (Required if SOL_LLM_PROVIDER=gemini)
GEMINI_API_KEY=your_gemini_api_key_here
SOL_GEMINI_MODEL=gemini-3.6-flash

# Groq API (Required if SOL_LLM_PROVIDER=groq or for fallback)
GROQ_API_KEY=your_groq_api_key_here
SOL_GROQ_MODEL=qwen/qwen3.8-27b
```

### 3. Start the Backend API

Run the Django development server:

```bash
python backend/sol_django/manage.py runserver 8000
```

Verify backend health:
```bash
curl http://localhost:8000/api/health
# Output: {"status": "ok"}
```

### 4. Start the Web Frontend

In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### 5. Load the Chrome Extension

1. Open Google Chrome or Microsoft Edge and navigate to `chrome://extensions/`.
2. Enable the **Developer mode** toggle in the top-right corner.
3. Click **Load unpacked**.
4. Select the [`extension/`](file:///c:/Vishwa/Projects/SOL_AI/extension/) directory.

---

## Testing & Verification

The repository maintains an automated test suite verifying endpoints, FST parsing, adapters, WSD logic, and semantic calibration:

```bash
# Run complete test suite (238 tests)
pytest tests/ -q
```

### Key Test Suites
- [`tests/test_wsd_overhaul.py`](file:///c:/Vishwa/Projects/SOL_AI/tests/test_wsd_overhaul.py): 14 unit and integration tests covering fractional, anatomical, structural contexts, abstention rules, and Django API requests.
- [`tests/test_semantic_calibration.py`](file:///c:/Vishwa/Projects/SOL_AI/tests/test_semantic_calibration.py): 15 tests verifying $K=25$, threshold $\tau=0.845$, exact preservation, and out-of-domain query suppression.
- [`tests/test_django_api.py`](file:///c:/Vishwa/Projects/SOL_AI/tests/test_django_api.py): 12 tests verifying endpoints, status codes, CORS headers, and error handling.
- [`tests/verify_django_parity.py`](file:///c:/Vishwa/Projects/SOL_AI/tests/verify_django_parity.py): Parity test harness comparing Django against legacy `server.py` across 74 assertions.

---

## Current Limitations & Technical Roadmap

In adherence to SOL AI's commitment to technical honesty:

1. **Tamil WordNet Definition Glosses:**
   In SOL AI's current data adapter, *Tamil WordNet* records provide synset graph hierarchies and lemma mappings, but `meaning=None` in the database. Consequently, WordNet does not contribute definition gloss candidates to WSD until gloss text is integrated into the underlying database.
2. **Akarathi Collapsed Definitions:**
   Raw entries in *Thani Thamizh Akarathi* occasionally group multiple distinct senses into a single semicolon-delimited string. While `extract_sense_candidates()` splits them where linguistic delimiters exist, some Akarathi sub-senses lack independent part-of-speech or English annotations.
3. **FOMA / flookup Dependency:**
   Full morphological decompounding relies on the external `flookup` binary (native Linux or WSL). When `flookup` is absent from the host environment, the engine gracefully falls back to WordNet morphtable mappings without crashing, but cannot analyze novel inflections.
4. **Sandhi-Merged Compounds:**
   Highly agglutinative compounds written without spaces (e.g., `கால்சட்டை` or `மேசைக்கால்`) rely on prior morphological segmentation before entering WSD.
5. **Domain Lexicon Scope:**
   The deterministic WSD domain dictionaries currently focus on Quantity/Measurement, Somatic/Anatomical, and Structural/Furniture vocabularies. Expanding these lexicons across additional semantic domains is planned for future milestones.
6. **Dense Embedding Geometric Cone:**
   Multilingual transformer models (`multilingual-e5-small`) map Tamil texts into a narrow directional cone in 384-dimensional space, yielding a baseline cosine similarity of ~0.80–0.83 between unrelated Tamil sentences. While our calibrated threshold ($\tau = 0.845$) suppresses 75% of out-of-domain queries while retaining 100% of gold matches, dense semantic retrieval is inherently noisier than deterministic FTS5 search and is treated strictly as an adjunct layer.
