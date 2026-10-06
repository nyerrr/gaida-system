-- ============================================================================
-- GAIDA pilot data export for Chapter 4 (Research Results)
-- ============================================================================
-- THREE separate queries. The Supabase SQL editor only shows the result of the
-- LAST statement in a paste, so run them ONE AT A TIME (select a query, Run,
-- "Export to CSV", save as the filename given above each query).
--
-- De-identified by design:
--   * No student numbers, participant codes, session ids, or names are selected.
--   * Each participant gets a pseudonym P001, P002, ... (pid). The numbering is
--     derived from a hash, not from the student number, so it cannot be mapped
--     back without the database itself.
--   * Only research sessions (is_research = true) are included.
--   * Free-text SUS comments ARE included (column `comment`). Skim them before
--     sharing the file, since a participant could type something identifying.
-- ============================================================================


-- ----------------------------------------------------------------------------
-- QUERY 1  ->  save as  pilot_gad7.csv
-- One row per GAD-7 submission, with the participant's demographics.
-- ----------------------------------------------------------------------------
with pids as (
  select participant_id,
         'P' || lpad(dense_rank() over (order by md5('gaida-pilot:' || participant_id))::text, 3, '0') as pid
  from research_participants
)
select
  p.pid,
  s.is_anonymous,
  rp.year_level, rp.program, rp.gender, rp.region,
  g.q1, g.q2, g.q3, g.q4, g.q5, g.q6, g.q7,
  g.total_score, g.severity_band,
  g.created_at
from gad7_responses g
join sessions s on s.session_token = g.session_id and s.is_research is true
left join research_participants rp on rp.participant_id = s.student_id
left join pids p on p.participant_id = s.student_id
order by p.pid, g.created_at;


-- ----------------------------------------------------------------------------
-- QUERY 2  ->  save as  pilot_sus.csv
-- One row per SUS submission (sus_score is already 0-100, Brooke scoring).
-- ----------------------------------------------------------------------------
with pids as (
  select participant_id,
         'P' || lpad(dense_rank() over (order by md5('gaida-pilot:' || participant_id))::text, 3, '0') as pid
  from research_participants
)
select
  p.pid,
  r.q1, r.q2, r.q3, r.q4, r.q5, r.q6, r.q7, r.q8, r.q9, r.q10,
  r.sus_score,
  r.comment,
  r.created_at
from sus_responses r
join sessions s on s.session_token = r.session_id and s.is_research is true
left join pids p on p.participant_id = s.student_id
order by p.pid, r.created_at;


-- ----------------------------------------------------------------------------
-- QUERY 3  ->  save as  pilot_funnel.csv
-- One row per research SESSION: how far did each get? (for the attrition /
-- completion funnel and for message counts). Uses the same pseudonyms.
-- ----------------------------------------------------------------------------
with pids as (
  select participant_id,
         'P' || lpad(dense_rank() over (order by md5('gaida-pilot:' || participant_id))::text, 3, '0') as pid
  from research_participants
)
select
  p.pid,
  s.is_anonymous,
  coalesce(s.created_at, s.started_at)                                   as session_started,
  (s.ended_at is not null)                                               as ended,
  exists (select 1 from gad7_responses g where g.session_id = s.session_token) as did_gad7,
  (select count(*) from interactions i where i.session_id = s.session_token)   as user_messages,
  exists (select 1 from sus_responses r where r.session_id = s.session_token)  as did_sus
from sessions s
left join pids p on p.participant_id = s.student_id
where s.is_research is true
order by p.pid, session_started;
