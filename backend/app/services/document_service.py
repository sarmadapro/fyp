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


class DocumentService:
    """Manages document upload, processing, and vector indexing."""

    def __init__(self):
        self._embeddings = None
        self._vector_store: FAISS | None = None
        self._current_doc_name: str | None = None
        self._current_doc_type: str | None = None
        self._chunk_count: int = 0

        self._text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " ", ""],
        )

        # Try to load existing index
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

    # ------------------------------------------------------------------ #
    #  Text Extraction
    # ------------------------------------------------------------------ #

    def _extract_text_from_pdf(self, file_path: Path) -> str:
        """Extract text from a PDF file using PyMuPDF."""
        doc = fitz.open(str(file_path))
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text

    def _extract_text_from_docx(self, file_path: Path) -> str:
        """Extract text from a DOCX file."""
        doc = DocxDocument(str(file_path))
        return "\n".join(para.text for para in doc.paragraphs if para.text.strip())

    def _extract_text_from_txt(self, file_path: Path) -> str:
        """Extract text from a plain text file."""
        return file_path.read_text(encoding="utf-8")

    def extract_text(self, file_path: Path, file_type: str) -> str:
        """Extract text from a document based on its type."""
        extractors = {
            ".pdf": self._extract_text_from_pdf,
            ".docx": self._extract_text_from_docx,
            ".txt": self._extract_text_from_txt,
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
        """
        Full pipeline: extract text → chunk → embed → build FAISS index.
        Returns the number of chunks created.
        """
        # 1. Extract text
        text = self.extract_text(file_path, file_type)

        # 2. Chunk
        chunks = self._text_splitter.split_text(text)
        if not chunks:
            raise ValueError("Document produced no text chunks.")

        logger.info(f"Created {len(chunks)} chunks from {file_name}")

        # 3. Build FAISS index
        self._vector_store = FAISS.from_texts(
            texts=chunks,
            embedding=self.embeddings,
            metadatas=[{"source": file_name, "chunk_index": i} for i, _ in enumerate(chunks)],
        )

        # 4. Persist index to disk
        self._vector_store.save_local(str(settings.INDEX_DIR))

        # 5. Save metadata
        self._current_doc_name = file_name
        self._current_doc_type = file_type
        self._chunk_count = len(chunks)

        # Save doc metadata to a simple file for reload
        meta_path = settings.INDEX_DIR / "doc_meta.txt"
        meta_path.write_text(f"{file_name}\n{file_type}\n{len(chunks)}", encoding="utf-8")

        logger.info(f"FAISS index saved with {len(chunks)} vectors.")
        return len(chunks)

    def delete_document(self):
        """Delete the current document and its index."""
        # Clear in-memory state
        self._vector_store = None
        self._current_doc_name = None
        self._current_doc_type = None
        self._chunk_count = 0

        # Clear upload directory
        for f in settings.UPLOAD_DIR.iterdir():
            if f.name != ".gitkeep":
                if f.is_file():
                    f.unlink()
                elif f.is_dir():
                    shutil.rmtree(f)

        # Clear index directory
        for f in settings.INDEX_DIR.iterdir():
            if f.name != ".gitkeep":
                if f.is_file():
                    f.unlink()
                elif f.is_dir():
                    shutil.rmtree(f)

        logger.info("Document and index deleted.")

    def _try_load_existing_index(self):
        """Try to load a previously saved FAISS index on startup."""
        index_path = settings.INDEX_DIR / "index.faiss"
        meta_path = settings.INDEX_DIR / "doc_meta.txt"

        if index_path.exists() and meta_path.exists():
            try:
                self._vector_store = FAISS.load_local(
                    str(settings.INDEX_DIR),
                    self.embeddings,
                    allow_dangerous_deserialization=True,
                )
                meta = meta_path.read_text(encoding="utf-8").strip().split("\n")
                self._current_doc_name = meta[0]
                self._current_doc_type = meta[1]
                self._chunk_count = int(meta[2])
                logger.info(f"Loaded existing index for: {self._current_doc_name}")
            except Exception as e:
                logger.warning(f"Failed to load existing index: {e}")

    def similarity_search(self, query: str, top_k: int | None = None) -> list[dict]:
        """
        Search the FAISS index for chunks similar to the query.
        Returns list of {"content": str, "metadata": dict, "score": float}.
        
        Args:
            query: The search query
            top_k: Number of results to return (default from settings)
        """
        if not self._vector_store:
            return []

        k = top_k or settings.RETRIEVAL_TOP_K
        results = self._vector_store.similarity_search_with_score(query, k=k)

        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": float(score),
            }
            for doc, score in results
        ]


# Singleton instance
document_service = DocumentService()
