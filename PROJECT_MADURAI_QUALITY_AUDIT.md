# SOL AI — Project Madurai Quality & Evidence Validation Audit Report

**Audit Type:** Read-Only Quality, Provenance, and Evidence Validation Audit  
**Date:** September 30, 2026  
**Auditor:** Antigravity (Google DeepMind - Advanced Agentic Coding)  
**Target:** Project Madurai Exact Retrieval Layer (`madurai_exact.db`, `ProjectMaduraiExactAdapter`, `RetrievalEngine`, `EvidencePack`)  
**Corpus Version:** 1.0.0  

---

## 1. Executive Summary

This audit evaluated whether the **50,238 ingested chunks** in `data/processed/madurai_exact.db` and their resulting `Evidence` objects are sufficiently trustworthy, coherent, and useful to serve as the ground-truth corpus for SOL AI and support the planned semantic retrieval layer.

The architectural foundation of the exact retrieval implementation is technically sound:
* The SQLite FTS5 index is configured with a validated Tamil Unicode diacritic-preserving tokenizer (`unicode61 remove_diacritics 0 tokenchars 'ஂாிீுூெேைொோௌ்ௗ'`).
* FTS5 query sanitization (`sanitize_fts_query`) prevents SQL errors and syntax injection across all edge cases.
* Sub-5ms database latency is achieved with WAL mode and pushdown `LIMIT 25` ordering.
* Evidence categorization in `EvidencePack` is generic (`literary_context`) without source-specific hardcoding.
* Provenance and lemma preservation operate correctly across Pass 1 surface retrieval and Pass 2 morphological expansion.

However, the **corpus ingestion and chunking quality suffers from three critical BLOCKER errors and several major CONCERNS**:
1. **Manifest File Inversion (`INIYAVAI`)**: `manifest.json` mapped release `PM0021` to *Iniyavai Narpathu* (இனியவை நாற்பது, authored by Boothanchendanar). `PM0021` is actually **Subramaniya Bharathiyar Songs Part II** (சி. சுப்பிரமணிய பாரதியார் பாடல்கள்). Consequently, **2,005 chunks of 20th-century modern poetry are misattributed** to a 5th-century Post-Sangam didactic poet.
2. **Couplet Shift in Tirukkural (`TK`)**: The couples parser failed to strip Project Madurai English header lines (ingested as `PM-TK-0001` through `PM-TK-0004`). This caused an off-by-one line shift across the entire work: every subsequent chunk pairs the second line of one Kural with the first line of the next Kural (e.g. `PM-TK-0005` pairs the chapter header with line 1 of Kural 1, and `PM-TK-0006` pairs line 2 of Kural 1 with line 1 of Kural 2).
3. **Catastrophic Aphorism Stripping (`AATHI` & `KONRAI`)**: In `parse_generic_stanzas`, lines matching `^\d+\.` were treated as chapter headers and stripped via `lines = lines[1:]`. Because each aphorism in *Aathichudi* and *Konrai Vendhan* is a single numbered line, **all 109 aphorisms of Aathichudi and all aphorisms of Konrai Vendhan were discarded**, leaving only 5 and 4 header/invocation chunks respectively.
4. **Severe Canto Metadata False Positives**: Substring matching on `"இயல்"` (nature/characteristic) and `"பகுதி"` (part) misidentified regular poetic lines (e.g. *"இயல்பானான்"*, *"இயல்வது"*, *"மெல் இயல்"*) as canto headings, broadcasting random poetic fragments as the `canto` attribute for thousands of chunks.
5. **Extreme Fragmentation**: 90.86% of all chunks in the corpus are under 50 characters (average length 42.0 characters), breaking 4-line quatrains and multi-line hymns into disjointed single lines.
6. **Boilerplate Ingestion**: Webpage navigation links (e.g. *"உள்ளுறை அட்டவணைக்குத் திரும்ப"* 65 times) and volunteer acknowledgment blocks were ingested into the master literary table.

**Audit Status:** **BLOCKER**  
**Recommendation:** The current exact-retrieval database is **NOT sufficiently trustworthy** to proceed to the semantic retrieval phase. Ingesting embeddings or building vector indices on shifted Kurals, misattributed modern poems, and fragmented single lines would pollute downstream semantic retrieval. The ingestion script and manifest must be corrected and the database cleanly regenerated before semantic indexing begins.

---

## 2. Verified Statistics

The following empirical statistics were verified directly from the production files and SQLite database:

| Metric | Target / Manifest | Actual Verified in Database / FS | Status |
| :--- | :--- | :--- | :--- |
| **Total Works** | 34 | 34 | MATCH |
| **Total Releases** | 30 | 30 | MATCH |
| **Total Chunks (`chunks` table)** | 50,238 | 50,238 | MATCH |
| **FTS5 Indexed Rows (`chunks_fts`)** | 50,238 | 50,238 | MATCH (100% Parity) |
| **Database File Size** | ~40 MB | 42,012,672 bytes (40.07 MB) | VERIFIED |
| **Raw HTML Source Files** | 30 | 30 files in `data/raw/project_madurai` | VERIFIED |
| **Distinct `work` names** | 34 | 34 | VERIFIED |
| **Distinct `release_no`** | 30 | 30 | VERIFIED |
| **Triggers Active** | 3 | 3 (`chunks_ai`, `chunks_ad`, `chunks_au`) | VERIFIED |
| **Secondary Indexes** | 2 | 2 (`idx_pm_work`, `idx_pm_release_no`) | VERIFIED |
| **Existing Unit Tests** | 20 | 20 passed (49.99s) | PASS |

