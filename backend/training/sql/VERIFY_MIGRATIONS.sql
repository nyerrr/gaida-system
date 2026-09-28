-- ============================================================================
-- Post-migration verification for the 7 files in this directory.
-- Read-only. Safe to run any number of times.
--
-- Companion to the migration set, not a migration itself. Run all 7 migrations
-- first, then run this to confirm they actually landed.
--
--   Block A  schema        — every object the 7 files create. Expect 25 'ok'.
--   Block B  backfill      — both must read 0. See the note below.
--   Block C  counts        — dataset size, and the P1 loss that is NOT recoverable.
--   Block D  export        — the check that actually matters (run separately,
--                             needs working Supabase credentials — not SQL).
--   Block E  browser       — manual end-to-end, not SQL.
--
-- Blocks A/B/C are meant to be pasted whole into the Supabase SQL editor.
-- ============================================================================


-- ============================================================================
-- BLOCK A — schema check
--
-- Every column, table and index created by these migrations, in one query.
-- MISSING rows sort to the top, so a clean run is 25 'ok' rows and nothing else.
--
-- 25, not 28: 2026_09_add_counselor_takeover_persistence.sql adds only
-- sessions.counselor_active, sessions.assigned_counselor_id and
-- idx_sessions_counselor_active, all three of which are already listed under
-- 2026_09_add_sessions_resolution_state.sql. The overlap is intentional.
--
-- If this query errors naming sus_responses.comment, migration 3 did not land.
-- ============================================================================
with expected(kind, obj) as (
  values
    -- 1: 2026_add_research_support.sql
    ('col','sessions.is_research'), ('col','sessions.is_anonymous'),
    ('col','sessions.participant_code'), ('col','sessions.year_level'),
    ('col','sessions.program'), ('col','sessions.gender'), ('col','sessions.region'),
    ('table','gad7_responses'),
    ('index','idx_gad7_session_id'), ('index','idx_sessions_is_research'),
    -- 2: 2026_02_add_research_participants.sql
    ('table','research_participants'),
    -- 3: 2026_09_add_sus_comments.sql
    ('col','sus_responses.comment'),
    -- 4: 2026_09_add_sessions_resolution_state.sql
    ('col','sessions.resolved'), ('col','sessions.resolved_at'),
    ('col','sessions.resolved_by'), ('col','sessions.counselor_active'),
    ('col','sessions.assigned_counselor_id'),
    ('col','counselor_alerts.counselor_took_over'),
    ('index','idx_sessions_counselor_active'),
    -- 5: 2026_09_add_message_feedback.sql
    ('table','message_feedback'),
    ('index','idx_message_feedback_session_id'),
    -- 6: 2026_09_add_counselor_alert_escalation.sql
    ('col','counselor_alerts.escalation_level'),
    ('col','counselor_alerts.needs_supervisor'),
    ('col','counselor_alerts.age_minutes'),
    ('index','idx_counselor_alerts_pending')
)
, checked as (
  select
    e.kind,
    e.obj,
    case e.kind
      when 'table' then (select count(*) from information_schema.tables t
                          where t.table_schema='public' and t.table_name = split_part(e.obj,'.',1))
      when 'col'   then (select count(*) from information_schema.columns c
                          where c.table_schema='public'
                            and c.table_name  = split_part(e.obj,'.',1)
                            and c.column_name = split_part(e.obj,'.',2))
      when 'index' then (select count(*) from pg_indexes i
                          where i.schemaname='public' and i.indexname = e.obj)
    end as present,
    case
      when e.kind = 'table' and not exists (select 1 from information_schema.tables t
              where t.table_schema='public' and t.table_name = split_part(e.obj,'.',1)) then 'MISSING'
      when e.kind = 'col'   and not exists (select 1 from information_schema.columns c
              where c.table_schema='public'
                and c.table_name  = split_part(e.obj,'.',1)
                and c.column_name = split_part(e.obj,'.',2)) then 'MISSING'
      when e.kind = 'index' and not exists (select 1 from pg_indexes i
              where i.schemaname='public' and i.indexname = e.obj) then 'MISSING'
      else 'ok'
    end as status
  from expected e
)
select kind, obj, present, status
from checked
-- Sort on a boolean so 'MISSING' floats to the top regardless of the
-- database's collation. This has to happen out here in the outer query:
-- ORDER BY can reference an output alias as a bare name, but NOT inside an
-- expression — "order by (status = 'MISSING')" one level up would fail with
-- 42703, because the alias does not exist in that query's FROM clause.
order by (status = 'MISSING') desc, kind, obj;


