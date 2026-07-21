"""
Enterprise Observability — OpenTelemetry tracing, custom metrics, structured logging.
Distributed tracing across services, Prometheus metrics, correlation IDs.
"""
import time
import uuid
from functools import wraps
from typing import Callable, Any, Optional
from contextlib import contextmanager
from ..core.logger import log


# ─── Prometheus Metrics ───────────────────────────────────────────────────────
# Extends prometheus_fastapi_instrumentator with custom business metrics

from prometheus_client import Counter, Histogram, Gauge, Summary

METRICS_PREFIX = "ai_ats"

# API metrics
api_request_duration = Histogram(
    f"{METRICS_PREFIX}_request_duration_seconds",
    "Request duration in seconds",
    ["method", "endpoint", "status"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

api_requests_total = Counter(
    f"{METRICS_PREFIX}_requests_total",
    "Total API requests",
    ["method", "endpoint", "status"],
)

# Business metrics
candidates_screened = Counter(
    f"{METRICS_PREFIX}_candidates_screened_total",
    "Total candidates screened",
    ["org_id", "status"],
)

resumes_uploaded_total = Counter(
    f"{METRICS_PREFIX}_resumes_uploaded_total",
    "Total resumes uploaded",
    ["source_format"],
)

screening_duration = Histogram(
    f"{METRICS_PREFIX}_screening_duration_seconds",
    "Resume screening processing time",
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
)

active_websockets = Gauge(
    f"{METRICS_PREFIX}_active_websockets",
    "Number of active WebSocket connections",
)

auth_events_total = Counter(
    f"{METRICS_PREFIX}_auth_events_total",
    "Authentication events",
    ["event", "status"],
)

# LLM / AI metrics
llm_call_duration = Histogram(
    f"{METRICS_PREFIX}_llm_call_duration_seconds",
    "LLM API call duration",
    ["model", "operation"],
    buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 20.0, 60.0),
)

llm_call_failures = Counter(
    f"{METRICS_PREFIX}_llm_call_failures_total",
    "Failed LLM API calls",
    ["model", "operation"],
)

# Database metrics
db_query_duration = Histogram(
    f"{METRICS_PREFIX}_db_query_duration_seconds",
    "Database query duration",
    ["operation"],
    buckets=(0.001, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0),
)

db_pool_size = Gauge(
    f"{METRICS_PREFIX}_db_pool_size",
    "Database connection pool size",
)

db_pool_available = Gauge(
    f"{METRICS_PREFIX}_db_pool_available",
    "Database connections available in pool",
)

# Job queue metrics
celery_tasks_total = Counter(
    f"{METRICS_PREFIX}_celery_tasks_total",
    "Celery tasks processed",
    ["task_name", "status"],
)

celery_queue_length = Gauge(
    f"{METRICS_PREFIX}_celery_queue_length",
    "Number of pending tasks in queue",
    ["queue"],
)


# ─── Distributed Tracing (Simplified without external OTLP) ───────────────────

_trace_counter = 0

@contextmanager
def trace_span(operation_name: str, attributes: dict = None):
    """Lightweight tracing context manager. Emits log correlation + timing.
    
    For full OpenTelemetry, replace with:
        from opentelemetry import trace
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span(operation_name) as span:
            ...
    """
    global _trace_counter
    _trace_counter += 1
    trace_id = uuid.uuid4().hex[:16]
    span_id = uuid.uuid4().hex[:8]
    parent_id = getattr(trace_span, "_current_span_id", None)

    start = time.time()
    try:
        setattr(trace_span, "_current_span_id", span_id)
        yield {"trace_id": trace_id, "span_id": span_id, "parent_id": parent_id}
    except Exception as e:
        duration = time.time() - start
        log.error(
            "trace_error",
            operation=operation_name,
            trace_id=trace_id,
            span_id=span_id,
            error=str(e),
            duration_ms=round(duration * 1000, 2),
            **(attributes or {}),
        )
        raise
    finally:
        duration = time.time() - start
        setattr(trace_span, "_current_span_id", parent_id)
        log.info(
            "trace_span",
            operation=operation_name,
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_id,
            duration_ms=round(duration * 1000, 2),
            **(attributes or {}),
        )


def instrument(func: Callable) -> Callable:
    """Decorator to time and trace any async function."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        with trace_span(func.__qualname__) as span:
            return await func(*args, **kwargs)
    return wrapper


# ─── Health Check Collectors ──────────────────────────────────────────────────

async def collect_health_metrics(db_session=None, redis_client=None):
    """Collect detailed health metrics for prometheus endpoint."""
    health_gauges = {}

    # DB pool health
    if db_session:
        try:
            pool = db_session.get_bind().pool
            db_pool_size.set(pool.size())
            db_pool_available.set(pool.size() - pool.checkedin())
            health_gauges["database"] = 1
        except Exception as e:
            health_gauges["database"] = 0
            log.error("health_check.db_failed", error=str(e))

    # Redis health
    if redis_client:
        try:
            pong = await redis_client.ping()
            health_gauges["redis"] = 1 if pong else 0
        except Exception:
            health_gauges["redis"] = 0

    return health_gauges


# ─── Structured Audit Logging ─────────────────────────────────────────────────

def audit_log(action: str, entity_type: str, entity_id: Any,
              user_id: Optional[int] = None, org_id: Optional[int] = None,
              details: dict = None):
    """Emit structured audit event for centralized log collection."""
    log.info(
        "audit_event",
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        user_id=str(user_id) if user_id else None,
        org_id=str(org_id) if org_id else None,
        timestamp=time.time(),
        **(details or {}),
    )

    # Increment Prometheus counter
    auth_events_total.labels(event=action, status="success").inc()
