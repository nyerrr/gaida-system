# GAIDA — Deployment Handoff

Written after a frontend remediation pass and a full browser verification against the
live deployment. Purpose: hand the backend/infra owner what they need without a meeting.

> **Status as of 2026-09-28.** The backend has already been redeployed — the `79f03ae`
> hardening is live in production. That changes the shape of the remaining work: see §1.

---

## 1. TL;DR

**One question is open, and only the backend owner can answer it: has
`2026_09_add_sus_comments.sql` been run?**

Measured live just now:

| Check | Result | Meaning |
|---|---|---|
| `GET /` | `200` | backend alive |
| `GET /docs` | `404` | `79f03ae` hardening **is deployed** |
| `GET /openapi.json` | `404` | `79f03ae` hardening **is deployed** |
| `POST /api/counselor/events/ticket` | `401` | SSE ticket auth **is deployed** (401 = present, rejecting an unauthenticated call) |
| `POST /api/research/participant-check` | `400` | research endpoints **are deployed** (400 = reached, rejected the empty body) |

So the earlier items are done: prod docs are closed, the ticket endpoint is live, the
frontend and backend are no longer out of sync.

**What that leaves:**

| # | Item | Status | Risk if missing |
|---|---|---|---|
| 1 | `2026_09_add_sus_comments.sql` | ❓ **Unknown — cannot check from outside** | 🔴 **Every SUS submission fails.** See below. |
| 2 | `2026_09_add_sessions_resolution_state.sql` | ❓ Unknown | 🟢 Low — see §2 |
| 3 | `ENVIRONMENT=production` in Replit secrets | ✅ Effective (but see §3) | 🟢 Low |
| 4 | Redeploy backend | ✅ Done | — |

### Why item 1 matters now

`backend/app/services/research.py:437` puts `"comment"` in the insert payload
**unconditionally**:

```python
"comment": comment or None,
```

PostgREST rejects the whole insert if the column doesn't exist. The field defaults to
`""` and is coerced to `None`, but it is **always present in the payload** — so this is
not "breaks only if a participant types a comment." **Every SUS submission 500s if the
migration has not been run.** The frontend already sends the field
(`ResearchSUS.jsx` → `POST /api/research/sus`), so the feature is live on the frontend
and dead on the database.

**Check it (30 seconds, Supabase SQL editor):**

```sql
select count(*) as comment_column
from information_schema.columns
where table_name = 'sus_responses' and column_name = 'comment';
-- 1 = applied, 0 = SUS submissions are currently failing
```

If it returns `0`, run `backend/training/sql/2026_09_add_sus_comments.sql`. It is a
single `ADD COLUMN IF NOT EXISTS` and is idempotent.

---

## 2. Item 2 — lower risk than it looks

`2026_09_add_sessions_resolution_state.sql` adds `sessions.resolved`, `resolved_at`,
`resolved_by`, `counselor_active`, `assigned_counselor_id`, and
`counselor_alerts.counselor_took_over`, plus two backfills.

It originally looked urgent because of a live bug: `load_session_from_db()` read six
sessions columns in one `select()`, and **PostgREST rejects an entire `select()` if any
one column is missing** — so on a database without `counselor_active`, `ended_at` /
`resolved` / `resolved_at` / `resolved_by` were silently blanked too, and every
rehydrated session looked "active and unresolved." Upstream reported ~54 ended sessions
resurrecting as live chats in the counselor dashboard after a backend restart, and
resolved cases vanishing from the Resolved view.

**That is already mitigated.** Commit `83a4e0d` split the read into two independent
queries so a missing column can only degrade its own group, and it is on `main` and
therefore deployed. Both states are now correct:

- migration **not** run → `counselor_active` is missing → query 2 fails → it stays
  `None` → the legacy-row fallback in `load_session_from_db()` runs → sessions render
  correctly.
- migration **run** (backfill included) → `counselor_active` is `True` for legacy rows →
  correct.