-- ============================================================================
-- BLOCK B — backfill check
--
-- BOTH values must read 0.
--
-- A non-zero result means the UPDATE statements in
-- 2026_09_add_sessions_resolution_state.sql were pasted incompletely — the
-- columns exist but the backfill did not run. That is the one state worth
-- fixing by hand, because it breaks something that otherwise looks fine:
-- load_session_from_db() detects "this column does not exist yet" by
-- counselor_active coming back as None. Once the column exists with
-- DEFAULT false it returns False forever, so the legacy-row fallback in
-- session_manager.py goes dead, and any session a counselor took over before
-- the migration silently flips back to GAIDA on both dashboards.
--
-- step4_backfill_misses: counselor_alerts rows at status='escalated' that
--   counselor_took_over is not set on.
-- step5_backfill_misses: sessions the alerts table says are counselor-held
--   but whose counselor_active is not true.
-- ============================================================================
select
  (select count(*) from counselor_alerts
    where status = 'escalated' and counselor_took_over is not true)  as step4_backfill_misses,
  (select count(*) from sessions s
    join counselor_alerts a on a.session_id = s.session_token
    where a.status = 'escalated' and a.counselor_took_over is true
      and s.counselor_active is not true)                          as step5_backfill_misses;


-- ============================================================================
-- BLOCK C — dataset counts
--
-- These counts are themselves the proof that migrations 1, 2 and 3 landed.
-- Do not skip this block even if Block A says every object is present:
--
--   gad7_rows > 0        -> gad7_responses exists and the intake write works.
--   sus_rows > 0         -> sus_responses.comment exists. research.py names
--                           the column in the insert payload UNCONDITIONALLY,
--                           so a single stored SUS row is proof the column is
--                           there. A missing column would have made all 31+
--                           of them fail, not just the commented ones.
--   research_sessions>0  -> the is_research column exists and the tagging
--                           write is succeeding, not just silently failing.
--
-- Expect sus_with_comment = 0. The comment field defaults to "" and is
-- stored as "comment or None", so a participant who left the box empty
-- writes NULL. Zero here is the normal state, not a symptom.
--
-- Expect feedback_rows = 0 or near it. Thumbs up/down degrades gracefully by
-- design and most participants never press it. This count cannot distinguish
-- "table missing" from "nobody clicked" — only Block A can.
-- ============================================================================
select
  (select count(*) from sessions where is_research is true)         as research_sessions,
  (select count(*) from research_participants)                     as participants,
  (select count(*) from gad7_responses)                             as gad7_rows,
  (select count(*) from sus_responses)                             as sus_rows,
  (select count(*) from sus_responses where comment is not null)   as sus_with_comment,
  (select count(*) from message_feedback)                          as feedback_rows;


-- ============================================================================
-- BLOCK C2 — the loss that cannot be recovered
--
-- READ CAREFULLY. This block decides whether real research data is missing,
-- and nothing in it can be fixed by any migration.
--
-- The trap, and why the obvious query is wrong:
--
--   This database is a COUNSELING system with a research mode on top. Most
--   sessions in it are ordinary counseling sessions, which are CORRECTLY
--   untagged — is_research stays false and they never do GAD-7, because
--   GAD-7 only exists in the research flow. So "untagged session" does NOT
--   mean "lost research session". Counting untagged rows and calling it loss
--   will report a large false alarm on a healthy database.
--
-- The precise discriminator is research_participants. In /api/research/start
-- the participant row is written BEFORE the sessions row is tagged
-- (research.py:182 then :198), and each is wrapped in its own try/except, so
-- they fail independently. sessions.student_id holds that same
-- participant_id, because start_session(user_id=participant_id) stores it.
--
--   untagged session WITH a research_participants row -> a real research
--   participant who started a session that will never be exported. Loss.
--
--   untagged session WITHOUT one -> an ordinary counseling session. Nothing
--   is wrong.
--
-- lost_research_sessions is the only number here that means data loss.
-- Do not add untagged_with_consent / untagged_with_chat as loss measures:
-- ordinary counseling sessions have consents and chats too, so those
-- columns count healthy traffic.
-- ============================================================================
select
  (select count(*) from sessions s
    where s.is_research is not true
      and exists (select 1 from research_participants p
                  where p.participant_id = s.student_id))          as lost_research_sessions,
  (select count(*) from sessions where is_research is not true)     as untagged_total,
  -- tagged sessions that never got a GAD-7 row. GAD-7 is mandatory and a
  -- failure is fatal to the flow (ResearchFlow.jsx throws on a non-ok
  -- response), so anything above 0 means intake did not complete.
  (select count(*) from sessions s
    where s.is_research is true
      and not exists (select 1 from gad7_responses g
                      where g.session_id = s.session_token))         as tagged_without_gad7,
  -- GAD-7 rows whose session row does not exist at all: the reverse
  -- direction, invisible to the query above.
  (select count(*) from gad7_responses g
    where not exists (select 1 from sessions s
                      where s.session_token = g.session_id))        as orphan_gad7;


-- ============================================================================
-- BLOCK C2b — moved to the end of this file. See the note there.
-- ============================================================================


