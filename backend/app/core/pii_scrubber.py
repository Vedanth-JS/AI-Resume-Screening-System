"""
Blind Screening — PII Scrubber
─────────────────────────────
Strips Personally Identifiable Information from resume text BEFORE the LLM
evaluates it, ensuring DE&I / GDPR-compliant blind hiring.

Scrubbed entities:
  • Name          → [CANDIDATE]
  • Email         → [EMAIL]
  • Phone         → [PHONE]
  • URLs/LinkedIn → [PROFILE_URL]
  • Physical address / city / country → [LOCATION]
  • Gender pronouns & titles (he/she/Mr/Ms) → [REDACTED]
  • Age / graduation year signals → [YEAR]

The original name is returned alongside the scrubbed text so the
application can still store/display it — only the LLM-facing text
is anonymised.
"""
import re
import spacy
from typing import Tuple, Dict, Any
from ..core.logger import log

try:
    _nlp = spacy.load("en_core_web_sm")
except Exception:
    _nlp = None
    log.warning("spacy_model_not_loaded", note="PII scrubber using regex-only mode.")

# ─── Regex patterns ───────────────────────────────────────────────────────────
_EMAIL_RE   = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", re.I)
_PHONE_RE   = re.compile(r"(\+?\d[\d\s\-().]{7,}\d)")
_URL_RE     = re.compile(r"https?://\S+|www\.\S+|linkedin\.com/\S+|github\.com/\S+", re.I)
_YEAR_RE    = re.compile(r"\b(19[6-9]\d|20[0-2]\d)\b")    # years 1960-2029
_GENDER_PRONOUNS = re.compile(
    r"\b(he|him|his|she|her|hers|mr\.|mrs\.|ms\.|miss|gentleman|lady)\b", re.I
)
_LOCATION_SIGNALS = re.compile(
    r"\b(street|st\.|avenue|ave\.|road|rd\.|lane|ln\.|blvd|drive|dr\.)\b"
    r"|\b\d{5,6}\b"         # ZIP / PIN codes
    r"|\b[A-Z][a-z]+,\s*[A-Z]{2}\b",  # City, State
    re.I
)


class PIIScrubber:
    """
    Scrubs PII from resume text for blind screening.

    Usage:
        scrubbed, meta = PIIScrubber.scrub(raw_text)
        # Send `scrubbed` to LLM; keep `meta["original_name"]` in DB.
    """

    @staticmethod
    def scrub(text: str) -> Tuple[str, Dict[str, Any]]:
        """
        Returns (scrubbed_text, metadata).
        metadata contains the original extracted PII for record-keeping.
        """
        original = text
        meta: Dict[str, Any] = {
            "original_emails":  _EMAIL_RE.findall(text),
            "original_phones":  _PHONE_RE.findall(text),
            "original_urls":    _URL_RE.findall(text),
            "original_name":    None,
            "scrubbed":         True,
        }

        # 1. Extract name with spaCy before scrubbing anything else
        if _nlp:
            doc = _nlp(text[:2000])    # only parse beginning where name appears
            for ent in doc.ents:
                if ent.label_ == "PERSON":
                    # Replace name globally
                    text = text.replace(ent.text, "[CANDIDATE]")
                    meta["original_name"] = ent.text
                    break

        # 2. Email
        text = _EMAIL_RE.sub("[EMAIL]", text)

        # 3. Phone
        text = _PHONE_RE.sub("[PHONE]", text)

        # 4. URLs / LinkedIn / GitHub
        text = _URL_RE.sub("[PROFILE_URL]", text)

        # 5. Gender markers
        text = _GENDER_PRONOUNS.sub("[REDACTED]", text)

        # 6. Location signals
        text = _LOCATION_SIGNALS.sub("[LOCATION]", text)

        # 7. Graduation year signals (e.g. "Class of 2019", "Batch 2021")
        text = re.sub(
            r"(class of|batch of?|graduated?|passout)\s*" + r"\b(19[6-9]\d|20[0-2]\d)\b",
            r"\1 [YEAR]",
            text,
            flags=re.I
        )

        scrubbed_chars = len(original) - len(text.replace("[CANDIDATE]", "X" * 9)
                                                     .replace("[EMAIL]", "X" * 5)
                                                     .replace("[PHONE]", "X" * 5))
        meta["scrub_ratio"] = round(1 - len(text) / max(len(original), 1), 3)

        log.info(
            "pii_scrubber.done",
            original_name=meta.get("original_name"),
            emails_found=len(meta["original_emails"]),
            phones_found=len(meta["original_phones"]),
        )
        return text, meta

    @staticmethod
    def restore_name(scrubbed_text: str, original_name: str) -> str:
        """Re-insert candidate name for display purposes."""
        if original_name:
            return scrubbed_text.replace("[CANDIDATE]", original_name, 1)
        return scrubbed_text