The one state to avoid is running the columns *without* the backfill, because
`counselor_active` with `DEFAULT false` returns `False` rather than `None`, which
disables that legacy fallback. The file does the columns and the backfill together and
is idempotent, so **just run the whole file** — don't paste only the `ALTER`s.

Run it for completeness and so a fresh database is never half-migrated. Nothing is
actively broken while it hasn't been run.

---

## 3. Item 3 — confirm it's explicit, not defaulted

`backend/app/main.py:40`:

```python
_IS_PROD = os.getenv("ENVIRONMENT", "production").lower() == "production"
```

`/docs` returning `404` confirms `_IS_PROD` is `True`, so this is working. But note the
**default is already `"production"`** — a missing variable and an explicitly-set one
behave identically. So the 404 does not prove the secret is set, only that the default
is doing the right thing. Worth setting explicitly so the behaviour doesn't depend on
that default. No code change needed.

---

## 4. Frontend: verified working

Checked in a real browser against the live deployment, plus local dev.

| Area | Result |
|---|---|
| Portal, student login, consent, forgot-password | Render |
| Route-level code splitting | Lazy chunks load; `Suspense` fallback observed |
| Offline banner | Appears on `offline`, clears on `online` |
| Consent form | Guidance Office address present, no placeholders left |
| Service worker | Registers → `installing` → `activated`; `controller` set after reload |
| Precache | 40 entries, 14 route-named chunks |
| `recharts` (counselor-only, 382 kB) | Correctly excluded from precache, still served from CDN |
| Route guards | `/counselor-dashboard` correctly redirects when unauthenticated (401) |
| Production console | Clean, except the Google item in §5 |
| Entry chunk | 195 kB (was 912 kB before `ff82b77`) |
| Frontend / backend sync | In sync — backend now includes the ticket endpoint the frontend expects |

### Not verified

- **True offline navigation.** The React `offline`/`online` path was exercised, but the
  network was never physically cut, so workbox serving `index.html` from cache while
  offline is unconfirmed. The available browser tooling had no offline-emulation mode.
- **Counselor dashboard charts** — needs a counselor login; the local backend's Supabase
  config is broken (§6), so this could not be driven end to end.
- **Install prompt** (`beforeinstallprompt`) — needs a real install context.

---

## 5. Google Sign-In — split ownership

Currently **non-functional in production**, and deliberately so: OAuth is not enabled
for the thesis deployment. Recorded here so it isn't later mistaken for a regression.

```
GET https://accounts.google.com/gsi/button?...   → 400
[GSI_LOGGER]: The given origin is not allowed for the given client ID.
```

The failure is **silent and fails closed** — GSI never initialises, so it never reports
a size, so the iframe collapses to `0 × 0` and the wrapper leaves a blank 40 px strip.
No broken button, no error text, no dead click target. The email + student-number form
login on the same page is unaffected and remains the working path.

**Infra / backend owner** — in Google Cloud Console, for the OAuth client in use, add
`https://gaida-system.vercel.app` to **Authorized JavaScript origins**.

**Frontend owner** — one decision, currently unmade. Local and production are on
*different* OAuth clients and *neither* is authorized for its own origin:

| Environment | Client ID | Authorized for its origin? |
|---|---|---|
| Production (Vercel) | `959450930386-cfkse1jbpsehbrkhv21qhbi2s46rd170` | ❌ |
| Local (`frontend/.env`) | `128861146885-ujuqvrergt1ab1jrg20deudgngsriqb7` | ❌ |

Pick one client, authorize the origins it needs, then set `VITE_GOOGLE_CLIENT_ID`
consistently in Vercel and in `frontend/.env`. Used by `StudentLogin.jsx:417` and
`CounselorLogin.jsx:293`.

To remove the empty strip before a demo without enabling OAuth, gate the
`<GoogleSignIn>` element in those two files behind a flag.

---

## 6. Local dev: known broken, does not affect production

`backend/.env` (gitignored, local only):

