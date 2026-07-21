"""
Image Resume Parser — OCR for PNG/JPG/WebP/TIFF resume images.
Uses Tesseract with language detection and pre-processing for quality.
"""
import io
import asyncio
from typing import Tuple, Optional
from concurrent.futures import ThreadPoolExecutor

try:
    from PIL import Image, ImageEnhance, ImageFilter
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

_EXECUTOR = ThreadPoolExecutor(max_workers=4)


# ISO 639-1 → Tesseract language codes
_LANG_MAP = {
    "en": "eng", "es": "spa", "fr": "fra", "de": "deu", "zh": "chi_sim",
    "ja": "jpn", "ko": "kor", "pt": "por", "it": "ita", "ru": "rus",
    "ar": "ara", "hi": "hin", "nl": "nld", "sv": "swe", "tr": "tur",
    "pl": "pol", "vi": "vie", "th": "tha",
}


class ImageParser:
    SUPPORTED_FORMATS = {".png", ".jpg", ".jpeg", ".webp", ".tiff", ".tif", ".bmp"}

    @staticmethod
    async def extract_text(
        file_content: bytes,
        language: str = "eng",
        dpi: int = 300,
    ) -> Tuple[str, dict]:
        """
        Extract text from an image file using Tesseract OCR.
        Returns (text, metadata).
        """
        meta = {
            "extraction_method": "ocr",
            "confidence": 0.0,
            "text_length": 0,
            "language": language,
            "preprocessed": True,
        }

        if not _PIL_AVAILABLE or not _TESSERACT_AVAILABLE:
            log.warning("image_parser.ocr_unavailable")
            return "", meta

        loop = asyncio.get_running_loop()
        try:
            text, conf = await loop.run_in_executor(
                _EXECUTOR, _ocr_image, file_content, language
            )
            meta["confidence"] = round(conf, 2)
            meta["text_length"] = len(text) if text else 0
            return (text or ""), meta
        except Exception as e:
            log.error("image_parser.ocr_failed", error=str(e))
            return "", meta

    @staticmethod
    def resolve_language_code(iso_lang: str) -> str:
        """Convert ISO 639-1 code to Tesseract language code, with fallback."""
        return _LANG_MAP.get(iso_lang, "eng")


def _ocr_image(content: bytes, language: str) -> Tuple[str, float]:
    """Preprocess image and run OCR."""
    img = Image.open(io.BytesIO(content))

    # Convert to RGB if needed
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    # Pre-processing: greyscale + contrast + sharpen
    if img.mode == "RGB":
        img = img.convert("L")
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.0)
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(1.5)
    img = img.filter(ImageFilter.MedianFilter(size=3))

    # OCR with confidence data
    data = pytesseract.image_to_data(img, lang=language, output_type=pytesseract.Output.DICT)
    text = " ".join([w for w in data.get("text", []) if w.strip()])
    confs = [int(c) for c in data.get("conf", []) if c != "-1"]
    avg_conf = float(sum(confs) / len(confs)) / 100.0 if confs else 0.0

    return text, avg_conf
