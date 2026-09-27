# GAIDA — Deployment Handoff

Written by the frontend dev after a remediation pass and a full browser
verification against the live deployment. Purpose: hand the backend/infra owner
what they need without a meeting.

> **Status as of 2026-09-28.** The backend is already redeployed — the `79f03ae`
> hardening is live in production. What remains is entirely a database schema
> question.

> ### Read §1 and you're done.
> It is self-contained and takes about five minutes. Everything after it is
> context, already-resolved history, or reference. Nothing in the appendix is
> required to act.

---

# §1 — Action required (backend dev)

**Everything outstanding is the database schema.** No frontend change, no Vercel
redeploy, and no backend code change is needed for any of it. The code is deployed
and already references these columns; only the schema is behind.

## The task in three steps

- [ ] **1. Find out what's missing.** Run the query below in the Supabase SQL
      editor. Any row reading `0` means that object does not exist.
- [ ] **2. Run all 7 files** in `backend/training/sql/` (ordered list below). All
      are guarded with `IF NOT EXISTS`, so re-running an applied one is a no-op.
      There is no downside to being thorough.
- [ ] **3. Verify the export script returns research rows.** This is the check
      that actually matters — everything else can look correct while the dataset
      is still empty. Details at the end of this section.

## Step 1 — what is actually missing

I could not run this. Every write path that would touch these objects sits behind
`get_current_user`, so each one returns `401` before reaching the database, and I
have no Supabase or Replit credentials. **This query has never been executed.**

```sql
-- TABLES
select 'table:gad7_responses' as object, count(*) as present
  from information_schema.tables
 where table_schema='public' and table_name='gad7_responses'
union all select 'table:research_participants', count(*)
  from information_schema.tables
 where table_schema='public' and table_name='research_participants'
union all select 'table:message_feedback', count(*)
  from information_schema.tables
 where table_schema='public' and table_name='message_feedback'
-- COLUMNS
union all select 'col:sus_responses.comment', count(*)
  from information_schema.columns
 where table_schema='public' and table_name='sus_responses' and column_name='comment'
union all select 'col:sessions.is_research', count(*)
  from information_schema.columns
 where table_schema='public' and table_name='sessions' and column_name='is_research'
union all select 'col:sessions.is_anonymous', count(*)
  from information_schema.columns
 where table_schema='public' and table_name='sessions' and column_name='is_anonymous'
union all select 'col:sessions.participant_code', count(*)
  from information_schema.columns
 where table_schema='public' and table_name='sessions' and column_name='participant_code'
union all select 'col:sessions.year_level', count(*)
  from information_schema.columns
 where table_schema='public' and table_name='sessions' and column_name='year_level'
union all select 'col:sessions.program', count(*)
  from information_schema.columns
 where table_schema='public' and table_name='sessions' and column_name='program'
union all select 'col:sessions.gender', count(*)
  from information_schema.columns
 where table_schema='public' and table_name='sessions' and column_name='gender'
union all select 'col:sessions.region', count(*)
  from information_schema.columns
 where table_schema='public' and table_name='sessions' and column_name='region'
union all select 'col:counselor_alerts.counselor_took_over', count(*)
  from information_schema.columns
 where table_schema='public' and table_name='counselor_alerts' and column_name='counselor_took_over'
union all select 'col:counselor_alerts.escalation_level', count(*)
  from information_schema.columns
 where table_schema='public' and table_name='counselor_alerts' and column_name='escalation_level'
union all select 'col:counselor_alerts.needs_supervisor', count(*)
  from information_schema.columns
 where table_schema='public' and table_name='counselor_alerts' and column_name='needs_supervisor'
order by 1;
```

If it errors, this one-liner answers the single most urgent question:

```sql
select count(*) from information_schema.columns
 where table_schema='public' and table_name='sus_responses' and column_name='comment';
-- 1 = applied, 0 = SUS submissions are currently failing
```

## Step 2 — the seven files, in the order to run them

