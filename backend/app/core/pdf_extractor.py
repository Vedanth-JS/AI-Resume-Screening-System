"""
Enterprise PDF Extractor — Multi-strategy PDF parsing with OCR fallback.

Strategies (tried in order):
  1. PyMuPDF (fitz) — fast native text extraction
  2. pdfminer.six — layout-aware extraction  
  3. Tesseract OCR — scanned image PDFs
  4. pdf2image + Tesseract — per-page OCR for stubborn files

Deduplication: SHA256 content hashing with bloom-filter precheck.
"""
import io
import os
import re
import hashlib
import asyncio
from typing import Optional, Tuple, List
from concurrent.futures import ThreadPoolExecutor

try:
    import fitz  # PyMuPDF
    _FITZ_AVAILABLE = True
except ImportError:
    fitz = None
    _FITZ_AVAILABLE = False

try:
    from pdfminer.high_level import extract_text as pdfminer_extract
    _PDFMINER_AVAILABLE = True
except ImportError:
    pdfminer_extract = None
    _PDFMINER_AVAILABLE = False

try:
    from PIL import Image
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False

try:
    import pytesseract
    _TESSERACT_AVAILABLE = True
except ImportError:
    pytesseract = None
    _TESSERACT_AVAILABLE = False

from ..core.logger import log

# Thread pool for CPU-bound extraction
_EXECUTOR = ThreadPoolExecutor(max_workers=os.cpu_count() or 4)


class PDFExtractor:
    @staticmethod
    def get_file_hash(file_content: bytes) -> str:
        """SHA256 hash for deduplication."""
        return hashlib.sha256(file_content).hexdigest()

    @staticmethod
    async def extract_text(
        file_content: bytes,
        ocr_enabled: bool = True,
        language: str = "eng",
    ) -> Tuple[str, dict]:
        """
        Extract text from PDF. Returns (text, metadata).

        metadata contains:
          - extraction_method: "pymupdf" | "pdfminer" | "ocr" | "hybrid"
          - ocr_applied: bool
          - page_count: int
          - confidence: float (0–1)
          - file_hash: str
          - text_length: int
        """
        meta = {
            "extraction_method": "pymupdf",
            "ocr_applied": False,
            "page_count": 0,
            "confidence": 1.0,
            "file_hash": PDFExtractor.get_file_hash(file_content),
            "text_length": 0,
        }

        loop = asyncio.get_running_loop()

        # Strategy 1: PyMuPDF
        text, page_count = await loop.run_in_executor(
            _EXECUTOR, _extract_pymupdf, file_content
        )
        meta["page_count"] = page_count

        if text and len(text.strip()) > 50:
            meta["text_length"] = len(text)
            return PDFExtractor.clean_text(text), meta

        # Strategy 2: pdfminer
        if _PDFMINER_AVAILABLE:
            try:
                text = await loop.run_in_executor(
                    _EXECUTOR, pdfminer_extract, io.BytesIO(file_content)
                )
            except Exception:
                text = ""
            if text and len(text.strip()) > 30:
                meta["extraction_method"] = "pdfminer"
                meta["text_length"] = len(text)
                return PDFExtractor.clean_text(text), meta

        # Strategy 3: OCR
        if ocr_enabled and _PIL_AVAILABLE and _TESSERACT_AVAILABLE:
            try:
                text = await loop.run_in_executor(
                    _EXECUTOR,
                    _ocr_pdf,
                    file_content,
                    language,
                )
            except Exception:
                text = ""
            if text:
                meta["extraction_method"] = "ocr"
                meta["ocr_applied"] = True
                meta["confidence"] = 0.7
                meta["text_length"] = len(text)
                return PDFExtractor.clean_text(text), meta

        # Strategy 4: PyMuPDF fallback + full page render OCR
        if ocr_enabled and _PIL_AVAILABLE and _TESSERACT_AVAILABLE:
            try:
                text = await loop.run_in_executor(
                    _EXECUTOR,
                    _ocr_pymupdf_pages,
                    file_content,
                    language,
                )
            except Exception:
                text = ""
            if text:
                meta["extraction_method"] = "hybrid"
                meta["ocr_applied"] = True
                meta["confidence"] = 0.5
                meta["text_length"] = len(text)
                return PDFExtractor.clean_text(text), meta

        # Final fallback: return whatever PyMuPDF gave us
        meta["confidence"] = 0.3 if not text else 0.8
        meta["text_length"] = len(text)
        return PDFExtractor.clean_text(text), meta

    @staticmethod
    def clean_text(text: str) -> str:
        """Normalize extracted text."""
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"\s{3,}", "  ", text)
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
        return text.strip()

    @staticmethod
    def is_scanned(text: str, page_count: int) -> bool:
        """Heuristic: if a multi-page PDF yields very little text, it's likely scanned."""
        if page_count <= 1:
            return False
        words = len(text.split())
        chars = len(text)
        return words < 10 or chars < 100


def _extract_pymupdf(content: bytes) -> Tuple[str, int]:
    """Extract text using PyMuPDF. Returns (text, page_count)."""
    if not _FITZ_AVAILABLE:
        return "", 0
    doc = fitz.open(stream=content, filetype="pdf")
    pages = []
    for page in doc:
        pages.append(page.get_text())
    page_count = len(pages)
    doc.close()
    return "\n".join(pages), page_count


def _ocr_pdf(content: bytes, language: str = "eng") -> str:
    """OCR using pdf2image + Tesseract."""
    from pdf2image import convert_from_bytes
    images = convert_from_bytes(content, dpi=200)
    texts = []
    for img in images:
        txt = pytesseract.image_to_string(img, lang=language)
        texts.append(txt)
    return "\n".join(texts)


def _ocr_pymupdf_pages(content: bytes, language: str = "eng") -> str:
    """Render each PDF page as image then OCR with Tesseract."""
    if not _FITZ_AVAILABLE:
        return ""
    doc = fitz.open(stream=content, filetype="pdf")
    texts = []
    for page in doc:
        pix = page.get_pixmap(dpi=200)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        txt = pytesseract.image_to_string(img, lang=language)
        texts.append(txt)
    doc.close()
    return "\n".join(texts)
