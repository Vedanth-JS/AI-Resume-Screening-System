"""
Enterprise Security Layer — Middleware, Headers, Input Sanitization, Output Encoding.
OWASP Top 10 protections, CSP, CORS hardening, XSS prevention, CSRF protection.
"""
import re
import html
import json
from typing import List, Optional, Tuple
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from ..core.config import settings


# ─── Security Headers Middleware ───────────────────────────────────────────────

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds OWASP-recommended security headers to every response."""

    async def dispatch(self, request: Request, call_next: Request) -> Response:
        response = await call_next(request)

        headers = response.headers

        # HSTS — force HTTPS for 1 year
        if settings.APP_ENV == "production":
            headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        # Prevent MIME type sniffing
        headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        headers["X-Frame-Options"] = "DENY"

        # XSS protection (legacy, but adds defense-in-depth)
        headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer policy — only send origin for same-origin
        headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions policy — restrict browser features
        headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), "
            "interest-cohort=(), usb=(), payment=()"
        )

        # Remove server fingerprinting
        headers["Server"] = ""

        # Cache control for sensitive pages
        if request.url.path.startswith("/api/auth"):
            headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            headers["Pragma"] = "no-cache"

        return response


# ─── Content Security Policy ───────────────────────────────────────────────────

class CSPMiddleware(BaseHTTPMiddleware):
    """Content Security Policy header generation."""

    CSP_TEMPLATE = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self'; "
        "connect-src 'self' https://accounts.google.com https://github.com "
        "https://login.microsoftonline.com https://www.linkedin.com; "
        "frame-src 'none'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "upgrade-insecure-requests;"
    )

    async def dispatch(self, request: Request, call_next: Request) -> Response:
        response = await call_next(request)
        # Only set for HTML responses
        content_type = response.headers.get("content-type", "")
        if "text/html" in content_type:
            response.headers["Content-Security-Policy"] = self.CSP_TEMPLATE
        return response


# ─── CORS Configuration Helper ─────────────────────────────────────────────────

def get_cors_config() -> dict:
    """Production-safe CORS configuration."""
    origins = settings.CORS_ORIGINS if settings.CORS_ORIGINS != ["*"] else (
        ["http://localhost:3000", "http://localhost:4173"]  # Safe defaults
    )
    return {
        "allow_origins": origins,
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "DELETE", "PATCH"],
        "allow_headers": [
            "Authorization", "Content-Type", "X-Request-ID",
            "X-API-Key", "X-Device-Name", "X-CSRF-Token",
        ],
        "expose_headers": ["X-Request-ID", "X-RateLimit-Remaining"],
        "max_age": 600,  # 10 minutes
    }


# ─── Input Sanitization ────────────────────────────────────────────────────────

# Regex patterns for sanitization
_SCRIPT_TAG_RE = re.compile(r"<\s*script[^>]*>.*?<\s*/\s*script\s*>", re.I | re.S)
_EVENT_HANDLER_RE = re.compile(r"\bon\w+\s*=", re.I)
_JAVASCRIPT_URI_RE = re.compile(r"javascript\s*:", re.I)
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_SQL_COMMENT_RE = re.compile(r"/\*.*?\*/", re.S)
_SQL_UNION_RE = re.compile(r"\bunion\b.*\bselect\b", re.I)
_SQL_DROP_RE = re.compile(r"\bdrop\b\s+\btable\b", re.I)
_DANGEROUS_CMDS_RE = re.compile(r"(;|\|\||&&)\s*(rm\b|shutdown|reboot|curl|wget|nc\b)", re.I)

# Unicode homoglyph sets for defanging (normalize to Latin-1)
_CONFUSABLE_MAP = {
    "\u0430": "a", "\u0435": "e", "\u043E": "o", "\u0440": "p", "\u0441": "c",
    "\u0455": "s", "\u0458": "j", "\u03F2": "c", "\u03B5": "e",
}


def sanitize_html(text: str) -> str:
    """Strip dangerous HTML/JavaScript from user input."""
    if not text:
        return ""
    # Normalize confusable characters
    for confusable, ascii_char in _CONFUSABLE_MAP.items():
        text = text.replace(confusable, ascii_char)
    text = _SCRIPT_TAG_RE.sub(" [REMOVED] ", text)
    text = _EVENT_HANDLER_RE.sub(" data-blocked=", text)
    text = _JAVASCRIPT_URI_RE.sub("blocked:", text)
    return text


def sanitize_sql_identifiers(text: str) -> str:
    """Remove SQL injection attempts from user-supplied identifiers."""
    if not text:
        return ""
    text = _SQL_COMMENT_RE.sub(" ", text)
    text = _SQL_UNION_RE.sub(" [BANNED] ", text)
    text = _SQL_DROP_RE.sub(" [BANNED] ", text)
    return text


def sanitize_for_llm(text: str, max_length: int = 12000) -> str:
    """Sanitize user text before sending to LLM to prevent prompt injection."""
    if not text:
        return ""
    # Truncate
    text = text[:max_length]
    # Remove any injected "system:" / "assistant:" / "human:" role prompts
    text = re.sub(r"(?im)^\s*(system|assistant|human|user)\s*:", "[BLOCKED]", text)
    # Remove XML/CDATA blocks
    text = re.sub(r"<!\[CDATA\[.*?\]\]>", " [CDATA_REMOVED] ", text, flags=re.S)
    # Remove any "ignore previous instructions" or similar jailbreak patterns
    jailbreak_patterns = [
        r"(?i)ignore\s+(all\s+)?(previous|above|prior)\s+(instructions|prompts|directives)",
        r"(?i)you\s+are\s+now\s+\w+\s+(mode|bot|assistant)",
        r"(?i)pretend\s+(to|you\s+are)",
        r"(?i)new\s+system\s+(prompt|instructions?)",
        r"(?i)DAN\s*mode|jailbreak|bypass",
    ]
    for pattern in jailbreak_patterns:
        text = re.sub(pattern, " [REQUEST_BLOCKED] ", text)
    return text


def sanitize_filename(filename: str) -> Tuple[str, str]:
    """Sanitize uploaded filename. Returns (safe_name, extension)."""
    import os.path
    # Strip path traversal
    name = os.path.basename(filename)
    # Remove null bytes
    name = name.replace("\x00", "")
    # Keep only alphanumeric, dash, underscore, dot
    name = re.sub(r"[^\w\-.]", "_", name)
    # Prevent double extensions like .pdf.exe by keeping the first suffix only.
    parts = name.split(".")
    if len(parts) >= 3:
        base = parts[0]
        ext = "." + parts[1].lower()
        return base[:100], ext
    parts = name.rsplit(".", 1)
    if len(parts) == 2:
        base, ext = parts[0], "." + parts[1].lower()
        return base[:100], ext
    return name[:100], ""


def validate_file_type(filename: str, content: bytes) -> bool:
    """Validate file content against its claimed extension using magic bytes."""
    magic_bytes = {
        ".pdf": b"%PDF",
        ".png": b"\x89PNG\r\n\x1a\n",
        ".jpg": b"\xff\xd8\xff",
        ".jpeg": b"\xff\xd8\xff",
        ".docx": b"PK\x03\x04",  # ZIP format
        ".zip": b"PK\x03\x04",
        ".tiff": b"II*\x00" if content[:4] != b"MM\x00*" else b"MM\x00*",
    }

    _, ext = sanitize_filename(filename)
    expected_magic = magic_bytes.get(ext)
    if expected_magic and not content[:len(expected_magic)] == expected_magic:
        return False
    return True


def validate_file_size(content_length: int, max_mb: int = 10) -> bool:
    """Check file doesn't exceed maximum size."""
    return content_length <= max_mb * 1024 * 1024