| # | File | Adds | Pri |
|---|---|---|---|
| 1 | `2026_add_research_support.sql` | `sessions.is_research`, `is_anonymous`, `participant_code`, `year_level`, `program`, `gender`, `region`; `gad7_responses` table + 2 indexes | P1, P3 |
| 2 | `2026_02_add_research_participants.sql` | `research_participants` table | P1 |
| 3 | `2026_09_add_sus_comments.sql` | `sus_responses.comment` | P2 |
| 4 | `2026_09_add_sessions_resolution_state.sql` | `sessions.resolved`, `resolved_at`, `resolved_by`, `counselor_active`, `assigned_counselor_id`; `counselor_alerts.counselor_took_over` + 2 backfills | P4 |
| 5 | `2026_09_add_message_feedback.sql` | `message_feedback` table + index | P5 |
| 6 | `2026_09_add_counselor_alert_escalation.sql` | `counselor_alerts.escalation_level`, `needs_supervisor`, `age_minutes` + index | P6 |
| 7 | `2026_09_add_counselor_takeover_persistence.sql` | `sessions.counselor_active`, `assigned_counselor_id` + index | P7 |

- **1 must run before 2.** File 2's own header says so: *"This is a SECOND
  migration — run `2026_add_research_support.sql` first if you haven't already."*
  The other five are independent.
- Files 4 and 7 both add `sessions.counselor_active` and
  `assigned_counselor_id`. Intentional and harmless under `IF NOT EXISTS` — not a
  mistake to clean up.
- **Run file 4 whole, columns and backfill together.** See §2.
- No backend redeploy is needed afterwards.

## Priority, and what each gap looks like from outside

"Traced" = I read the write path in the code. "Inferred" = from the migration's own
header comment; not traced end to end.

| Pri | Object | Symptom if missing | Confidence |
|---|---|---|---|
| **P1** | `sessions.is_research` + 6 siblings; `research_participants` | **No symptom at all.** Sessions run and chat works, but are never tagged as research, so the export script will not pick them up. Demographics never recorded. | Traced |
| P2 | `sus_responses.comment` | Every SUS submission 500s. Participant is stuck on the form with *"Something went wrong saving your responses. Please try again."* Retrying cannot help. | Traced |
| P3 | `gad7_responses` | Research intake 500s before the chat can start — *"Something went wrong starting your session."* Blocks the session at step one. | Traced |
| P4 | `sessions.resolved` and siblings | Low — `83a4e0d` already mitigated the worst of it. See §2. | Traced |
| P5 | `message_feedback` | Thumbs up/down silently not stored. Degrades gracefully **by design**. | Traced |
| P6 | `counselor_alerts.escalation_level`, `needs_supervisor`, `age_minutes` | Escalation state not persisted across restarts. Reads fall back to `"normal"`, so the dashboard may under-report escalation. | Inferred |
| P7 | `sessions.counselor_active`, `assigned_counselor_id` | Counselor-held sessions flip back to GAIDA/student on restart. Overlaps P4; `counselor_alerts.counselor_took_over` provides a fallback. | Inferred |

### P1 is the one that matters most

`backend/app/api/research.py:197-207`:

```python
try:
    supabase.table("sessions").update({
        "is_research": True,
        "is_anonymous": payload.anonymous,
        "participant_code": code_used,
        **demographics,          # year_level, program, gender, region
    }).eq("session_token", session_id).execute()
except Exception as e:
    # Non-fatal — the session still works for chat even if this tagging
    # update fails; it just won't be picked up by the export script.
    print(f"[research] session tagging failed: {e}")
```

`backend/app/api/research.py:181-188` has the same shape around the
`research_participants` insert. Two separate objects, from two separate files.

If they are missing, **nothing breaks and nothing is reported.** The participant
completes intake, the chat runs normally, they get a working session token, every
layer the team can see looks correct — and the session is never tagged
`is_research`, so the export script will not pick it up. The only trace anywhere
is a `print()` line in the Replit console.

