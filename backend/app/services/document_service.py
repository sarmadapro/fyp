"""
Document processing service — Phase 2: Hierarchical Chunking + Document Outline

Phase 1 (extraction):
  - Structured PDF extraction: tables as markdown, headings by font/bold/caps, page numbers
  - Tiny block merging, standalone page-number filtering

Phase 2 (this version):
  - Section grouping: detected headings become section boundaries
  - Parent-child chunking:
      children  → embedded in FAISS (small, precise retrieval targets)
      parents   → saved in parent_store.json (full section text delivered to LLM)
  - Document outline: chapter/section list with page ranges saved as outline.json
  - Domain summary: structured outline injected into every query (replaces random 5-chunk sample)
  - Chat service upgraded to swap matched children for their parent context before sending to LLM
"""

import os
import json
import shutil
import logging

import torch

_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
from pathlib import Path

import fitz  # PyMuPDF
from docx import Document as DocxDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

from app.core.config import settings

logger = logging.getLogger(__name__)


# ─── Single-User / Legacy Document Service ──────────────────────────────────

class DocumentService:
    """Manages document upload, processing, and vector indexing (single-user mode)."""

    # Parent chunks are capped at this many characters before being stored.
    # Full sections can be thousands of chars; this keeps the LLM context manageable.
    PARENT_MAX_CHARS = 2000

    def __init__(self):
        self._embeddings = None
        self._vector_store: FAISS | None = None
        self._current_doc_name: str | None = None
        self._current_doc_type: str | None = None
        self._chunk_count: int = 0
        self._domain_summary: str = ""
        self._parent_store: list[dict] = []   # [{text, heading, start_page, end_page}]
        self._outline: dict = {}              # {title, total_pages, sections: [...]}

        self._text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " ", ""],
        )

        self._try_load_existing_index()

    # ── Properties ──────────────────────────────────────────────────────────

    @property
    def embeddings(self) -> HuggingFaceEmbeddings:
        if self._embeddings is None:
            logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
            self._embeddings = HuggingFaceEmbeddings(
                model_name=settings.EMBEDDING_MODEL,
                model_kwargs={"device": _DEVICE},
                encode_kwargs={"normalize_embeddings": True},
            )
            logger.info("Embedding model loaded.")
        return self._embeddings

    @property
    def vector_store(self) -> FAISS | None:
        return self._vector_store

    @property
    def has_document(self) -> bool:
        return self._vector_store is not None

    @property
    def has_parent_store(self) -> bool:
        return bool(self._parent_store)

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

    @property
    def outline(self) -> dict:
        return self._outline

    def get_parent(self, parent_idx: int) -> dict | None:
        """Look up a parent chunk by index. Returns None if index is out of range."""
        try:
            return self._parent_store[parent_idx]
        except (IndexError, TypeError):
            return None

    # ── Phase 1: Structured PDF Extraction ──────────────────────────────────

    def _extract_text_from_pdf(self, file_path: Path) -> str:
        """Legacy flat-text PDF extractor — kept as fallback only."""
        doc = fitz.open(str(file_path))
        text = "".join(page.get_text() for page in doc)
        doc.close()
        return text

    def _extract_text_from_docx(self, file_path: Path) -> str:
        doc = DocxDocument(str(file_path))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

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

    def _extract_structured_from_pdf(self, file_path: Path) -> list[dict]:
        """
        Structured PDF extraction preserving tables, headings, and page numbers.

        Per-page pipeline:
          1. Tables   — extracted as markdown via find_tables() (PyMuPDF >= 1.23)
          2. Text     — font-size, bold flag, and ALL-CAPS heuristics detect headings
          3. Figures  — presence noted as marker blocks

        Heading detection uses three independent signals (any one is enough):
          - Size   : block's max font size >= 1.25x the page median body size
          - Bold   : at least one span has the bold bit set (flag & 16) AND text <= 120 chars
          - Caps   : all-uppercase, alphabetic, >= 2 words, <= 80 chars
        """
        HEADING_RATIO = 1.25

        doc = fitz.open(str(file_path))
        all_blocks: list[dict] = []
        logger.info(f"Structured extraction starting: {len(doc)} pages in {file_path.name}")

        for page_num, page in enumerate(doc, 1):
            table_rects: list[fitz.Rect] = []

            # Step 1: Tables
            try:
                for table in page.find_tables():
                    md = table.to_markdown()
                    if not md.strip():
                        continue
                    table_rects.append(fitz.Rect(table.bbox))
                    all_blocks.append({"type": "table", "text": md,
                                       "page": page_num, "heading": None})
            except AttributeError:
                if page_num == 1:
                    logger.warning("find_tables() unavailable — upgrade PyMuPDF >= 1.23")
            except Exception as e:
                logger.warning(f"Table extraction error page {page_num}: {e}")

            # Step 2: Text blocks with heading detection
            raw_blocks = page.get_text("dict").get("blocks", [])

            font_sizes: list[float] = []
            for b in raw_blocks:
                if b.get("type") == 0:
                    for line in b.get("lines", []):
                        for span in line.get("spans", []):
                            sz = float(span.get("size", 0))
                            if sz > 0:
                                font_sizes.append(sz)

            body_size = sorted(font_sizes)[len(font_sizes) // 2] if font_sizes else 12.0
            heading_threshold = body_size * HEADING_RATIO

            for b in raw_blocks:
                if b.get("type") != 0:
                    continue
                block_rect = fitz.Rect(b["bbox"])
                if any(block_rect.intersects(tr) for tr in table_rects):
                    continue

                lines_text: list[str] = []
                max_font_size = 0.0
                any_bold = False

                for line in b.get("lines", []):
                    parts: list[str] = []
                    for span in line.get("spans", []):
                        t = span.get("text", "")
                        if t.strip():
                            parts.append(t)
                        sz = float(span.get("size", 0))
                        if sz > max_font_size:
                            max_font_size = sz
                        if span.get("flags", 0) & 16:
                            any_bold = True
                    joined = "".join(parts).strip()
                    if joined:
                        lines_text.append(joined)

                text = " ".join(lines_text).strip()
                if not text:
                    continue

                words = text.split()
                is_all_caps = (
                    len(words) >= 2
                    and text == text.upper()
                    and text.replace(" ", "").isalpha()
                )
                is_heading = (
                    len(text) <= 200
                    and not text.endswith(".")
                    and (
                        max_font_size >= heading_threshold
                        or (any_bold and len(text) <= 120)
                        or (is_all_caps and len(text) <= 80)
                    )
                )
                all_blocks.append({
                    "type": "heading" if is_heading else "text",
                    "text": text,
                    "page": page_num,
                    "heading": text if is_heading else None,
                })

            # Step 3: Figure markers
            try:
                if page.get_images(full=False):
                    all_blocks.append({"type": "figure_reference",
                                       "text": f"[Figure on page {page_num}]",
                                       "page": page_num, "heading": None})
            except Exception:
                pass

        doc.close()
        counts = {t: sum(1 for b in all_blocks if b["type"] == t)
                  for t in ("text", "heading", "table", "figure_reference")}
        logger.info(
            f"Extraction complete — {counts['text']} text, {counts['heading']} headings, "
            f"{counts['table']} tables, {counts['figure_reference']} figures"
        )
        return all_blocks

    # Blocks shorter than this get merged into the preceding text block.
    _MIN_BLOCK_CHARS = 150

    def _merge_tiny_blocks(self, blocks: list[dict]) -> list[dict]:
        """
        Merge consecutive tiny text blocks and drop standalone page-number artifacts.
        Headings, tables, and figure references are never touched.
        """
        merged: list[dict] = []
        for block in blocks:
            text = block["text"].strip()

            # Drop standalone page numbers: <= 6 chars, only digits/symbols
            if (
                block["type"] == "text"
                and len(text) <= 6
                and text.replace("?", "").replace(" ", "").isdigit()
            ):
                continue

            if (
                block["type"] == "text"
                and len(text) < self._MIN_BLOCK_CHARS
                and merged
                and merged[-1]["type"] == "text"
            ):
                merged[-1] = {
                    **merged[-1],
                    "text": merged[-1]["text"].rstrip() + " " + text,
                }
            else:
                merged.append(dict(block))
        return merged

    # ── Phase 2: Section Grouping ────────────────────────────────────────────

    def _group_into_sections(self, blocks: list[dict]) -> list[dict]:
        """
        Split the block stream into sections at every heading boundary.

        Each section: {heading, start_page, end_page, blocks: [...]}
        Content before the first heading goes into a preamble section (heading="").
        """
        sections: list[dict] = []
        current: dict = {"heading": "", "start_page": 1, "end_page": 1, "blocks": []}

        for block in blocks:
            if block["type"] == "heading":
                if current["blocks"]:
                    sections.append(current)
                current = {
                    "heading": block["text"].strip(),
                    "start_page": block["page"],
                    "end_page": block["page"],
                    "blocks": [],
                }
            else:
                current["blocks"].append(block)
                current["end_page"] = max(current["end_page"], block["page"])

        if current["blocks"]:
            sections.append(current)

        logger.info(f"Grouped into {len(sections)} sections")
        return sections

    # ── Phase 2: Hierarchical Chunking ───────────────────────────────────────

    def _hierarchical_chunks(
        self, sections: list[dict], file_name: str
    ) -> tuple[list[str], list[dict], list[dict]]:
        """
        Build parent-child chunk pairs from section groups.

        Children  : small splits of each section's text → embedded in FAISS.
                    Each child stores parent_idx so its parent can be fetched after matching.
        Parents   : full section text (capped at PARENT_MAX_CHARS) → saved in parent_store.
                    After retrieval, matched children are swapped for their parent context
                    before sending to the LLM — giving the model the full section, not a fragment.

        Returns (child_chunks, child_metadatas, parent_store_list).
        """
        child_chunks: list[str] = []
        metadatas: list[dict] = []
        parent_store: list[dict] = []
        child_idx = 0

        for section in sections:
            parts: list[str] = []
            for block in section["blocks"]:
                t = block.get("text", "").strip()
                if t and block["type"] in ("text", "table"):
                    parts.append(t)

            section_text = "\n\n".join(parts).strip()
            if not section_text:
                continue

            parent_idx = len(parent_store)
            parent_store.append({
                "text": section_text[: self.PARENT_MAX_CHARS],
                "heading": section["heading"],
                "start_page": section["start_page"],
                "end_page": section["end_page"],
            })

            sub_chunks = self._text_splitter.split_text(section_text)
            heading = section["heading"]
            for j, sc in enumerate(sub_chunks):
                if j == 0 and heading:
                    sep = " " if heading.endswith((":", "-", ".")) else ": "
                    sc = f"{heading}{sep}{sc}"
                child_chunks.append(sc)
                metadatas.append({
                    "source": file_name,
                    "chunk_index": child_idx,
                    "chunk_type": "child",
                    "parent_idx": parent_idx,
                    "heading": heading,
                    "page": section["start_page"],
                    "start_page": section["start_page"],
                    "end_page": section["end_page"],
                })
                child_idx += 1

        logger.info(
            f"Hierarchical chunking: {len(child_chunks)} children, "
            f"{len(parent_store)} parent sections"
        )
        return child_chunks, metadatas, parent_store

    # ── Phase 2: Document Outline ────────────────────────────────────────────

    def _build_document_outline(
        self, sections: list[dict], file_name: str, total_pages: int
    ) -> dict:
        """Build the persistent document structure map from section groups."""
        return {
            "title": file_name,
            "total_pages": total_pages,
            "sections": [
                {
                    "heading": s["heading"] or "Preamble",
                    "start_page": s["start_page"],
                    "end_page": s["end_page"],
                    "block_count": len(s["blocks"]),
                }
                for s in sections
                if s["blocks"]
            ],
        }

    def _build_structured_summary(self, outline: dict) -> str:
        """
        Build the domain summary from the document outline.

        Replaces the old 5-random-chunk LLM call with a deterministic, structured
        summary that gives the LLM the full chapter map on every query. The LLM
        can now answer 'what topics does this book cover?' without any retrieval.
        """
        title = outline.get("title", "Document")
        total_pages = outline.get("total_pages", 0)
        sections = outline.get("sections", [])

        header = f"Document: {title}"
        if total_pages:
            header += f" ({total_pages} pages)"

        if not sections:
            return header

        lines = [header, f"\nThis document covers {len(sections)} topics:"]
        for s in sections:
            heading = s.get("heading", "")
            sp, ep = s.get("start_page"), s.get("end_page")
            page_info = f"p.{sp}" if sp == ep else f"p.{sp}-{ep}"
            lines.append(f"  - {heading} ({page_info})")

        return "\n".join(lines)

    # ── Phase 2: Shared Indexing Preparation ────────────────────────────────

    def _prepare_index_data(
        self, file_path: Path, file_name: str, file_type: str
    ) -> tuple[list[str], list[dict], list[dict], dict, str]:
        """
        Full pipeline from raw file to (chunks, metadatas, parent_store, outline, summary).
        PDFs get the full Phase 2 treatment. DOCX/TXT get flat chunking with empty outline.
        """
        if file_type == ".pdf":
            blocks = self._extract_structured_from_pdf(file_path)
            blocks = self._merge_tiny_blocks(blocks)
            sections = self._group_into_sections(blocks)
            chunks, metadatas, parent_store = self._hierarchical_chunks(sections, file_name)
            total_pages = max((b["page"] for b in blocks), default=0)
            outline = self._build_document_outline(sections, file_name, total_pages)
            domain_summary = self._build_structured_summary(outline)
            return chunks, metadatas, parent_store, outline, domain_summary

        # DOCX / TXT: flat path, no structural metadata
        text = self.extract_text(file_path, file_type)
        raw_chunks = self._text_splitter.split_text(text)
        metadatas = [
            {"source": file_name, "chunk_index": i, "chunk_type": "child",
             "parent_idx": None, "heading": "", "page": None}
            for i in range(len(raw_chunks))
        ]
        outline = {"title": file_name, "total_pages": 0, "sections": []}
        domain_summary = f"Document: {file_name}"
        return raw_chunks, metadatas, [], outline, domain_summary

    # ── Indexing ─────────────────────────────────────────────────────────────

    def process_and_index(self, file_path: Path, file_name: str, file_type: str) -> int:
        chunks, metadatas, parent_store, outline, domain_summary = \
            self._prepare_index_data(file_path, file_name, file_type)

        if not chunks:
            raise ValueError("Document produced no text chunks.")

        logger.info(f"Building FAISS index: {len(chunks)} child chunks from {file_name}")
        self._vector_store = FAISS.from_texts(
            texts=chunks, embedding=self.embeddings, metadatas=metadatas
        )
        self._vector_store.save_local(str(settings.INDEX_DIR))

        self._current_doc_name = file_name
        self._current_doc_type = file_type
        self._chunk_count = len(chunks)
        self._parent_store = parent_store
        self._outline = outline
        self._domain_summary = domain_summary

        idx_dir = settings.INDEX_DIR
        (idx_dir / "doc_meta.txt").write_text(
            f"{file_name}\n{file_type}\n{len(chunks)}", encoding="utf-8"
        )
        (idx_dir / "domain_summary.txt").write_text(domain_summary, encoding="utf-8")
        (idx_dir / "parent_store.json").write_text(
            json.dumps(parent_store, ensure_ascii=False), encoding="utf-8"
        )
        (idx_dir / "outline.json").write_text(
            json.dumps(outline, ensure_ascii=False), encoding="utf-8"
        )

        logger.info(
            f"Index saved — {len(chunks)} children, {len(parent_store)} parents"
        )
        return len(chunks)

    def delete_document(self):
        self._vector_store = None
        self._current_doc_name = None
        self._current_doc_type = None
        self._chunk_count = 0
        self._domain_summary = ""
        self._parent_store = []
        self._outline = {}

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
        if not (index_path.exists() and meta_path.exists()):
            return
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

            ps_path = settings.INDEX_DIR / "parent_store.json"
            if ps_path.exists():
                self._parent_store = json.loads(ps_path.read_text(encoding="utf-8"))

            ol_path = settings.INDEX_DIR / "outline.json"
            if ol_path.exists():
                self._outline = json.loads(ol_path.read_text(encoding="utf-8"))

            logger.info(f"Loaded existing index: {self._current_doc_name} "
                        f"({len(self._parent_store)} parents)")
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


# ─── Multi-Tenant Document Service (SaaS) ───────────────────────────────────

class ClientDocumentService(DocumentService):
    """
    Per-client document service with isolated storage.
    Inherits all Phase 1 + Phase 2 pipeline methods from DocumentService.
    Only overrides storage paths, the embedding singleton, and index persistence.
    """

    _shared_embeddings = None
    _instances: dict[str, "ClientDocumentService"] = {}

    @classmethod
    def get_or_create(cls, client_id: str) -> "ClientDocumentService":
        if client_id not in cls._instances:
            cls._instances[client_id] = cls(client_id)
        return cls._instances[client_id]

    @classmethod
    def invalidate(cls, client_id: str) -> None:
        cls._instances.pop(client_id, None)
        logger.info(f"[ClientDocumentService] Cache invalidated for {client_id}")

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
        self._parent_store: list[dict] = []
        self._outline: dict = {}

        self._try_load_existing_index()

    @property
    def embeddings(self) -> HuggingFaceEmbeddings:
        if ClientDocumentService._shared_embeddings is None:
            logger.info(f"Loading shared embedding model: {settings.EMBEDDING_MODEL}")
            ClientDocumentService._shared_embeddings = HuggingFaceEmbeddings(
                model_name=settings.EMBEDDING_MODEL,
                model_kwargs={"device": _DEVICE},
                encode_kwargs={"normalize_embeddings": True},
            )
            logger.info("Shared embedding model loaded.")
        return ClientDocumentService._shared_embeddings

    @property
    def upload_dir(self) -> Path:
        return self._upload_dir

    @property
    def index_dir(self) -> Path:
        return self._index_dir

    def process_and_index(self, file_path: Path, file_name: str, file_type: str) -> int:
        self._wipe_index()

        chunks, metadatas, parent_store, outline, domain_summary = \
            self._prepare_index_data(file_path, file_name, file_type)

        if not chunks:
            raise ValueError("Document produced no text chunks.")

        logger.info(f"[Client {self.client_id}] {len(chunks)} child chunks from '{file_name}'")
        self._vector_store = FAISS.from_texts(
            texts=chunks, embedding=self.embeddings, metadatas=metadatas
        )
        self._vector_store.save_local(str(self._index_dir))

        self._current_doc_name = file_name
        self._current_doc_type = file_type
        self._chunk_count      = len(chunks)
        self._parent_store     = parent_store
        self._outline          = outline
        self._domain_summary   = domain_summary

        (self._index_dir / "doc_meta.txt").write_text(
            f"{file_name}\n{file_type}\n{len(chunks)}", encoding="utf-8"
        )
        (self._index_dir / "domain_summary.txt").write_text(
            domain_summary, encoding="utf-8"
        )
        (self._index_dir / "parent_store.json").write_text(
            json.dumps(parent_store, ensure_ascii=False), encoding="utf-8"
        )
        (self._index_dir / "outline.json").write_text(
            json.dumps(outline, ensure_ascii=False), encoding="utf-8"
        )

        logger.info(
            f"[Client {self.client_id}] Index saved — "
            f"{len(chunks)} children, {len(parent_store)} parents"
        )
        return len(chunks)

    def _wipe_index(self):
        for f in self._index_dir.iterdir():
            if f.name != ".gitkeep":
                f.unlink() if f.is_file() else shutil.rmtree(f)
        self._vector_store     = None
        self._current_doc_name = None
        self._current_doc_type = None
        self._chunk_count      = 0
        self._domain_summary   = ""
        self._parent_store     = []
        self._outline          = {}

    def _wipe_uploads(self):
        for f in self._upload_dir.iterdir():
            if f.name != ".gitkeep":
                f.unlink() if f.is_file() else shutil.rmtree(f)

    def delete_document(self):
        self._wipe_uploads()
        self._wipe_index()
        ClientDocumentService._instances.pop(self.client_id, None)
        logger.info(f"[Client {self.client_id}] Document and index deleted.")

    def _try_load_existing_index(self):
        index_path = self._index_dir / "index.faiss"
        meta_path  = self._index_dir / "doc_meta.txt"
        if not (index_path.exists() and meta_path.exists()):
            return
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

            ps_path = self._index_dir / "parent_store.json"
            if ps_path.exists():
                self._parent_store = json.loads(ps_path.read_text(encoding="utf-8"))

            ol_path = self._index_dir / "outline.json"
            if ol_path.exists():
                self._outline = json.loads(ol_path.read_text(encoding="utf-8"))

            logger.info(
                f"[Client {self.client_id}] Loaded: {self._current_doc_name} "
                f"({len(self._parent_store)} parents)"
            )
        except Exception as e:
            logger.warning(f"[Client {self.client_id}] Failed to load index: {e}")

    def similarity_search(self, query: str, top_k: int | None = None) -> list[dict]:
        if not self._vector_store:
            return []
        k = top_k or settings.RETRIEVAL_TOP_K
        results = self._vector_store.similarity_search_with_score(query, k=k)
        return [
            {"content": doc.page_content, "metadata": doc.metadata, "score": float(score)}
            for doc, score in results
        ]
