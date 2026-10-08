"""Boot the app the way .replit does, with no Supabase credentials.

Previously this died inside `import_from_string` with exit status 1 before
uvicorn could print "Started server process", which is what the deploy platform
reported as a crash loop. The fix is only real if this reaches 200.
"""

import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request

os.environ["SUPABASE_URL"] = ""
os.environ["SUPABASE_KEY"] = ""

PORT = 8231
BASE = f"http://127.0.0.1:{PORT}"

_WRAP = (
    # Blank credentials inside the child process: passing an empty value via
    # `env=` is not reliably preserved on Windows, and `load_dotenv()` will
    # happily refill anything absent from `os.environ`.
    "import os, sys\n"
    "os.environ['SUPABASE_URL'] = ''\n"
    "os.environ['SUPABASE_KEY'] = ''\n"
    # Same entrypoint as `.replit`'s run command: click -> run -> load_app
    # -> import_from_string, which is the exact frame chain in the deploy log.
    "sys.argv = ['uvicorn', 'app.main:app', '--host', '127.0.0.1',"
    f" '--port', '{PORT}']\n"
    "from uvicorn.main import main\n"
    "main()\n"
)

proc = subprocess.Popen(
    [sys.executable, "-c", _WRAP],
    cwd=os.getcwd(),
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    errors="replace",
)

deadline = time.time() + 90
body = None
status = None
while time.time() < deadline:
    if proc.poll() is not None:
        break
    try:
        with urllib.request.urlopen(BASE + "/health", timeout=3) as resp:
            status = resp.status
            body = resp.read().decode()
        break
    except (urllib.error.HTTPError, urllib.error.URLError, ConnectionError, TimeoutError):
        time.sleep(0.4)

print(f"exit_before_request = {proc.poll()}")
print(f"/health status      = {status}")
print(f"/health body        = {body}")

# Give it a moment to flush startup lines, then collect output.
time.sleep(1.0)
try:
    proc.send_signal(signal.SIGTERM)
except OSError:
    proc.kill()
try:
    out = proc.communicate(timeout=20)[0]
except subprocess.TimeoutExpired:
    proc.kill()
    out = proc.communicate()[0]

out = out or ""
print("\n--- markers ---")
markers = {}
for marker in ("Started server process", "Application startup complete",
               "[GAIDA CONFIG ERROR]", "Missing Supabase credentials",
               "Traceback (most recent call last)"):
    markers[marker] = marker in out
    print(f"{marker!r}: {markers[marker]}")

print("\n--- first 40 lines of server output ---")
print("\n".join(out.splitlines()[:40]))

required = (
    "Started server process",
    "Application startup complete",
    "[GAIDA CONFIG ERROR]",
    "Missing Supabase credentials",
)
missing = [m for m in required if not markers[m]]

if status == 200 and not missing:
    print("\nRESULT: boots, serves /health, and reports the missing config")
elif missing:
    print(f"\nRESULT: FAILED - expected markers absent: {missing}")
    sys.exit(1)
else:
    print("\nRESULT: FAILED - app did not serve /health")
    sys.exit(1)