This is strictly worse than P2 and P3, which at least fail loudly and tell the
participant something is wrong. **P1 looks exactly like success.**

**If any data has already been collected, running the migration does not recover
it** — those rows were never tagged. Worth sizing that loss before assuming the
fix is complete.

The comment calling the write "non-fatal" is accurate about the session and
misleading as a risk statement: non-fatal to the *session*, fatal to the
*dataset*.

*Optional follow-up, your call:* that `print()`-only handling is what makes P1
silent, and it will hide the next failure the same way. A warning-level log, or a
health check that alerts when the tagging write fails, would mean the next
occurrence isn't discovered months later during analysis. Not blocking, and not
mine to change.

### Why P2 fails for every submission, not just commented ones

`backend/app/api/research.py:429-440` puts `"comment"` in the insert payload
**unconditionally**:

```python
"comment": comment or None,
```

PostgREST rejects the whole insert if the column doesn't exist, and merely naming
a column in the payload is enough. The field defaults to `""` and is coerced to
`None`, but it is always present — so this is not "breaks only when a participant
types a comment." **Every SUS submission fails, including ones where the comment
box was left blank.** No frontend workaround exists; only the migration fixes it.

### Why P3 blocks intake rather than the end of a session

`gad7_responses` (`backend/app/api/research.py:368`) is an unconditional insert
with no optional field at all, so it fails the same way. GAD-7 is collected during
intake, so a missing table stops the research session from *starting*. Visible to
the participant, but with no way forward.

## Step 3 — verify

1. Re-run the step 1 query. Every row should now read `1`.
2. Run one research session end to end: start it, finish the chat, submit the SUS
   form — with the comment box **left empty**, to confirm the unconditional-insert
   case specifically. It should succeed, and the session should be tagged.
3. **Confirm the export script now returns research rows.** Everything else can
   look correct while the dataset is still empty. This is the check that matters.
4. Confirm the session's demographics now appear in `research_participants`.

---

# §2 — P4 in detail: run the file whole

`2026_09_add_sessions_resolution_state.sql` adds `sessions.resolved`,
`resolved_at`, `resolved_by`, `counselor_active`, `assigned_counselor_id`, and
`counselor_alerts.counselor_took_over`, plus two backfills.

It originally looked urgent because of a live bug: `load_session_from_db()` read
six sessions columns in one `select()`, and **PostgREST rejects an entire
`select()` if any one column is missing** — so on a database without
`counselor_active`, `ended_at` / `resolved` / `resolved_at` / `resolved_by` were
silently blanked too, and every rehydrated session looked "active and unresolved."
Upstream reported ~54 ended sessions resurrecting as live chats in the counselor
dashboard after a backend restart, and resolved cases vanishing from the Resolved
view.

**That is already mitigated.** Commit `83a4e0d` split the read into two
independent queries so a missing column can only degrade its own group, and it is
on `main` and therefore deployed. Both states are now correct:

- migration **not** run → `counselor_active` is missing → query 2 fails → it stays
  `None` → the legacy-row fallback in `load_session_from_db()` runs → sessions
  render correctly.
- migration **run** (backfill included) → `counselor_active` is `True` for legacy
  rows → correct.

The one state to avoid is running the columns *without* the backfill, because
`counselor_active` with `DEFAULT false` returns `False` rather than `None`, which
disables that legacy fallback. The file does the columns and the backfill together
and is idempotent, so **just run the whole file** — don't paste only the `ALTER`s.

Run it for completeness and so a fresh database is never half-migrated. Nothing is
actively broken while it hasn't been run.

# §3 — `ENVIRONMENT=production`: cosmetic

`backend/app/main.py:40`:

```python
_IS_PROD = os.getenv("ENVIRONMENT", "production").lower() == "production"
```

`/docs` returning `404` confirms `_IS_PROD` is `True`, so this works. But the
**default is already `"production"`** — a missing variable and an explicitly-set
one behave identically, so the 404 does not prove the secret is set, only that the
default is doing the right thing. Worth setting explicitly so behaviour doesn't
depend on that default. No code change needed.

