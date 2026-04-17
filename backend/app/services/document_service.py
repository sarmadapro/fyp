"""
Document processing service.
Handles file upload, text extraction, chunking, and FAISS indexing.
"""

import os
import shutil
import logging
from pathlib import Path

import fitz  # PyMuPDF
from docx import Document as DocxDocument
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

from app.core.config import settings

logger = logging.getLogger(__name__)


# ─── Single-User / Legacy Document Service ──────────────────────────

class DocumentService:
    """Manages document upload, processing, and vector indexing (single-user mode)."""

    def __init__(self):
        self._embeddings = None
        self._vector_store: FAISS | None = None
        self._current_doc_name: str | None = None
        self._current_doc_type: str | None = None
        self._chunk_count: int = 0
        self._domain_summary: str = ""

        self._text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " ", ""],
        )

        self._try_load_existing_index()

    @property
    def embeddings(self) -> HuggingFaceEmbeddings:
        """Lazy-load embedding model to avoid startup delay."""
        if self._embeddings is None:
            logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
            self._embeddings = HuggingFaceEmbeddings(
                model_name=settings.EMBEDDING_MODEL,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
            logger.info("Embedding model loaded successfully.")
        return self._embeddings

    @property
    def vector_store(self) -> FAISS | None:
        return self._vector_store

    @property
    def has_document(self) -> bool:
        return self._vector_store is not None

    @property
    def document_name(self) -> str | None:
        return self._current_doc_name

    @property
    def document_type(self) -> str | None:
        return self._current_doc_type

    @property
    def chunk_count(self) -> int:
        return self._chunk_count

    @property
    def domain_summary(self) -> str:
        return self._domain_summary or ""

    # ------------------------------------------------------------------ #
    #  Domain summary (built once at index time, cached to disk)
    # ------------------------------------------------------------------ #

    def _build_domain_summary(self, chunks: list[str], file_name: str) -> str:
        """
        Produce a short (1–2 sentence) description of what this document is
        about, so the chat LLM can orient itself without re-probing FAISS.
        Tries a cheap LLM call; falls back to a deterministic excerpt on any
        failure so RAG keeps working offline.
        """
        sample = "\n\n".join(chunks[:3])[:2000].strip()
        if not sample:
            return f"Document: {file_name}"

        try:
            # Lazy import to avoid circular dependency with chat_service.
            from app.services.chat_service import _get_rewriter_llm
            llm = _get_rewriter_llm()
            prompt = (
                "In one or two short sentences, describe the subject/domain of "
                "the following document excerpt. No preamble, no markdown.\n\n"
                f"FILENAME: {file_name}\n\nEXCERPT:\n{sample}"
            )
            result = llm.invoke(prompt)
            summary = (getattr(result, "content", None) or str(result)).strip()
            if summary:
                return summary
        except Exception as e:
            logger.warning(f"Domain summary LLM failed, using fallback: {e}")

        # Deterministic fallback: filename + truncated opening.
        opener = sample[:400].replace("\n", " ").strip()
        return f"Document: {file_name}. Opening: {opener}"

    # ------------------------------------------------------------------ #
    #  Text Extraction
    # ------------------------------------------------------------------ #

    def _extract_text_from_pdf(self, file_path: Path) -> str:
        doc = fitz.open(str(file_path))
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text

    def _extract_text_from_docx(self, file_path: Path) -> str:
        doc = DocxDocument(str(file_path))
        return "\n".join(para.text for para in doc.paragraphs if para.text.strip())

    def _extract_text_from_txt(self, file_path: Path) -> str:
        return file_path.read_text(encoding="utf-8")

    def extract_text(self, file_path: Path, file_type: str) -> str:
        extractors = {
            ".pdf":  self._extract_text_from_pdf,
            ".docx": self._extract_text_from_docx,
            ".txt":  self._extract_text_from_txt,
        }
        extractor = extractors.get(file_type)
        if not extractor:
            raise ValueError(f"Unsupported file type: {file_type}")
        text = extractor(file_path)
        if not text.strip():
            raise ValueError("No text could be extracted from the document.")
        logger.info(f"Extracted {len(text)} characters from {file_path.name}")
        return text

    # ------------------------------------------------------------------ #
    #  Indexing
    # ------------------------------------------------------------------ #

    def process_and_index(self, file_path: Path, file_name: str, file_type: str) -> int:
        text   = self.extract_text(file_path, file_type)
        chunks = self._text_splitter.split_text(text)
        if not chunks:
            raise ValueError("Document produced no text chunks.")

        logger.info(f"Created {len(chunks)} chunks from {file_name}")

        self._vector_store = FAISS.from_texts(
            texts=chunks,
            embedding=self.embeddings,
            metadatas=[{"source": file_name, "chunk_index": i} for i, _ in enumerate(chunks)],
        )
        self._vector_store.save_local(str(settings.INDEX_DIR))

        self._current_doc_name = file_name
        self._current_doc_type = file_type
        self._chunk_count = len(chunks)
        self._domain_summary = self._build_domain_summary(chunks, file_name)

        meta_path = settings.INDEX_DIR / "doc_meta.txt"
        meta_path.write_text(f"{file_name}\n{file_type}\n{len(chunks)}", encoding="utf-8")
        (settings.INDEX_DIR / "domain_summary.txt").write_text(
            self._domain_summary, encoding="utf-8"
        )

        logger.info(f"FAISS index saved with {len(chunks)} vectors.")
        return len(chunks)

    def delete_document(self):
        self._vector_store = None
        self._current_doc_name = None
        self._current_doc_type = None
        self._chunk_count = 0
        self._domain_summary = ""

        for f in settings.UPLOAD_DIR.iterdir():
            if f.name != ".gitkeep":
                f.unlink() if f.is_file() else shutil.rmtree(f)

        for f in settings.INDEX_DIR.iterdir():
            if f.name != ".gitkeep":
                f.unlink() if f.is_file() else shutil.rmtree(f)

        logger.info("Document and index deleted.")

    def _try_load_existing_index(self):
        index_path = settings.INDEX_DIR / "index.faiss"
        meta_path  = settings.INDEX_DIR / "doc_meta.txt"
        if index_path.exists() and meta_path.exists():
            try:
                self._vector_store = FAISS.load_local(
                    str(settings.INDEX_DIR), self.embeddings,
                    allow_dangerous_deserialization=True,
                )
                meta = meta_path.read_text(encoding="utf-8").strip().split("\n")
                self._current_doc_name = meta[0]
                self._current_doc_type = meta[1]
                self._chunk_count = int(meta[2])
                summary_path = settings.INDEX_DIR / "domain_summary.txt"
                if summary_path.exists():
                    self._domain_summary = summary_path.read_text(encoding="utf-8").strip()
                logger.info(f"Loaded existing index for: {self._current_doc_name}")
            except Exception as e:
                logger.warning(f"Failed to load existing index: {e}")

    def similarity_search(self, query: str, top_k: int | None = None) -> list[dict]:
        if not self._vector_store:
            return []
        k = top_k or settings.RETRIEVAL_TOP_K
        results = self._vector_store.similarity_search_with_score(query, k=k)
        return [
            {"content": doc.page_content, "metadata": doc.metadata, "score": float(score)}
            for doc, score in results
        ]


# Singleton instance (backward-compat for single-user mode)
document_service = DocumentService()


# ─── Multi-Tenant Document Service (SaaS) ───────────────────────────

class ClientDocumentService(DocumentService):
    """
    Per-client document service with isolated storage.
    Each client's data lives in data/clients/{client_id}/

    STRICT SINGLE-DOCUMENT POLICY:
    Only one document is allowed per client at any time.
    Uploading a new document fully overwrites the previous FAISS index.

    The class-level cache (_instances) keeps one loaded instance per client in
    memory so FAISS indices are not re-read from disk on every HTTP request.
    Call ClientDocumentService.invalidate(client_id) whenever a document is
    uploaded or deleted so the next request gets a fresh instance.
    """

    _shared_embeddings = None  # One embedding model shared across all clients
    _instances: dict[str, "ClientDocumentService"] = {}  # in-memory service cache

    # ── Cache helpers ──────────────────────────────────────────────────

    @classmethod
    def get_or_create(cls, client_id: str) -> "ClientDocumentService":
        """Return a cached instance, loading from disk only on first access."""
        if client_id not in cls._instances:
            cls._instances[client_id] = cls(client_id)
        return cls._instances[client_id]

    @classmethod
    def invalidate(cls, client_id: str) -> None:
        """Drop the cached instance so the next call reloads from disk."""
        cls._instances.pop(client_id, None)
        logger.info(f"[ClientDocumentService] Cache invalidated for client {client_id}")

    def __init__(self, client_id: str):
        self.client_id = client_id

        base_dir = Path(os.getenv("CLIENT_DATA_DIR", "./data/clients"))
        self._client_dir = base_dir / client_id
        self._upload_dir = self._client_dir / "uploads"
        self._index_dir  = self._client_dir / "indices"

        self._upload_dir.mkdir(parents=True, exist_ok=True)
        self._index_dir.mkdir(parents=True, exist_ok=True)

        self._text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " ", ""],
        )

        self._embeddings       = None
        self._vector_store     = None
        self._current_doc_name = None
        self._current_doc_type = None
        self._chunk_count      = 0
        self._domain_summary   = ""

        self._try_load_existing_index()

    # ── Shared embedding ───────────────────────────────────────────────

    @property
    def embeddings(self) -> HuggingFaceEmbeddings:
        if ClientDocumentService._shared_embeddings is None:
            logger.info(f"Loading shared embedding model: {settings.EMBEDDING_MODEL}")
            ClientDocumentService._shared_embeddings = HuggingFaceEmbeddings(
                model_name=settings.EMBEDDING_MODEL,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
            logger.info("Shared embedding model loaded.")
        return ClientDocumentService._shared_embeddings

    # ── Directory helpers ──────────────────────────────────────────────

    @property
    def upload_dir(self) -> Path:
        return self._upload_dir

    @property
    def index_dir(self) -> Path:
        return self._index_dir

    # ── Indexing (overwrites previous) ────────────────────────────────

    def process_and_index(self, file_path: Path, file_name: str, file_type: str) -> int:
        """
        Extract, chunk, embed, and save a new FAISS index.
        Any previously stored index and upload is fully replaced.
        """
        # 1. Wipe the old index first so we start fresh
        self._wipe_index()

        text   = self.extract_text(file_path, file_type)
        chunks = self._text_splitter.split_text(text)
        if not chunks:
            raise ValueError("Document produced no text chunks.")

        logger.info(f"[Client {self.client_id}] {len(chunks)} chunks from '{file_name}'")

        self._vector_store = FAISS.from_texts(
            texts=chunks,
            embedding=self.embeddings,
            metadatas=[{"source": file_name, "chunk_index": i} for i, _ in enumerate(chunks)],
        )
        self._vector_store.save_local(str(self._index_dir))

        self._current_doc_name = file_name
        self._current_doc_type = file_type
        self._chunk_count      = len(chunks)
        self._domain_summary   = self._build_domain_summary(chunks, file_name)

        (self._index_dir / "doc_meta.txt").write_text(
            f"{file_name}\n{file_type}\n{len(chunks)}", encoding="utf-8"
        )
        (self._index_dir / "domain_summary.txt").write_text(
            self._domain_summary, encoding="utf-8"
        )
        logger.info(f"[Client {self.client_id}] FAISS index saved — {len(chunks)} vectors.")
        return len(chunks)

    # ── Deletion ───────────────────────────────────────────────────────

    def _wipe_index(self):
        """Remove only the FAISS index files (NOT the uploads dir)."""
        for f in self._index_dir.iterdir():
            if f.name != ".gitkeep":
                f.unlink() if f.is_file() else shutil.rmtree(f)

        self._vector_store     = None
        self._current_doc_name = None
        self._current_doc_type = None
        self._chunk_count      = 0
        self._domain_summary   = ""

    def _wipe_uploads(self):
        """Remove all previously uploaded raw files."""
        for f in self._upload_dir.iterdir():
            if f.name != ".gitkeep":
                f.unlink() if f.is_file() else shutil.rmtree(f)

    def delete_document(self):
        """Delete the current document and its index."""
        self._wipe_uploads()
        self._wipe_index()
        # Remove from cache so next request starts fresh
        ClientDocumentService._instances.pop(self.client_id, None)
        logger.info(f"[Client {self.client_id}] Document and index deleted.")

    # ── On-startup index reload ────────────────────────────────────────

    def _try_load_existing_index(self):
        index_path = self._index_dir / "index.faiss"
        meta_path  = self._index_dir / "doc_meta.txt"
        if index_path.exists() and meta_path.exists():
            try:
                self._vector_store = FAISS.load_local(
                    str(self._index_dir), self.embeddings,
                    allow_dangerous_deserialization=True,
                )
                meta = meta_path.read_text(encoding="utf-8").strip().split("\n")
                self._current_doc_name = meta[0]
                self._current_doc_type = meta[1]
                self._chunk_count      = int(meta[2])
                summary_path = self._index_dir / "domain_summary.txt"
                if summary_path.exists():
                    self._domain_summary = summary_path.read_text(encoding="utf-8").strip()
                logger.info(f"[Client {self.client_id}] Loaded index: {self._current_doc_name}")
            except Exception as e:
                logger.warning(f"[Client {self.client_id}] Failed to load index: {e}")

    # ── Search ─────────────────────────────────────────────────────────

    def similarity_search(self, query: str, top_k: int | None = None) -> list[dict]:
        if not self._vector_store:
            return []
        k = top_k or settings.RETRIEVAL_TOP_K
        results = self._vector_store.similarity_search_with_score(query, k=k)
        return [
            {"content": doc.page_content, "metadata": doc.metadata, "score": float(score)}
            for doc, score in results
        ]
