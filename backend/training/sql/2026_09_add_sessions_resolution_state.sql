-- Adds the case-resolution and counselor-takeover columns the counselor API
-- already reads and writes, but which no earlier migration created.
--
-- On a database where these were never applied, load_session_from_db()'s
-- sessions-row select() fails as a whole (PostgREST rejects a select() if ANY
-- one column is missing), so ended_at / resolved / resolved_at / resolved_by
-- were never read and every session rehydrated from Supabase came back looking
-- "active and unresolved" — resurrecting ended sessions as live chats and
-- hiding resolved cases.
--
-- This file is self-contained on purpose: it also creates counselor_active +
-- assigned_counselor_id (normally 2026_09_add_counselor_takeover_persistence.sql)
-- so a fresh database is never half-migrated. Safe to re-run (idempotent).
-- Run this in the Supabase SQL editor.

-- 1. Resolution state on the sessions row. Written by
--    POST /api/counselor/sessions/resolve and read back by
--    load_session_from_db() so a backend restart can't un-resolve a closed
--    case. resolved_by is the counselor who closed it; resolved_at is a
--    timestamptz (the API sends an ISO-8601 "...Z" string, which Postgres casts).
ALTER TABLE public.sessions
    ADD COLUMN IF NOT EXISTS resolved boolean NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS resolved_at timestamptz,
    ADD COLUMN IF NOT EXISTS resolved_by text;

-- 2. Counselor-takeover state on the sessions row. Set by
--    POST /api/counselor/takeover / /return-to-gaida. MUST come before the
--    backfill in step 5, which both reads and filters on counselor_active.
ALTER TABLE public.sessions
    ADD COLUMN IF NOT EXISTS counselor_active boolean NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS assigned_counselor_id text;

-- 3. counselor_took_over on counselor_alerts. Read by load_session_from_db()'s
--    legacy-row fallback and written by POST /api/counselor/takeover. MUST
--    come before step 4, which reads it.
ALTER TABLE public.counselor_alerts
    ADD COLUMN IF NOT EXISTS counselor_took_over boolean NOT NULL DEFAULT false;

-- 4. Backfill the alerts flag from status. A row still sitting at
--    status='escalated' means a counselor took the session over and never
--    handed it back, so counselor_took_over is true for it. Re-running is
--    harmless: the WHERE clause excludes rows already flagged.
UPDATE public.counselor_alerts
SET counselor_took_over = true
WHERE status = 'escalated'
  AND counselor_took_over = false;

-- 5. Backfill sessions.counselor_active from those alerts. REQUIRED, not
--    cosmetic: load_session_from_db() detects "this column doesn't exist yet"
--    by seeing counselor_active come back as None, and only then falls back to
--    counselor_alerts. Once the column exists with DEFAULT false it returns
--    False forever, so that fallback goes dead. Any session taken over before
--    this migration would silently flip back to GAIDA/student on both
--    dashboards unless we copy the state across now.
UPDATE public.sessions s
SET counselor_active = true
FROM public.counselor_alerts a
WHERE a.session_id = s.session_token
  AND a.status = 'escalated'
  AND a.counselor_took_over = true
  AND s.counselor_active = false;

-- 6. Partial index: the welfare/escalation scans only ever ask for the sessions
--    where a counselor is currently holding the conversation.
CREATE INDEX IF NOT EXISTS idx_sessions_counselor_active
    ON public.sessions (counselor_active) WHERE counselor_active = true;

-- Verify after running: all five should report EXISTS.
--   select resolved from sessions limit 1;
--   select resolved_by from sessions limit 1;
--   select counselor_active from sessions limit 1;
--   select assigned_counselor_id from sessions limit 1;
--   select counselor_took_over from counselor_alerts limit 1;
