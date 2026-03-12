# backend/app/services/rate_limiter.py

import time
from fastapi import HTTPException, Request

# Simple in-memory rate limiting
# Keyed by user IP, value is last request timestamp
RATE_LIMIT = 5          # number of requests
TIME_WINDOW = 60        # time window in seconds

users_requests = {}

def check_rate_limit(request: Request):
    """Raises HTTPException if user exceeds rate limit."""
    user_ip = request.client.host
    current_time = time.time()
    
    if user_ip not in users_requests:
        users_requests[user_ip] = []

    # Remove requests older than TIME_WINDOW
    users_requests[user_ip] = [
        timestamp for timestamp in users_requests[user_ip]
        if current_time - timestamp < TIME_WINDOW
    ]

    if len(users_requests[user_ip]) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    # Record this request
    users_requests[user_ip].append(current_time)