# backend/app/services/rate_limiter.py

import time
from fastapi import HTTPException

RATE_LIMIT = 5
TIME_WINDOW = 60

users_requests = {}

def check_rate_limit(session_id: str):  # ← changed from request: Request
    """Raises HTTPException if session exceeds rate limit."""
    current_time = time.time()

    if session_id not in users_requests:
        users_requests[session_id] = []

    # Remove requests older than TIME_WINDOW
    users_requests[session_id] = [
        timestamp for timestamp in users_requests[session_id]
        if current_time - timestamp < TIME_WINDOW
    ]

    if len(users_requests[session_id]) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    users_requests[session_id].append(current_time)