### Per-Work Chunk Distribution in Database
```
அபிராமி அந்தாதி                | PM0026_01 | count:   515 | PM-ABHIRAMI-0001        .. PM-ABHIRAMI-0515
ஆசாரக்கோவை                     | PM0063   | count:   258 | PM-ACHARA-0001          .. PM-ACHARA-0258
ஆத்திசூடி                      | PM0002   | count:     5 | PM-AATHI-0001           .. PM-AATHI-0005   [CRITICAL: 109 aphorisms lost]
இனியவை நாற்பது                 | PM0021   | count:  2005 | PM-INIYAVAI-0001        .. PM-INIYAVAI-2005 [CRITICAL: Bharathiyar content]
இன்னா நாற்பது                  | PM0020   | count:   176 | PM-INNA-0001            .. PM-INNA-0176
ஏலாதி                          | PM0029   | count:   328 | PM-ELATHI-0001          .. PM-ELATHI-0328
கலித்தொகை                      | PM0221   | count:  4171 | PM-KALI-0001            .. PM-KALI-4171
குறுந்தொகை                     | PM0110   | count:  1676 | PM-KURU-0001            .. PM-KURU-1676
கொன்றை வேந்தன்                 | PM0002   | count:     4 | PM-KONRAI-0001          .. PM-KONRAI-0004  [CRITICAL: aphorisms lost]
சிறுபஞ்சமூலம்                  | PM0029   | count:   391 | PM-SIRUPANCHA-0001       .. PM-SIRUPANCHA-0391
சிலப்பதிகாரம் - புகார்க்காண்டம் | PM0046   | count:  1696 | PM-SILAP_PUGAR-0001      .. PM-SILAP_PUGAR-1696
சிலப்பதிகாரம் - மதுரைக்காண்டம் | PM0111_01 | count:  2075 | PM-SILAP_MADURAI-0001    .. PM-SILAP_MADURAI-2075
சிலப்பதிகாரம் - வஞ்சிக்காண்டம் | PM0111_02 | count:  1497 | PM-SILAP_VANJI-0001      .. PM-SILAP_VANJI-1497
சீவக சிந்தாமணி - சுருக்கம்     | PM0509   | count:  2239 | PM-CHINTHAMANI-0001      .. PM-CHINTHAMANI-2239
திரிகடுகம்                     | PM0048   | count:   406 | PM-THIRIKADU-0001        .. PM-THIRIKADU-0406
திருக்குறள்                    | PM0001   | count:  1330 | PM-TK-0001              .. PM-TK-1330      [CRITICAL: shifted lines]
திருப்பல்லாண்டு                | PM0005_01 | count:    51 | PM-THIRUPPALLANDU-0001   .. PM-THIRUPPALLANDU-0051
திருப்பாவை                     | PM0005_02 | count:   279 | PM-THIRUPPAVAI-0001      .. PM-THIRUPPAVAI-0279 [Fragmented: 30 pasurams]
திருமந்திரம் (தந்திரங்கள் 1-2) | PM0004   | count:  2231 | PM-THIRUMANTHIRAM-0001   .. PM-THIRUMANTHIRAM-2231
திருவாசகம் (பாகம் 1)           | PM0003_01 | count:  1872 | PM-THIRUVASAGAM_1-0001   .. PM-THIRUVASAGAM_1-1872
திருவாசகம் (பாகம் 2)           | PM0003_02 | count:  1998 | PM-THIRUVASAGAM_2-0001   .. PM-THIRUVASAGAM_2-1998
தேவாரம் - முதல் திருமுறை (பாகம் 1) | PM0150   | count:  3877 | PM-THEVARAM_1-0001       .. PM-THEVARAM_1-3877
நற்றிணை                        | PM0296   | count:  5214 | PM-NATR-0001            .. PM-NATR-5214
நல்வழி                         | PM0002   | count:   165 | PM-NALVAZHI-0001         .. PM-NALVAZHI-0165
நான்மணிக்கடிகை                 | PM0047   | count:   431 | PM-NANMANI-0001         .. PM-NANMANI-0431
நாலடியார்                      | PM0016   | count:  1208 | PM-NALADI-0001          .. PM-NALADI-1208  [Fragmented: 400 venbas]
பதிற்றுப்பத்து                 | PM0038   | count:  2234 | PM-PATHITRU-0001        .. PM-PATHITRU-2234
பரிபாடல்                       | PM0087   | count:  2336 | PM-PARI-0001            .. PM-PARI-2336
பழமொழி நானூறு                  | PM0036   | count:  1609 | PM-PAZHAMOZHI-0001       .. PM-PAZHAMOZHI-1609
பாரதியார் பாடல்கள்             | PM0049   | count:  1951 | PM-BHARATHI-0001        .. PM-BHARATHI-1951
புறநானூறு                      | PM0057   | count:   788 | PM-PURAM-0001           .. PM-PURAM-0788
மணிமேகலை                       | PM0141   | count:  4819 | PM-MANI-0001            .. PM-MANI-4819
முதுமொழிக்காஞ்சி               | PM0064   | count:   278 | PM-MUTHU-0001           .. PM-MUTHU-0278
மூதுரை                         | PM0002   | count:   125 | PM-MOODHURAI-0001        .. PM-MOODHURAI-0125
```