-- ============================================================================
-- BLOCK C3 — the timeline, by day.
--
-- Block C2 tells you how much was lost; this tells you WHEN. Read it as: on
-- any day where tagged = 0 but sessions exist, the tagging write was failing
-- for that day's traffic.
--
-- created_at is coalesced with started_at because start_session() inserts
-- started_at explicitly and only gets created_at from the column default,
-- so created_at can be null on older rows.
--
-- C3 is superseded by C2b at the end of this file, which is a superset of it.
-- Kept because it is the clearest view of the one anomaly that matters: a day
-- where tagged is high but with_gad7 is zero.
-- ============================================================================
select
  date_trunc('day', coalesce(s.created_at, s.started_at))          as day,
  count(*)                                                          as sessions,
  count(*) filter (where s.is_research is true)                     as tagged,
  count(*) filter (where s.is_research is not true)                 as untagged,
  count(*) filter (where exists (select 1 from gad7_responses g
                                 where g.session_id = s.session_token)) as with_gad7
from sessions s
group by 1
order by 1;


-- ============================================================================
-- BLOCK D — the export. THE CHECK THAT ACTUALLY MATTERS.
--
-- Everything above can look perfect while the dataset is still empty.
--
-- Fix SUPABASE_URL in backend/.env first. It must be
-- https://<project-ref>.supabase.co, not the dashboard URL — a dashboard URL
-- makes PostgREST return an HTML page, and iterating it yields characters.
--
--     cd backend
--     python training/export_research_data.py --out research_export_for_review.csv
--
-- Three outcomes. Only the first is a pass:
--
--   CSV written with rows
--       -> working.
--
--   "No research sessions found (sessions.is_research = true)."
--       -> the tagging write is still failing. Look for
--          "[research] session tagging failed:" in the Replit console
--          (app/api/research.py). Block C's research_sessions will agree: 0.
--
--   "Found research sessions, but none had both a completed GAD-7 and messages."
--       -> tagging is fine; the session you tested did not complete intake.
--          This message is a success with incomplete test data, not a failure.
--          Re-run Block E and finish the GAD-7 step.
-- ============================================================================


-- ============================================================================
-- BLOCK E — browser end-to-end. Manual, not SQL.
--
-- On https://gaida-system.vercel.app, signed in as a research participant:
--
--   1. Start a session, complete GAD-7, chat, finish.
--   2. Submit the SUS form with THE COMMENT BOX LEFT EMPTY.
--      This specific case is what proves the sus_responses.comment migration.
--      Testing WITH a comment is not a stricter test — the column is named in
--      the insert payload unconditionally (research.py), so a blank-comment
--      submission and a commented one were equally broken.
--   3. Re-run Block C. research_sessions, gad7_rows and sus_rows should all
--      have gone up by one.
--   4. Re-run Block D. It should now produce rows.
--
-- Then signed in as a counselor:
--
--   - dashboard loads without falling back to polling
--   - an ended session does NOT appear as a live chat
--   - a resolved case still appears in the Resolved view
--
-- The last two are the counselor_active backfill regression check. An ended
-- session reappearing as a live chat means step5_backfill_misses in Block B
-- was not 0.
-- ============================================================================


-- ============================================================================
-- BLOCK C2b — split the untagged sessions by day, benign vs. real.
--
-- THIS IS THE LAST STATEMENT IN THE FILE ON PURPOSE.
--
-- The Supabase SQL editor only renders a result grid for the final statement
-- of a multi-statement paste; everything before it runs but its output is
-- discarded. An earlier revision of this file ended on C3, so pasting the
-- whole file always displayed C3 and silently hid A, B, C, C2 and this block
-- — they had all executed correctly, their results were just never shown.
-- The most important query is therefore last. If you need to see another
-- block's output, select just that statement and run it on its own.
--
-- Read untagged_ordinary first. If it accounts for nearly all the untagged
-- traffic, those sessions are ordinary counseling sessions and nothing is
-- lost — GAD-7 only exists in the research flow, so an untagged session
-- having no GAD-7 row is expected, not suspicious. Only untagged_research
-- indicates a real research session the export will never see.
--
-- tagged_with_chat is the diagnostic for any day where tagged is high but
-- with_gad7 (Block C3) is zero: a tagged session with no chat stopped at the
-- GAD-7 step, because that submit is mandatory and throws on a non-ok
-- response.
-- ============================================================================
select
  date_trunc('day', coalesce(s.created_at, s.started_at))          as day,
  count(*) filter (where s.is_research is true)                     as tagged,
  count(*) filter (where s.is_research is not true)                 as untagged,
  count(*) filter (where s.is_research is not true
    and exists (select 1 from research_participants p
                where p.participant_id = s.student_id))            as untagged_research,
  count(*) filter (where s.is_research is not true
    and not exists (select 1 from research_participants p
                    where p.participant_id = s.student_id))        as untagged_ordinary,
  -- Did tagged sessions get past intake? If a day has tagged sessions with
  -- no chat, they stopped at the GAD-7 step.
  count(*) filter (where s.is_research is true
    and exists (select 1 from interactions i
                where i.session_id = s.session_token))             as tagged_with_chat,
  count(*) filter (where s.is_research is true
    and exists (select 1 from sus_responses r
                where r.session_id = s.session_token))              as tagged_with_sus
from sessions s
group by 1
order by 1;
