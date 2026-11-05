-- Persist signed session-token revocations across backend instances.
-- The application stores only SHA-256 token hashes, never bearer tokens.
CREATE TABLE IF NOT EXISTS public.revoked_session_tokens (
    token_hash text PRIMARY KEY,
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_revoked_session_tokens_expires_at
    ON public.revoked_session_tokens (expires_at);

ALTER TABLE public.revoked_session_tokens ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.revoked_session_tokens FROM anon, authenticated;
GRANT ALL ON TABLE public.revoked_session_tokens TO service_role;