---

## 3. Corpus Integrity

### 3.1 Empty Content & Length Distribution
* **Empty `original_text`:** 0 (0.00%)
* **Empty `normalized_text`:** 0 (0.00%)
* **Minimum Length:** 11 characters (`PM-SILAP_VANJI-0034`: `'கொளுச் சொல்'`)
* **Maximum Length:** 1,820 characters (`PM-CHINTHAMANI-0081`: commentary paragraph)
* **Average Length:** 42.0 characters

```
Content Length Buckets:
  Short (< 15 chars):       111  (0.22%)
  Short (< 25 chars):     4,126  (8.21%)
  Short (< 50 chars):    45,644 (90.86%)  <-- 91% of chunks are single line fragments
  Long (> 500 chars):       182  (0.36%)
  Long (> 1000 chars):       17  (0.03%)
  Long (> 2000 chars):        0  (0.00%)
```

### 3.2 Unicode & Tamil Integrity
* **Unicode Replacement Characters (`\uFFFD`):** 0 chunks found.
* **Control Characters (ASCII < 32 excluding `\n`, `\r`, `\t`):** 0 chunks found.
* **Zero-Width Characters (`\u200B`–`\u200D`, `\uFEFF`):**
  * Present in `original_text`: 177 chunks.
  * Present in `normalized_text`: 0 chunks (cleanly removed by `normalize_tamil_text`).
* **Broken Combining Marks:** 1 chunk found (`PM-SILAP_VANJI-1442`: `'ிற் படியோர் தம்முன்'`), where a pulli/vowel marker starts the chunk due to source text wrapping.
* **Mojibake Patterns (e.g. `Ã`, `à®`):** 0 detected.
* **ASCII Content:**
  * Total Tamil letters in corpus: 1,823,066
  * Total ASCII letters in corpus: 609
  * 9 chunks contain > 30% ASCII characters. Most notable: `PM-TK-0001` through `PM-TK-0004` contain English Project Madurai header boilerplate rather than Tamil text.

### 3.3 Duplicate Content Analysis
* **Total Chunks:** 50,238
* **Distinct `normalized_text` values:** 49,355
* **Exact Duplicate Text Entries:** 883 (1.76%)
* **Duplicate `(work, stanza_number, normalized_text)`:** 0 (None)
* **Duplicate `(work, stanza_number)`:** 0 (None)
* **Top Repetitions Across Corpus:**
  1. `'திருச்சிற்றம்பலம்'` (104 times in *Thiruvasagam 1 & 2* and *Thevaram 1*) — **Legitimate** Saivite liturgical refrain.
  2. `'உள்ளுறை அட்டவணைக்குத் திரும்ப'` (65 times in *Thevaram 1*) — **Ingestion Defect**: HTML webpage navigation link ("Return to Table of Contents") parsed as literary content.
  3. `'தூக்கு: செந்தூக்கு'` (54 times in *Pathitrupathu*) — **Legitimate** metrical colophon.
  4. `'வண்ணம்: ஒழுகு வண்ணம்'` (47 times in *Pathitrupathu*) — **Legitimate** metrical colophon.
  5. `'இத்தலம் சோழநாட்டிலுள்ளது.'` (30 times in *Thevaram 1*) — **Ingestion Defect**: Editorial geographic commentary parsed as a stanza.
  6. `'கடவுள் வாழ்த்து'` (22 times across 12 works) — **Legitimate** invocation section heading.

---

## 4. Chunk Quality Audit

Representative chunks from 12 distinct works spanning Sangam, Didactic, Epic, Bhakti, and Modern epochs were audited.

### Detailed Findings by Work Sample

#### 1. Tirukkural (`TK`) — Couplet Misalignment [BLOCKER]
The Couplet parser (`parse_tirukkural`) expected verbatim two-line couplets starting immediately at line 0 of the stripped text. However, lines 1–4 contained English Project Madurai header text:
* `PM-TK-0001`: `"tirukuRaL of tiruvaLLuvar (in tamil script, unicode format)"`
* `PM-TK-0002`: `"(in Tamil Script, unicode/UTF-8 format) திருவள்ளுவர் அருளிய திருக்குறள்"`
* `PM-TK-0003`: `"The content subsequently converted to Unicode encoding..."`
* `PM-TK-0004`: `"https://www.projectmadurai.org/ You are welcome to freely distribute..."`
* `PM-TK-0005`: `"1.1 கடவுள் வாழ்த்து \n அகர முதல எழுத்தெல்லாம் ஆதி"` (Chapter title + Kural 1, Line 1)
* `PM-TK-0006`: `"பகவன் முதற்றே உலகு. \n கற்றதனால் ஆய பயனென்கொல் வாலறிவன்"` (Kural 1, Line 2 + Kural 2, Line 1)

