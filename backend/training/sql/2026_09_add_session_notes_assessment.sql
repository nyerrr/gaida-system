-- Adds the counselor's independent professional assessment to session notes.
-- Thesis Ch3 "Virtual Agent Module": the dashboard includes an override field
-- where guidance professionals record their own assessment of the student's
-- anxiety level and the action they intend to take, kept distinct from GAIDA's
-- automated classification. The API (POST /api/counselor/session-notes) falls
-- back to the base columns until this migration is applied.
--
-- Run in the Supabase SQL editor. Safe to run more than once.

ALTER TABLE session_notes
    ADD COLUMN IF NOT EXISTS counselor_assessment varchar(2000) DEFAULT '';