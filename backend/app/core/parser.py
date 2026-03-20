import pdfplumber
import docx2txt
import io
import re

class ResumeParser:
    @staticmethod
    def extract_text(file_content: bytes, filename: str) -> str:
        if filename.endswith(".pdf"):
            return ResumeParser._extract_from_pdf(file_content)
        elif filename.endswith(".docx"):
            return ResumeParser._extract_from_docx(file_content)
        else:
            raise ValueError("Unsupported file format. Please upload PDF or DOCX.")

    @staticmethod
    def _extract_from_pdf(file_content: bytes) -> str:
        text = ""
        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        return ResumeParser._clean_text(text)

    @staticmethod
    def _extract_from_docx(file_content: bytes) -> str:
        text = docx2txt.process(io.BytesIO(file_content))
        return ResumeParser._clean_text(text)

    @staticmethod
    def _clean_text(text: str) -> str:
        # Remove extra whitespace and special characters
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\x00-\x7F]+', ' ', text) # Remove non-ascii
        return text.strip()
