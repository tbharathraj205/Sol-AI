# SOL AI (சொல் AI) — Complete Setup, Configuration & Script Execution Guide (`Command.md`)

Welcome to the **SOL AI** complete operational manual. This guide is written so that **anyone—even without a technical background and on a brand-new computer—can set up, configure, and run every part of SOL AI from scratch**.

---

## 📋 Table of Contents

1. [Before You Begin: Installing Required Software](#1-before-you-begin-installing-required-software)
2. [Step 1: Cloning the Project Repository](#2-step-1-cloning-the-project-repository)
3. [Step 2: Setting Up the Python Environment & Installing Requirements](#3-step-2-setting-up-the-python-environment--installing-requirements)
4. [Step 3: Setting Up the Databases & Linguistic Corpora (`data/`)](#4-step-3-setting-up-the-databases--linguistic-corpora-data)
5. [Step 4: Adding API Keys & Configuring `.env`](#5-step-4-adding-api-keys--configuring-env)
6. [Step 5: Running the Backend Server (Django REST API)](#6-step-5-running-the-backend-server-django-rest-api)
7. [Step 6: Setting Up & Running the Frontend Web App (Next.js)](#7-step-6-setting-up--running-the-frontend-web-app-nextjs)
8. [Step 7: Installing & Using the Browser Extension (Chrome / Edge)](#8-step-7-installing--using-the-browser-extension-chrome--edge)
9. [Step 8: Detailed Guide to Running Every Script in the Project](#9-step-8-detailed-guide-to-running-every-script-in-the-project)
   - [8A. Interactive CLI Query & Interpretation Scripts](#8a-interactive-cli-query--interpretation-scripts)
   - [8B. Individual Resource Adapter CLI Tools](#8b-individual-resource-adapter-cli-tools)
   - [8C. Database & Vector Index Build Scripts](#8c-database--vector-index-build-scripts)
   - [8D. Benchmark, Calibration & Evaluation Scripts](#8d-benchmark-calibration--evaluation-scripts)
   - [8E. Database Inspection & Diagnostic Scripts](#8e-database-inspection--diagnostic-scripts)
   - [8F. Automated Testing Suites (Python & JavaScript)](#8f-automated-testing-suites-python--javascript)
10. [Step 9: Daily Quick-Start Cheat Sheet (TL;DR)](#10-step-9-daily-quick-start-cheat-sheet-tldr)
11. [Step 10: Troubleshooting Common Issues](#11-step-10-troubleshooting-common-issues)

---

## 1. Before You Begin: Installing Required Software

If you are setting up a brand-new computer, install these **four free programs** first:

### 1.1 Git (To download the code)
* **Download:** [https://git-scm.com/downloads](https://git-scm.com/downloads)
* Run the installer and click **Next** on all default options.
* **Verify installation:** Open **PowerShell** (Windows) or **Terminal** (Mac/Linux) and run:
  ```bash
  git --version
  ```

### 1.2 Python (Version 3.10, 3.11, or 3.12)
* **Download:** [https://www.python.org/downloads/](https://www.python.org/downloads/)
* ⚠️ **CRITICAL FOR WINDOWS USERS:** On the very first screen of the Python installer, **check the box at the bottom that says `"Add python.exe to PATH"`** before clicking "Install Now".
* **Verify installation:**
  ```bash
  python --version
  pip --version
  ```

### 1.3 Node.js (Version 18 LTS or 20+ LTS — for the Web App)
* **Download:** [https://nodejs.org/](https://nodejs.org/) (Choose the **LTS** button).
* Run the installer with default settings.
* **Verify installation:**
  ```bash
  node --version
  npm --version
  ```

### 1.4 Google Chrome or Microsoft Edge (For the Browser Extension)
* **Download:** [https://www.google.com/chrome/](https://www.google.com/chrome/)

### 1.5 *(Optional)* FOMA Finite-State Morphology Binary (`flookup`)
* `ThamizhiMorph` uses the `flookup` command-line tool to run real-time morphological decomposition on `.fst` files.
* **If you do not install `flookup`:** SOL AI will still work! It will automatically fall back to Tamil WordNet's 434,849-entry morphological root table and dictionary headwords without crashing.
* **To install `flookup`:**
  * **Windows (via WSL / Ubuntu):**
    ```bash
    wsl --install
    wsl sudo apt-get update
    wsl sudo apt-get install -y foma
    ```
  * **Linux (Ubuntu/Debian):**
    ```bash
    sudo apt-get update && sudo apt-get install -y foma
    ```
  * **macOS (Homebrew):**
    ```bash
    brew install foma
    ```

---

## 2. Step 1: Cloning the Project Repository

Open your terminal (**PowerShell** on Windows, or **Terminal** on macOS/Linux), navigate to the folder where you want to store the project, and run:

```bash
# 1. Clone the repository from GitHub
git clone https://github.com/vishwavel05/SOL_AI.git

# 2. Enter the project folder
cd SOL_AI
```

> **Note:** Every command in this guide assumes your terminal is inside this root `SOL_AI` folder unless stated otherwise.

---

## 3. Step 2: Setting Up the Python Environment & Installing Requirements

A **Python Virtual Environment (`venv`)** keeps all of SOL AI's Python packages neatly isolated in one folder so they don't interfere with anything else on your computer.

### 3.1 Create the Virtual Environment
Run this inside the `SOL_AI` folder:

```bash
python -m venv venv
```

### 3.2 Activate the Virtual Environment
Choose the command that matches your operating system:

* **Windows (PowerShell):**
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```
  *(💡 **Troubleshooting PowerShell:** If you see a red error saying `"running scripts is disabled on this system"`, run this command once and then try activating again:)*
  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```

* **Windows (Command Prompt / CMD):**
  ```cmd
  venv\Scripts\activate.bat
  ```

* **macOS / Linux:**
  ```bash
  source venv/bin/activate
  ```

*(When activated, you will see `(venv)` appear at the very beginning of your terminal prompt!)*

### 3.3 Install All Python Requirements

First, upgrade `pip` to avoid any package installation issues:
```bash
python -m pip install --upgrade pip
```

Next, install the core web & API dependencies from `requirements.txt`:
```bash
pip install -r requirements.txt
```
*(This installs `django`, `django-cors-headers`, `pydantic`, `python-dotenv`, `requests`, and `pytest`.)*

Next, install the **Machine Learning & Semantic Vector Search dependencies** required by Project Madurai's dense semantic retrieval engine (`intfloat/multilingual-e5-small`) and the offline translator:
```bash
pip install numpy torch transformers sentencepiece
```

#### One-Line Full Install Command (Core + Semantic ML)
If you want to install every required Python library in one single command, run:
```bash
pip install -r requirements.txt numpy torch transformers sentencepiece
```

---

## 4. Step 3: Setting Up the Databases & Linguistic Corpora (`data/`)

Because processed SQLite databases and raw literary dumps are several hundred megabytes in size, `data/raw/` and `data/processed/` are listed in `.gitignore` and are **not** downloaded automatically by `git clone`.

You have **two ways** to set up the `data/` folder on a new machine:

### Option A: Copy the Pre-Built `data/` Folder (Fastest — Recommended)
If you have access to the pre-built `data/` archive (via Google Drive, USB, or project release zip), place the files into `SOL_AI/data/processed/` so that your directory contains these 7 files:

| File Path in `SOL_AI/` | Approx. Size | Purpose |
| :--- | :---: | :--- |
| `data/processed/akarathi_index.json` | ~140.8 MB | Thani Thamizh Akarathi JSON dictionary index |
| `data/processed/wordnet_index.db` | ~109.0 MB | Tamil WordNet SQLite index (synsets, senses, 434k morph roots) |
| `data/processed/wiktionary_index.db` | ~75.8 MB | Offline Tamil Wiktionary SQLite definitions database |
| `data/processed/sentamizh_index.db` | ~65.9 MB | Sentamizh classical Sangam & Bhakti 10,393-verse SQLite DB |
| `data/processed/madurai_exact.db` | ~25.7 MB | Project Madurai 35-work (14,383 stanzas) SQLite FTS5 DB |
| `data/processed/madurai_semantic_vectors.npy` | ~20.4 MB | Precomputed 384-D E5-small vector matrix (13,284 stanzas) |
| `data/processed/madurai_semantic_meta.json` | ~7.3 MB | Passage metadata aligned with `madurai_semantic_vectors.npy` |

Also ensure `data/raw/thamizhimorph/FST-Models/` is present if you are using `flookup`.

---

### Option B: Download Raw Sources & Build All Databases from Scratch
If you only cloned the GitHub code and want to download the raw open-source corpora and build every database from scratch on your computer, run these commands in order from the `SOL_AI` root folder:

```bash
# 1. Clone ThamizhiMorph FST models into data/raw/thamizhimorph
git clone https://github.com/sarves/thamizhi-morph.git data/raw/thamizhimorph

# 2. Clone Thani Thamizh Akarathi raw dictionaries into data/raw/thani_thamizh_akarathi/agarathi
git clone https://github.com/ThaniThamizhAkarathiKalanjiyam/agarathi.git data/raw/thani_thamizh_akarathi/agarathi

# 3. Clone Sentamizh Classical Corpus into data/raw/sentamizh
git clone https://github.com/indic-corpora/sentamizh-corpus.git data/raw/sentamizh

# 4. Build Thani Thamizh Akarathi JSON Index (-> data/processed/akarathi_index.json)
python scripts/build_akarathi_index.py

# 5. Build Sentamizh SQLite Index (-> data/processed/sentamizh_index.db)
python scripts/build_sentamizh_index.py

# 6. Auto-Download & Build Tamil Wiktionary SQLite Index (-> data/processed/wiktionary_index.db)
#    (Automatically downloads ~39 MB dump from dumps.wikimedia.org)
python scripts/build_wiktionary_index.py

# 7. Build Tamil WordNet SQLite Index (-> data/processed/wordnet_index.db)
#    (Requires TamilWordnet.tgz placed at data/raw/tamil_wordnet/TamilWordnet.tgz)
python scripts/build_wordnet_index.py

# 8. Auto-Download & Build Project Madurai FTS5 Database (-> data/processed/madurai_exact.db)
#    (Requires data/raw/project_madurai/manifest.json; fetches 35 works from projectmadurai.org)
python scripts/build_madurai_index.py

# 9. Build Project Madurai 384-D Semantic Vectors (-> madurai_semantic_vectors.npy & meta.json)
#    (Downloads intfloat/multilingual-e5-small from Hugging Face and encodes 13,284 stanzas)
python scripts/build_madurai_semantic_vectors.py
```

---

## 5. Step 4: Adding API Keys & Configuring `.env`

### Where Do API Keys Go?
All API keys live in **one single file**:
```text
SOL_AI/.env
```
*(Directly inside the main `SOL_AI` project folder, right next to `README.md` and `requirements.txt`.)*

> 🔒 **Security Guarantee:** Neither the Next.js Frontend (`frontend/`) nor the Browser Extension (`extension/`) ever stores or sees your API keys. Only the Python backend reads `SOL_AI/.env`.

### 5.1 Create Your `.env` File
Copy the template file `.env.example` to `.env`:

* **Windows (PowerShell or CMD):**
  ```powershell
  copy .env.example .env
  ```
* **macOS / Linux:**
  ```bash
  cp .env.example .env
  ```

### 5.2 How to Get Your API Keys (Free)

SOL AI supports **three LLM interpretation modes**:
1. **`mock` (Offline Mode — Default):** Uses a deterministic rule-based synthesis engine. **Requires ZERO API keys** and works 100% offline.
2. **`gemini` (Google Gemini Mode):** Uses Google's Gemini model to synthesize contextual explanations from retrieved evidence.
3. **`groq` (Groq Mode / Automatic Fallback):** Uses Groq's ultra-fast inference API (`qwen/qwen3.8-27b`) as either the primary interpreter or automatic backup if Gemini is rate-limited.

#### Where to get a Google Gemini API Key:
1. Go to **Google AI Studio**: [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account.
3. Click **"Create API key"** and copy the key string (it starts with `AIza...`).

#### Where to get a Groq API Key (Optional):
1. Go to **Groq Cloud Console**: [https://console.groq.com/keys](https://console.groq.com/keys)
2. Sign in and click **"Create API Key"**.
3. Copy the key string (it starts with `gsk_...`).

### 5.3 Edit `SOL_AI/.env`
Open `SOL_AI/.env` in Notepad, VS Code, or any text editor, and paste the following configuration (replace the placeholder keys with your own):

```env
# ============================================================================
# 1. DJANGO SERVER CONFIGURATION
# ============================================================================
DJANGO_SECRET_KEY=django-insecure-sol-ai-dev-secret-key
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=*
CORS_ALLOW_ALL=True

# ============================================================================
# 2. LLM PROVIDER SELECTION
# Options:
#   mock   -> 100% Offline deterministic interpreter (No API key needed!)
#   gemini -> Google Gemini API
#   groq   -> Groq Cloud API
# ============================================================================
SOL_LLM_PROVIDER=gemini

# ============================================================================
# 3. GOOGLE GEMINI CONFIGURATION (Required if SOL_LLM_PROVIDER=gemini)
# ============================================================================
GEMINI_API_KEY=PASTE_YOUR_GEMINI_API_KEY_HERE
SOL_GEMINI_MODEL=gemini-2.5-flash

# ============================================================================
# 4. GROQ API CONFIGURATION (Required if SOL_LLM_PROVIDER=groq, or as fallback)
# ============================================================================
GROQ_API_KEY=PASTE_YOUR_GROQ_API_KEY_HERE
SOL_GROQ_MODEL=qwen/qwen3.8-27b
```

> 💡 **Tip:** If you don't want to set up any API keys right now, simply set `SOL_LLM_PROVIDER=mock` in `.env` and save the file! Everything—including the Web App, Browser Extension, WSD engine, morphology, and classical literary search—will work immediately.

---

## 6. Step 5: Running the Backend Server (Django REST API)

The backend server is the brain of SOL AI. **Both the Web App and the Browser Extension require the backend server to be running.**

Make sure your terminal is in the `SOL_AI` root directory and your `(venv)` virtual environment is activated:

### 6.1 Verify Django Configuration (Optional Sanity Check)
```bash
python backend/sol_django/manage.py check
```
*(Expected output: `System check identified no issues (0 silenced).` Note: SOL AI uses a stateless REST architecture with custom SQLite adapters, so you do **not** need to run `manage.py migrate`.)*

### 6.2 Start the Django Backend Server
```bash
python backend/sol_django/manage.py runserver 127.0.0.1:8000
```
*(Leave this terminal window open and running!)*

### 6.3 Verify the Backend is Working
Open your web browser and visit:
* [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

Or run this in a second terminal window:
* **macOS / Linux / Git Bash:**
  ```bash
  curl http://127.0.0.1:8000/api/health
  ```
* **Windows PowerShell:**
  ```powershell
  Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health"
  ```
You should see:
```json
{"status": "ok"}
```

---

## 7. Step 6: Setting Up & Running the Frontend Web App (Next.js)

The SOL AI Web Application (`frontend/`) provides a rich visual interface with a built-in Tamil phonetic keyboard (Keyman), Word Explorer, Morphology Breakdown, Etymology, and Classical Literature cards.

### 7.1 Open a Second Terminal Window
**Keep your Backend terminal running**, and open a **new** terminal window in the `SOL_AI` folder.

### 7.2 Navigate to `frontend/` and Install Node Packages
```bash
# 1. Enter the frontend directory
cd frontend

# 2. Install all JavaScript / React / Next.js dependencies
npm install
```
*(You only need to run `npm install` the first time you set up the project.)*

### 7.3 *(Optional)* Custom Backend URL for Frontend
By default, the frontend automatically connects to `http://localhost:8000` (configured in `frontend/lib/api.js`). If you ever run the backend on a different port or server, create a file named `frontend/.env.local` and add:
```env
NEXT_PUBLIC_SOL_API_BASE_URL=http://localhost:8000
```

### 7.4 Start the Next.js Web App
```bash
npm run dev
```

Once it says `Ready`, open your browser and go to:
👉 **[http://localhost:3000](http://localhost:3000)**

### Other Frontend Commands (`frontend/package.json`)
| Command (run inside `frontend/`) | What It Does |
| :--- | :--- |
| `npm run dev` | Starts the Next.js development server at `http://localhost:3000` with hot-reloading. |
| `npm run build` | Compiles an optimized production build of the web application. |
| `npm run start` | Runs the compiled production server (must run `npm run build` first). |
| `npm run lint` | Runs ESLint to check all React/Next.js frontend files for code quality issues. |

---

## 8. Step 7: Installing & Using the Browser Extension (Chrome / Edge)

The **SOL AI Browser Extension** (`extension/`) lets you highlight any Tamil word on any website (Wikipedia, news sites, blogs, Project Madurai, etc.) and see its root lemma, morphology, contextual meaning, and Sangam literature verses in a floating side panel.

### 8.1 How to Install the Extension (Step-by-Step)

1. Make sure your **Backend Server** (`python backend/sol_django/manage.py runserver 127.0.0.1:8000`) is running.
2. Open **Google Chrome** (or **Microsoft Edge**).
3. In the address bar at the top, type the following and press **Enter**:
   * On Chrome: `chrome://extensions/`
   * On Edge: `edge://extensions/`
4. Look at the **top-right corner** (or left sidebar on Edge) and turn **ON** the switch labeled **"Developer mode"**.
5. New buttons will appear at the top-left. Click the button labeled **"Load unpacked"**.
6. A file browser window will pop up. Navigate to where you cloned `SOL_AI`, click on the **`extension`** folder (`SOL_AI/extension`), and click **Select Folder**.
7. 🎉 **Done!** You will now see **"SOL AI — Tamil Etymological Assistant"** in your extensions list.
8. *(Recommended)* Click the **Puzzle Piece icon (🧩)** in the top-right toolbar of Chrome and click the **Pin icon (📌)** next to **SOL AI** so its icon stays visible in your browser toolbar.

### 8.2 How to Use the Extension

#### Method 1: Right-Click Any Tamil Word on Any Webpage (Contextual Mode)
1. Open any Tamil webpage—or open the built-in test page located at `SOL_AI/extension/test-page.html` by dragging and dropping `test-page.html` into a Chrome tab.
2. **Highlight (select)** any Tamil word (for example: `மரங்களில்`, `கால்`, `யாழ்`, `அகதி`, `வந்தார்கள்`).
3. **Right-click** the highlighted word and click **"Explain with SOL AI"** from the menu.
4. A floating **SOL AI Side Panel** will slide out on the right side of the page showing:
   * The exact **Contextual Meaning** in that sentence (powered by the deterministic Tamil WSD engine)
   * **Root Lemma & Dictionary Senses**
   * **Morphological Breakdown** (Part of Speech, Case, Number, Tense, Core vs. Guesser FST model)
   * **Classical Literary Context** (Sangam poetry & Tirukkural stanzas with highlighted matches)
   * **Related Words** & **Source Provenance**

#### Method 2: Manual Lookup via the Toolbar Popup
1. Click the **SOL AI icon** in your browser toolbar.
2. Type or paste any Tamil word into the search box.
3. Press **Enter** or click **Analyze**.

#### Method 3: Changing the Backend URL in the Extension
* By default, the extension connects to `http://127.0.0.1:8000`.
* To change this: Click the **SOL AI icon** in your browser toolbar → Click the **Gear icon (⚙)** in the top-right of the popup → Enter your backend URL → Click **Save**.

---

## 9. Step 8: Detailed Guide to Running Every Script in the Project

Every command below should be run from the **root `SOL_AI/` directory** with your Python virtual environment `(venv)` activated.

---

### 8A. Interactive CLI Query & Interpretation Scripts

#### 1. `scripts/query_sol.py` — Unified Multi-Resource Retrieval CLI
Runs Pass 1 (Surface Lookup), Pass 2 (FST & WordNet Lemma Expansion), and Pass 3 (Dense Semantic Retrieval) across all 6 linguistic adapters and prints a formatted terminal report showing hits per resource and cross-resource lemma agreement.
* **Command:**
  ```bash
  python scripts/query_sol.py "<tamil_word>"
  ```
* **Examples:**
  ```bash
  python scripts/query_sol.py "மரங்களில்"
  python scripts/query_sol.py "யாழ்"
  python scripts/query_sol.py "அகதி"
  ```

#### 2. `scripts/interpret_query.py` — Full Pipeline + LLM Interpretation CLI
Runs the complete SOL AI pipeline from the terminal: deterministic retrieval $\rightarrow$ `EvidencePack` construction $\rightarrow$ LLM/Mock interpretation $\rightarrow$ structured `SOLResponse` output.
* **Command & Options:**
  ```bash
  python scripts/interpret_query.py "<tamil_word>" [--provider mock|gemini|groq] [--debug] [--max-contexts 5]
  ```
* **Arguments:**
  * `"<tamil_word>"`: *(Required)* The Tamil word or phrase to analyze.
  * `--provider`: *(Optional)* Choose `mock` (offline), `gemini`, or `groq`. Defaults to `SOL_LLM_PROVIDER` in `.env` (or `mock`).
  * `--debug`: *(Optional)* Prints the raw `EvidencePack` counts, lemma candidates, and conflicts before printing the final response.
  * `--max-contexts`: *(Optional)* Maximum number of classical literary passages to include (default: `5`).
* **Examples:**
  ```bash
  # Run offline with Mock interpreter
  python scripts/interpret_query.py "மரங்களில்" --provider mock

  # Run live with Google Gemini and print debug EvidencePack
  python scripts/interpret_query.py "மரங்களில்" --provider gemini --debug

  # Run live with Groq
  python scripts/interpret_query.py "கல்வி" --provider groq --max-contexts 3
  ```

#### 3. `test_api.py` — Quick Live API Query Script
Sends a `POST /api/query` request to a running local backend (`http://localhost:8000/api/query`) and saves the full JSON response into `test_output.json`.
* **Prerequisite:** The backend server must be running on port `8000`.
* **Command:**
  ```bash
  python test_api.py "<tamil_word>"
  ```
* **Example:**
  ```bash
  python test_api.py "மரங்களில்"
  ```

#### 4. `backend/api/server.py` — Legacy Standalone HTTP Server *(Deprecated Fallback)*
Starts the original lightweight Python `ThreadingHTTPServer` backend (retained for backwards compatibility and parity testing against Django).
* **Command:**
  ```bash
  python backend/api/server.py --host 127.0.0.1 --port 8000
  ```

---

### 8B. Individual Resource Adapter CLI Tools

Each linguistic adapter in `backend/resources/` can be executed directly as a Python module (`python -m`) to test that specific dictionary or corpus in isolation:

#### 5. `backend.resources.thamizhimorph` — FOMA FST Morphological Analyzer CLI
Tests morphological decomposition (`noun.fst`, `verb-*.fst`, and guesser models) for an inflected Tamil word.
* **Command:**
  ```bash
  python -m backend.resources.thamizhimorph "<tamil_word>"
  ```
* **Example:**
  ```bash
  python -m backend.resources.thamizhimorph "வந்தார்கள்"
  python -m backend.resources.thamizhimorph "மரங்களில்"
  ```

#### 6. `backend.resources.akarathi` — Thani Thamizh Akarathi CLI
Looks up pure-Tamil equivalents and definitions across Devaneya Pavanar's dictionary, Neelambigai Ammaiyar's Sanskrit-to-Tamil dictionary, and the Isaiyini dictionary.
* **Command:**
  ```bash
  python -m backend.resources.akarathi "<tamil_word>"
  ```
* **Example:**
  ```bash
  python -m backend.resources.akarathi "அகதி"
  ```

#### 7. `backend.resources.wordnet` — Tamil WordNet CLI
Queries `data/processed/wordnet_index.db` for synset nodes, POS tags, hypernyms, morphological roots (`morphtable`), and corpus frequency.
* **Command:**
  ```bash
  python -m backend.resources.wordnet "<tamil_word>"
  ```
* **Example:**
  ```bash
  python -m backend.resources.wordnet "மரம்"
  ```

#### 8. `backend.resources.wiktionary` — Tamil Wiktionary CLI
Queries `data/processed/wiktionary_index.db` for crowd-sourced Tamil Wiktionary definitions and multiple word senses.
* **Command:**
  ```bash
  python -m backend.resources.wiktionary "<tamil_word>"
  ```
* **Example:**
  ```bash
  python -m backend.resources.wiktionary "கால்"
  ```

#### 9. `backend.resources.sentamizh` — Sentamizh Classical Literary Corpus CLI
Queries `data/processed/sentamizh_index.db` across 10,393 annotated verses from 9 classical Sangam, Epic, and Bhakti works (*Kuruntokai*, *Natrinai*, *Purananuru*, *Akananuru*, *Manimekalai*, *Silappatikaram*, *Thevaram*, *Divya Prabandham*, *Thirumanthiram*).
* **Command:**
  ```bash
  python -m backend.resources.sentamizh "<tamil_word>"
  ```
* **Example:**
  ```bash
  python -m backend.resources.sentamizh "யாழ்"
  ```

---

### 8C. Database & Vector Index Build Scripts

These scripts parse raw linguistic files in `data/raw/` and build the high-speed indexes in `data/processed/`.

#### 10. `scripts/build_akarathi_index.py`
Parses `Pav_Words.txt`, `Sanskrit to Tamil - Dictionary by Neelambigai Ammaiyar.txt`, and the markdown files in `data/raw/thani_thamizh_akarathi/agarathi/search/` to build `data/processed/akarathi_index.json`.
* **Command:**
  ```bash
  python scripts/build_akarathi_index.py
  ```

#### 11. `scripts/build_wordnet_index.py`
Extracts `tvudump.sql` from `data/raw/tamil_wordnet/TamilWordnet.tgz`, converts Romanized Tamil into modern Unicode Tamil, and builds `data/processed/wordnet_index.db` (50,497 `twn` rows, 41,013 `sense` rows, 434,849 `morphtable` rows, and 6,914 `frequency` rows).
* **Command:**
  ```bash
  python scripts/build_wordnet_index.py
  ```

#### 12. `scripts/build_wiktionary_index.py`
Automatically downloads the latest Tamil Wiktionary XML dump (`tawiktionary-latest-pages-articles.xml.bz2`) into `data/raw/tamil_wiktionary/`, strips MediaWiki markup, and builds `data/processed/wiktionary_index.db`.
* **Command:**
  ```bash
  python scripts/build_wiktionary_index.py
  ```

#### 13. `scripts/build_sentamizh_index.py`
Reads the 9 processed JSON files in `data/raw/sentamizh/data/processed/`, tokenizes 265,212 Tamil surface tokens, and builds `data/processed/sentamizh_index.db`.
* **Command:**
  ```bash
  python scripts/build_sentamizh_index.py
  ```

#### 14. `scripts/build_madurai_index.py`
Reads `data/raw/project_madurai/manifest.json`, fetches any missing HTML e-texts directly from `projectmadurai.org`, parses 35 canonical works into 14,383 stanzas/couplets, and builds the diacritic-preserving SQLite FTS5 database at `data/processed/madurai_exact.db`.
* **Command & Options:**
  ```bash
  python scripts/build_madurai_index.py [--manifest PATH] [--raw-dir PATH] [--db-path PATH] [--force-download] [--limit-works N]
  ```
* **Examples:**
  ```bash
  # Standard full build (uses cached HTML files if present, downloads if missing)
  python scripts/build_madurai_index.py

  # Force re-downloading all HTML e-texts from projectmadurai.org
  python scripts/build_madurai_index.py --force-download

  # Quick test build ingesting only the first 3 works
  python scripts/build_madurai_index.py --limit-works 3
  ```

#### 15. `scripts/build_madurai_semantic_vectors.py`
Opens `data/processed/madurai_exact.db` in strict read-only mode, filters out non-poetic headers via `prepare_chunk()`, encodes all 13,284 eligible classical stanzas using the pinned Hugging Face model `intfloat/multilingual-e5-small` (`revision: 614241f6...`), verifies L2 normalization and SHA-256 database immutability, and writes:
* `data/processed/madurai_semantic_vectors.npy`
* `data/processed/madurai_semantic_meta.json`
* **Command & Options:**
  ```bash
  python scripts/build_madurai_semantic_vectors.py [--db-path PATH] [--output-dir PATH] [--batch-size 32] [--num-threads 6]
  ```
* **Example:**
  ```bash
  python scripts/build_madurai_semantic_vectors.py --batch-size 32 --num-threads 6
  ```

#### 16. `scripts/download_translator.py`
Downloads and caches Meta's `facebook/nllb-200-distilled-600M` (~1.2 GB) sequence-to-sequence translation model from Hugging Face for offline Tamil-to-English gloss translation (`backend/interpretation/translator.py`).
* **Command:**
  ```bash
  python scripts/download_translator.py
  ```

---

### 8D. Benchmark, Calibration & Evaluation Scripts

#### 17. `scripts/run_benchmark.py` — ThamizhiMorph Morphology Benchmark
Evaluates `ThamizhiMorphAdapter` against the inflected test cases in `research/BENCHMARK.md`, measuring Core vs. Guesser FST accuracy, and saves results to `data/evaluation/thamizhimorph_results.json`.
* **Command:**
  ```bash
  python scripts/run_benchmark.py
  ```

#### 18. `scripts/run_akarathi_benchmark.py` — Thani Thamizh Akarathi Benchmark
Evaluates `ThaniThamizhAkarathiAdapter` across all 60 lexical test cases in `research/BENCHMARK.md` and saves results to `data/evaluation/akarathi_results.json`.
* **Command:**
  ```bash
  python scripts/run_akarathi_benchmark.py
  ```

#### 19. `scripts/run_wordnet_benchmark.py` — Tamil WordNet Benchmark
Evaluates `TamilWordNetAdapter` across all 60 benchmark cases (measuring lexical coverage, morphology root coverage, POS distribution, and relation codes) and writes `data/evaluation/wordnet_results.json`.
* **Command:**
  ```bash
  python scripts/run_wordnet_benchmark.py
  ```

#### 20. `scripts/run_sentamizh_benchmark.py` — Sentamizh Literary Benchmark
Evaluates `SentamizhAdapter` across all 60 benchmark cases and writes `data/evaluation/sentamizh_results.json`.
* **Command:**
  ```bash
  python scripts/run_sentamizh_benchmark.py
  ```

#### 21. `scripts/run_unified_benchmark.py` — 60-Case Unified Multi-Resource Benchmark
Runs the full `RetrievalEngine` across all 60 benchmark cases (`L001`–`L055` and `M001`–`M005`), computing multi-resource coverage, cross-resource lemma agreement, and conflicts. Saves output to `data/evaluation/unified_results.json`.
* **Command:**
  ```bash
  python scripts/run_unified_benchmark.py
  ```

#### 22. `scripts/benchmark_embeddings.py` — Candidate Embedding Model Benchmark (Step 3B)
Empirically compares `intfloat/multilingual-e5-small` (384-D) vs. `intfloat/multilingual-e5-base` (768-D) on cold load time, p50/p95 query latency, batch throughput, Recall@K, Precision@K, and MRR against `tests/data/semantic_benchmark.json`. Saves output to `scratch/step3b_benchmark_results.json`.
* **Command:**
  ```bash
  python scripts/benchmark_embeddings.py
  ```

#### 23. `scripts/calibrate_semantic_retrieval.py` — Semantic Threshold ($\tau$) & $K$-Sweep Calibration (Step 3F)
Runs a $K$-sweep ($K \in \{5, 10, 15, 20, 25\}$) and similarity threshold sweep ($\tau \in [0.70, 0.90]$) over the permanent Project Madurai vectors to validate the production operating point ($K = 25, \tau = 0.845$). Saves detailed metrics to `scratch/calibration_data.json`.
* **Command:**
  ```bash
  python scripts/calibrate_semantic_retrieval.py
  ```

#### 24. `research/run_benchmark.py` — Live HTTP API Benchmark Report Generator
Queries the running local API server (`http://localhost:8000/api/query`) for every case in `research/BENCHMARK.md` and generates a formatted Markdown report at `research/BENCHMARK_RESULTS.md`.
* **Prerequisite:** Backend server must be running on port `8000`.
* **Command:**
  ```bash
  python research/run_benchmark.py
  ```

---

### 8E. Database Inspection & Diagnostic Scripts

#### 25. `scripts/test_db.py` — Wiktionary SQLite Quick Check
Connects to `data/processed/wiktionary_index.db` and queries sample definitions matching `வீரம்` to verify the database is readable.
* **Command:**
  ```bash
  python scripts/test_db.py
  ```

#### 26. `scripts/inspect_thok.py` — Tholkappiyam Raw SQLite Inspector
Inspects table names, column schemas, and sample rows inside `data/raw/thani_thamizh_akarathi/agarathi/ThokKappiyam.db`.
* **Command:**
  ```bash
  python scripts/inspect_thok.py
  ```

#### 27. `scripts/profile_resource.py`
Empty placeholder script reserved for custom resource profiling experiments.

---

### 8F. Automated Testing Suites (Python & JavaScript)

SOL AI includes **238 automated Python tests**, a **74-point dual-server parity harness**, and a **Node.js browser extension reliability suite**.

#### 28. Run All 238 Python Unit & Integration Tests (`pytest`)
```bash
pytest tests/ -q
```
Or run with verbose test names:
```bash
pytest tests/ -v
```

#### Run Individual Python Test Suites:
| Command | What It Tests |
| :--- | :--- |
| `pytest tests/test_akarathi.py -v` | Thani Thamizh Akarathi adapter lookups & provenance |
| `pytest tests/test_wordnet.py -v` | Tamil WordNet synsets, morphtable roots, and frequencies |
| `pytest tests/test_wiktionary.py -v` *(or via `test_retrieval.py`)* | Wiktionary definitions lookup |
| `pytest tests/test_sentamizh.py -v` | Sentamizh classical verse retrieval & 32-field metadata |
| `pytest tests/test_thamizhimorph.py -v` | ThamizhiMorph FST parsing, POS/case/number extraction |
| `pytest tests/test_project_madurai.py -v` | Project Madurai SQLite FTS5 exact stanza retrieval & Tirukkural couplet integrity |
| `pytest tests/test_semantic_preprocessing.py -v` | Non-poetic header/stub suppression & E5 passage formatting |
| `pytest tests/test_embedding_benchmark.py -v` | E5 embedding model pooling, normalization, and determinism |
| `pytest tests/test_semantic_vectors.py -v` | Permanent `.npy` vector matrix & metadata alignment verification |
| `pytest tests/test_project_madurai_semantic.py -v` | `ProjectMaduraiSemanticAdapter` cosine search & error safety |
| `pytest tests/test_semantic_retrieval_integration.py -v` | Pass 3 semantic integration & exact-match deduplication in `RetrievalEngine` |
| `pytest tests/test_semantic_short_circuit.py -v` | Smart short-circuiting when Pass 1/2 exact matches saturate ($\ge 25$) |
| `pytest tests/test_semantic_calibration.py -v` | Calibrated threshold ($\tau = 0.845$) out-of-domain query suppression |
| `pytest tests/test_retrieval.py -v` | Multi-pass `RetrievalEngine` & `EvidenceAggregator` ranking |
| `pytest tests/test_unified_benchmark.py -v` | 60-case unified benchmark regression tests |
| `pytest tests/test_context_selector.py -v` | Literary work diversity & passage quality scoring |
| `pytest tests/test_literary_processor.py -v` | Snippet extraction & keyword highlight offset calculation |
| `pytest tests/test_evidence_pack.py -v` | `EvidencePack` categorization & conflict detection |
| `pytest tests/test_contextual_disambiguation.py -v` | Core Tamil WSD contextual sense disambiguation |
| `pytest tests/test_wsd_overhaul.py -v` | Fractional, somatic, structural WSD detectors & principled abstention |
| `pytest tests/test_interpreter.py -v` | `MockLLMInterpreter`, `GeminiLLMInterpreter`, `GroqLLMInterpreter` & schemas |
| `pytest tests/test_api.py -v` | Legacy REST API endpoints & error codes |
| `pytest tests/test_django_api.py -v` | Django REST endpoints (`/api/query`, `/api/health`), CORS, & fallback cascade |
| `pytest tests/test_integration.py -v` | Full end-to-end query-to-response integration tests |

#### 29. `tests/verify_django_parity.py` — 74-Point Dual-Server Parity Verification
Spins up both the legacy server (`backend/api/server.py`) and the Django WSGI server (`backend/sol_django`) simultaneously on ephemeral ports and runs 74 side-by-side assertions verifying 100% response, status code, schema, and CORS parity.
* **Command:**
  ```bash
  python tests/verify_django_parity.py
  ```

#### 30. `tests/test_extension_reliability.js` — Browser Extension Watchdog & UI Reliability Suite
Runs a standalone Node.js test harness verifying the Chrome Extension's Shadow DOM state transitions, 25-second watchdog timer, error recovery, and race-condition guards.
* **Command:**
  ```bash
  node tests/test_extension_reliability.js
  ```

---

## 10. Step 9: Daily Quick-Start Cheat Sheet (TL;DR)

Once you have completed the initial setup, here is all you need to run SOL AI every day:

### Terminal 1 — Start the Backend (Port 8000)
```powershell
cd SOL_AI
# Activate virtual environment (Windows PowerShell):
.\venv\Scripts\Activate.ps1
# (Or on macOS/Linux: source venv/bin/activate)

# Start Django Backend:
python backend/sol_django/manage.py runserver 127.0.0.1:8000
```

### Terminal 2 — Start the Frontend Web App (Port 3000)
```powershell
cd SOL_AI/frontend
npm run dev
```
* **Open Web App:** [http://localhost:3000](http://localhost:3000)
* **Use Browser Extension:** Highlight any Tamil text on any webpage in Chrome $\rightarrow$ Right-click $\rightarrow$ **"Explain with SOL AI"**.

---

## 11. Step 10: Troubleshooting Common Issues

| Problem / Error Message | Cause | Exact Fix |
| :--- | :--- | :--- |
| **`SOL AI server could not be reached` (in Web App or Extension)** | The Python Django backend is not running. | Open a terminal in `SOL_AI/`, activate `venv`, and run `python backend/sol_django/manage.py runserver 127.0.0.1:8000`. |
| **`ModuleNotFoundError: No module named 'django'` (or `'numpy'`, `'torch'`, `'transformers'`)** | Either your virtual environment is not activated, or ML packages weren't installed. | 1. Activate `venv` (`.\venv\Scripts\Activate.ps1` on Windows or `source venv/bin/activate` on Mac/Linux).<br>2. Run `pip install -r requirements.txt numpy torch transformers sentencepiece`. |
| **`GEMINI_API_KEY environment variable is not configured`** | `SOL_LLM_PROVIDER` is set to `gemini`, but `GEMINI_API_KEY` is blank in `.env`. | Either paste a valid key after `GEMINI_API_KEY=` in `SOL_AI/.env`, **or** change `SOL_LLM_PROVIDER=mock` in `SOL_AI/.env` to run without an API key, then restart the backend server. |
| **PowerShell says `Activate.ps1 cannot be loaded because running scripts is disabled`** | Windows default PowerShell execution policy blocks local scripts. | Run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` in PowerShell, type `Y`, and press Enter. |
| **Right-clicking in Chrome does not show `"Explain with SOL AI"` or nothing happens** | The browser tab was opened before the extension was installed, or you are on a restricted `chrome://` page. | 1. Refresh the webpage (`F5` or `Ctrl+R`).<br>2. Note that Chrome blocks all extensions from running on internal `chrome://` pages or the Chrome Web Store—test on a normal website or `extension/test-page.html`. |
| **First semantic query takes ~3–5 seconds** | `ProjectMaduraiSemanticAdapter` lazily loads the `multilingual-e5-small` neural network into memory on the very first semantic query. | This is normal! Once loaded on the first query, all subsequent queries execute in milliseconds. |
