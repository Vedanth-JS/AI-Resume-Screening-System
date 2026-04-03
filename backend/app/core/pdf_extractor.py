import os
import re
import hashlib
from typing import Optional
import fitz  # PyMuPDF
try:
    from pdfminer.high_level import extract_text as pdfminer_extract
except ImportError:
    pdfminer_extract = None

class PDFExtractor:
    """
    Robust PDF text extraction with multiple fallbacks and deduplication.
    """
    
    @staticmethod
    def get_file_hash(file_content: bytes) -> str:
        """Generate SHA256 hash for deduplication."""
        return hashlib.sha256(file_content).hexdigest()

    @staticmethod
    async def extract_text(file_content: bytes) -> str:
        """
        Extract text from PDF content using PyMuPDF (fast) with fallback to pdfminer.
        """
        text = ""
        try:
            # 1. Try PyMuPDF
            doc = fitz.open(stream=file_content, filetype="pdf")
            for page in doc:
                text += page.get_text()
            doc.close()
            
            # If PyMuPDF returned almost nothing, try fallback
            if len(text.strip()) < 50 and pdfminer_extract:
                import io
                text = pdfminer_extract(io.BytesIO(file_content))
                
        except Exception as e:
            # 2. Fallback to pdfminer if primary fails
            if pdfminer_extract:
                try:
                    import io
                    text = pdfminer_extract(io.BytesIO(file_content))
                except:
                    raise ValueError(f"Failed to extract text from PDF: {str(e)}")
            else:
                raise ValueError(f"Primary extraction failed and no fallback available: {str(e)}")

        return PDFExtractor.clean_text(text)

    @staticmethod
    def clean_text(text: str) -> str:
        """Basic normalization of extracted text."""
        # Replace multiple newlines/spaces
        text = re.sub(r'\n+', '\n', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
