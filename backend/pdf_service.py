import pdfplumber
import io
import re


def extract_text(file_bytes: bytes) -> str:
    """Extract text from PDF bytes using pdfplumber."""
    text_parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts).strip()


def extract_name_email(text: str) -> tuple[str, str]:
    """Heuristically extract name and email from resume text."""
    # Email extraction
    email_pattern = r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, text)
    email = emails[0] if emails else None

    # Name: take the first non-empty line that looks like a name
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    name = None
    for line in lines[:5]:
        # Skip lines that look like email/phone/address/url
        if '@' in line or re.search(r'\d{5,}', line) or 'http' in line.lower():
            continue
        words = line.split()
        if 2 <= len(words) <= 4 and all(w[0].isupper() for w in words if w):
            name = line
            break
    if not name and lines:
        name = lines[0][:100]

    return name, email
