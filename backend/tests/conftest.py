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

os.environ.setdefault("GAIDA_DISABLE_PERSISTENCE", "1")
