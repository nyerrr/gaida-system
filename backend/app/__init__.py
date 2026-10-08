"""GAIDA application package.

This file exists for one reason: to make startup failures legible.

Every crash this deployment has hit has been an exception raised while
importing the application. Uvicorn's console script prints those as a raw
traceback on stderr, and the deploy log interleaves that stderr with its own
healthcheck lines and emits them out of order -- which is why the final line,
the one naming the actual exception, keeps falling outside whatever window
gets copied. Three separate reports of the same crash arrived without it.

`app/__init__.py` is imported before `app.main` and therefore before any of
its dependencies, so a hook installed here is in place for every failure that
can happen inside the application -- including a SyntaxError in main.py itself.
The hook prints one self-contained, clearly-delimited block *first*, followed
by the normal traceback, so the diagnosis survives the interleaving even if
nothing else does.

Environment values are reported as presence and length only; secrets are never
written to the log.
"""

import os
import sys

_original_excepthook = sys.excepthook

_WATCHED_ENV = (
    "SUPABASE_URL",
    "SUPABASE_KEY",
    "OPENAI_API_KEY",
    "GOOGLE_CLIENT_ID",
)


def _environment_snapshot():
    """One line describing the environment the failure happened in."""
    parts = ["python " + sys.version.split()[0]]
    try:
        parts.append("cwd=" + os.getcwd())
    except Exception:  # pragma: no cover - cwd deleted under us
        parts.append("cwd=?")
    parts.append("sys.path[0]=" + repr(sys.path[0]) if sys.path else "sys.path=[]")

    for key in _WATCHED_ENV:
        value = os.environ.get(key)
        if value:
            parts.append(f"{key}=set(len={len(value)})")
        else:
            parts.append(f"{key}=MISSING")

    # load_dotenv() reads this file; knowing whether it exists tells us whether
    # the values above came from a file or from the deployment's own secrets.
    env_path = os.path.join(os.getcwd(), ".env")
    parts.append(f".env={'yes' if os.path.isfile(env_path) else 'no'}")
    return "  ".join(parts)


def _gaida_excepthook(exc_type, exc_value, exc_tb):
    name = getattr(exc_type, "__name__", exc_type)
    print(
        "\n"
        "============================================================\n"
        f"[GAIDA STARTUP FAILED] {name}: {exc_value}\n"
        f"{_environment_snapshot()}\n"
        "============================================================\n",
        file=sys.stderr,
        flush=True,
    )
    _original_excepthook(exc_type, exc_value, exc_tb)


sys.excepthook = _gaida_excepthook