# ─── Prompt Injury Protection ──────────────────────────────────────────────────

def build_llm_prompt(template: str, **kwargs) -> str:
    """Build a prompt for LLM with sanitized inputs and explicit boundaries."""
    sanitized = {}
    for key, value in kwargs.items():
        if isinstance(value, str):
            sanitized[key] = sanitize_for_llm(value)
        else:
            sanitized[key] = value

    # Wrap user content in explicit boundaries
    if "resume_text" in sanitized:
        sanitized["resume_text"] = (
            "<resume_data>\n" + sanitized["resume_text"] + "\n</resume_data>"
        )
    if "jd_text" in sanitized:
        sanitized["jd_text"] = (
            "<job_description>\n" + sanitized["jd_text"] + "\n</job_description>"
        )

    return template.format(**sanitized)


# ─── Rate Limiter ──────────────────────────────────────────────────────────────

import time
from collections import defaultdict

class InMemoryRateLimiter:
    """Fallback rate limiter when Redis unavailable. Tracks per-IP request counts."""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self._buckets: dict = defaultdict(list)

    def is_allowed(self, key: str) -> Tuple[bool, int]:
        """Returns (allowed, remaining)."""
        now = time.time()
        bucket = self._buckets[key]
        # Prune old entries
        bucket[:] = [t for t in bucket if now - t < self.window]
        remaining = max(0, self.max_requests - len(bucket))
        if len(bucket) >= self.max_requests:
            return False, remaining
        bucket.append(now)
        return True, remaining


# Global rate limiter instance
_api_rate_limiter = InMemoryRateLimiter(
    max_requests=settings.RATE_LIMIT_API_PER_MINUTE, window_seconds=60
)


# ─── GDPR Data Classification ──────────────────────────────────────────────────

GDPR_SENSITIVE_FIELDS = {
    "email": "PII_EMAIL",
    "phone": "PII_PHONE",
    "name": "PII_NAME",
    "address": "PII_ADDRESS",
    "ip_address": "PII_NETWORK",
    "location": "PII_LOCATION",
}


def classify_data_field(field_name: str) -> str:
    """Classify a data field for GDPR compliance."""
    return GDPR_SENSITIVE_FIELDS.get(field_name, "NON_PII")


def mask_pii_for_logs(data: dict) -> dict:
    """Redact PII from log output."""
    if not data:
        return {}
    masked = {}
    for key, value in data.items():
        if key in GDPR_SENSITIVE_FIELDS and isinstance(value, str):
            masked[key] = value[:3] + "***" + value[-3:] if len(value) > 6 else "***"
        else:
            masked[key] = value
    return masked


# ─── TLS / HSTS Config ─────────────────────────────────────────────────────────

def enforce_https(request: Request) -> Optional[JSONResponse]:
    """Middleware dependency: redirect HTTP to HTTPS in production."""
    if settings.APP_ENV == "production":
        # Check for forwarded protocol (behind reverse proxy)
        forwarded_proto = request.headers.get("x-forwarded-proto", "")
        if forwarded_proto and forwarded_proto != "https":
            url = request.url.replace(scheme="https")
            return JSONResponse(
                {"detail": "HTTPS required"},
                status_code=301,
                headers={"Location": str(url)},
            )
    return None
