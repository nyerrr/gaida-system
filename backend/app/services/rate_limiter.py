# backend/app/services/rate_limiter.py

import time
from fastapi import HTTPException

RATE_LIMIT = 5
TIME_WINDOW = 60
CLEANUP_INTERVAL = 300  # sweep stale sessions every 5 min

users_requests = {}
_last_cleanup = time.time()


def _window_for_bucket(bucket_key: str) -> int:
    """Recover a bucket's own window from its key suffix (see check_rate_limit)
    so a stricter/longer-window bucket (e.g. ":w3600") isn't swept as stale
    just because it's been quiet for longer than the 60s default window —
    that would silently reset its count early and undermine the stricter limit."""
    if ":w" in bucket_key:
        try:
            return int(bucket_key.rsplit(":w", 1)[1])
        except ValueError:
            pass
    return TIME_WINDOW


def _cleanup_stale_sessions(current_time: float):
    """Remove session entries with no requests left in the window."""
    stale = [
        sid for sid, timestamps in users_requests.items()
        if not timestamps or current_time - timestamps[-1] >= _window_for_bucket(sid)
    ]
    for sid in stale:
        del users_requests[sid]


def check_rate_limit(session_id: str, limit: int = RATE_LIMIT, window: int = TIME_WINDOW):
    """Raises HTTPException if session exceeds rate limit.

    `limit`/`window` let a specific call site use a stricter bucket than the
    global default (e.g. the research withdrawal endpoint, which should allow
    far fewer attempts per hour than an ordinary login does per minute) while
    every existing caller that doesn't pass them keeps the original behavior.
    Each (session_id, window) pair gets its own bucket internally, so a
    stricter caller can't be starved by a looser one sharing the same key.
    """
    global _last_cleanup
    current_time = time.time()
    bucket_key = session_id if window == TIME_WINDOW else f"{session_id}:w{window}"

    if bucket_key not in users_requests:
        users_requests[bucket_key] = []

    # Remove requests older than this bucket's window
    users_requests[bucket_key] = [
        timestamp for timestamp in users_requests[bucket_key]
        if current_time - timestamp < window
    ]

    if len(users_requests[bucket_key]) >= limit:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    users_requests[bucket_key].append(current_time)

    # Periodic sweep so idle sessions don't accumulate forever
    if current_time - _last_cleanup > CLEANUP_INTERVAL:
        _cleanup_stale_sessions(current_time)
        _last_cleanup = current_time