# SOL AI — P1 Context-Aware Polysemy / Word-Sense Disambiguation Report

**Status:** Completed, Corrected & Fully Verified  
**Date:** 2026-10-02  
**Target Feature:** High-priority context-aware polysemy disambiguation for Tamil word senses  

---

## 1. Executive Summary & Critical Demo Correction

In the initial implementation of the P1 Contextual Word-Sense Disambiguation (WSD) module, automated synthetic tests passed, but testing the **actual Chrome extension demo sentence** revealed a failure:

### Real Demo Sentence:
```text
அவனுடைய தம்பி கால் கிலோ மாம்பழம் வாங்கி வந்தான்.
```
**Highlighted query:** `கால்`  
**Expected contextual meaning:** `நான்கில் ஒரு பங்கு` / `¼` (specifically `கால் கிலோ` = ¼ kg / 250g)  
**Imperative constraint:** The system **MUST NOT** return `உடல் உறுப்பான கால் (பாதம்/கால்)` (physical foot/leg).

---

## 2. Root Cause Analysis of Real Demo Failure

Tracing the real demo query through the initial WSD engine revealed the exact point of breakdown:

| Component | Observation | Root Cause |
|---|---|---|
| **Context Extraction** | Context received: `"அவனுடைய தம்பி கால் கிலோ மாம்பழம் வாங்கி வந்தான்."` | Healthy |
| **Token Filtering** | Tokens: `['தம்பி', 'கிலோ', 'மாம்பழம்', 'வாங்கி', 'வந்தான்']` | Healthy |
| **Partition Word Match** | Checked `PARTITION_TERMS = {'பகுதி', 'பங்கு', 'பாகம்', ...}` | **FAILURE**: `கிலோ` was absent from `PARTITION_TERMS`. |
| **Dictionary Synonyms** | Looked up `கிலோ` in `ThaniThamizhAkarathi` | **FAILURE**: `கிலோ` (metric borrowing: kilogram) has no classical entry; returned empty synonym set. |
| **Sense Overlap** | Compared sentence tokens against candidate definitions of `கால்` | **FAILURE**: None of `['தம்பி', 'கிலோ', 'மாம்பழம்', 'வாங்கி', 'வந்தான்']` appear in any definition of `கால்`. |
| **Sense Scoring** | Every candidate sense (Sense 0 through 36) scored `0.0`. | **FAILURE**: Top score < 1.0 caused WSD to return `contextual_meaning = None`. |
| **Extension UI Rendering** | When `contextual_meaning` was `None`, the UI only displayed `General Meaning`, where Bullet 1 was Sense 0 (`மாந்தர்கள் உட்பட விலங்குகளின் ஓர் உடல் உறுப்பு`). | **FAILURE**: The user was presented with physical foot/leg for buying mangoes! |

---

## 3. Generic Quantity / Unit Architecture (Zero Hardcoding)

To resolve this without word-specific hacks (strictly prohibiting `if query == "கால்"` or `if "கால் கிலோ" in context`), a **domain-agnostic quantity/unit collocation framework** was implemented:

### 3.1 Tamil Quantity & Measurement Taxonomy (`QUANTITY_UNIT_TERMS`)
Covers modern metric units, imperial units, temporal intervals, traditional Tamil volume/weight measures, and partition classifiers:
- **Mass / Weight:** `கிலோ`, `கிலோகிராம்`, `கிராம்`, `மில்லிகிராம்`, `டன்`, `பவுண்டு`, `குவிண்டால்`, `வீசை`, `பலம்`, `கழஞ்சு`, `துலாம்`, `குன்றிமணி`, `தொடி`, `சேர்`, `பவுன்`
- **Volume / Liquid:** `லிட்டர்`, `மில்லிலிட்டர்`, `படி`, `ஆழாக்கு`, `உழக்கு`, `மரக்கால்`, `நாழி`, `குறுணி`, `பதக்கு`, `கலம்`, `முகத்தல்`
- **Length / Distance / Area:** `மீட்டர்`, `சென்டிமீட்டர்`, `மில்லிமீட்டர்`, `கிலோமீட்டர்`, `அடி`, `இன்ச்`, `கஜம்`, `மைல்`, `சாண்`, `முழம்`, `விரற்கடை`, `காணி`, `குழி`, `மா`, `ஏக்கர்`, `ஹெக்டேர்`, `சென்ட்`
- **Time:** `மணி`, `வினாடி`, `நொடி`, `நிமிடம்`, `நாழிகை`, `நாள்`, `வாரம்`, `மாதம்`, `வருடம்`, `ஆண்டு`
- **Partition / Proportions:** `பங்கு`, `பகுதி`, `பாகம்`, `கூறு`, `வீதம்`, `விழுக்காடு`, `சதவீதம்`, `அளவு`, `மடங்கு`
- **Monetary:** `ரூபாய்`, `காசு`, `பைசா`, `பணம்`

