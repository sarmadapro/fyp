#!/usr/bin/env python3
"""
Phase 1 Manual Test: Structured PDF Extraction
===============================================
Tests the new extraction pipeline WITHOUT running the full indexing pipeline.
No embedding model is loaded. No API calls are made.

Usage (run from the backend/ directory):
    python test_extraction.py path/to/document.pdf
    python test_extraction.py path/to/document.pdf --verbose    # print ALL chunks
    python test_extraction.py path/to/document.pdf --page 5     # inspect one page

What to look for:
    HEADINGS  - Do they match the chapter/section titles in the PDF?
                False positives (normal text flagged as heading) -> raise HEADING_RATIO
                False negatives (headings missed) -> lower HEADING_RATIO
                HEADING_RATIO is set in document_service._extract_structured_from_pdf

    TABLES    - Are column headers present? Are rows properly separated?
                If "None detected" -> check PyMuPDF version (needs >= 1.23)

    CHUNKS    - Do they have page numbers? Section context? Reasonable sizes?
                Check first sub-chunk of each text block -- heading should be prepended.

    COVERAGE  - Do the 5 domain-summary samples span the whole document?
                First sample and last sample should cover different topics.
"""

import sys
import os
import logging
from pathlib import Path

# Must run from backend/ so the app package is importable.
_script_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(_script_dir))

# Suppress noisy startup logs so the test output is readable.
logging.basicConfig(level=logging.WARNING)

try:
    from app.services.document_service import DocumentService
except ImportError as e:
    print(f"\nImport error: {e}")
    print("Make sure you are running this script from the backend/ directory:")
    print("  cd backend && python test_extraction.py path/to/doc.pdf")
    sys.exit(1)

W = 74


def sep(title="", char="="):
    if title:
        pad = max(0, (W - len(title) - 2) // 2)
        right = W - pad - len(title) - 2
        print(f"\n{char * pad} {title} {char * right}")
    else:
        print(char * W)


def trunc(text, n=220):
    flat = text.replace("\n", " ").strip()
    return (flat[:n] + "...") if len(flat) > n else flat


def parse_args():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)
    pdf = Path(args[0])
    verbose = "--verbose" in args or "-v" in args
    page_filter = None
    if "--page" in args:
        idx = args.index("--page")
        try:
            page_filter = int(args[idx + 1])
        except (IndexError, ValueError):
            print("--page requires an integer argument")
            sys.exit(1)
    return pdf, verbose, page_filter


