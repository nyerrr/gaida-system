# GAIDA Deployment Handoff

**Last reviewed:** 2026-11-07
**Repository:** `nyerrr/gaida-system`

This document describes the current deployment state and the remaining production
operator tasks. It replaces the older handoff that listed seven migrations and
historical frontend defects.

## Current system status

| Area | Current status |
|---|---|
| Frontend | React/Vite PWA in `frontend/`; production build passes |
| Backend | FastAPI service in `backend/`; production docs are disabled when `ENVIRONMENT=production` |
| Frontend deployment | Vercel or another static-host deployment |
| Backend deployment | Render blueprint in [`render.yaml`](./render.yaml) |
| Database | Supabase/Postgres; migrations are maintained in [`backend/training/sql/`](./backend/training/sql/) |
| Counselor UI | Responsive desktop sidebar and mobile drawer/bottom navigation |
| Offline support | App shell and queued offline messages are supported; replies still require a connection |
| Known validation issue | `npm run lint` currently reports the unused `closeSidebarTooltip` symbol in `CounselorDashboard.jsx:187` |

The current working tree may contain uncommitted changes. Confirm the commit and
deployment revision before declaring a release complete.

## Release checklist

- [ ] Confirm the intended commit is pushed to the deployment branch.
- [ ] Configure the backend variables in the production secret store.
- [ ] Configure `VITE_BACKEND_URL` and `VITE_GOOGLE_CLIENT_ID` in the frontend
      build environment.
- [ ] Apply all database migrations in the order below.
- [ ] Run [`VERIFY_MIGRATIONS.sql`](./backend/training/sql/VERIFY_MIGRATIONS.sql).
- [ ] Deploy the backend and wait for the health check to pass.
- [ ] Build and deploy the frontend.
- [ ] Run the smoke tests in the final section.
- [ ] Record the deployed frontend URL, backend URL, commit, migration result,
      and test result.

## Database migration procedure

Run the following migration files in Supabase SQL Editor or through the approved
database migration process. Each migration is intended to be idempotent.

1. `2026_add_research_support.sql`
2. `2026_02_add_research_participants.sql`
3. `2026_09_add_sus_comments.sql`
4. `2026_09_add_sessions_resolution_state.sql`
5. `2026_09_add_message_feedback.sql`
6. `2026_09_add_counselor_alert_escalation.sql`
7. `2026_09_add_feedback_comment.sql`
8. `2026_09_add_session_notes_assessment.sql`
9. `2026_09_add_counselor_takeover_persistence.sql`
10. `2026_11_add_revoked_session_tokens.sql`

Do not run `VERIFY_MIGRATIONS.sql` as a migration. Run it after the ten files
above. The verification query should report no missing schema objects and zero
backfill misses. If an earlier migration fails, stop and resolve that failure
before continuing.

The research-participant migration depends on the research-support migration.
The resolution-state migration must be run as a whole, including its backfill.
Do not copy only its `ALTER TABLE` statements.

### Database verification

After applying the migrations:

1. Run `VERIFY_MIGRATIONS.sql`.
2. Confirm all rows in the schema block report `ok`.
3. Confirm both backfill miss counts are `0`.
4. Run a research session through intake and SUS submission.
5. Confirm the research session is tagged and appears in the expected research
   tables.
6. Confirm a counselor takeover remains represented after a backend restart or
   rehydration test.

## Deployment procedure

### Backend

1. Confirm the production variables in the environment checklist below.
2. Push the approved backend commit.
3. Allow Render to build and deploy the service from [`render.yaml`](./render.yaml).
4. Confirm the service health endpoint returns:

   ```json
   {"status":"ok","message":"GAIDA Backend"}
   ```

5. Confirm `/docs` and `/openapi.json` are unavailable in production.
6. Review deployment logs for failed database, model, email, or startup warnings.

### Frontend

1. Set `VITE_BACKEND_URL` to the deployed backend origin.
2. Set `VITE_GOOGLE_CLIENT_ID` only when Google OAuth is configured for the
   deployed frontend origin.
3. Run `npm run build` from `frontend/`.
4. Deploy the generated frontend through the approved Vercel project.
5. Confirm the browser can call the backend without a CORS error.
6. Verify that the deployed frontend is using the intended backend URL; Vite
   variables are baked into the build and are not runtime settings.

## Environment variable summary

### Required backend variables

- `ENVIRONMENT=production`
- `OPENAI_API_KEY`
- `SUPABASE_URL` — Supabase API URL, not the dashboard URL
- `SUPABASE_KEY`
- `AUTH_SECRET`
- `CAPTCHA_SECRET`
- `PARTICIPANT_TOKEN_SECRET`
- `FRONTEND_URL`

### Required for password-based counselor login

- `COUNSELOR_ACCOUNTS` — JSON list containing counselor IDs, passwords, names,
  and optional email addresses

### Required for Google sign-in

- `GOOGLE_CLIENT_ID`
- `COUNSELOR_EMAILS` for the counselor email allow-list where applicable
- Matching authorized origins and redirect settings in Google Cloud Console

### Optional alert email variables

- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASSWORD`
- `ALERT_FROM_EMAIL`
- `COUNSELOR_ALERT_EMAILS`
- `ESCALATION_EMAILS`

If alert email settings are absent, dashboard alerts still work but email
notifications are not sent.

### Optional model/runtime variables

- `WHISPER_MODEL`
- `GAIDA_ALLOW_DEMO_COUNSELORS=1` — temporary pilot-only fallback; never enable
  for real participant data

Never commit values for any secret, password, token, or API key. Use
[`backend/.env.example`](./backend/.env.example) and
[`frontend/.env.example`](./frontend/.env.example) as naming references only.

## Smoke tests

- [ ] Portal page loads.
- [ ] Student login succeeds with an approved test account.
- [ ] Consent can be recorded.
- [ ] Student can send a text message and receive a reply.
- [ ] Student can request a counselor and sees a failure message if the request
      cannot be submitted.
- [ ] Counselor login succeeds with a production-configured account.
- [ ] Counselor sees alerts and active sessions.
- [ ] Counselor can open a transcript, send a reply, and resolve a session.
- [ ] Welfare checks, reports, resolved cases, notes, and PDF export load.
- [ ] Crisis hotlines are visible from the student and counselor surfaces.
- [ ] Mobile drawer opens and closes; desktop sidebar collapse works only on
      desktop.
- [ ] Offline banner and queued-message behavior work in a controlled test.

## Known limitations

- GAIDA's anxiety detection is a support signal, not a medical diagnosis.
- Emergency situations must be directed to emergency services or crisis hotlines.
- Backend in-memory runtime state can be lost during a restart; permanent records
  are stored in Supabase.
- Google sign-in requires valid Google Cloud origin configuration and matching
  production environment variables.