**Impact:** Every single couplet from Kural 1 through Kural 1,330 is split across chunk boundaries, combining the bottom line of one couplet with the top line of the subsequent couplet.

#### 2. Aathichudi (`AATHI`) & Konrai Vendhan (`KONRAI`) — Discarded Aphorisms [BLOCKER]
In `parse_generic_stanzas`, lines matching `re.match(r'^\d+\.', lines[0])` were assumed to be stanza section headers followed by the poem text on `lines[1:]`:
```python
if lines and re.match(r'^\d+\.', lines[0]):
    ...
    lines = lines[1:]  # Truncates the aphorism!
if not lines:
    continue           # Discards the entire chunk!
```
In `pmuni0002.html`, every aphorism is a single numbered line:
* `1. அறம் செய விரும்பு.`
* `2. ஆறுவது சினம்.`
* `3. இயல்வது கரவேல்.`

When `lines = lines[1:]` executed, `lines` became empty, and the block was silently discarded. **Out of 109 aphorisms in Aathichudi, 0 aphorisms were ingested.** Only 5 unnumbered header lines (`கடவுள் வாழ்த்து`, `உயிர் வருக்கம்`, etc.) exist in the database. The identical defect occurred in *Konrai Vendhan* (only 4 chunks created).

#### 3. Iniyavai Narpathu (`INIYAVAI`) — Misattributed Content [BLOCKER]
Due to a release number mismatch in `manifest.json` (`PM0021` instead of the actual Iniyavai Narpathu release), the ingestion pipeline processed `pmuni0021.html`, which is **Subramaniya Bharathiyar Songs Part II (Gnanap Padalkal)**:
* `PM-INIYAVAI-0001`: `"சி. சுப்ரமணிய பாரதியார் எழுதிய"`
* `PM-INIYAVAI-0005`: `"அச்சமில்லை அச்சமில்லை அச்சமென்ப தில்லையே"`
* `PM-INIYAVAI-1003`: `"பாயும் கடிநாய்ப் போலீசுக்-காரப் / பார்ப்பானுக் குண்டிதிலே பீசு."`

All 2,005 chunks are tagged with:
* `work`: `"இனியவை நாற்பது"`
* `author`: `"பூதஞ்சேந்தனார்"`
* `period`: `"Post-Sangam (Didactic)"`
* `genre`: `"Didactic Poetry"`

This introduces modern colloquial 20th-century political poetry under a 5th-century classical didactic attribution.

#### 4. Naladiyar (`NALADI`) — Excessive Quatrain Fragmentation [CONCERN]
*Naladiyar* consists of 400 classical 4-line venbas. In the database, it contains 1,208 chunks because HTML `<p>` tags separated lines within stanzas.
* `PM-NALADI-0605`: Line 3 of quatrain 187 (`வரிமுகம் புண்படுக்கும் வள்ளுகிர் நோன்றாள்`)
* `PM-NALADI-0606`: Line 4 of quatrain 187 (`அரிமா மதுகை யவர்.`)

The quatrain is broken into disjointed single-line or couplet chunks, preventing whole-stanza semantic retrieval.

#### 5. Purananuru (`PURAM`), Manimekalai (`MANI`), Thiruvasagam (`THIRUVASAGAM_1`) — Boilerplate Chunks [CONCERN]
Chunks 1–3 in multiple works contain web editorial boilerplate:
* `PM-PURAM-0001` to `0003`: School name, donor acknowledgment, coordinator Dr. C. Kesavaraj, and student typist names.
* `PM-MANI-0001` to `0003`: Repeated parenthetical title strings (`"(ஆசிரியர் - சீத்தலைச்சாத்தனார்)"`).
* `PM-THIRUVASAGAM_1-0003`: `"பொருள் அடக்கம்"` (Table of Contents header).

---

## 5. Metadata Quality Audit

### 5.1 Completeness Matrix

