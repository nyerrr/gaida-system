"""Login accounts.

COUNSELOR accounts are no longer hardcoded for production. They come from the
COUNSELOR_ACCOUNTS environment variable, a JSON list such as

    [{"id": "COUNSELOR01", "password": "a-long-random-password",
      "name": "Dr. Jane Cruz", "email": "jane.cruz@ue.edu.ph"}]

(`email` is optional and only used to map a Google sign-in to the account.)

Student accounts must be supplied through STUDENT_ACCOUNTS, a JSON list with
the enrolled student's number, UE email, and access code. Thesis-defense demo
accounts are available only when ALLOW_DEMO_ACCOUNTS=1.
"""

import json
import os

_DEMO_STUDENT_ACCOUNTS = {
    "2024001": {
        "email": "student1@ue.edu.ph",
        "access_code": "ACCESS123",
        "name": "Maria Santos",
        "program": "BS Psychology",
        "year": 2,
        "role": "student",
    },
    "2024002": {
        "email": "student2@ue.edu.ph",
        "access_code": "ACCESS456",
        "name": "Juan dela Cruz",
        "program": "BS Computer Science",
        "year": 3,
        "role": "student",
    },
    "2024003": {
        "email": "student3@ue.edu.ph",
        "access_code": "ACCESS789",
        "name": "Ana Reyes",
        "program": "BS Nursing",
        "year": 1,
        "role": "student",
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


def _students_from_env(raw: str) -> dict:
    """Parse the enrolled student roster without retaining credentials in code."""
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
        student_number = str(item.get("student_number", "")).strip()
        email = str(item.get("email", "")).strip().lower()
        access_code = str(item.get("access_code", ""))
        if not student_number or not email or not access_code:
            continue
        accounts[student_number] = {
            "email": email,
            "access_code": access_code,
            "name": str(item.get("name") or student_number),
            "program": str(item.get("program") or ""),
            "year": item.get("year"),
            "role": "student",
        }
    return accounts


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
    """Build configured enrolled accounts and explicitly enabled demo accounts."""
    env = os.environ if env is None else env
    allow_demo = env.get("ALLOW_DEMO_ACCOUNTS", "").strip().lower() in (
        "1", "true", "yes", "on"
    )
    accounts = _students_from_env(env.get("STUDENT_ACCOUNTS", ""))
    if allow_demo:
        accounts.update(_DEMO_STUDENT_ACCOUNTS)
        accounts.update(_students_from_env(env.get("DEMO_STUDENT_ACCOUNTS", "")))
    configured = _counselors_from_env(env.get("COUNSELOR_ACCOUNTS", ""))
    if configured:
        accounts.update(configured)
    elif allow_demo:
        accounts.update(_DEMO_COUNSELORS)
    return accounts


TEST_CREDENTIALS = build_test_credentials()

if any(
    c.get("role") == "counselor" and c.get("access_code") == "counsel123"
    for c in TEST_CREDENTIALS.values()
):
    print("[security] demo counselor accounts are enabled - set COUNSELOR_ACCOUNTS before real use")
