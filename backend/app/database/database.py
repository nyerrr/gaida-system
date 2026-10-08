"""Supabase client.

This module deliberately does *not* raise at import time.

`app.main` reaches it through `app.services.session_manager` (module-level
`from app.database.database import supabase`, line 4), so a `raise` here kills
`import app.main` outright -- which means uvicorn never prints "Started server
process", never binds, and never serves `/health`. The deploy platform then
reports a healthcheck failure and declares the deployment crash-looping, with
a raw traceback interleaved into the log so thoroughly that the line naming the
exception gets cut off. That is exactly how this backend's publish gate became
unpassable: a missing config value looked identical to a broken build.

So credentials are validated but never fatal *at import*. If they are absent,
the process still boots, `/health` still answers 200, and the full diagnostic
is printed once to stderr at import and raised again on first real use -- so
the failure is impossible to miss without ever being able to hide the server.

This matters more than it looks: `.env` is gitignored (see the root
`.gitignore`), so it exists in the Replit workspace -- where `python -c
"import app.main"` succeeds -- while a deployment built from git does not have
it. Whether the deployment has its own secrets is then the difference between
a working app and a crash loop, and that difference used to be invisible.
"""

import sys
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

import os

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


def _describe_config_problem() -> str:
    env_path = Path(".env").resolve()
    return (
        "Missing Supabase credentials.\n"
        f"  - Expected config file: {env_path} (exists={env_path.exists()})\n"
        f"  - SUPABASE_URL set: {bool(SUPABASE_URL)}\n"
        f"  - SUPABASE_KEY set: {bool(SUPABASE_KEY)}\n"
        "  Fix: copy backend/.env.example to backend/.env and fill in your "
        "real values, or add SUPABASE_URL and SUPABASE_KEY to this "
        "deployment's Secrets."
    )


class UnconfiguredSupabase:
    """Stand-in returned when credentials are missing or rejected.

    It looks enough like the real client that importing it is harmless --
    which is the point -- but the first attempt to actually touch Supabase
    raises with the full diagnostic instead of failing mysteriously somewhere
    deeper in the stack.
    """

    def __init__(self, message: str) -> None:
        self._message = message

    def __getattr__(self, name: str):
        # Dunders must stay AttributeError so that `hasattr()` and any
        # introspection by libraries keep working normally.
        if name.startswith("__"):
            raise AttributeError(name)

        message = self._message

        # Deliberately returns rather than raises, so `hasattr(client, "table")`
        # answers honestly instead of propagating a RuntimeError out of an
        # inspection. The failure belongs where the query is attempted.
        def _fail(*_args, **_kwargs):
            raise RuntimeError(f"{message}\n  (raised via supabase.{name})")

        _fail.__name__ = name
        return _fail


_config_error: str | None = None

if not SUPABASE_URL or not SUPABASE_KEY:
    _config_error = _describe_config_problem()
else:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as exc:  # malformed URL/key must not kill the import either
        _config_error = f"Supabase client failed to initialise: {exc}"

if _config_error:
    # stderr, so it sits alongside the startup traceback rather than being
    # buffered away. Not fatal: the process has to reach "Application startup
    # complete." for this line to be readable at all.
    print(
        "\n[GAIDA CONFIG ERROR]\n" + _config_error + "\n",
        file=sys.stderr,
        flush=True,
    )
    supabase = UnconfiguredSupabase(_config_error)
