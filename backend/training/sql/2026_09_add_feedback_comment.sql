-- Adds the optional open-text comment on per-message feedback.
-- Thesis Ch3 "Session Feedback and Rating Mechanism": a thumbs rating plus an
-- optional short comment on any response the student found inaccurate or
-- unhelpful. The API (POST /api/session/feedback) falls back to the base
-- columns until this migration is applied, so ratings are never dropped.
--
-- Run in the Supabase SQL editor. Safe to run more than once.

ALTER TABLE message_feedback
    ADD COLUMN IF NOT EXISTS comment varchar(1000) DEFAULT '';