def main():
    pdf_path, verbose, page_filter = parse_args()

    if not pdf_path.exists():
        print(f"\nError: file not found: {pdf_path}")
        sys.exit(1)
    if pdf_path.suffix.lower() != ".pdf":
        print(f"\nError: expected a .pdf file, got '{pdf_path.suffix}'")
        sys.exit(1)

    size_kb = pdf_path.stat().st_size / 1024
    print(f"\nFile : {pdf_path.name}")
    print(f"Size : {size_kb:.1f} KB  ({size_kb / 1024:.2f} MB)")

    # Instantiate service without triggering embeddings or index load.
    svc = DocumentService.__new__(DocumentService)
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from app.core.config import settings
    svc._text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " ", ""],
    )

    # ------------------------------------------------------------------ #
    sep("EXTRACTION")
    print(f"\nRunning extraction...  (chunk_size={settings.CHUNK_SIZE}, overlap={settings.CHUNK_OVERLAP})")

    logging.getLogger("app.services.document_service").setLevel(logging.INFO)
    blocks = svc._extract_structured_from_pdf(pdf_path)
    logging.getLogger("app.services.document_service").setLevel(logging.WARNING)

    if page_filter is not None:
        blocks = [b for b in blocks if b["page"] == page_filter]
        print(f"(filtered to page {page_filter} -- {len(blocks)} blocks)")

    text_blocks = [b for b in blocks if b["type"] == "text"]
    headings    = [b for b in blocks if b["type"] == "heading"]
    tables      = [b for b in blocks if b["type"] == "table"]
    figures     = [b for b in blocks if b["type"] == "figure_reference"]
    all_pages   = sorted({b["page"] for b in blocks})

    lo = min(all_pages) if all_pages else 0
    hi = max(all_pages) if all_pages else 0
    print(f"\nPages spanned  : {lo} to {hi}")
    print(f"Total blocks   : {len(blocks)}")
    print(f"  Text blocks  : {len(text_blocks)}")
    print(f"  Headings     : {len(headings)}")
    print(f"  Tables       : {len(tables)}")
    print(f"  Figure refs  : {len(figures)}")

    # ------------------------------------------------------------------ #
    sep("HEADINGS DETECTED (first 20)", char="-")
    if not headings:
        print("\n  None detected.")
        print("  If your PDF has headings, try lowering HEADING_RATIO in")
        print("  document_service._extract_structured_from_pdf (default 1.25 -> 1.15).")
    else:
        for h in headings[:20]:
            txt = h["text"].encode("ascii", errors="replace").decode("ascii")
            print(f"  [p{h['page']:>4}]  {txt[:80]}")
        if len(headings) > 20:
            print(f"  ... and {len(headings) - 20} more")

    # ------------------------------------------------------------------ #
    sep("TABLES DETECTED (first 3 shown)", char="-")
    if not tables:
        print("\n  None detected.")
        print("  PyMuPDF find_tables() works on PDFs with real table structure.")
        print("  Scanned PDFs or image-based tables will not be detected.")
    else:
        for i, t in enumerate(tables[:3], 1):
            rows = t["text"].split("\n")
            print(f"\n  TABLE {i}  [page {t['page']}]")
            for row in rows[:10]:
                safe = row.encode("ascii", errors="replace").decode("ascii")
                print(f"    {safe}")
            if len(rows) > 10:
                print(f"    ... ({len(rows)} rows total)")

    # ------------------------------------------------------------------ #
    # Phase 2: section grouping and hierarchical chunks
    sep("PHASE 2 -- SECTION GROUPING", char="-")
    sections = svc._group_into_sections(blocks)
    print(f"\nTotal sections : {len(sections)}")
    non_empty = [s for s in sections if s["blocks"]]
    print(f"Non-empty      : {len(non_empty)}")
    print(f"\nFirst 20 sections:")
    for s in non_empty[:20]:
        heading = (s["heading"] or "(preamble)").encode("ascii", errors="replace").decode("ascii")
        sp, ep = s["start_page"], s["end_page"]
        page_info = f"p.{sp}" if sp == ep else f"p.{sp}-{ep}"
        print(f"  {page_info:<12}  {heading[:65]}")
    if len(non_empty) > 20:
        print(f"  ... and {len(non_empty) - 20} more")

    sep("CHUNKING (Phase 2 hierarchical)", char="-")
    chunks, metadatas, parent_store = svc._hierarchical_chunks(sections, pdf_path.name)

    chunk_types = {}
    for m in metadatas:
        t = m.get("chunk_type", "unknown")
        chunk_types[t] = chunk_types.get(t, 0) + 1

    lengths = [len(c) for c in chunks]
    print(f"\nTotal chunks   : {len(chunks)}")
    for t, count in sorted(chunk_types.items()):
        print(f"  {t:<22}: {count}")
    if lengths:
        print(f"\nChunk length (chars):")
        print(f"  Min  : {min(lengths)}")
        print(f"  Max  : {max(lengths)}")
        print(f"  Avg  : {sum(lengths) // len(lengths)}")
        tiny  = sum(1 for l in lengths if l < 80)
        large = sum(1 for l in lengths if l > 1800)
        if tiny:
            print(f"  Tiny (<80 chars)    : {tiny}  <- add noise, consider filtering")
        if large:
            print(f"  Large (>1800 chars) : {large}  <- consider lowering CHUNK_SIZE")

    # ------------------------------------------------------------------ #
    sep("SAMPLE CHUNKS (first 8)", char="-")
    for i, (chunk, meta) in enumerate(zip(chunks[:8], metadatas[:8])):
        safe_chunk = chunk.encode("ascii", errors="replace").decode("ascii")
        safe_sec   = str(meta.get("heading", "")).encode("ascii", errors="replace").decode("ascii")
        print(f"\n  CHUNK {i + 1}")
        print(f"    page    : {meta.get('page', 'N/A')}")
        print(f"    type    : {meta.get('chunk_type')}")
        print(f"    section : {safe_sec[:70]}")
        print(f"    text    : {trunc(safe_chunk, 260)}")

    # ------------------------------------------------------------------ #
    if verbose:
        sep("ALL CHUNKS", char="-")
        for i, (chunk, meta) in enumerate(zip(chunks, metadatas)):
            safe_chunk = chunk.encode("ascii", errors="replace").decode("ascii")
            section    = str(meta.get("heading", ""))[:50]
            print(f"\n  [{i:>4}] p={meta['page']}  type={meta['chunk_type']:<8}  sec={section}")
            print(f"         {trunc(safe_chunk, 300)}")

    # ------------------------------------------------------------------ #
    sep("PHASE 2 -- PARENT STORE (first 3 parents)", char="-")
    print(f"\nTotal parents  : {len(parent_store)}")
    for i, p in enumerate(parent_store[:3]):
        safe_h = str(p.get("heading", "")).encode("ascii", errors="replace").decode("ascii")
        safe_t = p["text"].encode("ascii", errors="replace").decode("ascii")
        sp, ep = p.get("start_page"), p.get("end_page")
        page_info = f"p.{sp}" if sp == ep else f"p.{sp}-{ep}"
        print(f"\n  PARENT {i}")
        print(f"    heading  : {safe_h[:70]}")
        print(f"    pages    : {page_info}")
        print(f"    length   : {len(p['text'])} chars")
        print(f"    preview  : {trunc(safe_t, 200)}")

    # ------------------------------------------------------------------ #
    sep("PHASE 2 -- DOMAIN SUMMARY (structured outline)", char="-")
    total_pages_doc = max((b["page"] for b in blocks), default=0)
    outline = svc._build_document_outline(sections, pdf_path.name, total_pages_doc)
    summary = svc._build_structured_summary(outline)
    safe_summary = summary.encode("ascii", errors="replace").decode("ascii")
    print(f"\n{safe_summary}")

    # ------------------------------------------------------------------ #
    sep("CHECKLIST", char="-")
    print("""
  1. HEADINGS / SECTIONS
     [OK] Headings match chapter/section titles in the actual PDF?
     [OK] Section count is reasonable (not 1 giant section, not 500 tiny ones)?
     [!]  Too few sections (1-5 for a long doc) -> headings not detected, lower HEADING_RATIO
     [!]  Too many sections (>300 for 150 pages) -> false positives, raise HEADING_RATIO

  2. TABLES
     [OK] Column headers appear in the first row of each table?
     [OK] Cell values are correctly separated by pipe | characters?
     [!]  Table cells run together -> PDF uses image-based tables (not parseable)

  3. PARENT STORE
     [OK] Each parent contains a full, coherent section of text (not a fragment)?
     [OK] Parent headings match what's in the actual PDF?
     [!]  Parents are very short (<100 chars) -> section has no text content, just a title
          -> Check if the PDF uses images for the section body

  3. CHUNKS
     [OK] Every text chunk starts with "SectionName: ..." (heading prepended)?
     [OK] Page numbers are correct (compare with the actual PDF)?
     [!]  Chunks are too small (< 100 chars)?
          -> Raise CHUNK_SIZE in .env (default: 1000)
     [!]  Chunks are too large (> 2000 chars)?
          -> Lower CHUNK_SIZE in .env

  4. DOMAIN SUMMARY SAMPLES
     [OK] First and last samples cover different topics/sections?
     [!]  All samples look similar (same section repeated)?
          -> OK for Phase 1 -- Phase 2 will use chapter-level summaries
""")

    sep()
    print(f"Done.  {len(chunks)} chunks ready for embedding.\n")


if __name__ == "__main__":
    main()