### 3.2 Distance-Aware Collocation Weighting
The WSD algorithm computes the token distance $d = \min(|i - q|)$ from each context word to every occurrence of the target query in the sentence:
- **Immediate Adjacency ($d = 1$):** When a target word with a documented fractional sense (`s_has_fraction`) is immediately followed or preceded by a quantity unit (e.g., `கால் கிலோ`, `கால் லிட்டர்`, `கால் மீட்டர்`, `கால் மணி`, `கால் பகுதி`), it receives a maximum collocation boost of **$+35.0$**.
- **Clause Proximity ($d \le 3$):** Collocations within the immediate clause receive a decaying boost of **$+\frac{20.0}{d}$**.
- **Distant Mentions ($d > 3$):** Receive a weak boost of **$+\frac{5.0}{d}$**.
- **Non-fractional senses:** Receive **$+0.0$** unit boost, completely preventing false positive associations.

### 3.3 Dynamic Contextual Gloss Formatting (`format_fraction_unit_gloss`)
When a fractional candidate wins and is collocated with a unit ($d \le 2$), the output generates an explicit contextual explanation:
```text
நான்கில் ஒரு பங்கு — இங்கு 'கால் கிலோ' என்பது ஒரு கிலோவின் நான்கில் ஒரு பங்கு (¼ kg / 250g).
```
This is fully dynamic and generalizes across any Tamil fractional word (`கால்`, `அரை`, `முக்கால்`, `அரைக்கால்`) and any measurement unit.

---

## 4. Before vs. After Behavior

### Case 1: Real Demo Sentence (Fractional Measure)
- **Sentence:** `"அவனுடைய தம்பி கால் கிலோ மாம்பழம் வாங்கி வந்தான்."`
- **Query:** `கால்`
- **Before:**
  - WSD Scores: Fractional Sense = 0.0, Physical Foot Sense = 0.0
  - `contextual_meaning` = `None`
  - UI Card: Rendered General Meaning with Bullet 1: `மாந்தர்கள் உட்பட விலங்குகளின் ஓர் உடல் உறுப்பு` ❌
- **After:**
  - WSD Scores: Fractional Sense = **35.0**, Physical Foot Sense = **0.0**
  - `contextual_meaning` = **`"நான்கில் ஒரு பங்கு — இங்கு 'கால் கிலோ' என்பது ஒரு கிலோவின் நான்கில் ஒரு பங்கு (¼ kg / 250g)."`** ✅
  - UI Card: Renders `"In this context (இச்சூழலில்)"` at the top with `¼ kg / 250g`. Physical foot/leg is **completely absent**.

### Case 2: Physical Foot/Leg Context
- **Sentence:** `"அவன் கல்லில் நடக்கும்போது கால் வழுக்கி கீழே விழுந்தான்."`
- **Query:** `கால்`
- **Before & After:**
  - WSD Scores: Physical Foot Sense = **20.8** (stem match `நடக்கும்போது` $\rightarrow$ `நடக்கவோ`), Fractional Sense = **0.0**
  - `contextual_meaning` = **`"மாந்தர்கள் உட்பட விலங்குகளின் ஓர் உடல் உறுப்பு. இது தரையில் ஊன்றி நடக்கவோ, நகரவோ பயன்படுவது."`** ✅
  - UI Card: Renders physical foot/leg sense under `"In this context (இச்சூழலில்)"`.

### Case 3: Quantity Unit Generalization
- **Volume:** `"கால் லிட்டர் பால் வாங்கினேன்."`
  $\rightarrow$ `contextual_meaning` = `"நான்கில் ஒரு பங்கு — இங்கு 'கால் லிட்டர்' என்பது ஒரு லிட்டரின் நான்கில் ஒரு பங்கு (¼ L / 250ml)."` ✅
- **Length:** `"கால் மீட்டர் துணி வாங்கினான்."`
  $\rightarrow$ `contextual_meaning` = `"நான்கில் ஒரு பங்கு — இங்கு 'கால் மீட்டர்' என்பது ஒரு மீட்டரின் நான்கில் ஒரு பங்கு (¼ m / 25cm)."` ✅
- **Time:** `"கால் மணி நேரம் காத்திருந்தேன்."`
  $\rightarrow$ `contextual_meaning` = `"நான்கில் ஒரு பங்கு — இங்கு 'கால் மணி' என்பது ஒரு மணியின் நான்கில் ஒரு பங்கு (15 நிமிடங்கள் / ¼ hour)."` ✅
