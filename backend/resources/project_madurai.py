"""
Project Madurai Exact Retrieval Adapter for SOL AI.

Deterministic exact token lookup adapter querying the canonical Project Madurai SQLite
database (data/processed/madurai_exact.db) using SQLite FTS5 full-text indexing.

Conforms to ResourceAdapter contract.
Emits standard Evidence objects with evidence_type='literary_context' and source='Project Madurai'.
Thread-safe for Django concurrent workers; pushes LIMIT 25 and deterministic ORDER BY to SQL.
"""

import re
import sqlite3
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

from backend.schemas.evidence import Evidence
from backend.resources.base import ResourceAdapter

logger = logging.getLogger(__name__)


def sanitize_fts_query(token: str) -> str:
    """
    Sanitize raw query input for SQLite FTS5 exact MATCH.
    Strips FTS control characters (*, ^, :, {, }, (, ), [, ], +, -, ~),
    escapes internal double quotes by doubling them, and wraps the result in
    double quotes to enforce exact whole-token or phrase matching.
    """
    if not token or not token.strip():
        return '""'
    # Strip FTS5 operators and control syntax
    cleaned = re.sub(r'[\*\^\:\{\}\(\)\[\]\+\-\~]', ' ', token)
    cleaned = ' '.join(cleaned.split())
    # Escape existing double quotes
    cleaned = cleaned.replace('"', '""')
    if not cleaned:
        return '""'
    return f'"{cleaned}"'


class ProjectMaduraiExactAdapter(ResourceAdapter):
    """
    Resource adapter for deterministic exact retrieval across the Project Madurai corpus.
    Queries an SQLite FTS5 index configured with Tamil-aware tokenization preserving diacritics.
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize Project Madurai exact adapter.
        
        :param db_path: Optional path to madurai_exact.db. Defaults to data/processed/madurai_exact.db.
        """
        if db_path is None:
            project_root = Path(__file__).resolve().parents[2]
            self.db_path = project_root / "data" / "processed" / "madurai_exact.db"
        else:
            self.db_path = Path(db_path)

    def _get_connection(self) -> sqlite3.Connection:
        """
        Create a thread-safe connection to the SQLite index.
        Uses WAL mode and Row factory. Connection is short-lived per lookup.
        """
        conn = sqlite3.connect(str(self.db_path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        return conn

    def lookup(self, query: str, lemma: Optional[str] = None) -> List[Evidence]:
        """
        Perform exact token lookup in the Project Madurai corpus.
        
        :param query: Tamil surface token or phrase to look up.
        :param lemma: Optional candidate lemma provided by the caller/pipeline.
                      NEVER fabricated by the adapter itself.
        :return: List of Evidence objects representing matching literary stanzas.
        """
        clean_query = query.strip() if query else ""
        if not clean_query:
            return []

        if not self.db_path.exists():
            logger.warning("Project Madurai database file not found at: %s", self.db_path)
            return [
                Evidence(
                    surface=clean_query,
                    lemma=lemma,
                    source="Project Madurai",
                    evidence_type="literary_context",
                    metadata={
                        "error": f"Database file not found: {self.db_path}",
                        "status": "ERROR"
                    }
                )
            ]

        sanitized_term = sanitize_fts_query(clean_query)
        if sanitized_term == '""':
            return [
                Evidence(
                    surface=clean_query,
                    lemma=lemma,
                    source="Project Madurai",
                    evidence_type="literary_context",
                    metadata={"status": "NOT_FOUND"}
                )
            ]

        sql = """
        SELECT c.*
        FROM chunks c
        JOIN chunks_fts fts ON c.rowid = fts.rowid
        WHERE chunks_fts MATCH ?
        ORDER BY c.chunk_id ASC
        LIMIT 25;
        """

        try:
            with self._get_connection() as conn:
                cur = conn.cursor()
                rows = cur.execute(sql, (sanitized_term,)).fetchall()
        except Exception as e:
            logger.error("Project Madurai query error for %r: %s", clean_query, e)
            return [
                Evidence(
                    surface=clean_query,
                    lemma=lemma,
                    source="Project Madurai",
                    evidence_type="literary_context",
                    metadata={
                        "error": str(e),
                        "status": "ERROR"
                    }
                )
            ]

        if not rows:
            return [
                Evidence(
                    surface=clean_query,
                    lemma=lemma,
                    source="Project Madurai",
                    evidence_type="literary_context",
                    metadata={"status": "NOT_FOUND"}
                )
            ]

        results: List[Evidence] = []
        for r in rows:
            verse_val = (
                str(r["verse_number"]) if r["verse_number"] is not None
                else (str(r["stanza_number"]) if r["stanza_number"] is not None else None)
            )

            results.append(
                Evidence(
                    surface=clean_query,
                    lemma=lemma,  # Preserves caller-supplied lemma or None. Never fabricated.
                    source="Project Madurai",
                    evidence_type="literary_context",
                    passage=r["original_text"],
                    work=r["work"],
                    author=r["author"],
                    period=r["period"],
                    genre=r["genre"],
                    verse=verse_val,
                    source_url=r["source_url"],
                    source_id=r["chunk_id"],
                    metadata={
                        "chunk_id": r["chunk_id"],
                        "corpus_version": r["corpus_version"],
                        "release_no": r["release_no"],
                        "canto": r["canto"],
                        "chapter": r["chapter"],
                        "stanza_number": r["stanza_number"],
                        "verse_number": verse_val,
                        "line_range": r["line_range"],
                        "file_path": r["file_path"],
                        "retrieval_method": "exact",
                        "status": "FOUND"
                    }
                )
            )

        return results
