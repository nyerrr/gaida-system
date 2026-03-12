import time
from collections import defaultdict

MAX_MESSAGES = 5
WINDOW_SECONDS = 10

#stores timestamps per user/session
message_log = defaultdict(list)

def check_rate_limit(user_id: str):
    now = time.time()

    timestamps = message_log[user_id]

    #remove timestamps outsie time window
    message_log[user_id] = [
        t for t in timestamps if now - t < WINDOW_SECONDS
    ]

    if len(message_log[user_id]) >= MAX_MESSAGES:
        raise Exception("Too many messages. Please wait for a few seconds.")
    
    message_log[user_id].append(now)