| Field Name | Expected Source | Null / Empty Count | Completeness | Quality Assessment |
| :--- | :--- | :--- | :--- | :--- |
| `chunk_id` | Deterministic Format | 0 | 100.00% | PASS: Stable `PM-{WORK}-{STANZA:04d}` |
| `corpus_version` | Manifest | 0 | 100.00% | PASS: Constant `1.0.0` |
| `source` | Manifest | 0 | 100.00% | PASS: Constant `"Project Madurai"` |
| `release_no` | Manifest | 0 | 100.00% | PASS: Accurate PM release strings |
| `work` | Manifest | 0 | 100.00% | CONCERN: PM0021 labeled *Iniyavai* |
| `author` | Manifest / Colophon | 0 | 100.00% | CONCERN: Misattribution for PM0021 |
| `period` | Manifest | 0 | 100.00% | PASS: Accurate to manifest |
| `genre` | Manifest | 0 | 100.00% | PASS: Accurate to manifest |
| `canto` | Parsed Header | 16,363 | 67.43% | **BLOCKER**: Major false positives |
| `chapter` | Couplet Parser | 48,908 | 2.65% | Populated only for Tirukkural |
| `line_range` | Couplet Parser | 48,908 | 2.65% | Populated only for Tirukkural |
| `stanza_number` | Parser Sequence | 0 | 100.00% | PASS: Sequential integers |
| `verse_number` | Colophon / Sequence | 0 | 100.00% | PASS: Preserved where parsed |
| `source_url` | Manifest | 0 | 100.00% | PASS: Canonical web URLs |
| `file_path` | Ingestion File | 0 | 100.00% | PASS: Relative workspace paths |

### 5.2 The Canto Keyword False Positive Anomaly [CONCERN]
In `scripts/build_madurai_index.py` line 282:
```python
if any(k in header_line for k in ["காண்டம்", "காதை", "படலம்", "பதிகம்", "இயல்", "அதிகாரம்", "திருமுறை", "பகுதி"]):
    current_canto = header_line
    continue
```
The substring check for `"இயல்"` and `"பகுதி"` matched ordinary poetic lines containing Tamil vocabulary with those morphological substrings:
* `"இயல்பானான்"` (became nature)
* `"இயல்வது"` (what is possible)
* `"மெல் இயல்"` (delicate nature)
* `"இயங்கு பொருளின் இயல்பெலாம்"` (the nature of moving things)
* `"உப்பு இயல் பாவை"` (salt doll)
* `"காட்டிய பகுதியைக் கவினுற வரைந்தான்"` (painted the depicted region)

**Impact:** Over 15,000 chunks inherited arbitrary poetic lines as their structural `canto` metadata (e.g. 1,735 chunks in *Chinthamani* have `canto = '40. தாம் அளந்துகொண்டு காத்த அருந் தவம் - தம்மால் இயல்வது'`, and 1,610 chunks have `canto = 'பிரியல் ஆடவர்க்கு இயல்பு எனின்'`). Furthermore, those actual poetic lines were skipped from the corpus text.

---

## 6. Provenance Audit

Traceability was evaluated end-to-end:
$$\text{Query} \longrightarrow \text{Evidence} \longrightarrow \text{chunk\_id} \longrightarrow \text{work\_id} \longrightarrow \text{DB Row} \longrightarrow \text{Source HTML}$$

### Traceability Verification: `மரம்`
1. Query: `"மரம்"`
2. Evidence returned: `source_id = "PM-CHINTHAMANI-1075"`
3. DB Row retrieved: `chunk_id = "PM-CHINTHAMANI-1075"`, `file_path = "data/raw/project_madurai/pmuni0509_01.html"`
4. Verbatim Text Check in Raw File:
   `'144 பருமித்த - ஆயத்தம் செய்யப்பட்ட. பை யென - மெல்லென. குருமித்து - முழங்கி... கூம்பு - பாய் மரம்.'`
   **Found verbatim in raw file:** `True`
5. Provenance attributes:
   * `source`: `"Project Madurai"` (PASS)
   * `evidence_type`: `"literary_context"` (PASS)
   * `lemma`: `None` (PASS: No fabricated lemma in Pass 1)

### Traceability Verification: `மரங்களில்` (Pass 2 Expansion)
1. Query: `"மரங்களில்"`
2. ThamizhiMorph extracted candidate lemmas: `['மரங்', 'மரம்']`
3. Pass 2 Secondary Lookup retrieved `PM-ACHARA-0206` (for candidate `'மரங்'`) and `PM-CHINTHAMANI-1075` (for candidate `'மரம்'`).
4. Evidence attributes:
   * `surface`: `'மரம்'`
   * `lemma`: `'மரம்'` (PASS: Caller lemma correctly preserved)
   * `evidence_type`: `'literary_context'` (PASS)

---

## 7. Retrieval Quality Benchmark

A benchmark of 12 queries spanning common nouns, verbs, literary instruments, inflected plural/case forms, and high-frequency terms was executed through `RetrievalEngine`:

