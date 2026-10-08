"""Deployment healthcheck and startup-path regression tests.

These lock the two changes that fixed a Replit crash-loop:

  * `GET /` and `GET /health` must answer without touching any warm-up work,
    because the deploy platform polls them while the app is still starting.
  * The startup event must not block on prewarm(). Prewarm loads ~50MB of
    pickles and makes two un-timed Supabase calls; run inline it held uvicorn
    in "Waiting for application startup." for ~11s (7.69s measured locally),
    during which the platform's healthcheck got no answer and the deployment
    was declared crash-looping even though the app was otherwise healthy.

The client is deliberately not used as a context manager in the route tests:
entering it runs the lifespan, which would start the escalation monitor that
re-notifies counselors by email.
"""

import time

from fastapi.testclient import TestClient

from app.main import app


def test_root_returns_ok():
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_root_head_returns_ok():
    # FastAPI does not auto-add HEAD for a GET route, and several platforms
    # probe with HEAD, so both are registered explicitly.
    client = TestClient(app)
    assert client.head("/").status_code == 200


def test_health_returns_ok_with_warmup_state():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "GAIDA Backend"
    assert set(body["warmup"]) == {"ml", "supabase", "alerts"}


def test_health_head_returns_ok():
    client = TestClient(app)
    assert client.head("/health").status_code == 200


def test_health_is_200_even_when_warmup_has_not_run():
    """The whole point of /health: readiness must never gate liveness.

    If this endpoint reported warm-up state as its status, a stalled warm-up
    would fail the healthcheck forever -- which is the exact outage this
    endpoint exists to prevent. Warm-up progress belongs in the body only.
    """
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    # Flags are False here because the client never ran the lifespan.
    assert resp.json()["warmup"]["ml"] is False
    assert resp.json()["status"] == "ok"


def test_unknown_path_is_still_404():
    # Guards against a catch-all being introduced while adding the routes.
    client = TestClient(app)
    assert client.get("/does-not-exist").status_code == 404


def test_startup_event_does_not_block_on_prewarm(monkeypatch):
    """Measured: inline prewarm cost 7.69s; the startup event must not wait."""
    import app.main as main_mod

    def _slow_prewarm():
        time.sleep(1.0)

    monkeypatch.setattr(main_mod, "_prewarm", _slow_prewarm)

    started = time.time()
    with TestClient(main_mod.app) as client:
        elapsed = time.time() - started
        assert elapsed < 0.75, (
            f"startup event blocked for {elapsed:.2f}s waiting on prewarm; "
            "a slow warm-up will starve the deployment healthcheck again"
        )
        assert client.get("/health").status_code == 200
