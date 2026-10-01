"""
Project Madurai Semantic Retrieval Adapter for SOL AI.

Dense vector retrieval adapter performing cosine similarity search over the permanent
Project Madurai vector matrix (data/processed/madurai_semantic_vectors.npy) and metadata
(data/processed/madurai_semantic_meta.json).

Conforms strictly to the ResourceAdapter contract.
Emits standard Evidence objects with evidence_type='literary_context',
source='Project Madurai', and metadata['retrieval_mode']='semantic'.

Architectural Principles:
- Lazy Process-Local Lifecycle: Pinned model, vectors, and metadata are loaded upon first lookup.
- Pinned E5-small Model: intfloat/multilingual-e5-small @ revision 614241f622f53c4eeff9890bdc4f31cfecc418b3.
- Query Prefix: Always uses 'query: {user_query}'.
- Deterministic Ordering: Ranked by descending similarity, ties broken by chunk_id ascending.
- Defensive Artifact Validation: Validates shape, dtype, norms, alignment, and schema before use.
- Safe Failure: Fail closed and return safe ERROR evidence if artifacts or encoding fail,
  ensuring deterministic exact retrieval is NEVER disrupted.
"""

import json
import logging
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer

from backend.resources.base import ResourceAdapter
from backend.schemas.evidence import Evidence

logger = logging.getLogger(__name__)

# Pinned Model Configuration
PINNED_MODEL_ID = "intfloat/multilingual-e5-small"
PINNED_MODEL_REVISION = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
PINNED_EMBEDDING_DIM = 384
MAX_SEQUENCE_LENGTH = 512
QUERY_PREFIX = "query: "

# Process-local model cache: (model_id, revision, device_str) -> (tokenizer, model)
_MODEL_CACHE: Dict[Tuple[str, str, str], Tuple[AutoTokenizer, AutoModel]] = {}
_CACHE_LOCK = threading.Lock()


class SemanticArtifactError(Exception):
    """Raised when permanent semantic vector artifacts or metadata fail validation."""
    pass


def _get_shared_model(
    model_id: str,
    revision: str,
    num_threads: int,
    target_device: Optional[str] = None,
) -> Tuple[Tuple[AutoTokenizer, AutoModel], torch.device]:
    """
    Retrieve or load the pinned model and tokenizer from process-local cache.
    Thread-safe.
    """
    device_str = target_device or ("cuda" if torch.cuda.is_available() else "cpu")
    key = (model_id, revision, device_str)

    with _CACHE_LOCK:
        if key in _MODEL_CACHE:
            return _MODEL_CACHE[key], torch.device(device_str)

        if num_threads > 0:
            torch.set_num_threads(num_threads)

        device = torch.device(device_str)
        logger.info(
            "Loading pinned E5 model %s (rev: %s) on %s...",
            model_id,
            revision[:8],
            device,
        )
        tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision)
        model = AutoModel.from_pretrained(model_id, revision=revision)
        model.to(device)
        model.eval()

        _MODEL_CACHE[key] = (tokenizer, model)
        return (tokenizer, model), device


