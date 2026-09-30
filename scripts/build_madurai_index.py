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
    Clean HTML markup from Project Madurai e-texts while preserving line breaks.
    """
    html_str = html_str.replace('&nbsp;', ' ')
    html_str = html_str.replace('&copy;', '(c)')
    html_str = html_str.replace('&amp;', '&')
    html_str = html_str.replace('&quot;', '"')
    html_str = html_str.replace('&lt;', '<')
    html_str = html_str.replace('&gt;', '>')
    # Turn <br> into \n
    text = re.sub(r'<br\s*/?>', '\n', html_str, flags=re.I)
    # Turn paragraph and header tags into \n\n
    text = re.sub(r'</?(?:p|h[1-6]|tr|div|center|font|ul|li)[^>]*>', '\n\n', text, flags=re.I)
    # Strip remaining HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)
    return text


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
    (e.g., PM0002 containing Aathichudi, Konrai Vendhan, Moodhurai, Nalvazhi).
    """
    # Specific section markers for bundled releases
    section_map = {
        "AATHI": ("1.  ஆத்திசூடி", "2.  கொன்றை வேந்தன்"),
        "KONRAI": ("2.  கொன்றை வேந்தன்", "3.  மூதுரை"),
        "MOODHURAI": ("3.  மூதுரை", "4.  நல்வழி"),
        "NALVAZHI": ("4.  நல்வழி", None),
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


def parse_tirukkural(
    work_meta: Dict[str, Any],
    clean_text: str,
    file_rel_path: str
) -> List[Dict[str, Any]]:
    """
    Parse Tirukkural couplets into 1,330 distinct canonical chunks.
    Preserves couplet couplet numbers 1..1330.
    """
    work_id = work_meta["work_id"]
    work_title = work_meta["work"]
    author = work_meta.get("author", "திருவள்ளுவர்")
    period = work_meta.get("period", "Post-Sangam (Didactic)")
    genre = work_meta.get("genre", "Didactic Couplets")
    release_no = work_meta.get("release_no", "PM0001")
    source_url = work_meta.get("source_url")

    lines = clean_text.splitlines()
    all_lines: List[Tuple[str, Optional[str], Optional[str]]] = []
    current_chap: Optional[str] = "கடவுள் வாழ்த்து"
    current_sec: Optional[str] = "அறத்துப்பால்"

    for raw_l in lines:
        l = raw_l.strip()
        if not l:
            continue
        # Track chapter
        chap_m = re.search(r'\d+\.\d+\.\d+\s*([\u0B80-\u0BFF\s]+)', l)
        if chap_m:
            current_chap = chap_m.group(1).strip()
            continue
        # Track section / paal
        sec_m = re.search(r'\d+\.\s*([\u0B80-\u0BFF\s]+பால்)', l)
        if sec_m:
            current_sec = sec_m.group(1).strip()
            continue

        # Skip isolated header titles
        if l in ["அறத்துப்பால்", "பொருட்பால்", "காமத்துப்பால்", "திருக்குறள்"]:
            continue

        # Skip English and volunteer boilerplate
        if "Project Madurai" in l or "Etext" in l or "Kalyanasundaram" in l:
            continue

        all_lines.append((l, current_chap, current_sec))

    chunks = []
    st_num = 1
    idx = 0
    total_lines = len(all_lines)

    while idx < total_lines and st_num <= 1330:
        l1, chap1, sec1 = all_lines[idx]
        if idx + 1 < total_lines:
            l2, chap2, sec2 = all_lines[idx + 1]
            idx += 2
        else:
            l2 = ""
            idx += 1

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
                "canto": sec1,
                "chapter": chap1,
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
    canonical stanza/verse chunks.
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
        if tamil_chars < 12:
            continue

        # Skip PM copyright and volunteer acknowledgments
        if "Project Madurai" in b and ("initiative" in b or "free" in b or "prepared" in b or "Etext" in b):
            continue
        if "இம்மின்னுரை" in b or "மின்னூலாக்கம்" in b or "உரிமை - பொதுக் களம்" in b:
            continue

        lines = [l.strip() for l in b.splitlines() if l.strip()]
        if not lines:
            continue

        # Check for canto or chapter title (short block with header keywords)
        if len(lines) == 1 and len(lines[0]) < 60:
            header_line = lines[0]
            if any(k in header_line for k in ["காண்டம்", "காதை", "படலம்", "பதிகம்", "இயல்", "அதிகாரம்", "திருமுறை", "பகுதி"]):
                current_canto = header_line
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
        if len(numbered_lines) >= 2 and len(numbered_lines) == len(lines):
            for nl in lines:
                m = re.match(r'^(\d+)\.\s*(.*)', nl)
                if not m:
                    continue
                v_num, v_text = m.group(1), m.group(2).strip()
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

        # Check for verse numbering at start of stanza (e.g. "3. குறிஞ்சி - தலைவி கூற்று" or "4.")
        verse_num = str(st_num)
        canto_info = current_canto
        if lines and re.match(r'^\d+\.', lines[0]):
            header_match = re.match(r'^(\d+)\.\s*(.*)', lines[0])
            if header_match:
                verse_num = header_match.group(1)
                sub_label = header_match.group(2).strip()
                if sub_label:
                    canto_info = f"{current_canto} - {sub_label}" if current_canto else sub_label
            lines = lines[1:]

        if not lines:
            continue

        orig_text = '\n'.join(lines)
        norm_text = normalize_tamil_text(' '.join(lines))

        if len(norm_text) < 10:
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