| Query | Normalized | Candidate Lemmas | PM Hits | SM Hits | Total Literary | PM Works Represented | Notes |
| :--- | :--- | :--- | :---: | :---: | :---: | :--- | :--- |
| **மரம்** | மரம் | `['மரம்']` | 25 | 24 | 49 | கலித்தொகை, மணிமேகலை, சிந்தாமணி | Capped at LIMIT 25 |
| **மனிதன்** | மனிதன் | `['மனி', 'மனிதன்']` | 2 | 0 | 2 | பாரதியார் பாடல்கள், இனியவை (பாரதி) | SM has 0 hits; PM adds coverage |
| **செய்** | செய் | `['செய்']` | 25 | 66 | 91 | அபிராமி, இனியவை, கலித்தொகை | High frequency verb |
| **யாழ்** | யாழ் | `['யாழ்']` | 24 | 6 | 30 | ஆசாரக்கோவை, கலி, பரிபாடல், மணி | Classical string instrument |
| **அகத்தி** | அகத்தி | `['அகத்தி']` | 1 | 0 | 1 | இனியவை (பாரதியார்) | Botanical term; SM has 0 |
| **மரங்களில்** | மரங்களில் | `['மரங்', 'மரம்']` | 26 | 24 | 50 | ஆசாரக்கோவை, கலி, மணி, சிந்தாமணி | Surface=0, Lemma=26 (Pass 2) |
| **மனிதர்களுக்கு** | மனிதர்களுக்கு | `['மனிதன்', 'மனிதர்']`| 11 | 1 | 12 | அபிராமி, திருமந்திரம், பாரதியார் | Dative plural; SM has only 1 |
| **செய்தார்கள்** | செய்தார்கள் | `['செய்', 'செய்தார்']` | 36 | 70 | 106 | 10 works across Sangam & Epic | Past 3rd plural; multi-lemma |
| **வீட்டில்** | வீட்டில் | `['வீடு', 'வீட்டில்']` | 31 | 22 | 53 | 13 works across corpus | Locative noun; Surface=6, Lemma=25 |
| **நீர்** | நீர் | `['நீர்']` | 25 | 127 | 152 | அபிராமி, கலி, சிந்தாமணி, பாரதி | Capped at LIMIT 25 |
| **அறம்** | அறம் | `['அறம்']` | 25 | 52 | 77 | அபிராமி, கலித்தொகை, மணிமேகலை | Fundamental didactic term |
| **அன்பு** | அன்பு | `['அன்பு']` | 25 | 21 | 46 | அபிராமி, கலி, சிந்தாமணி, பாரதி | Capped at LIMIT 25 |

### Deterministic Limit Behavior
* SQL query uses `ORDER BY c.chunk_id ASC LIMIT 25;`
* When surface hits exceed 25, the earliest chunks by deterministic `chunk_id` are consistently returned.
* For multi-lemma queries in Pass 2 (e.g. `மரங்களில்` producing candidate lemmas `மரங்` and `மரம்`), each candidate lemma executes a separate query capped at 25, resulting in combined deduplicated sets (e.g. 26 total PM items).

---

## 8. Sentamizh vs Project Madurai Comparison

| Dimension | Sentamizh Corpus | Project Madurai Exact Index | Synthesis & Value Assessment |
| :--- | :--- | :--- | :--- |
| **Scope / Epochs** | Sangam, Early Epics, Early Bhakti (3rd BCE – 10th CE) | Sangam, Post-Sangam, Epics, Bhakti, Late Medieval, Modern (3rd BCE – 20th CE) | **Complementary Coverage:** Project Madurai substantially extends literary breadth into didactic works (*Pazhamozhi*, *Acharakovai*), later Bhakti (*Abhirami Anthathi*), and modern poetry (*Bharathiyar*). |
| **Passage Unit** | Full multi-line stanzas (typically 4–20 lines) | Mostly single lines or couplets (91% < 50 chars) due to ingestion fragmentation | **Granularity Difference:** Sentamizh provides complete poetic context; PM currently provides fragmented citation lines. |
| **Metadata Richness** | Deep literary poetics: `thinai`, `turai`, `pann`, `rasa`, `speaker_role`, modern paraphrase | Textual provenance: `release_no`, `canto`, `source_url`, `file_path` | **Distinct Functions:** Sentamizh acts as an annotated poetic corpus; PM acts as a broad-coverage primary text citation index. |
| **Unique Matches** | Rich Sangam contexts for classical roots | Exclusively matched terms absent from classical anthologies (e.g. `மனிதன்`, `அகத்தி`) | **Added Value:** Answering the core question: **Yes**, Project Madurai adds substantial independent evidence and temporal reach to the literary layer. |

---

## 9. EvidencePack Pipeline Audit

The complete flow was verified:
$$\text{Query} \longrightarrow \text{RetrievalEngine} \longrightarrow \text{EvidenceAggregator} \longrightarrow \text{EvidencePack}$$

* **Generic Classification:** In `backend/interpretation/evidence_pack.py`, `LITERARY_EVIDENCE_TYPES` includes `"literary_context"`. All Project Madurai evidence objects are automatically routed to `pack.literary_evidence` without requiring a hardcoded source check.
* **No Mislabeled Evidence:**
  * Project Madurai evidence in `pack.lexical_evidence`: **0** (PASS)
  * Project Madurai evidence in `pack.morphology_evidence`: **0** (PASS)
* **Sentamizh Retention:** Sentamizh evidence remains correctly classified in `pack.literary_evidence`.
* **Context Selection:** `SentamizhContextSelector.select()` correctly prioritizes diverse works across both Sentamizh and Project Madurai results. For query `"மரம்"`, the top 5 selected literary contexts contained 3 PM items and 2 Sentamizh items representing 4 distinct works (*Chinthamani*, *Kuruntokai*, *Kalithokai*, *Manimekalai*).
* **Provenance Statistics:** `pack.source_provenance["Project Madurai"]` accurately reports `status: "FOUND"` and `total_entries: 25`.
* **Zero Lemma Fabrication:** Direct surface queries in Pass 1 yield `lemma = None`.