- `SUPABASE_URL` is set to `https://supabase.com/dashboa...` — the **dashboard** URL, not
  the API endpoint. It must be `https://<project-ref>.supabase.co`. PostgREST therefore
  returns an HTML page, `rows.data` is an ~18 KB string, and iterating it yields
  characters:

  ```
  AttributeError: 'str' object has no attribute 'get'
    app/services/session_manager.py:163
  ```

  This is the sole cause of
  `tests/test_services.py::test_crisis_hold_requires_safety_confirmation` failing
  locally (**16 passed, 1 failed**). Upstream reports 17/17 on a machine with a working
  Supabase connection. Credentials problem, not a code defect.

- `OPENAI_API_KEY` is still `sk-REPLACE-WITH-YOUR-KEY`.
- `ENVIRONMENT` is not set, so local `/docs` 404s.

Consequence: **any browser test that touches the database fails locally** until
`SUPABASE_URL` is corrected. This is why the counselor dashboard could not be verified
end to end.

> Running `npm` in PowerShell requires `npm.cmd` (execution policy blocks bare `npm`).

---

## 7. Known deferred — no action required

| Item | Why it's fine |
|---|---|
| Dev `/sw.js` returns `index.html` as `text/html`, so SW registration throws `SecurityError` twice per dev load. Pre-existing: `devOptions.enabled: true` predates the frontend work and the registration path was untouched. | Dev-only. Production serves a real workbox `sw.js` and registers cleanly. Side effect: PWA behaviour cannot be tested locally at all. |
| `App.jsx:69-70` — bare `sessionStorage.getItem`/`setItem` next to a `try/catch`'d `removeItem` on line 63. | Inconsistent, impact low: if storage is blocked the storage error replaces the real chunk error. No reload loop; the error still surfaces. |
| `index.html:16` `theme-color: #7c6af7` (purple) vs the app's blue/red palette. | Only visible in an installed PWA's status bar. |
| Offline message queue | Removed. The worker that would have provided it was never built. A student who loses connectivity mid-crisis now loses the message with no retry — a real product gap, not a code defect. The banner no longer promises delivery. Recoverable from `a0e1e9d`; read the `vite.config.js` comment first. |

---

## 8. How to verify

```bash
B=https://gaida-system--rainierburlasa4.replit.app

# hardening live — both should be 404
curl -s -o /dev/null -w '%{http_code}\n' $B/docs
curl -s -o /dev/null -w '%{http_code}\n' $B/openapi.json

# SSE ticket endpoint live — 401 = present and rejecting an unauthenticated call
curl -s -o /dev/null -w '%{http_code}\n' -X POST $B/api/counselor/events/ticket

# research endpoints live — 400 = reached and rejected the empty body
curl -s -o /dev/null -w '%{http_code}\n' -X POST \
  -H 'Content-Type: application/json' -d '{}' $B/api/research/participant-check
```

> Replit sleeps when idle. The first request after a quiet period can take 30–60 s and
> may need a retry; that is not an outage. Once awake it answers in ~0.4 s.

Then in a browser on `https://gaida-system.vercel.app`, **signed in as a research
participant**, the real test for §1:

- complete the SUS questionnaire with a comment → it **saves** (this is what fails if
  the `comment` migration is missing)
- counselor dashboard loads **without** falling back to polling
- an ended session does **not** appear as a live chat
- a resolved case still appears in the Resolved view
- DevTools → Application → Service Workers: activated, precache holds 40 entries

---

## 9. Commit reference

`main` is at `0310da1`.

| Commit | Contents | Deployed? |
|---|---|---|
| `ff82b77` | Frontend: removed the never-built `src/sw.js` and its dead plumbing, route-level code splitting + `manualChunks` + precache exclusion, stale-chunk reload guard, corrected the offline banner copy, Guidance Office address, `.env.example` rewritten, dead dev proxy removed. | ✅ |
| `79f03ae` | Backend: disable prod docs, rate-limit research endpoints, ticket-based SSE auth. | ✅ (verified: `/docs` 404, ticket endpoint 401) |
| `83a4e0d` | Backend: split the sessions read so a missing column can't blank the rest; adds the resolution-state migration. | ✅ (on `main`) |
