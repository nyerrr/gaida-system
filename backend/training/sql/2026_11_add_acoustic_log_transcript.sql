alter table public.acoustic_logs
  add column if not exists transcript text;