- **Partition:** `"இந்த நிலத்தின் கால் பகுதி மட்டுமே பயிரிடப்பட்டுள்ளது."`
  $\rightarrow$ `contextual_meaning` = `"நான்கில் ஒரு பங்கு — இங்கு 'கால் பகுதி' என்பது நான்கில் ஒரு பகுதி (¼)."` ✅

### Case 4: General Meaning Preserved
- `meaning` continues to retain all 37 documented senses separated by semicolons:
  `"1. மாந்தர்கள் உட்பட விலங்குகளின் ஓர் உடல் உறுப்பு...; 2. ஒன்றை ஈடாகப் பங்கிட்ட நான்கில் ஒரு பங்கு...; 3. காற்று..."`
- `meaning != contextual_meaning` (Polysemy fully preserved).

---

## 5. Test Suite Verification

### 5.1 Focused Suite: `tests/test_contextual_disambiguation.py`
```text
tests/test_contextual_disambiguation.py::TestContextualDisambiguation::test_01_real_demo_kaal_kilo PASSED [ 11%]
tests/test_contextual_disambiguation.py::TestContextualDisambiguation::test_02_physical_foot_meaning PASSED [ 22%]
tests/test_contextual_disambiguation.py::TestContextualDisambiguation::test_03_same_query_different_context_different_senses PASSED [ 33%]
tests/test_contextual_disambiguation.py::TestContextualDisambiguation::test_04_quantity_unit_generalization PASSED [ 44%]
    - subtest 'liter': PASSED
    - subtest 'meter': PASSED
    - subtest 'time': PASSED
    - subtest 'partition': PASSED
tests/test_contextual_disambiguation.py::TestContextualDisambiguation::test_05_general_meaning_remains_separate PASSED [ 55%]
tests/test_contextual_disambiguation.py::TestContextualDisambiguation::test_06_context_absent_leaves_contextual_meaning_none PASSED [ 66%]
tests/test_contextual_disambiguation.py::TestContextualDisambiguation::test_07_context_irrelevant_handles_ambiguity PASSED [ 77%]
tests/test_contextual_disambiguation.py::TestContextualDisambiguation::test_08_inflected_word_thamizhimorph_and_context PASSED [ 88%]
tests/test_contextual_disambiguation.py::TestContextualDisambiguation::test_09_direct_mock_interpreter_wsd PASSED [100%]

================ 9 passed, 1 warning, 4 subtests passed in 64.86s ================
```

### 5.2 Full Regression Test Suite
- `pytest tests/test_interpreter.py tests/test_django_api.py tests/test_evidence_pack.py`: **26/26 PASSED**
- `pytest tests/test_semantic_short_circuit.py tests/test_semantic_calibration.py`: **21/21 PASSED**
- `node tests/test_extension_reliability.js`: **5/5 PASSED**

---

## 6. Files Changed

1. `backend/interpretation/wsd.py`:
   - Added comprehensive `QUANTITY_UNIT_TERMS` set covering mass, volume, length, time, partition, and monetary measures.
   - Expanded `FRACTION_INDICATORS` to detect mathematical fractions (`1/4`, `\frac`, etc.).
   - Implemented token distance calculation from target query word occurrences.
   - Added distance-weighted collocation boost (+35.0 for $d = 1$, $+20.0/d$ for $d \le 3$) for fractional senses collocated with units.
   - Added `format_fraction_unit_gloss()` to generate contextual glosses explaining the fractional measure with conversion notes.
2. `tests/test_contextual_disambiguation.py`:
   - Added `test_01_real_demo_kaal_kilo` validating `"அவனுடைய தம்பி கால் கிலோ மாம்பழம் வாங்கி வந்தான்."`.
   - Added `test_04_quantity_unit_generalization` verifying generalization across liter, meter, hour, and partition.
   - Preserved all physical, absent, irrelevant, inflected, and pipeline tests.
3. `P1_CONTEXTUAL_WSD_REPORT.md`: Updated comprehensive documentation.

---

## 7. Strict Boundaries Maintained

- **NO Word-Specific Hardcoding:** Zero conditional checks for `கால்` or `கிலோ`. The mechanism applies to all Tamil fractional words paired with any quantity unit.
- **Retrieval Engine & Embeddings:** Unaltered (`multilingual-e5-small`, K=25, threshold=0.845).
- **Project Madurai:** Unaltered (FTS5 and SQLite vector indices).
- **ThamizhiMorph:** Unaltered (FST finite state transducers).
- **API Response Schema:** Backwards-compatible `SOLResponse` schema preserved.
