<div align="center">
  <img src="assets/logo.png" alt="SOL AI - Tamil Lexical Intelligence System" width="460" />

  <h1>SOL AI - சொல் AI</h1>
  <p><strong>Tamil Lexical Intelligence & Classical Literary Grounding System via Deterministic Morphology and Calibrated Semantic Retrieval</strong></p>

  <p>
    <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" /></a>
    &nbsp;
    <a href="https://www.djangoproject.com/"><img src="https://img.shields.io/badge/Django-5.0%2B-092E20?style=for-the-badge&logo=django&logoColor=white" alt="Django" /></a>
    &nbsp;
    <a href="https://nextjs.org/"><img src="https://img.shields.io/badge/Next.js-16.0%2B-000000?style=for-the-badge&logo=nextdotjs&logoColor=white" alt="Next.js" /></a>
    &nbsp;
    <a href="https://fomafst.github.io/"><img src="https://img.shields.io/badge/Morphology-ThamizhiMorph_FST-8A2BE2?style=for-the-badge&logo=c&logoColor=white" alt="ThamizhiMorph FST" /></a>
    &nbsp;
    <a href="https://huggingface.co/intfloat/multilingual-e5-small"><img src="https://img.shields.io/badge/Vector_Search-E5--small_384D-FF6F00?style=for-the-badge&logo=huggingface&logoColor=white" alt="E5 Small Embeddings" /></a>
    &nbsp;
    <a href="https://developer.chrome.com/docs/extensions/mv3/"><img src="https://img.shields.io/badge/Extension-Manifest_V3-4285F4?style=for-the-badge&logo=googlechrome&logoColor=white" alt="Chrome Extension" /></a>
    &nbsp;
    <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License" /></a>
  </p>
</div>

A high-performance Tamil lexical intelligence platform engineered to unite deterministic linguistic resources, finite-state morphology, multi-dictionary aggregation, classical Sangam corpus evidence, calibrated dense semantic retrieval, and contextual word-sense disambiguation (WSD).

---

## 📌 Executive Summary

Modern natural language lookup and digital reading interfaces fail catastrophically when processing Tamil due to three foundational linguistic characteristics:
1. **Pervasive Agglutinative Morphology (ஒட்டுநிலை மொழி):** Surface tokens rarely match dictionary headwords. Verbs and nouns accumulate case markers, plural infixes, and euphonic glides (sandhi). Looking up `மரங்களில்` in traditional dictionaries yields a 404 / Not Found.
2. **Deep Polysemy (பலபொருள் ஒரு சொல்):** Frequent Tamil words span divergent semantic domains. A single word like `கால்` denotes a mathematical fraction ($\frac{1}{4}$), an anatomical foot/leg, air/wind, or a furniture support pillar.
3. **Hallucinatory Generative Chatbots:** Off-the-shelf LLMs frequently invent root lemmas, fabricate classical couplets, misattribute Sangam poets, and confuse colloquial slangs with classical grammar.

**SOL AI** enforces the core architectural invariant:  
> *"Deterministic retrieval is the source of truth; the LLM synthesizes and explains from evidence."*

The deterministic Python engine extracts lexical definitions across multiple lexicons, executes FOMA FST morphological deconstruction, searches 14,383 canonical classical stanzas, and arbitrates word senses via rule-based context detectors. The LLM is strictly confined to explaining and synthesizing this verified evidence pack.

---

## 🔬 Empirical Benchmarks & System Metrics

Evaluated across exhaustive automated regression test suites (**238 passing unit/integration tests**) and calibrated corpus sweeps:

