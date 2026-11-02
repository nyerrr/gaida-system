"""Login accounts.

STUDENT test accounts are demo accounts for the pilot login.

COUNSELOR accounts are no longer hardcoded for production. They come from the
COUNSELOR_ACCOUNTS environment variable, a JSON list such as

    [{"id": "COUNSELOR01", "password": "a-long-random-password",
      "name": "Dr. Jane Cruz", "email": "jane.cruz@ue.edu.ph"}]

(`email` is optional and only used to map a Google sign-in to the account.)

When COUNSELOR_ACCOUNTS is not set, the old demo counselors (COUNSELOR01 /
counsel123 and so on) are only available if ENVIRONMENT=development or
GAIDA_ALLOW_DEMO_COUNSELORS=1. On a deployed server with neither, the ID and
password counselor login simply has no accounts, and counselors sign in with
Google (COUNSELOR_EMAILS) instead. Nothing here changes how a login is checked
in app/api/auth.py: it still looks accounts up by role == "counselor".
"""

import json
import os

_STUDENT_ACCOUNTS = {
    "2024001": {
        "email": "student1@ue.edu.ph",
        "access_code": "ACCESS123",
        "name": "Maria Santos",
        "program": "BS Psychology",
        "year": 2,
    },
    "2024002": {
        "email": "student2@ue.edu.ph",
        "access_code": "ACCESS456",
        "name": "Juan dela Cruz",
        "program": "BS Computer Science",
        "year": 3,
    },
    "2024003": {
        "email": "student3@ue.edu.ph",
        "access_code": "ACCESS789",
        "name": "Ana Reyes",
        "program": "BS Nursing",
        "year": 1,
    },
}

_DEMO_COUNSELORS = {
    "COUNSELOR01": {
        "email": "counselor01",
        "access_code": "counsel123",
        "name": "Dr. Patricia Lim",
        "role": "counselor",
    },
    "COUNSELOR02": {
        "email": "counselor02",
        "access_code": "counsel202",
        "name": "Guidance Counselor 2",
        "role": "counselor",
    },
    "COUNSELOR03": {
        "email": "counselor03",
        "access_code": "counsel303",
        "name": "Guidance Counselor 3",
        "role": "counselor",
    },
    "COUNSELOR04": {
        "email": "counselor04",
        "access_code": "counsel404",
        "name": "Guidance Counselor 4",
        "role": "counselor",
    },
    "COUNSELOR05": {
        "email": "counselor05",
        "access_code": "counsel505",
        "name": "Guidance Counselor 5",
        "role": "counselor",
    },
}


def _counselors_from_env(raw: str) -> dict:
    """Parse COUNSELOR_ACCOUNTS. A malformed value yields no accounts rather
    than crashing the server at import time."""
    try:
        items = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    accounts = {}
    if not isinstance(items, list):
        return accounts
    for item in items:
        if not isinstance(item, dict):
            continue
        cid = str(item.get("id", "")).strip().upper()
        pw = str(item.get("password", ""))
        if not cid or not pw:
            continue
        accounts[cid] = {
            "email": str(item.get("email") or cid.lower()).strip().lower(),
            "access_code": pw,
            "name": str(item.get("name") or cid),
            "role": "counselor",
        }
    return accounts


def build_test_credentials(env=None) -> dict:
    """Student demo accounts plus whichever counselor accounts `env` allows."""
    env = os.environ if env is None else env
    accounts = dict(_STUDENT_ACCOUNTS)
    configured = _counselors_from_env(env.get("COUNSELOR_ACCOUNTS", ""))
    if configured:
        accounts.update(configured)
    elif (
        env.get("ENVIRONMENT", "").strip().lower() == "development"
        or env.get("GAIDA_ALLOW_DEMO_COUNSELORS", "").strip().lower() in ("1", "true", "yes")
    ):
        accounts.update(_DEMO_COUNSELORS)
    return accounts


TEST_CREDENTIALS = build_test_credentials()

if any(
    c.get("role") == "counselor" and c.get("access_code") == "counsel123"
    for c in TEST_CREDENTIALS.values()
):
    print("[security] demo counselor accounts are enabled - set COUNSELOR_ACCOUNTS before real use")