class ProjectMaduraiSemanticAdapter(ResourceAdapter):
    """
    Resource adapter for dense semantic retrieval across the Project Madurai corpus.
    Queries the permanent float32 L2-normalized vector matrix via dot-product cosine similarity.
    """

    def __init__(
        self,
        vectors_path: Optional[Path] = None,
        metadata_path: Optional[Path] = None,
        db_path: Optional[Path] = None,
        model_id: str = PINNED_MODEL_ID,
        model_revision: str = PINNED_MODEL_REVISION,
        dimension: int = PINNED_EMBEDDING_DIM,
        num_threads: int = 4,
        device: Optional[str] = None,
    ):
        """
        Initialize Project Madurai semantic adapter.
        Does NOT load vectors or model eagerly; initialization is lazy.
        
        :param vectors_path: Path to madurai_semantic_vectors.npy.
        :param metadata_path: Path to madurai_semantic_meta.json.
        :param db_path: Path to madurai_exact.db for enriching candidate passages.
        :param model_id: Pinned HF model ID.
        :param model_revision: Pinned git commit revision.
        :param dimension: Expected vector dimension (384).
        :param num_threads: Torch thread limit.
        :param device: Optional target device override ('cpu', 'cuda').
        """
        project_root = Path(__file__).resolve().parents[2]
        self.vectors_path = Path(vectors_path) if vectors_path else project_root / "data" / "processed" / "madurai_semantic_vectors.npy"
        self.metadata_path = Path(metadata_path) if metadata_path else project_root / "data" / "processed" / "madurai_semantic_meta.json"
        self.db_path = Path(db_path) if db_path else project_root / "data" / "processed" / "madurai_exact.db"

        self.model_id = model_id
        self.model_revision = model_revision
        self.dimension = dimension
        self.num_threads = num_threads
        self._target_device = device

        self.source_name = "Project Madurai"
        self.evidence_type = "literary_context"

        # Lazy state (populated on first lookup or explicit ensure_loaded())
        self._is_loaded = False
        self._load_lock = threading.Lock()
        self._vectors: Optional[np.ndarray] = None
        self._metadata: Optional[Dict[str, Any]] = None
        self._metadata_items: Optional[List[Dict[str, Any]]] = None
        self._chunk_ids: Optional[np.ndarray] = None
        self._corpus_fingerprint: Optional[str] = None
        self._database_sha256: Optional[str] = None

        self._tokenizer = None
        self._model = None
        self._device = None

    @property
    def is_loaded(self) -> bool:
        """Return True if model and vector matrix have been loaded."""
        return self._is_loaded

    @property
    def corpus_fingerprint(self) -> Optional[str]:
        """Return the database/build fingerprint recorded in metadata."""
        return self._corpus_fingerprint

    @property
    def database_sha256(self) -> Optional[str]:
        """Return the canonical database SHA-256 recorded in metadata."""
        return self._database_sha256

    @property
    def vector_count(self) -> int:
        """Return the count of eligible semantic vectors."""
        return len(self._metadata_items) if self._metadata_items is not None else 0

    def validate_artifacts(self) -> None:
        """
        Validate vector file and metadata JSON against specifications.
        Raises SemanticArtifactError or FileNotFoundError if invalid.
        """
        if not self.vectors_path.exists():
            raise FileNotFoundError(f"Vector matrix file not found: {self.vectors_path}")
        if not self.metadata_path.exists():
            raise FileNotFoundError(f"Metadata file not found: {self.metadata_path}")

        try:
            with open(self.metadata_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception as e:
            raise SemanticArtifactError(f"Failed to parse metadata JSON: {e}") from e

        try:
            with open(self.vectors_path, "rb") as f:
                vectors = np.load(f)
        except Exception as e:
            raise SemanticArtifactError(f"Failed to load vector matrix: {e}") from e

        self._validate_artifacts_data(vectors, meta)

    def _validate_artifacts_data(self, vectors: np.ndarray, meta: Dict[str, Any]) -> None:
        """Internal validation of in-memory vector array and metadata dict."""
        if not isinstance(vectors, np.ndarray):
            raise SemanticArtifactError(f"Vectors must be numpy.ndarray, got {type(vectors)}")
        if vectors.dtype != np.float32:
            raise SemanticArtifactError(f"Vector matrix dtype must be float32, got {vectors.dtype}")
        if vectors.ndim != 2:
            raise SemanticArtifactError(f"Vector matrix must be 2D, got ndim={vectors.ndim}")
        if vectors.shape[1] != self.dimension:
            raise SemanticArtifactError(
                f"Vector dimension mismatch: expected {self.dimension}, got {vectors.shape[1]}"
            )
        if np.isnan(vectors).any():
            raise SemanticArtifactError("Vector matrix contains NaN values")
        if np.isinf(vectors).any():
            raise SemanticArtifactError("Vector matrix contains Inf values")

        # Metadata validation
        if not isinstance(meta, dict):
            raise SemanticArtifactError("Metadata root must be a JSON object")
        if "schema_version" not in meta:
            raise SemanticArtifactError("Metadata missing 'schema_version'")

        emb = meta.get("embedding")
        if not isinstance(emb, dict):
            raise SemanticArtifactError("Metadata missing 'embedding' section")
        if emb.get("model_id") != self.model_id:
            raise SemanticArtifactError(
                f"Model ID mismatch in metadata: expected {self.model_id}, got {emb.get('model_id')}"
            )
        if emb.get("model_revision") != self.model_revision:
            raise SemanticArtifactError(
                f"Model revision mismatch in metadata: expected {self.model_revision}, got {emb.get('model_revision')}"
            )
        if emb.get("dimension") != self.dimension:
            raise SemanticArtifactError(
                f"Embedding dimension mismatch in metadata: expected {self.dimension}, got {emb.get('dimension')}"
            )

        items = meta.get("items")
        if not isinstance(items, list):
            raise SemanticArtifactError("Metadata missing 'items' list")

        if len(items) != vectors.shape[0]:
            raise SemanticArtifactError(
                f"Alignment mismatch: {len(items)} metadata items vs {vectors.shape[0]} vector rows"
            )

        idx_section = meta.get("index")
        if isinstance(idx_section, dict):
            if idx_section.get("vector_count") != vectors.shape[0]:
                raise SemanticArtifactError(
                    f"Index vector_count mismatch: {idx_section.get('vector_count')} != {vectors.shape[0]}"
                )

        seen_chunk_ids = set()
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                raise SemanticArtifactError(f"Metadata item at index {idx} is not an object")
            if item.get("vector_index") != idx:
                raise SemanticArtifactError(
                    f"Metadata item at index {idx} has vector_index {item.get('vector_index')}"
                )
            cid = item.get("chunk_id")
            if not cid:
                raise SemanticArtifactError(f"Metadata item at index {idx} missing chunk_id")
            if cid in seen_chunk_ids:
                raise SemanticArtifactError(f"Duplicate chunk_id in metadata: {cid}")
            seen_chunk_ids.add(cid)

        # Validate vector normalization on representative sample
        sample_indices = np.linspace(0, vectors.shape[0] - 1, min(50, vectors.shape[0]), dtype=int)
        sample_norms = np.linalg.norm(vectors[sample_indices], axis=1)
        if not np.allclose(sample_norms, 1.0, atol=1e-3):
            raise SemanticArtifactError(
                f"Vectors not L2 normalized: sample min={np.min(sample_norms):.4f}, max={np.max(sample_norms):.4f}"
            )

    def ensure_loaded(self) -> None:
        """
        Lazily load and validate vectors, metadata, and the pinned E5 model.
        Thread-safe; idempotent.
        """
        if self._is_loaded:
            return

        with self._load_lock:
            if self._is_loaded:
                return

            self.validate_artifacts()

            with open(self.metadata_path, "r", encoding="utf-8") as f:
                self._metadata = json.load(f)

            self._metadata_items = self._metadata["items"]
            self._chunk_ids = np.array([item["chunk_id"] for item in self._metadata_items])
            self._corpus_fingerprint = self._metadata.get("corpus_fingerprint")
            self._database_sha256 = self._metadata.get("corpus", {}).get("database_sha256")

            # Load vectors into memory
            with open(self.vectors_path, "rb") as f:
                self._vectors = np.load(f)

            # Load pinned model and tokenizer
            (self._tokenizer, self._model), self._device = _get_shared_model(
                self.model_id,
                self.model_revision,
                self.num_threads,
                self._target_device,
            )

            self._is_loaded = True
            logger.info(
                "Project Madurai Semantic Adapter loaded: %d vectors, model=%s @ %s",
                self._vectors.shape[0],
                self.model_id,
                self.model_revision[:8],
            )

    @staticmethod
    def _average_pool(last_hidden_states: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        """Mean pooling over token representations respecting attention mask."""
        last_hidden = last_hidden_states.masked_fill(~attention_mask[..., None].bool(), 0.0)
        return last_hidden.sum(dim=1) / attention_mask.sum(dim=1)[..., None]

    def encode_query(self, query: str) -> np.ndarray:
        """
        Encode a single runtime query into a 384-dimensional L2-normalized float32 vector.
        Prefixes query with 'query: ' according to E5 model specification.
        """
        self.ensure_loaded()
        clean = query.strip() if query else ""
        if not clean:
            raise ValueError("Cannot encode empty query")

        prefixed_text = f"{QUERY_PREFIX}{clean}"
        inputs = self._tokenizer(
            [prefixed_text],
            max_length=MAX_SEQUENCE_LENGTH,
            padding=True,
            truncation=True,
            return_tensors="pt",
        )
        inputs = {k: v.to(self._device) for k, v in inputs.items()}

        with torch.inference_mode():
            outputs = self._model(**inputs)
            embeddings = self._average_pool(outputs.last_hidden_state, inputs["attention_mask"])
            embeddings = F.normalize(embeddings, p=2, dim=1)

        vec = embeddings.cpu().float().numpy()[0]
        if vec.shape != (self.dimension,):
            raise ValueError(f"Expected query vector shape ({self.dimension},), got {vec.shape}")
        if np.isnan(vec).any() or np.isinf(vec).any():
            raise ValueError("Query vector contains NaN or Inf")

        return vec

    def _get_db_connection(self) -> sqlite3.Connection:
        """Create read-only connection to exact Project Madurai database."""
        conn = sqlite3.connect(f"file:{self.db_path.as_posix()}?mode=ro", uri=True, timeout=5.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _fetch_db_rows(self, chunk_ids: List[str]) -> Dict[str, sqlite3.Row]:
        """Fetch canonical rows from SQLite database for given chunk_ids."""
        if not self.db_path or not self.db_path.exists() or not chunk_ids:
            return {}

        placeholders = ",".join("?" for _ in chunk_ids)
        sql = f"SELECT * FROM chunks WHERE chunk_id IN ({placeholders});"
        try:
            with self._get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute("PRAGMA query_only = ON;")
                rows = cur.execute(sql, chunk_ids).fetchall()
                return {r["chunk_id"]: r for r in rows}
        except Exception as e:
            logger.warning("Failed to fetch database rows from %s: %s", self.db_path, e)
            return {}

    def _build_evidence_list(
        self,
        clean_query: str,
        lemma: Optional[str],
        top_indices: np.ndarray,
        scores: np.ndarray,
    ) -> List[Evidence]:
        """Convert top indices and similarity scores into standard Evidence objects."""
        top_cids = [self._metadata_items[idx]["chunk_id"] for idx in top_indices]
        db_rows = self._fetch_db_rows(top_cids)

        evidence_list: List[Evidence] = []
        for idx in top_indices:
            item = self._metadata_items[idx]
            cid = item["chunk_id"]
            score = float(scores[idx])
            db_row = db_rows.get(cid)

            passage = db_row["original_text"] if db_row else None

            verse_val = None
            if db_row:
                if db_row["verse_number"] is not None:
                    verse_val = str(db_row["verse_number"])
                elif db_row["stanza_number"] is not None:
                    verse_val = str(db_row["stanza_number"])
            elif item.get("stanza_number") is not None:
                verse_val = str(item["stanza_number"])

            work = (db_row["work"] if db_row else None) or item.get("work_name")
            author = (db_row["author"] if db_row else None) or item.get("author")
            period = (db_row["period"] if db_row else None) or item.get("period")
            genre = (db_row["genre"] if db_row else None) or item.get("genre")
            source_url = (db_row["source_url"] if db_row else None) or item.get("source_url")
            line_range = db_row["line_range"] if db_row else None
            file_path = db_row["file_path"] if db_row else None
            corpus_version = db_row["corpus_version"] if db_row else None
            release_no = (db_row["release_no"] if db_row else None) or item.get("work_id")
            canto = (db_row["canto"] if db_row else None) or item.get("section")
            chapter = (db_row["chapter"] if db_row else None) or item.get("sub_section")

            ev = Evidence(
                surface=clean_query,
                lemma=lemma,  # Preserves caller-supplied lemma or None. Never fabricated.
                source=self.source_name,
                evidence_type=self.evidence_type,
                passage=passage,
                work=work,
                author=author,
                period=period,
                genre=genre,
                verse=verse_val,
                source_url=source_url,
                source_id=cid,
                metadata={
                    "chunk_id": cid,
                    "vector_index": int(item.get("vector_index", idx)),
                    "similarity_score": round(score, 6),
                    "retrieval_mode": "semantic",
                    "retrieval_method": "semantic",
                    "status": "FOUND",
                    "work_id": item.get("work_id"),
                    "section": item.get("section"),
                    "sub_section": item.get("sub_section"),
                    "stanza_number": item.get("stanza_number"),
                    "verse_number": verse_val,
                    "line_range": line_range,
                    "file_path": file_path,
                    "corpus_version": corpus_version,
                    "release_no": release_no,
                    "canto": canto,
                    "chapter": chapter,
                }
            )
            evidence_list.append(ev)

        return evidence_list

    def lookup(
        self,
        query: str,
        lemma: Optional[str] = None,
        top_k: int = 10,
    ) -> List[Evidence]:
        """
        Perform dense semantic lookup in the Project Madurai corpus.
        
        :param query: Tamil surface query string.
        :param lemma: Optional candidate lemma provided by caller/pipeline.
                      NEVER fabricated by the adapter itself.
        :param top_k: Number of top semantic candidates to return (default: 10).
        :return: List of Evidence objects representing matching literary passages.
        """
        clean_query = query.strip() if query else ""
        if not clean_query:
            return []

        if top_k <= 0:
            return []

        try:
            self.ensure_loaded()
            query_vector = self.encode_query(clean_query)

            # Cosine similarity via inner product on normalized vectors
            scores = self._vectors @ query_vector

            # Deterministic top-k ordering:
            # Primary: descending similarity (-scores)
            # Secondary: ascending chunk_id (lexicographic)
            order = np.lexsort((self._chunk_ids, -scores))
            k = min(top_k, len(order))
            top_indices = order[:k]

            return self._build_evidence_list(clean_query, lemma, top_indices, scores)

        except Exception as e:
            logger.error("Project Madurai Semantic lookup error for %r: %s", clean_query, e)
            return [
                Evidence(
                    surface=clean_query,
                    lemma=lemma,
                    source=self.source_name,
                    evidence_type=self.evidence_type,
                    metadata={
                        "error": str(e),
                        "status": "ERROR",
                        "retrieval_mode": "semantic",
                    }
                )
            ]