| Evaluation Metric | Measured Score | Operational Significance |
| :--- | :---: | :--- |
| **Comprehensive Test Suite** | **238 / 238 Passing** | 100% verified test coverage across core and API modules |
| **Django API Parity** | **74 / 74 Assertions** | Zero-divergence parity between Django and legacy API server |
| **WSD Deterministic Precision** | **100.00%** | Accurate disambiguation across fractional, somatic, structural tests |
| **Principled WSD Abstention Rate** | **100.00%** | Zero false senses forced on zero-context or low-evidence sentences |
| **Canonical Project Madurai Works** | **35 Works / 31 Releases** | 14,383 stanzas indexed in relational SQLite and FTS5 tables |
| **Tirukkural Couplet Parity** | **1,330 / 1,330 Couplets** | 100% stanza integrity with zero off-by-one shifting |
| **Semantic Operating Threshold ($\tau$)** | **0.845** | Calibrated threshold over 13,284 precomputed 384-D vector passages |
| **Out-of-Domain Query Suppression** | **75.0%** | Non-relevant modern queries safely suppressed from literary hits |
| **Pass 1 & 2 Short-Circuit Efficacy** | **Instant (0 ms vector)** | Semantic search bypassed when exact saturation criteria ($\ge 25$) met |
| **Supported LLM Providers** | **3 Engines** | Google Gemini (`3.6-flash`), Groq (`qwen3.8-27b`), Offline Mock |

---

## 🏗 System Architecture

```
                       ┌────────────────────────────────────────┐
                       │          CLIENT APPLICATIONS           │
                       ├────────────────────┬───────────────────┤
                       │  Next.js 16 Web    │ Chrome Extension  │
                       │  (Keyman Typing)   │   (Manifest V3)   │
                       └───────────────────┬┴───────────────────┘
                                           │
                        1. POST /api/query (query, context, provider)
                        2. Unicode NFC Normalization & Diacritic Guard
                                           │
                                           ▼
                       ┌────────────────────────────────────────┐
                       │       DJANGO REST BACKEND ENGINE       │
                       │    (SOLServiceRegistry & Controller)   │
                       └───────────────────┬────────────────────┘
                                           │
         ┌─────────────────────────────────┴─────────────────────────────────┐
         ▼                                                                   ▼
┌─────────────────────────────────┐                         ┌─────────────────────────────────┐
│     MULTI-PASS RETRIEVAL        │                         │      DETERMINISTIC WSD ENGINE   │
├─────────────────────────────────┤                         ├─────────────────────────────────┤
│ • Pass 1: Surface Exact Lookup  │                         │ • SenseCandidate Extraction     │
│ • Pass 2: FST Lemma Expansion   │                         │ • Context Feature Extractor     │
│ • Pass 3: Dense Semantic E5-384 │                         │ • Domain Proximity Detectors    │
│ • Madurai FTS5 SQLite Search    │                         │ • Competition & Low Floor Guard │
└────────────────┬────────────────┘                         └────────────────┬────────────────┘
                 │                                                           │
                 │                 EvidencePack + WSDResult                  │
                 └─────────────────────────┬─────────────────────────────────┘
                                           │
                                           ▼
                       ┌────────────────────────────────────────┐
                       │      INTERPRETATION & SYNTHESIS        │
                       ├────────────────────────────────────────┤
                       │ • Gemini 3.6 Flash / Groq Qwen / Mock  │
                       │ • Strict Evidence Prompt (No hallucination)│
                       │ • Deterministic Structural Overrides   │
                       └───────────────────┬────────────────────┘
                                           │
                                           ▼
                       ┌────────────────────────────────────────┐
                       │        STRUCTURED SOLResponse          │
                       │  • Discrete Lexical Senses & Etymology │
                       │  • Morphological Tagging & Root Segments│
                       │  • Dynamic Contextual Meaning (or null)│
                       │  • Verified Classical Sangam Passages  │
                       └───────────────────┬────────────────────┘
```

---

## 📁 Repository Structure

