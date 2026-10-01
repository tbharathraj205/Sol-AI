"""
Canonical Ingestion and Build Script for Project Madurai Exact Retrieval Corpus.

Responsibilities:
1. Load data/raw/project_madurai/manifest.json
2. Fetch or load raw Project Madurai e-texts (.html / .txt)
3. Validate and decode UTF-8 content
4. Parse structural stanzas/verses per work genre
5. Normalize text using Unicode NFC and zero-width filtering
6. Preserve original verbatim poetic text and formatted line breaks
7. Assign stable, deterministic identifiers: PM-{WORK_ID}-{STANZA:04d}
8. Create SQLite database with canonical chunks table
9. Create SQLite FTS5 index with validated Tamil diacritic-preserving tokenizer:
   tokenize="unicode61 remove_diacritics 0 tokenchars 'ஂாிீுூெேைொோௌ்ௗ'"
10. Ensure idempotent, deterministic rebuilding without duplicates or drifting IDs.
"""

import sys
import os
import re
import json
import sqlite3
import hashlib
import argparse
import unicodedata
import urllib.request
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = PROJECT_ROOT / "data" / "raw" / "project_madurai" / "manifest.json"
DEFAULT_RAW_DIR = PROJECT_ROOT / "data" / "raw" / "project_madurai"
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "processed" / "madurai_exact.db"

# Validated SQLite FTS5 tokenizer configuration for Tamil combining marks
TAMIL_FTS5_TOKENIZER = 'tokenize="unicode61 remove_diacritics 0 tokenchars \'ஂாிீுூெேைொோௌ்ௗ\'"'


def compute_sha256(data: bytes) -> str:
    """Compute hex SHA-256 checksum for byte content."""
    return hashlib.sha256(data).hexdigest()


def normalize_tamil_text(text: str) -> str:
    """
    Apply canonical Unicode NFC normalization and clean non-printing artifacts:
    - Unicode NFC normalization
    - Strip zero-width joiners / non-joiners / spaces (\u200B - \u200D, \uFEFF)
    - Collapse multiple whitespace to single space
    """
    if not text:
        return ""
    norm = unicodedata.normalize("NFC", text)
    # Remove zero-width characters
    norm = re.sub(r'[\u200B-\u200D\uFEFF]', '', norm)
    # Collapse whitespace per line
    lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in norm.splitlines()]
    return '\n'.join([line for line in lines if line])


def clean_html_tags(html_str: str) -> str:
    """
    Clean HTML markup from Project Madurai e-texts while preserving line breaks and stanza structure.
    Handles both raw HTML e-texts (where <br> and block tags define line breaks)
    and plain text snippets (preserving existing newlines).
    """
    if not html_str:
        return ""

    text = html_str.replace('&nbsp;', ' ').replace('&copy;', '(c)').replace('&amp;', '&').replace('&quot;', '"').replace('&lt;', '<').replace('&gt;', '>')
    text = re.sub(r'<!--.*?-->', '', text, flags=re.S)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.I | re.S)
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.I | re.S)

    has_html_breaks = bool(re.search(r'<(?:br|p|div|h[1-6]|tr|center)[^>]*>', text, re.I))
    if has_html_breaks:
        text = re.sub(r'[\r\n]+', ' ', text)
        text = re.sub(r'(?:<br\s*/?>\s*){2,}', '\n\n', text, flags=re.I)
        text = re.sub(r'</?(?:p|h[1-6]|tr|div|center|font|ul|li|hr|table|blockquote)[^>]*>', '\n\n', text, flags=re.I)
        text = re.sub(r'<br\s*/?>', '\n', text, flags=re.I)
    else:
        text = text.replace('\r\n', '\n').replace('\r', '\n')

    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\n[ \t]*\n+', '\n\n', text)
    return text.strip()


