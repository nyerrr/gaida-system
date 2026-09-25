-- Adds the optional participant comment collected at the end of the
-- post-session System Usability Scale (SUS) survey.
-- Run this in the Supabase SQL editor before deploying the updated API.
-- Safe to re-run.

ALTER TABLE public.sus_responses
    ADD COLUMN IF NOT EXISTS comment varchar(1000);