---

## 10. Error & Edge Case Audit

19 edge cases were evaluated across `ProjectMaduraiExactAdapter` and `RetrievalEngine`:

| Input Test Case | Raw Query | FTS5 Sanitized Expression | Adapter Result | Engine Result | Status |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **Empty string** | `""` | `""` | 0 items | 0 items | PASS |
| **Whitespace** | `"   \t\n  "` | `""` | 0 items | 0 items | PASS |
| **ASCII Punctuation** | `.,;:?!` | `".,; ?!"` | `NOT_FOUND` | `NOT_FOUND` | PASS |
| **Tamil Punctuation** | `அறம்! என்ன?` | `"அறம்! என்ன?"` | `NOT_FOUND` | `NOT_FOUND` | PASS |
| **Mixed Tamil/English** | `மரம் tree` | `"மரம் tree"` | `NOT_FOUND` | `NOT_FOUND` | PASS |
| **Double Quotes** | `"மரம்"` | `"""மரம்"""` | 25 items | 25 items | PASS |
| **Single Quotes** | `'மரம்'` | `"'மரம்'"` | 25 items | 25 items | PASS |
| **FTS Wildcard (`*`)** | `மரம்*` | `"மரம்"` | 25 items | 25 items | PASS |
| **FTS Prefix (`^`)** | `^மரம்` | `"மரம்"` | 25 items | 25 items | PASS |
| **FTS Column Match (`:`)** | `normalized_text:மரம்`| `"normalized_text மரம்"`| `NOT_FOUND` | `NOT_FOUND` | PASS |
| **FTS Braces / Parens** | `{மரம்} (மரம்) [மரம்]`| `"மரம் மரம் மரம்"` | `NOT_FOUND` | `NOT_FOUND` | PASS |
| **FTS Operators (`+ - ~`)**| `+மரம் -மரம் ~மரம்` | `"மரம் மரம் மரம்"` | `NOT_FOUND` | `NOT_FOUND` | PASS |
| **FTS Booleans (`OR AND`)**| `மரம் OR அறம் NOT நீர்`| `"மரம் OR அறம் NOT நீர்"`| `NOT_FOUND` | `NOT_FOUND` | PASS |
| **FTS `NEAR()` Syntax** | `NEAR(மரம் அறம், 10)` | `"NEAR மரம் அறம், 10"` | `NOT_FOUND` | `NOT_FOUND` | PASS |
| **Mismatched Quotes** | `"மரம்` | `"""மரம்"` | 25 items | 25 items | PASS |
| **High Frequency Term** | `நீர்` | `"நீர்"` | 25 items | 25 items | PASS |
| **Non-existent Tamil** | `ஸுப்ரகலாவிசித்ர` | `"ஸுப்ரகலாவிசித்ர"` | `NOT_FOUND` | `NOT_FOUND` | PASS |
| **Non-existent English** | `xyz123nonexistent` | `"xyz123nonexistent"` | `NOT_FOUND` | `NOT_FOUND` | PASS |
| **Inflected Tamil Word** | `மரங்களை` | `"மரங்களை"` | `NOT_FOUND` | 27 items (Pass 2) | PASS |

**Result:** Zero SQL exceptions, zero syntax injection crashes, and zero unhandled errors.

---

## 11. Determinism Audit

5 representative queries (`மரம்`, `நீர்`, `அறம்`, `யாழ்`, `அன்பு`) were executed 3 consecutive times:
* **Result count stability:** 100% identical across all runs.
* **Result order stability:** 100% identical across all runs.
* **Chunk ID stability:** 100% identical sequence (`chunk_id_0 == chunk_id_1 == chunk_id_2`).
* **Metadata stability:** All metadata key-value pairs identical across runs.
* **Empirical ORDER BY Verification:** Every result list strictly satisfied `chunk_ids == sorted(chunk_ids)`.

**Determinism Status:** **PASS**

---

## 12. Performance Observation

Latency was measured over repeated lookups on warm SQLite connections:

| Lookup Category | Sample Query | Direct Adapter Latency (FTS5) | Full Engine Latency (All Resources) |
| :--- | :--- | :---: | :---: |
| **Low-frequency exact** | `அகத்தி` (1 hit) | **0.68 ms** | 3,595 ms |
| **Medium-frequency exact** | `யாழ்` (24 hits) | **4.05 ms** | 3,485 ms |
| **High-frequency exact** | `நீர்` (294 hits / 25 limit) | **4.06 ms** | 3,383 ms |
| **Lemma-expanded query** | `மரங்களை` (Pass 1 surface + Pass 2) | **0.72 ms** (surface pass) | 3,754 ms |

### Observation
The Project Madurai SQLite FTS5 index is exceptionally fast (**sub-5ms** for all queries). Full `RetrievalEngine` search time (~3.5 seconds) is dominated by the ThamizhiMorph FST external process and multi-adapter candidate lemma lookups, not by Project Madurai retrieval.

