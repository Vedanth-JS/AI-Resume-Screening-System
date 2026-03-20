import fitz  # PyMuPDF
import io
import re

class ResumeParser:
    @staticmethod
    def extract_text(file_content: bytes, filename: str) -> str:
        if filename.lower().endswith(".pdf"):
            return ResumeParser._extract_from_pdf(file_content)
        elif filename.lower().endswith((".docx", ".txt")):
            # PyMuPDF can actually handle some docx/txt too, or we can use a simpler fallback
            return ResumeParser._extract_from_generic(file_content, filename)
        else:
            raise ValueError("Unsupported file format. Please upload PDF, DOCX, or TXT.")

    @staticmethod
    def _extract_from_pdf(file_content: bytes) -> str:
        text = ""
        with fitz.open(stream=file_content, filetype="pdf") as doc:
            for page in doc:
                text += page.get_text()
        return ResumeParser._clean_text(text)

    @staticmethod
    def _extract_from_generic(file_content: bytes, filename: str) -> str:
        # Fallback for TXT or other formats PyMuPDF might handle
        try:
            with fitz.open(stream=file_content, filetype=filename.split('.')[-1]) as doc:
                text = ""
                for page in doc:
                    text += page.get_text()
                return ResumeParser._clean_text(text)
        except Exception:
            # Last resort: simple string decode
            return ResumeParser._clean_text(file_content.decode('utf-8', errors='ignore'))

    @staticmethod
    def _clean_text(text: str) -> str:
        # Remove extra whitespace and special characters
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\x00-\x7F]+', ' ', text) # Remove non-ascii
        return text.strip()
