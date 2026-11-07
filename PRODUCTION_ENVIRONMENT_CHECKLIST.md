# GAIDA Production Environment Checklist

Use this checklist before deploying the backend or building the frontend. Never
commit the completed checklist with secret values.

## Backend secret store

Configure these variables in the backend deployment platform:

| Variable | Required | Purpose |
|---|---:|---|
| `ENVIRONMENT` | Yes | Set to `production`; disables FastAPI docs and OpenAPI |
| `OPENAI_API_KEY` | Yes | AI responses and hosted speech-to-text |
| `SUPABASE_URL` | Yes | Supabase API URL, for example `https://<project>.supabase.co` |
| `SUPABASE_KEY` | Yes | Supabase service key used by the backend |
| `AUTH_SECRET` | Yes | Signs authenticated session tokens |
| `CAPTCHA_SECRET` | Yes | Signs and validates captcha challenges |
| `PARTICIPANT_TOKEN_SECRET` | Yes | Signs anonymous research participant tokens |
| `FRONTEND_URL` | Yes | Primary frontend origin allowed by CORS |
| `COUNSELOR_ACCOUNTS` | For password login | JSON counselor account list |
| `GOOGLE_CLIENT_ID` | For Google login | Google OAuth client ID |
| `COUNSELOR_EMAILS` | For counselor Google login | Comma-separated counselor email allow-list |

Generate separate, long random values for `AUTH_SECRET`, `CAPTCHA_SECRET`, and
`PARTICIPANT_TOKEN_SECRET`. Do not reuse the OpenAI or Supabase key as a signing
secret.

## Optional email notification variables

Configure all of the following together when counselor email alerts are needed:

- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASSWORD`
- `ALERT_FROM_EMAIL`
- `COUNSELOR_ALERT_EMAILS`
- `ESCALATION_EMAILS`

Dashboard alerts do not depend on email delivery. Verify SMTP separately before
relying on email escalation.

## Frontend build variables

Configure these in the frontend build environment:

| Variable | Required | Purpose |
|---|---:|---|
| `VITE_BACKEND_URL` | Yes | Backend origin baked into the Vite bundle |
| `VITE_GOOGLE_CLIENT_ID` | For Google login | Google OAuth client ID exposed to the browser |

`VITE_BACKEND_URL` must not be omitted in a deployed build. The fallback points
at port 8000 on the page host and is not a production backend.

## Origin and OAuth checks

- [ ] `FRONTEND_URL` exactly matches the deployed frontend origin, without a
      trailing slash.
- [ ] `VITE_BACKEND_URL` exactly matches the deployed backend origin.
- [ ] Backend CORS includes the frontend origin.
- [ ] Google Cloud Console includes the frontend origin in authorized
      JavaScript origins.
- [ ] Google OAuth redirect settings match the deployed login flow.
- [ ] Preview domains are not treated as production unless intentionally
      allow-listed.

## Database and deployment checks

- [ ] Apply the ten SQL migrations listed in [`HANDOFF.md`](./HANDOFF.md).
- [ ] Run [`VERIFY_MIGRATIONS.sql`](./backend/training/sql/VERIFY_MIGRATIONS.sql).
- [ ] Confirm no schema objects are missing.
- [ ] Confirm backfill miss counts are zero.
- [ ] Deploy the backend after migration verification.
- [ ] Build the frontend after setting Vite variables.
- [ ] Confirm backend health, authenticated login, chat, counselor takeover, and
      crisis hotline access.
- [ ] Confirm production `/docs` and `/openapi.json` are disabled.

## Secret handling

- Store secrets only in Render/Vercel/project secret settings or an approved
  secret manager.
- Do not paste secrets into issues, screenshots, chat, logs, or committed files.
- Rotate a secret if it appears in source control or an external log.
- Keep separate credentials for development, staging, and production.
