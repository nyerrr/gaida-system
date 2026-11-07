"""Shared pytest configuration.

The test suite must never write to the live Supabase database. Without this,
any test that runs a real crisis message through the pipeline (directly or via
the ``/virtual-agent`` endpoint) inserts a genuine-looking "pending" Crisis row
into the shared ``counselor_alerts`` table — which is exactly how a counselor
dashboard ended up showing ~50 fake alerts.

Setting ``GAIDA_DISABLE_PERSISTENCE=1`` before the app is imported puts the
process in dry-run mode: session/interaction/alert rows are not written and
counselors are not emailed, while detection still runs identically. The flag is
read at call time in ``app.utils.config.persistence_disabled``.
"""

import os
import json

os.environ.setdefault("GAIDA_DISABLE_PERSISTENCE", "1")
os.environ["AUTH_REVOCATION_BACKEND"] = "memory"
# Authentication tests use an explicit test-only roster; production defaults
# contain no demo student or counselor accounts.
os.environ.setdefault("ALLOW_DEMO_ACCOUNTS", "1")
os.environ.setdefault("DEMO_STUDENT_ACCOUNTS", json.dumps([
    {
        "student_number": "2024001",
        "email": "student1@ue.edu.ph",
        "access_code": "ACCESS123",
        "name": "Maria Santos",
    },
]))
