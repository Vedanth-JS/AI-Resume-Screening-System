"""
Performance Optimization Layer — Background task routing, bulk operations,
lazy imports, connection pooling, and resource management.
Configures Celery priority queues and async processing patterns.
"""

# ─── Celery Priority Queue Configuration ──────────────────────────────────────
# Queue priority: screening (critical) > notifications (standard) > analytics (low)

CELERY_QUEUE_CONFIG = {
    "task_queues": {
        "screening": {"priority": 10},      # Resume processing — highest priority
        "notifications": {"priority": 7},    # User notifications
        "analytics": {"priority": 5},        # Analytics computation
        "batch": {"priority": 3},            # Bulk operations
        "maintenance": {"priority": 1},      # Cleanup, housekeeping
    },
    "task_default_queue": "screening",
    "task_default_priority": 5,
    "worker_concurrency": 4,                # Per worker
    "worker_prefetch_multiplier": 1,        # Fair distribution
    "task_acks_late": True,                 # Re-deliver on failure
    "task_reject_on_worker_lost": True,
    "task_time_limit": 600,                 # 10 min hard limit
    "task_soft_time_limit": 540,            # 9 min soft limit
}

# ─── Bulk Processing Patterns ─────────────────────────────────────────────────

async def process_in_chunks(items: list, chunk_size: int, processor_func, *args, **kwargs):
    """Process a large list in chunks to avoid memory pressure."""
    results = []
    for i in range(0, len(items), chunk_size):
        chunk = items[i:i + chunk_size]
        result = await processor_func(chunk, *args, **kwargs)
        results.extend(result if isinstance(result, list) else [result])
    return results


# ─── Lazy Import Pattern ──────────────────────────────────────────────────────

# Heavy modules deferred until first access to reduce startup time
_lazy_modules = {}

def lazy_import(module_name: str):
    """Import a module only when first accessed."""
    if module_name not in _lazy_modules:
        import importlib
        _lazy_modules[module_name] = importlib.import_module(module_name)
    return _lazy_modules[module_name]


# ─── Connection Pool Warming ──────────────────────────────────────────────────

async def warm_up_connections(db_session, redis_client=None, num_connections: int = 5):
    """Pre-establish database connections on startup."""
    import asyncio
    # Execute simple queries to fill the connection pool
    from sqlalchemy import text
    tasks = [db_session.execute(text("SELECT 1")) for _ in range(num_connections)]
    await asyncio.gather(*tasks, return_exceptions=True)


# ─── Resource Cleanup ─────────────────────────────────────────────────────────

async def cleanup_expired_sessions(db_session):
    """Periodic cleanup of expired sessions and tokens."""
    from sqlalchemy import text
    await db_session.execute(
        text("DELETE FROM login_attempts WHERE created_at < NOW() - INTERVAL '7 days'")
    )
    await db_session.execute(
        text("UPDATE user_sessions SET status = 'expired' WHERE expires_at < NOW() AND status = 'active'")
    )
    await db_session.commit()
