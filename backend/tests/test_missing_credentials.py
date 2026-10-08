"""The deployment must boot even when Supabase credentials are missing.

This is the regression test for a publish gate that became unpassable.

`app.main` reaches `app.database.database` at import time via
`app.services.session_manager`'s module-level import, and `database.py` used to
`raise RuntimeError` when credentials were absent. That killed `import app.main`
before uvicorn could print "Started server process", so nothing ever bound, the
healthcheck got a connection failure reported as a 500, and the platform
declared a crash loop -- with the traceback interleaved into the log until the
exception line was cut off. Publishing was blocked because the app could not
start, and the reason it could not start could not be read.

`.env` is gitignored, so this exact split is not hypothetical: the workspace
has the file (import succeeds) while an artifact built from git does not.

Each test runs in a subprocess because the module under test is mutated at
import time and is otherwise already in `sys.modules` by the time the suite
reaches it.
"""

import os
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]

# Blank the credentials *inside* the child before importing, so the result does
# not depend on how a given platform treats an empty value in `env={}`.
# python-dotenv will not overwrite them -- it never overrides existing keys --
# so this reliably reproduces a deployment with no configuration at all.
_BLANK_CREDENTIALS = (
    "import os\n"
    "os.environ['SUPABASE_URL'] = ''\n"
    "os.environ['SUPABASE_KEY'] = ''\n"
)


def _run(source: str, timeout: int = 180) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", _BLANK_CREDENTIALS + source],
        cwd=str(BACKEND_DIR),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def test_database_module_imports_without_credentials():
    result = _run(
        "import app.database.database as d\n"
        "print('CLIENT_TYPE=' + type(d.supabase).__name__)\n"
    )
    assert result.returncode == 0, (
        "database.py must not raise at import time\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "CLIENT_TYPE=UnconfiguredSupabase" in result.stdout
    # The diagnosis still has to be visible, even though it is no longer fatal.
    assert "[GAIDA CONFIG ERROR]" in result.stderr
    assert "Missing Supabase credentials" in result.stderr


def test_app_main_imports_without_credentials():
    """The one that blocked publishing: `import app.main` must succeed."""
    result = _run("import app.main\nprint('IMPORT_OK')\n")
    assert result.returncode == 0, (
        "importing the application must succeed without Supabase credentials\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "IMPORT_OK" in result.stdout
    # Evidence the import reached the config path rather than being skipped.
    assert "Missing Supabase credentials" in result.stderr


def test_unconfigured_client_raises_the_full_diagnostic_on_first_use():
    """Failing later is fine; failing silently or cryptically is not."""
    result = _run(
        "import app.database.database as d\n"
        "try:\n"
        "    d.supabase.table('sessions')\n"
        "except RuntimeError as exc:\n"
        "    print('RAISED=' + str(exc).splitlines()[0])\n"
        "else:\n"
        "    raise SystemExit('placeholder accepted a real query')\n"
    )
    assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"
    assert "RAISED=Missing Supabase credentials." in result.stdout


def test_unconfigured_client_introspects_normally():
    """`hasattr` must stay honest, or libraries probing the client misbehave.

    Dunders report absent (as on any object lacking them); real attributes
    answer present, matching the live client, and only fail when called.
    """
    result = _run(
        "import app.database.database as d\n"
        "print('HAS_DUNDER=' + str(hasattr(d.supabase, '__aenter__')))\n"
        "print('HAS_TABLE=' + str(hasattr(d.supabase, 'table')))\n"
    )
    assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"
    assert "HAS_DUNDER=False" in result.stdout
    assert "HAS_TABLE=True" in result.stdout


def test_configured_client_is_used_when_credentials_exist():
    """The fix must be a no-op once real credentials are present.

    Credentials come from `backend/.env` via `load_dotenv()` here, which is the
    same path the Replit workspace takes.
    """
    result = subprocess.run(
        [sys.executable, "-c", "import app.database.database as d\nprint(type(d.supabase).__name__)"],
        cwd=str(BACKEND_DIR),
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"
    assert "UnconfiguredSupabase" not in result.stdout, (
        "credentials are present but the placeholder was returned"
        f"\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "[GAIDA CONFIG ERROR]" not in result.stderr