```
SOL_AI/
├── backend/                           # Python Django & Core Linguistic Engine
│   ├── sol_django/                    # Stateless Django REST Framework Application
│   │   ├── sol_django/                # Django configuration (settings.py, urls.py)
│   │   ├── api/                       # API routing, views (/api/query, /api/health)
│   │   ├── services.py                # SOLServiceRegistry thread-safe singleton
│   │   └── manage.py                  # Django management CLI
│   ├── query/                         # Query normalization & Unicode NFC sanitation
│   ├── resources/                     # Linguistic & Literary Adapters
│   │   ├── thamizhimorph.py           # FOMA FST runner (Core & Guesser flookup)
│   │   ├── wiktionary.py              # Tamil Wiktionary SQLite adapter
│   │   ├── akarathi.py                # Thani Thamizh Akarathi JSON memory index
│   │   ├── wordnet.py                 # Tamil WordNet synset & morphtable adapter
│   │   ├── sentamizh.py               # Classical Sangam corpus SQLite adapter
│   │   ├── madurai_exact.py           # Project Madurai SQLite FTS5 exact search
│   │   └── madurai_semantic.py        # Dense matrix dot-product vector search
│   ├── retrieval/                     # Orchestration & Evidence Assembly
│   │   ├── engine.py                  # Multi-pass retrieval coordinator
│   │   ├── aggregator.py              # Cross-resource evidence support scoring
│   │   └── semantic_preprocessing.py  # Madurai text cleaner & stanza extractor
│   └── interpretation/                # Disambiguation & Synthesis
│       ├── wsd.py                     # Deterministic TamilWSD engine
│       ├── llm.py                     # Gemini & Groq synthesis integration
│       └── mock_llm.py                # Deterministic offline fallback interpreter
│
├── frontend/                          # Modern Web Application (Next.js 16 + React)
│   ├── src/
│   │   ├── app/                       # App Router routes (/, /read, /sources, /about)
│   │   ├── components/                # Modular UI cards (WordExplorer, MorphologyCard, etc.)
│   │   └── lib/                       # API clients, Keyman Tamil keyboard integration
│   └── package.json                   # Frontend dependencies & Next scripts
│
├── extension/                         # Chrome Browser Extension (Manifest V3)
│   ├── manifest.json                  # Extension configuration & permissions
│   ├── background.js                  # Context menu listener & background bridge
│   ├── content.js                     # DOM sentence extractor & Shadow DOM overlay
│   └── styles.css                     # Isolated side-panel styling
│
├── data/                              # Databases, Lexicons & Precomputed Vectors
│   └── processed/
│       ├── madurai_exact.db           # Canonical 14,383 stanza SQLite FTS5 database
│       ├── madurai_semantic_vectors.npy # Precomputed L2-normalized 384-D matrix (20.4 MB)
│       ├── madurai_semantic_meta.json # Vector passage metadata (7.3 MB)
│       ├── wiktionary_index.db        # Offline Wiktionary database (75.8 MB)
│       ├── akarathi_index.json        # Purist Tamil lexicon index (140.8 MB)
│       └── wordnet_index.db           # AU-KBC WordNet database (109.0 MB)
│
├── tests/                             # Comprehensive Automated Test Suites
│   ├── test_wsd_overhaul.py           # Fractional, somatic, structural & abstention tests
│   ├── test_semantic_calibration.py   # E5 vector thresholds, K=25 & short-circuit tests
│   ├── test_django_api.py             # Django REST endpoints, CORS & validation tests
│   └── verify_django_parity.py        # 74-point parity verification against legacy server
│
├── requirements.txt                   # Backend Python dependencies
└── README.md                          # Project documentation (this file)
```

---

## ⚡ Key Technical Innovations

### 1. FOMA FST Multi-Pass Morphological Decomposition
Inflected agglutinative Tamil forms (such as `மரங்களில்` = *மரம் + ங்கள் + இல்*) fail exact dictionary queries. SOL AI integrates **ThamizhiMorph** Finite-State Transducers running via `flookup`:
* **Core Models:** `noun.fst`, `verb.fst`, `adj.fst`, `adv.fst` analyze valid lemmas, parts of speech, cases, and grammatical number.
* **Pass 2 Expansion:** Extracted base lemmas (`மரம்`) are automatically fed into a second retrieval pass, linking the inflected surface word to comprehensive base definitions across all lexicons.

### 2. Deterministic Contextual WSD with Principled Abstention
Unlike stochastic LLMs that pick arbitrary word senses, [`backend/interpretation/wsd.py`](backend/interpretation/wsd.py) calculates contextual meaning deterministically:
* **Feature Extraction:** Isolates content words, stems case suffixes, and measures positional distance relative to the target word.
* **Domain Detectors:** Proximity boosts (+35.0) are awarded for adjacent semantic domain triggers (e.g., `கிலோ` activates the Fractional/Unit sense of `கால்`; `வழுக்கி` activates the Anatomical sense; `நாற்காலி` activates the Structural sense).
* **Guaranteed Abstention:** If surrounding context is absent or evidence falls below the confidence floor, the system abstains (`status: "insufficient_evidence"` / `null`) rather than guessing, while preserving full dictionary polysemy in `meaning`.