---

## 13. Audit Issue Classification

### BLOCKER (Must be resolved before semantic retrieval)

1. **`ISSUE-PM-01` — Manifest Inversion of Iniyavai Narpathu (`INIYAVAI`)**
   * *Description:* `manifest.json` maps `INIYAVAI` to `PM0021` (`pmuni0021.html`), which is actually Subramaniya Bharathiyar Songs Part II.
   * *Impact:* 2,005 chunks of 20th-century modern nationalist poetry are misattributed to a 5th-century Post-Sangam didactic work by Boothanchendanar. Building semantic embeddings on this work will corrupt didactic semantic retrieval.
2. **`ISSUE-PM-02` — Couplet Shift in Tirukkural (`TK`)**
   * *Description:* Unstripped English header lines in `pmuni0001.html` shifted line pairings across the entire work.
   * *Impact:* All 1,330 couplets are misaligned across stanza boundaries, pairing line 2 of one Kural with line 1 of the next Kural. Generating sentence embeddings on these chunks would produce nonsensical, hybrid semantic vectors.
3. **`ISSUE-PM-03` — Discarded Aphorisms in Aathichudi & Konrai Vendhan (`AATHI`, `KONRAI`)**
   * *Description:* `lines = lines[1:]` in `parse_generic_stanzas` stripped single-line numbered aphorisms as verse headers.
   * *Impact:* All 109 famous aphorisms of *Aathichudi* and all aphorisms of *Konrai Vendhan* are absent from the database.

### CONCERN (Quality/reliability issues to address before production use)

1. **`ISSUE-PM-04` — Canto Keyword False Positives**
   * *Description:* Substring match on `"இயல்"` and `"பகுதி"` in `build_madurai_index.py` captured ordinary poetic lines containing those roots.
   * *Impact:* Over 15,000 chunks carry arbitrary poetic lines as their structural `canto` attribute, and those poetic lines were omitted from the text chunks.
2. **`ISSUE-PM-05` — Over-Fragmentation of Classical Stanzas**
   * *Description:* Splitting on `\n\s*\n+` after HTML tag cleaning fragmented 90.86% of the corpus into chunks under 50 characters (average 42 characters).
   * *Impact:* Four-line didactic venbas (*Naladiyar*) and eight-line hymns (*Tiruppavai*) are split into disjointed single lines or half-lines rather than complete stanzas.
3. **`ISSUE-PM-06` — Ingestion of Web Navigation and Volunteer Boilerplate**
   * *Description:* Navigation strings (e.g. *"உள்ளுறை அட்டவணைக்குத் திரும்ப"* 65 times in Thevaram) and volunteer typist acknowledgments (in Purananuru, Manimekalai) were ingested as literary chunks.

### OBSERVATION (Technical achievements worth preserving)

1. **`OBS-PM-01`:** FTS5 query latency is sub-5ms across low, medium, and high-frequency queries.
2. **`OBS-PM-02`:** `sanitize_fts_query` provides robust protection against FTS5 operator injection and unclosed quotes.
3. **`OBS-PM-03`:** `EvidencePack` generically integrates `literary_context` without requiring hardcoded source checks.
4. **`OBS-PM-04`:** Determinism is 100% stable with strict `ORDER BY chunk_id ASC`.
5. **`OBS-PM-05`:** Zero lemma fabrication in Pass 1, and caller lemma candidate preservation in Pass 2.

### PASS (Verified components conforming to specification)

* SQLite WAL mode and connection pooling lifecycle.
* FTS5 schema with Unicode61 Tamil diacritic-preserving tokenization.
* SQLite insert/update/delete synchronization triggers (`chunks_ai`, `chunks_ad`, `chunks_au`).
* Error boundaries returning graceful empty/error `Evidence` objects without throwing exceptions.
* End-to-end evidence flow through `RetrievalEngine` and `EvidencePack`.

---

## 14. Audit Recommendation

### Question
> *Is the current Project Madurai exact-retrieval layer sufficiently trustworthy to proceed to the next semantic-retrieval phase?*

### Answer
**NO.**

While the query engine, adapter, FTS5 indexing, and EvidencePack pipeline are architecturally sound and production-ready, the underlying database contains **three critical BLOCKERS**:
1. Misattribution of 2,005 Bharathiyar chunks as *Iniyavai Narpathu*.
2. Off-by-one line shift across all 1,330 couplets of *Tirukkural*.
3. Complete loss of all aphorisms in *Aathichudi* and *Konrai Vendhan*.

If semantic embeddings are trained or generated over `madurai_exact.db` in its current state, the vector space will encode misaligned verses, hybrid couplets, and corrupted author metadata.

**Action Required Before Semantic Retrieval:**
The build script (`scripts/build_madurai_index.py`) and manifest (`data/raw/project_madurai/manifest.json`) must be updated to address these blockers, followed by a clean rebuild of `madurai_exact.db`. Once the database reflects properly aligned couplets, intact aphorisms, and verified work mappings, semantic indexing can proceed with confidence.
