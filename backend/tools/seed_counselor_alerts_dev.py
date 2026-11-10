"""Seed four synthetic alerts into a local Supabase instance for UI work.

This utility is intentionally limited to Supabase running on loopback at the
default local development port. It never accepts a remote host, and it only
writes when the explicit --confirm-local-dev-seed flag is supplied.

Run from the backend directory with local Supabase credentials configured:
    python tools/seed_counselor_alerts_dev.py --confirm-local-dev-seed
"""

from __future__ import annotations

import argparse
import os
from collections import Counter
from urllib.parse import urlsplit

from dotenv import load_dotenv
from supabase import create_client


SEEDS = (
    ("crisis", "Crisis", 100),
    ("high", "High", 85),
    ("moderate", "Moderate", 65),
    ("requested", "Requested", 0),
)
PREFIX = "gaida-layout-dev-seed-"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
LOCAL_PORT = 54321


def local_client():
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    load_dotenv(os.path.join(backend_dir, ".env"))
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_KEY", "").strip()
    parsed = urlsplit(url)

    if parsed.scheme != "http" or parsed.hostname not in LOCAL_HOSTS or parsed.port != LOCAL_PORT:
        raise SystemExit(
            "Refusing to seed: SUPABASE_URL must point to local Supabase "
            "on http://localhost:54321 (or another loopback host)."
        )
    if not key:
        raise SystemExit("Refusing to seed: SUPABASE_KEY is not configured.")

    return create_client(url, key)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--confirm-local-dev-seed",
        action="store_true",
        help="confirm these synthetic rows should be added to local development data",
    )
    args = parser.parse_args()
    if not args.confirm_local_dev_seed:
        parser.error("pass --confirm-local-dev-seed to write synthetic local rows")

    client = local_client()
    table = client.table("counselor_alerts")
    rows = table.select("session_id,severity").execute().data or []
    existing = {
        row["session_id"]: row.get("severity")
        for row in rows
        if str(row.get("session_id", "")).startswith(PREFIX)
    }
    expected = {f"{PREFIX}{slug}": severity for slug, severity, _ in SEEDS}
    conflicts = [sid for sid, severity in existing.items() if expected.get(sid) != severity]
    if conflicts:
        raise SystemExit("Refusing to seed: a known layout seed ID has an unexpected severity.")

    missing = [(slug, severity, score) for slug, severity, score in SEEDS if f"{PREFIX}{slug}" not in existing]
    if missing:
        payload = [
            {
                "session_id": f"{PREFIX}{slug}",
                "user_id": "GAIDA-DEV-LAYOUT-SEED",
                "intent": "layout_verification_seed",
                "anxiety_score": score,
                "severity": severity,
                "message": "Synthetic layout verification alert; not a real student report.",
                "status": "pending",
                "deleted": False,
            }
            for slug, severity, score in missing
        ]
        table.insert(payload).execute()

    final_rows = table.select("session_id,severity").execute().data or []
    seeded = [row for row in final_rows if row.get("session_id") in expected]
    counts = Counter(row.get("severity") for row in seeded)
    if len(seeded) != len(SEEDS) or any(counts[severity] != 1 for _, severity, _ in SEEDS):
        raise SystemExit(f"Seed verification failed: {dict(counts)}")

    print("Verified local synthetic alert counts:", dict(counts))


if __name__ == "__main__":
    main()