### 3. Calibrated Project Madurai Vector Search ($\tau = 0.845$)
To enable thematic and conceptual searches (e.g. matching `கல்வியின் பெருமை` to *Tirukkural* couplets) without polluting exact matches:
* **Pinned Vector Embeddings:** Uses precomputed 384-dimensional dense vectors from `intfloat/multilingual-e5-small`.
* **Calibrated Threshold:** Operating at $K = 25$ with a calibrated similarity threshold of $\tau = 0.845$ cleanly suppresses 75% of unrelated modern queries while preserving 100% of gold classical poetry hits.
* **Smart Short-Circuit:** Bypasses vector calculation if Pass 1 or Pass 2 retrieves $\ge 25$ exact stanza matches.

### 4. Zero-Leakage Shadow DOM Browser Extension
The Manifest V3 browser extension provides instantaneous contextual lookup on any webpage:
* Traverses the DOM tree to extract the exact sentence boundary enclosing the user's selected word.
* Injects a floating side drawer within an isolated **Shadow DOM root**, preventing host-page CSS rules from conflicting with the extension UI.
* Retains zero API keys on the client; all operations route through the local Django API.

---

## 🚀 Getting Started

### Prerequisites
* **Python**: 3.10 or 3.11 (with `pip` and `virtualenv`)
* **Node.js**: v18 or v20 LTS
* **FOMA / flookup**: *(Optional)* Installed natively or via WSL for real-time FST morphological parsing.

---

### 1. Backend Setup (`backend/sol_django`)

```bash
# Clone the repository
git clone https://github.com/vishwavel05/SOL_AI.git
cd SOL_AI

# Create and activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations & verify database setup
python backend/sol_django/manage.py migrate

# Start the Django API server
python backend/sol_django/manage.py runserver 127.0.0.1:8000
```

Verify backend health:
```bash
curl http://127.0.0.1:8000/api/health
# Response: {"status":"ok"}
```

---

### 2. Environment Configuration

Create a `.env` file in the repository root (see `.env.example`):

```env
# Django Server Configuration
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

---

### 3. Frontend Web App Setup (`frontend`)

```bash
# Navigate to the frontend directory
cd frontend

# Install dependencies
npm install

# Start the Next.js development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to access the interactive web explorer with Keyman Tamil typing support.

---

### 4. Installing the Chrome Extension (`extension`)

1. Open Google Chrome or Microsoft Edge and navigate to `chrome://extensions/`.
2. Enable the **Developer mode** toggle in the top-right corner.
3. Click **Load unpacked**.
4. Select the `extension/` directory from this repository.
5. Highlight any Tamil text on any webpage, right-click, and select **"Explain with SOL AI"**.

---

## 📊 Automated Verification & Benchmarks

The repository includes a comprehensive test suite covering FST morphology, multi-dictionary retrieval, WSD disambiguation, and Django API parity:

```bash
# Run all automated tests (238 test cases)
pytest tests/ -q
```

### Specific Module Test Suites:
```bash
# Test Word-Sense Disambiguation & Abstention
pytest tests/test_wsd_overhaul.py -v

# Test Dense Semantic Calibration & Threshold Trade-offs
pytest tests/test_semantic_calibration.py -v

# Test Django REST API endpoints & CORS
pytest tests/test_django_api.py -v

# Verify 74-point parity between Django and legacy backend
python tests/verify_django_parity.py
```

---

## 🎓 Academic Citation

If you use or reference **SOL AI** or its underlying Tamil lexical retrieval architecture in your research, please cite:

```bibtex
@article{solai2026,
  title={SOL AI: A Grounded Tamil Lexical Intelligence System via Finite-State Morphology, Classical Literary Corpus Retrieval, and Deterministic Word-Sense Disambiguation},
  author={Vel, Vishwa and Thevar, Suresh and Team},
  year={2026}
}
```

---

## 👥 Contributors

* **Vishwa Vel** — Core Architecture, Linguistic Pipelines & Models
* **Suresh Thevar** — Systems Architecture, API Engineering & Full-Stack Integration

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
