"""
DOCX Resume Parser — Extracts text and structure from .docx files.
Uses python-docx for native extraction with style-based section detection.
Fallback: unzip + raw XML parsing if python-docx fails.
"""
import io
import re
import zipfile
import asyncio
from xml.etree import ElementTree
from typing import Tuple, Optional
from concurrent.futures import ThreadPoolExecutor

try:
    from docx import Document as DocxDocument
    _PYTHON_DOCX_AVAILABLE = True
except ImportError:
    _PYTHON_DOCX_AVAILABLE = False

from ..core.logger import log

_EXECUTOR = ThreadPoolExecutor(max_workers=2)


class DOCXParser:
    @staticmethod
    async def extract_text(file_content: bytes) -> Tuple[str, dict]:
        """
        Extract text from DOCX. Returns (text, metadata).
        metadata includes section detection, paragraph count, extraction method.
        """
        meta = {"extraction_method": "python-docx", "paragraph_count": 0, "sections_detected": []}

        if _PYTHON_DOCX_AVAILABLE:
            loop = asyncio.get_running_loop()
            try:
                text, meta = await loop.run_in_executor(_EXECUTOR, _extract_python_docx, file_content)
                if text and len(text.strip()) > 20:
                    return DOCXParser.clean_text(text), meta
            except Exception as e:
                log.warning("docx_parser.python_docx_failed", error=str(e))

        # Fallback: raw XML extraction
        try:
            text = _extract_raw_xml(file_content)
            meta["extraction_method"] = "raw_xml"
            return DOCXParser.clean_text(text), meta
        except Exception as e:
            log.error("docx_parser.raw_xml_failed", error=str(e))
            return "", meta

    @staticmethod
    def clean_text(text: str) -> str:
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"\s{3,}", "  ", text)
        return text.strip()


def _extract_python_docx(content: bytes) -> Tuple[str, dict]:
    """Native python-docx extraction with style-based section detection."""
    doc = DocxDocument(io.BytesIO(content))
    paragraphs = []
    sections = set()
    for para in doc.paragraphs:
        if para.style and para.style.name:
            sections.add(para.style.name)
        paragraphs.append(para.text)
    meta = {
        "extraction_method": "python-docx",
        "paragraph_count": len(paragraphs),
        "sections_detected": list(sections),
    }
    return "\n".join(paragraphs), meta


def _extract_raw_xml(content: bytes) -> str:
    """Fallback: extract text from OOXML directly."""
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        if "word/document.xml" not in z.namelist():
            raise ValueError("Not a valid DOCX file")
        xml_content = z.read("word/document.xml")
    root = ElementTree.fromstring(xml_content)
    # All text elements in the document
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    texts = []
    for t in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"):
        if t.text:
            texts.append(t.text)
    return "\n".join(texts)
