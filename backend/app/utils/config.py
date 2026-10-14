# NOTE: most values are read directly from environment variables in main.py /
# individual routers where needed. This module also hosts small shared helpers.

import os

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
ENV = os.getenv("ENV", "development")


def persistence_disabled() -> bool:
    """True when GAIDA must not write to the live database (dry-run mode).

    Set ``GAIDA_DISABLE_PERSISTENCE=1`` to stop GAIDA from writing session,
    interaction, and counselor-alert rows to Supabase. Reads (consent checks,
    session rehydration) are unaffected, so detection behaviour is identical —
    only the side effects are suppressed.

    This exists so offline harnesses (``tests/test_detection.py``) and the
    pytest suite can exercise the real pipeline without polluting the shared
    production database with fake Crisis alerts. It is evaluated at call time,
    not import time, so callers may set the variable after importing modules.
    """
    return os.getenv("GAIDA_DISABLE_PERSISTENCE", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