---

# Appendix — context, no action required

## A. Already verified done

Measured live earlier in this engagement:

| Check | Result | Meaning |
|---|---|---|
| `GET /` | `200` | backend alive |
| `GET /docs` | `404` | `79f03ae` hardening **is deployed** |
| `GET /openapi.json` | `404` | `79f03ae` hardening **is deployed** |
| `POST /api/counselor/events/ticket` | `401` | SSE ticket auth **is deployed** (401 = present, rejecting an unauthenticated call) |
| `POST /api/research/participant-check` | `400` | research endpoints **are deployed** (400 = reached, rejected the empty body) |

So the earlier items are done: prod docs are closed, the ticket endpoint is live,
and the frontend and backend are no longer out of sync.

Frontend, checked in a real browser against the live deployment plus local dev:

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
| Production console | Clean, except the Google item in §B |
| Entry chunk | 195 kB (was 912 kB before `ff82b77`) |

**Not verified:** true offline navigation (the network was never physically cut;
the available browser tooling had no offline-emulation mode); counselor dashboard
charts (needs a counselor login, and the local backend's Supabase config is broken
— see §C); the install prompt (`beforeinstallprompt` needs a real install
context).

## B. Google Sign-In — deliberately off, split ownership

Currently **non-functional in production**, and deliberately so: OAuth is not
enabled for the thesis deployment. Recorded so it isn't later mistaken for a
regression.

```
GET https://accounts.google.com/gsi/button?...   → 400
[GSI_LOGGER]: The given origin is not allowed for the given client ID.
```

The failure is **silent and fails closed** — GSI never initialises, so it never
reports a size, so the iframe collapses to `0 × 0` and the wrapper leaves a blank
40 px strip. No broken button, no error text, no dead click target. The email +
student-number form login on the same page is unaffected and remains the working
path.

**Infra / backend owner** — in Google Cloud Console, for the OAuth client in use,
add `https://gaida-system.vercel.app` to **Authorized JavaScript origins**.

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

## C. Local dev: known broken, does not affect production

`backend/.env` (gitignored, local only):

- `SUPABASE_URL` is set to `https://supabase.com/dashboa...` — the **dashboard**
  URL, not the API endpoint. It must be `https://<project-ref>.supabase.co`.
  PostgREST therefore returns an HTML page, `rows.data` is an ~18 KB string, and
  iterating it yields characters:

  ```
  AttributeError: 'str' object has no attribute 'get'
    app/services/session_manager.py:163
  ```

  This is the sole cause of
  `tests/test_services.py::test_crisis_hold_requires_safety_confirmation` failing
  locally (**16 passed, 1 failed**). Upstream reports 17/17 on a machine with a
  working Supabase connection. Credentials problem, not a code defect.

- `OPENAI_API_KEY` is still `sk-REPLACE-WITH-YOUR-KEY`.
- `ENVIRONMENT` is not set, so local `/docs` 404s.

Consequence: **any browser test that touches the database fails locally** until
`SUPABASE_URL` is corrected. This is why the counselor dashboard could not be
verified end to end.

> Running `npm` in PowerShell requires `npm.cmd` (execution policy blocks bare
> `npm`).

## D. Deferred / known open

