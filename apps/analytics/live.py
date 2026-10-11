"""Live-visitor tracking.

Uses the Django cache (Redis in production, LocMem in local dev) to keep a set
of session keys with timestamps, plus a per-session reference count so multiple
tabs from one visitor are counted once.
"""
import time

from django.conf import settings
from django.core.cache import cache

VISITORS_KEY = "live_visitors"
REFS_KEY = "live_visitor_refs"
TTL = getattr(settings, "LIVE_VISITOR_TTL_SECONDS", 300)
CACHE_TTL = TTL * 2


def _get(key):
    return cache.get(key) or {}


def cleanup_stale():
    now = time.time()
    visitors = _get(VISITORS_KEY)
    stale = [sk for sk, ts in visitors.items() if now - ts > TTL]
    if stale:
        for sk in stale:
            visitors.pop(sk, None)
        cache.set(VISITORS_KEY, visitors, CACHE_TTL)
    return len(visitors)


def add_visitor(session_key):
    if not session_key:
        return cleanup_stale()
    refs = _get(REFS_KEY)
    refs[session_key] = refs.get(session_key, 0) + 1
    visitors = _get(VISITORS_KEY)
    visitors[session_key] = time.time()
    cache.set(REFS_KEY, refs, CACHE_TTL)
    cache.set(VISITORS_KEY, visitors, CACHE_TTL)
    return cleanup_stale()


def remove_visitor(session_key):
    if not session_key:
        return cleanup_stale()
    refs = _get(REFS_KEY)
    remaining = refs.get(session_key, 1) - 1
    if remaining <= 0:
        refs.pop(session_key, None)
        visitors = _get(VISITORS_KEY)
        visitors.pop(session_key, None)
        cache.set(VISITORS_KEY, visitors, CACHE_TTL)
    else:
        refs[session_key] = remaining
    cache.set(REFS_KEY, refs, CACHE_TTL)
    return cleanup_stale()


def live_count():
    return cleanup_stale()
