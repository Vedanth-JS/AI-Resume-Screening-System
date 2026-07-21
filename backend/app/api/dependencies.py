"""
Shared API Utilities — Pagination, Filtering, Sorting, Search.
Standardizes list endpoints across all resources.
"""
from typing import TypeVar, Generic, List, Optional, Any
from dataclasses import dataclass
from pydantic import BaseModel, Field, field_validator
from fastapi import Query
from datetime import datetime
import re


# ─── Pagination ────────────────────────────────────────────────────────────────

@dataclass
class PaginationParams:
    """Extracted from query params for any list endpoint."""
    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


def get_pagination(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
) -> PaginationParams:
    return PaginationParams(page=page, page_size=page_size)


class PaginatedResponse(BaseModel, Generic[Generic]):
    """Standard wrapper for paginated list responses."""
    items: List[Any] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 0
    has_next: bool = False
    has_previous: bool = False

    @staticmethod
    def create(items: List[Any], total: int, pagination: PaginationParams):
        total_pages = max(1, (total + pagination.page_size - 1) // pagination.page_size)
        return PaginatedResponse(
            items=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            total_pages=total_pages,
            has_next=pagination.page < total_pages,
            has_previous=pagination.page > 1,
        )


# ─── Sorting ───────────────────────────────────────────────────────────────────

@dataclass
class SortParams:
    """Unified sort specification."""
    field: str = "created_at"
    direction: str = "desc"  # asc or desc

    @property
    def is_ascending(self) -> bool:
        return self.direction == "asc"


def get_sort(
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$", description="Sort direction"),
) -> SortParams:
    return SortParams(field=sort_by, direction=sort_dir)


# ─── Filtering ─────────────────────────────────────────────────────────────────

# Whitelist of filterable fields per entity (prevents SQL injection via column names)
ALLOWED_FILTERS = {
    "candidates": ["status", "name", "email", "created_at", "org_id"],
    "jobs": ["status", "title", "posted_at", "created_at", "org_id"],
    "applications": ["status", "score", "job_id", "created_at", "org_id"],
    "sessions": ["status", "device_type", "created_at"],
    "audit_logs": ["action", "entity_type", "created_at", "user_id", "org_id"],
    "notifications": ["is_read", "created_at"],
    "interviews": ["status", "scheduled_at", "interview_type"],
}


def validate_filters(entity: str, filters: Optional[str]) -> dict:
    """Parse and validate comma-separated filter string.
    Format: key:value,key:value  (e.g., 'status:active,score:>=70')
    """
    if not filters:
        return {}
    allowed = ALLOWED_FILTERS.get(entity, [])
    result = {}
    for part in filters.split(","):
        if ":" not in part:
            continue
        key, value = part.split(":", 1)
        key = key.strip().lower()
        if key not in allowed and not key.startswith("min_") and not key.startswith("max_"):
            continue  # silently ignore unknown filters

        # Parse filter operators
        if value.startswith(">="):
            result[f"{key}__gte"] = _parse_value(value[2:])
        elif value.startswith("<="):
            result[f"{key}__lte"] = _parse_value(value[2:])
        elif value.startswith(">"):
            result[f"{key}__gt"] = _parse_value(value[1:])
        elif value.startswith("<"):
            result[f"{key}__lt"] = _parse_value(value[1:])
        elif value.startswith("~"):  # fuzzy match
            result[f"{key}__like"] = f"%{value[1:]}%"
        else:
            result[key] = _parse_value(value)
    return result


def _parse_value(value: str) -> Any:
    """Parse string value to appropriate Python type."""
    value = value.strip()
    # Boolean
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    # Integer
    try:
        return int(value)
    except ValueError:
        pass
    # Float
    try:
        return float(value)
    except ValueError:
        pass
    # Datetime (ISO format)
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        pass
    return value


# ─── Search ─────────────────────────────────────────────────────────────────────

def get_search_query(
    q: Optional[str] = Query(None, description="Full-text search query"),
    search_fields: Optional[str] = Query(None, description="Comma-separated fields to search"),
) -> dict:
    """Build a search specification."""
    return {
        "query": q,
        "fields": (search_fields or "").split(",") if search_fields else [],
    }


# ─── Date Range ────────────────────────────────────────────────────────────────

def get_date_range(
    from_date: Optional[datetime] = Query(None, description="Filter from this date (ISO 8601)"),
    to_date: Optional[datetime] = Query(None, description="Filter to this date (ISO 8601)"),
) -> dict:
    return {"from_date": from_date, "to_date": to_date}


# ─── ETag / Conditional Requests ───────────────────────────────────────────────

def get_etag(entity_id: int, updated_at: datetime) -> str:
    """Generate an ETag from entity ID and update timestamp."""
    import hashlib
    raw = f"{entity_id}:{updated_at.isoformat()}"
    return hashlib.md5(raw.encode()).hexdigest()  # noqa: S324 — not crypto, just cache