def fetch_source_file(
    work_entry: Dict[str, Any],
    raw_dir: Path,
    force_download: bool = False
) -> Tuple[bytes, str]:
    """
    Fetch source e-text from web or local cache.
    Returns (raw_bytes, checksum).
    """
    raw_dir.mkdir(parents=True, exist_ok=True)
    file_name = work_entry.get("file_name") or f"{work_entry['work_id'].lower()}.html"
    local_path = raw_dir / file_name

    if local_path.exists() and not force_download:
        data = local_path.read_bytes()
        checksum = compute_sha256(data)
        return data, checksum

    source_url = work_entry["source_url"]
    print(f"  [DOWNLOAD] Fetching {source_url} -> {file_name}...")
    req = urllib.request.Request(
        source_url,
        headers={"User-Agent": "SOL-AI-ProjectMaduraiIngester/1.0 (+https://github.com/vishwavel05/SOL_AI)"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = resp.read()

    local_path.write_bytes(data)
    checksum = compute_sha256(data)
    return data, checksum


def slice_work_section(text: str, work_id: str, title: str) -> str:
    """
    Extract specific sub-work text when multiple works are bundled in a single file
    (e.g., PM0002 containing Aathichudi, Konrai Vendhan, Moodhurai, Nalvazhi; PM0025 containing Iniyavai Narpathu).
    """
    section_map = {
        "AATHI": ("1.  ஆத்திசூடி", "2.  கொன்றை வேந்தன்"),
        "KONRAI": ("2.  கொன்றை வேந்தன்", "3.  மூதுரை"),
        "MOODHURAI": ("3.  மூதுரை", "4.  நல்வழி"),
        "NALVAZHI": ("4.  நல்வழி", None),
        "INIYAVAI": ("இனியவை நாற்பது : பூதஞ்சேந்தனார்", "3.  களவழி நாற்பது"),
        "ELATHI": ("2. கணிமேதையார் அருளிய", "3. காரியாசான்"),
        "SIRUPANCHA": ("3. காரியாசான்", "சிறுபஞ்சமூலம் முற்றிற்று"),
        "THIRUPPALLANDU": ("பெரியாழ்வார் அருளிச்செய்த   திருப்பல்லாண்டு", "பெரியாழ்வார் திருமொழி"),
        "THIRUPPAVAI": ("ஸ்ரீ ஆண்டாள் அருளிச் செய்த திருப்பாவை", "ஸ்ரீ: ஆண்டாள் அருளிச்செய்த நாச்சியார் திருமொழி"),
    }

    if work_id in section_map:
        start_marker, end_marker = section_map[work_id]
        start_idx = text.find(start_marker)
        if start_idx != -1:
            if end_marker:
                end_idx = text.find(end_marker, start_idx + len(start_marker))
                if end_idx != -1:
                    return text[start_idx:end_idx]
            return text[start_idx:]

    return text


def is_boilerplate(b: str, work_title: str = "") -> bool:
    """
    Identify and exclude Project Madurai website navigation links, TOC controls,
    contributor acknowledgements, typist credits, and web boilerplate.
    Conservative: preserves legitimate literary colophons and invocations.
    """
    b_norm = re.sub(r'[\u200B-\u200D\uFEFF]', '', b).strip()

    if any(k in b_norm.lower() for k in [
        "in tamil script", "unicode format", "unicode encoding", "unicode/utf-8", "utf-8 format"
    ]):
        return True

    if "Project Madurai" in b_norm or "மதுரைத் திட்டம்" in b_norm:
        return True

    if any(k in b_norm for k in [
        "உள்ளுறை அட்டவணைக்குத் திரும்ப",
        "அட்டவணைக்குத் திரும்ப",
        "இம்மின்னுரை",
        "மின்னூலாக்கம்",
        "உரிமை - பொதுக் களம்",
        "இப்பதிவினைச் செய்தவர்கள்",
        "கி.ஆ.பெ.விசுவநாதம்",
        "Our Sincere thanks go to",
        "Our sincere thanks go to",
        "Sincere thanks go to",
        "This webpage presents",
        "This page was first put up",
        "To view the Tamil text correctly",
        "Unicode fonts containing Tamil Block",
        "Feel free to send the corrections",
        "send the corrections by email",
        "In case of difficulties send an email",
        "தட்டச்சு செய்தவர்",
        "பிழை திருத்தியவர்",
        "சரிபார்த்தவர்",
    ]):
        return True

    if re.match(r'^இத்தலம்\s+[\u0B80-\u0BFF\s]+நாட்டிலுள்ளது\s*\.?$', b_norm):
        return True

    if b_norm in ["உள்ளடக்கம்", "பொருளடக்கம்", "பொருள் அடக்கம்", "உள்ளுறை", "பொருளடக்கம்:"]:
        return True

    if any(k in b_norm for k in [
        "(எட்டுத்தொகை நூல்களில் ஒன்று)",
        "(ஐம்பெருங்காப்பியங்களில் ஒன்று)",
        "எட்டுத்தொகை நூல்களுள் ஒன்றான",
        "(பதினெண்கீழ்க்கணக்கு நூல்களில் ஒன்று)",
        "(பதினென் கீழ்க்கணக்கு நூல்)",
        "(பதினெண்கீழ்க்கணக்கு நூல்)",
        "(பதினெண் கீழ்க்கணக்கு நூல்)",
        "(ஆசிரியர் - சீத்தலைச்சாத்தனார்)",
    ]) and len(b_norm) < 120:
        return True

    if work_title and b_norm == work_title:
        return True

    return False


def is_structural_heading(line: str) -> bool:
    """
    Conservatively identify genuine structural headings (canto, kathai, padalam, athikaram, etc.).
    Prevents ordinary poetic text containing substrings such as 'இயல்பானான்', 'இயல்வது',
    'மெல் இயல்', or 'பகுதியைக்' from being misidentified as headings.
    """
    line = line.strip()
    if not line or len(line) > 60:
        return False
    if re.search(r'[,\.;\?!]$', line):
        return False
    if re.search(r'(?:^|\s)[\u0B80-\u0BFF\s]*காண்டம்$', line):
        return True
    if re.search(r'(?:^|\s)[\u0B80-\u0BFF\s]*காதை$', line):
        return True
    if re.search(r'(?:^|\s)[\u0B80-\u0BFF\s]*படலம்$', line):
        return True
    if re.search(r'(?:^|\s)[\u0B80-\u0BFF\s]*பதிகம்$', line):
        return True
    if re.search(r'(?:^|\s)அதிகாரம்(?:\s+\d+|\s*:.*)?$', line) or re.search(r'^\d+[\.\s]+[\u0B80-\u0BFF\s]+அதிகாரம்$', line):
        return True
    if re.search(r'(?:^|\s)[\u0B80-\u0BFF\s]*திருமுறை(?:\s*\(.*?\))?$', line):
        return True
    if re.match(r'^(?:\d+[\.\d\s]*\s+)?[\u0B80-\u0BFF]{3,15}(?:வியல்|இயல்)$', line):
        if not re.search(r'(?:இயல்வது|இயல்பானான்|இயல்பு|இயல்பின்|இயல்பாக)$', line):
            return True
    if re.match(r'^(?:பகுதி|பாகம்)\s*[-:]?\s*\d+', line) or re.search(r'^(?:முதல்|இரண்டாம்|மூன்றாம்|நான்காம்)\s*(?:பகுதி|பாகம்)$', line):
        return True
    if line in ["கடவுள் வாழ்த்து", "நூல் முகம்", "தற்சிறப்புப் பாயிரம்", "பொதுப் பாயிரம்", "சிறப்புப் பாயிரம்"]:
        return True
    if line.endswith("வருக்கம்"):
        return True
    return False


def parse_tirukkural(
    work_meta: Dict[str, Any],
    clean_text: str,
    file_rel_path: str
) -> List[Dict[str, Any]]:
    """
    Parse Tirukkural couplets into 1,330 distinct canonical chunks with zero couplet shift.
    Excludes English/header boilerplate and preserves exact lines and chapter metadata.
    """
    work_id = work_meta["work_id"]
    work_title = work_meta["work"]
    author = work_meta.get("author", "திருவள்ளுவர்")
    period = work_meta.get("period", "Post-Sangam (Didactic)")
    genre = work_meta.get("genre", "Didactic Couplets")
    release_no = work_meta.get("release_no", "PM0001")
    source_url = work_meta.get("source_url")

    raw_lines = clean_text.splitlines()
    lines = [re.sub(r'[ \t]+', ' ', l).strip() for l in raw_lines]
    lines = [l for l in lines if l]

    try:
        start_idx = next(i for i, l in enumerate(lines) if l.startswith("அகர முதல"))
        end_idx = next(i for i in range(len(lines)-1, -1, -1) if re.search(r'\s+1330\s*$', lines[i]))
    except StopIteration:
        return []

    def is_tk_header(l: str) -> bool:
        if re.match(r'^\d+[\d\.,\s]*\s+[\u0B80-\u0BFF]', l):
            return True
        if l.endswith('முற்றிற்று'):
            return True
        if l in ['அறத்துப்பால்', 'பொருட்பால்', 'காமத்துப்பால்', 'திருக்குறள்']:
            return True
        if l.endswith('இயல்') and len(l) < 20:
            return True
        return False

    current_sec = "அறத்துப்பால்"
    current_chap = "கடவுள் வாழ்த்து"
    chunks = []
    st_num = 1
    i = start_idx

    while i <= end_idx and st_num <= 1330:
        l = lines[i]
        if is_tk_header(l):
            sec_m = re.match(r'^\d+\.\s*([\u0B80-\u0BFF]+பால்)', l)
            if sec_m:
                current_sec = sec_m.group(1).strip()
            elif l in ['அறத்துப்பால்', 'பொருட்பால்', 'காமத்துப்பால்']:
                current_sec = l

            chap_m = re.match(r'^\d+[\d\.,\s]*\s+([\u0B80-\u0BFF\s]+)', l)
            if chap_m:
                candidate = chap_m.group(1).strip()
                if not candidate.endswith('பால்') and not candidate.endswith('இயல்'):
                    current_chap = candidate
            i += 1
            continue

        l1 = l
        if i + 1 <= end_idx:
            l2 = lines[i + 1]
            i += 2
        else:
            l2 = ""
            i += 1

        clean_l1 = re.sub(r'\s*\d{1,5}\s*$', '', l1).strip()
        clean_l2 = re.sub(r'\s*\d{1,5}\s*$', '', l2).strip()

        orig_text = f"{clean_l1}\n{clean_l2}".strip()
        norm_text = normalize_tamil_text(f"{clean_l1} {clean_l2}")

        if len(norm_text) > 10:
            chunk_id = f"PM-{work_id}-{st_num:04d}"
            chunks.append({
                "chunk_id": chunk_id,
                "corpus_version": "1.0.0",
                "source": "Project Madurai",
                "release_no": release_no,
                "work": work_title,
                "author": author,
                "period": period,
                "genre": genre,
                "canto": current_sec,
                "chapter": current_chap,
                "stanza_number": st_num,
                "verse_number": str(st_num),
                "line_range": f"{st_num*2-1}-{st_num*2}",
                "original_text": orig_text,
                "normalized_text": norm_text,
                "source_url": source_url,
                "file_path": file_rel_path,
            })
            st_num += 1

    return chunks


def parse_generic_stanzas(
    work_meta: Dict[str, Any],
    clean_text: str,
    file_rel_path: str
) -> List[Dict[str, Any]]:
    """
    Parse Sangam poetry, didactic venbas, epic cantos, and bhakti hymns into
    canonical stanza/verse chunks, preserving whole literary units and aphorisms.
    """
    work_id = work_meta["work_id"]
    work_title = work_meta["work"]
    author = work_meta.get("author")
    period = work_meta.get("period")
    genre = work_meta.get("genre")
    release_no = work_meta.get("release_no")
    source_url = work_meta.get("source_url")

    # Split into paragraph / stanza blocks
    blocks = [b.strip() for b in re.split(r'\n\s*\n+', clean_text) if b.strip()]

    chunks = []
    st_num = 1
    current_canto: Optional[str] = None
    current_chapter: Optional[str] = None

    for b in blocks:
        # Check Tamil character density
        tamil_chars = len(re.findall(r'[\u0B80-\u0BFF]', b))
        if tamil_chars < 6:
            continue

        # Skip PM copyright, volunteer acknowledgments, and navigation boilerplate
        if is_boilerplate(b, work_title):
            continue

        lines = [l.strip() for l in b.splitlines() if l.strip()]
        if not lines:
            continue

        # Check for standalone canto/chapter/varukkam title
        if len(lines) == 1 and len(lines[0]) < 60:
            header_line = lines[0]
            if is_structural_heading(header_line):
                # Don't treat work title numbers (e.g. 1. ஆத்திசூடி) as canto
                if not re.match(r'^\d+\.\s*(?:ஆத்திசூடி|கொன்றை வேந்தன்|மூதுரை|நல்வழி)$', header_line):
                    current_canto = header_line
                continue

        # If line 0 is a varukkam header inside a multi-line block
        if lines[0].endswith("வருக்கம்"):
            current_canto = lines[0]
            lines = lines[1:]
            if not lines:
                continue

        # Check for poet attribution line at end (e.g. "-தேவகுலத்தார்." or "-ஔவையார்.")
        stanza_author = author
        if len(lines) > 1 and lines[-1].startswith("-") and len(lines[-1]) < 50:
            candidate_poet = lines[-1].lstrip("-").strip(" .")
            if len(candidate_poet) > 2:
                stanza_author = candidate_poet
            lines = lines[:-1]

        # Check if the block consists of multiple separately numbered aphorisms/verses
        numbered_lines = [l for l in lines if re.match(r'^\d+\.\s*[\u0B80-\u0BFF]', l)]
        if len(numbered_lines) >= 2 or (len(lines) == 1 and re.match(r'^\d+\.\s*[\u0B80-\u0BFF]', lines[0])):
            for nl in lines:
                m = re.match(r'^(\d+)\.\s*(.*)', nl)
                if not m:
                    continue
                v_num, v_text = m.group(1), m.group(2).strip()
                if v_text in ["ஆத்திசூடி", "கொன்றை வேந்தன்", "மூதுரை", "நல்வழி"]:
                    continue
                v_norm = normalize_tamil_text(v_text)
                if len(v_norm) < 4:
                    continue
                chunk_id = f"PM-{work_id}-{st_num:04d}"
                chunks.append({
                    "chunk_id": chunk_id,
                    "corpus_version": "1.0.0",
                    "source": "Project Madurai",
                    "release_no": release_no,
                    "work": work_title,
                    "author": stanza_author,
                    "period": period,
                    "genre": genre,
                    "canto": current_canto,
                    "chapter": current_chapter,
                    "stanza_number": st_num,
                    "verse_number": v_num,
                    "line_range": None,
                    "original_text": v_text,
                    "normalized_text": v_norm,
                    "source_url": source_url,
                    "file_path": file_rel_path,
                })
                st_num += 1
            continue

        # Check for multi-line stanza starting with a verse number (e.g. Naladiyar, Kuruntokai)
        verse_num = str(st_num)
        canto_info = current_canto

        if lines and re.match(r'^\d+\.', lines[0]):
            header_match = re.match(r'^(\d+)\.\s*(.*)', lines[0])
            if header_match:
                v_num = header_match.group(1)
                sub_label = header_match.group(2).strip()

                if sub_label in ["ஆத்திசூடி", "கொன்றை வேந்தன்", "மூதுரை", "நல்வழி", "அறத்துப்பால்", "பொருட்பால்", "காமத்துப்பால்"]:
                    continue

                is_pure_header = False
                if not sub_label:
                    is_pure_header = True
                elif sub_label in ['கடவுள் வாழ்த்து', 'நூல்', 'பாயிரம்', 'சிறப்புப் பாயிரம்', 'பொதுப் பாயிரம்', 'குறிஞ்சி', 'முல்லை', 'மருதம்', 'நெய்தல்', 'பாலை']:
                    is_pure_header = True
                elif ('கூற்று' in sub_label or 'திணை' in sub_label or 'துறை' in sub_label or 'பாடியவர்' in sub_label) and len(sub_label) <= 30 and not re.search(r'[,;\?!]', sub_label):
                    is_pure_header = True
                elif len(lines) >= 4 and len(sub_label) <= 20 and not re.search(r'[,;\?!]', sub_label) and ' ' not in sub_label:
                    is_pure_header = True

                if is_pure_header:
                    verse_num = v_num
                    if sub_label in ['குறிஞ்சி', 'முல்லை', 'மருதம்', 'நெய்தல்', 'பாலை'] and not current_canto:
                        canto_info = sub_label
                    lines = lines[1:]
                else:
                    verse_num = v_num
                    lines[0] = sub_label

        if not lines:
            continue

        # Check for trailing verse number on last line (e.g. "... 40" in Iniyavai, Nanmanikkadikai)
        last_m = re.search(r'\s+(\d{1,4})\s*$', lines[-1])
        if last_m and verse_num == str(st_num):
            verse_num = last_m.group(1)
            lines[-1] = re.sub(r'\s*\d{1,4}\s*$', '', lines[-1]).strip()

        orig_text = '\n'.join(lines)
        norm_text = normalize_tamil_text(' '.join(lines))

        if len(norm_text) < 4:
            continue

        chunk_id = f"PM-{work_id}-{st_num:04d}"
        chunks.append({
            "chunk_id": chunk_id,
            "corpus_version": "1.0.0",
            "source": "Project Madurai",
            "release_no": release_no,
            "work": work_title,
            "author": stanza_author,
            "period": period,
            "genre": genre,
            "canto": canto_info,
            "chapter": current_chapter,
            "stanza_number": st_num,
            "verse_number": verse_num,
            "line_range": None,
            "original_text": orig_text,
            "normalized_text": norm_text,
            "source_url": source_url,
            "file_path": file_rel_path,
        })
        st_num += 1

    return chunks


def build_chunks_for_work(
    work_meta: Dict[str, Any],
    raw_dir: Path,
    force_download: bool = False
) -> List[Dict[str, Any]]:
    """
    Download/load, decode, slice, and parse a single work into canonical chunks.
    """
    raw_bytes, checksum = fetch_source_file(work_meta, raw_dir, force_download=force_download)
    # Store checksum in work_meta for manifest provenance
    work_meta["checksum_sha256"] = checksum

    raw_html = raw_bytes.decode(work_meta.get("encoding", "utf-8"), errors="replace")
    clean_text = clean_html_tags(raw_html)

    # Slice if sub-work
    section_text = slice_work_section(clean_text, work_meta["work_id"], work_meta["work"])
    file_rel_path = f"data/raw/project_madurai/{work_meta.get('file_name', '')}"

    strategy = work_meta.get("chunk_strategy", "short_stanza")
    if strategy == "couplet":
        return parse_tirukkural(work_meta, section_text, file_rel_path)
    else:
        return parse_generic_stanzas(work_meta, section_text, file_rel_path)


def init_database(db_path: Path) -> sqlite3.Connection:
    """
    Initialize SQLite database with chunks master table and FTS5 index.
    Preserves exact audited schema and Tamil unicode61 tokenizer parameters.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        print(f"  [RESET] Removing existing index database at: {db_path}")
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("PRAGMA journal_mode = WAL;")
    cur.execute("PRAGMA synchronous = NORMAL;")

    # Master chunks table
    cur.execute("""
    CREATE TABLE chunks (
        chunk_id TEXT PRIMARY KEY,
        corpus_version TEXT NOT NULL,
        source TEXT NOT NULL,
        release_no TEXT,
        work TEXT NOT NULL,
        author TEXT,
        period TEXT,
        genre TEXT NOT NULL,
        canto TEXT,
        chapter TEXT,
        stanza_number INTEGER,
        verse_number TEXT,
        line_range TEXT,
        original_text TEXT NOT NULL,
        normalized_text TEXT NOT NULL,
        source_url TEXT,
        file_path TEXT NOT NULL
    );
    """)

    # FTS5 Virtual Table with validated Tamil tokenizer
    fts_sql = f"""
    CREATE VIRTUAL TABLE chunks_fts USING fts5(
        normalized_text,
        content='chunks',
        content_rowid='rowid',
        {TAMIL_FTS5_TOKENIZER}
    );
    """
    cur.execute(fts_sql)

    # Triggers for continuous synchronization
    cur.execute("""
    CREATE TRIGGER chunks_ai AFTER INSERT ON chunks BEGIN
        INSERT INTO chunks_fts(rowid, normalized_text) VALUES (new.rowid, new.normalized_text);
    END;
    """)
    cur.execute("""
    CREATE TRIGGER chunks_ad AFTER DELETE ON chunks BEGIN
        INSERT INTO chunks_fts(chunks_fts, rowid, normalized_text) VALUES ('delete', old.rowid, old.normalized_text);
    END;
    """)
    cur.execute("""
    CREATE TRIGGER chunks_au AFTER UPDATE ON chunks BEGIN
        INSERT INTO chunks_fts(chunks_fts, rowid, normalized_text) VALUES ('delete', old.rowid, old.normalized_text);
        INSERT INTO chunks_fts(rowid, normalized_text) VALUES (new.rowid, new.normalized_text);
    END;
    """)

    # Indices on master table
    cur.execute("CREATE INDEX idx_pm_work ON chunks(work);")
    cur.execute("CREATE INDEX idx_pm_release_no ON chunks(release_no);")

    conn.commit()
    return conn


def insert_chunks(conn: sqlite3.Connection, chunks: List[Dict[str, Any]]) -> int:
    """
    Batch insert chunks into SQLite master table.
    Triggers automatically populate chunks_fts.
    """
    cur = conn.cursor()
    sql = """
    INSERT INTO chunks (
        chunk_id, corpus_version, source, release_no, work, author, period, genre,
        canto, chapter, stanza_number, verse_number, line_range, original_text,
        normalized_text, source_url, file_path
    ) VALUES (
        :chunk_id, :corpus_version, :source, :release_no, :work, :author, :period, :genre,
        :canto, :chapter, :stanza_number, :verse_number, :line_range, :original_text,
        :normalized_text, :source_url, :file_path
    );
    """
    cur.executemany(sql, chunks)
    conn.commit()
    return len(chunks)


def build_madurai_index(
    manifest_path: Path = DEFAULT_MANIFEST,
    raw_dir: Path = DEFAULT_RAW_DIR,
    db_path: Path = DEFAULT_DB_PATH,
    force_download: bool = False,
    limit_works: Optional[int] = None
) -> Dict[str, Any]:
    """
    Execute full Project Madurai ingestion and indexing pipeline.
    """
    print("=" * 70)
    print("PROJECT MADURAI CANONICAL INGESTION & FTS5 INDEX BUILD")
    print("=" * 70)
    print(f"Manifest: {manifest_path}")
    print(f"Raw dir:  {raw_dir}")
    print(f"DB path:  {db_path}")

    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    works = manifest_data.get("works", [])
    if limit_works is not None:
        works = works[:limit_works]

    print(f"Target Works Count: {len(works)}\n")

    conn = init_database(db_path)

    total_chunks = 0
    successful_works = []
    failed_works = []

    for i, work_meta in enumerate(works, 1):
        work_id = work_meta["work_id"]
        work_title = work_meta["work"]
        print(f"[{i:02d}/{len(works):02d}] Ingesting {work_id:15} | {work_title}...")
        try:
            chunks = build_chunks_for_work(work_meta, raw_dir, force_download=force_download)
            if not chunks:
                print(f"  [WARN] Zero chunks produced for {work_id}")
                failed_works.append({"work_id": work_id, "error": "Zero chunks produced"})
                continue

            insert_chunks(conn, chunks)
            total_chunks += len(chunks)
            successful_works.append({
                "work_id": work_id,
                "work": work_title,
                "chunks": len(chunks),
                "checksum": work_meta.get("checksum_sha256", "")
            })
            print(f"  [DONE] Inserted {len(chunks)} chunks (e.g. {chunks[0]['chunk_id']})")
        except Exception as e:
            print(f"  [ERROR] Failed to ingest {work_id}: {e}")
            failed_works.append({"work_id": work_id, "error": str(e)})

    # Update manifest with checksums for exact reproducibility
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, ensure_ascii=False, indent=2)

    # Verify FTS count
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM chunks;")
    master_count = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM chunks_fts;")
    fts_count = cur.fetchone()[0]
    conn.close()

    print("\n" + "=" * 70)
    print("INGESTION & INDEXING SUMMARY")
    print("=" * 70)
    print(f"Works Ingested:   {len(successful_works)} / {len(works)}")
    print(f"Works Failed:     {len(failed_works)}")
    print(f"Total Chunks:     {master_count}")
    print(f"FTS5 Index Rows:  {fts_count}")
    print(f"Index Parity:     {'MATCH' if master_count == fts_count else 'MISMATCH'}")
    print(f"Database File:    {db_path} ({db_path.stat().st_size / (1024*1024):.2f} MB)")
    print("=" * 70)

    return {
        "status": "SUCCESS" if not failed_works else "PARTIAL",
        "works_count": len(successful_works),
        "failed_count": len(failed_works),
        "total_chunks": master_count,
        "fts_count": fts_count,
        "successful_works": successful_works,
        "failed_works": failed_works,
        "db_path": str(db_path),
    }


def main():
    parser = argparse.ArgumentParser(description="Build Project Madurai Exact Retrieval SQLite FTS5 Index")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help="Path to manifest.json")
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR, help="Path to raw HTML directory")
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH, help="Path to output SQLite database")
    parser.add_argument("--force-download", action="store_true", help="Force re-download of source files")
    parser.add_argument("--limit-works", type=int, default=None, help="Limit number of works to ingest")

    args = parser.parse_args()
    summary = build_madurai_index(
        manifest_path=args.manifest,
        raw_dir=args.raw_dir,
        db_path=args.db_path,
        force_download=args.force_download,
        limit_works=args.limit_works
    )
    if summary["failed_count"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