| Item | Status |
|---|---|
| Dev `/sw.js` returned `index.html` as `text/html`, throwing `SecurityError` twice per dev load. Root cause: vite-plugin-pwa serves its dev worker at `dev-sw.js?dev-sw`, and our `register("/sw.js")` was *replacing* the plugin's registration — the browser keeps one per scope. | ✅ Fixed in `6d9f23f` — dev console is now clean. Note localhost still has no service worker at all, because `injectRegister: false` also gates the plugin's dev path. |
| `App.jsx` — bare `sessionStorage.getItem`/`setItem` next to a `try/catch`'d `removeItem`. If storage was blocked the storage error replaced the real chunk error. | ✅ Fixed in `6d9f23f` — storage failures now degrade the guard, and an unarmable guard means no reload rather than a loop. |
| `npm run lint` reported 32 phantom errors from `frontend/dev-dist/` (vite-plugin-pwa's dev worker output, gitignored but not in `globalIgnores`). | ✅ Fixed in `6d9f23f` — `dev-dist` ignored. |
| `index.html:16` `theme-color: #7c6af7` (purple) vs the app's blue/red palette. | ⬜ Open — only visible in an installed PWA's status bar. |
| Offline message queue | ⬜ Open by decision. The worker that would have provided it was never built. A student who loses connectivity mid-crisis now loses the message with no retry — a real product gap, not a code defect. The banner no longer promises delivery. Recoverable from `a0e1e9d`; read the `vite.config.js` comment first. |

## E. How to verify the backend

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

> Replit sleeps when idle. The first request after a quiet period can take 30–60 s
> and may need a retry; that is not an outage. Once awake it answers in ~0.4 s.

Then in a browser on `https://gaida-system.vercel.app`, **signed in as a research
participant**:

- complete the SUS questionnaire **leaving the comment blank** → it should save.
  This is the case that fails if the `comment` migration is missing, because the
  column is named in the insert unconditionally — testing *with* a comment is not
  a stricter test, both are equally broken.
- counselor dashboard loads **without** falling back to polling
- an ended session does **not** appear as a live chat
- a resolved case still appears in the Resolved view
- DevTools → Application → Service Workers: activated, precache holds 40 entries

## F. Commit reference

| Commit | Contents | Deployed? |
|---|---|---|
| `6d9f23f` | Frontend: hardened the stale-chunk reload guard against unavailable storage, stopped registering `/sw.js` in dev, ignored `dev-dist` in eslint. | ❌ Not yet — needs a Vercel redeploy. Production bundle verified byte-identical, so behaviour is unchanged until then. |
| `6baa04f` | Handoff document. | ✅ (on `main`) |
| `ff82b77` | Frontend: removed the never-built `src/sw.js` and its dead plumbing, route-level code splitting + `manualChunks` + precache exclusion, stale-chunk reload guard, corrected the offline banner copy, Guidance Office address, `.env.example` rewritten, dead dev proxy removed. | ✅ |
| `79f03ae` | Backend: disable prod docs, rate-limit research endpoints, ticket-based SSE auth. | ✅ (verified: `/docs` 404, ticket endpoint 401) |
| `83a4e0d` | Backend: split the sessions read so a missing column can't blank the rest; adds the resolution-state migration. | ✅ (on `main`) |

## G. For anyone else reading this

**If you are looking for the migration status:** it's §1, and it is the whole
action. This document used to be split across `backend/PENDING_MIGRATIONS.md`;
that file is now deleted and its content folded in here, because the two copies
drifted apart during drafting and one of them attributed a migration to the wrong
file. One source of truth is the point.

**If you are the frontend dev:** you cannot resolve §1, and it is not yours to.
The write paths that would reveal the problem sit behind `get_current_user`, so
it cannot even be checked without Supabase or Replit credentials. What *was*
verified from the frontend side: the app is deployed and working, and the SUS and
GAD-7 error handling correctly surfaces failures to the participant — which is
exactly what makes P2 and P3 visible instead of silent. What was *not* verified:
whether any migration is unapplied.

**Corrections made to earlier drafts of this document**, for the record:

- SUS submissions were described as failing "silently." They do not —
  `ResearchSUS.jsx:92` checks `if (!res.ok) throw`, so the participant sees a real
  error message. It is a visible hard block, not hidden data loss. **P1** above is
  the one that is genuinely silent.
- The SUS insert was cited as `backend/app/services/research.py`. **That file does
  not exist.** It is `backend/app/api/research.py`.
- `research_participants` was attributed to `2026_add_research_support.sql`. It is
  created by `2026_02_add_research_participants.sql`.
