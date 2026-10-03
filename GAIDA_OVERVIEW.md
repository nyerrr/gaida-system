# GAIDA — Plain-Language System Overview

**GAIDA =** **G**uidance system with multimodal Anx**I**ety Intelligence and **D**etection **A**ssistance

*Up-to-date as of 2026-10-03 (includes the uncommitted changes on `main`).*

A virtual counseling assistant for University of the East students. It chats in Tagalog,
Taglish, and English, looks for signs of anxiety in both text and voice, brings in a human
counselor when things get serious, and keeps a record of the sessions you agreed to save. It
also works as an installable app that can run with no internet.

**Live:** backend `https://gaida-system--rainierburlasa4.replit.app` · frontend `https://gaida-system.vercel.app`

---

## What it actually does

| Feature | In plain terms |
|---|---|
| AI chat | A fine-tuned OpenAI model (based on GPT-3.5 turbo, `ft:gpt-3.5-turbo-0125`) replies warmly and copies whatever language the student used. |
| Text anxiety detection | Every message is sorted into a mood — neutral, stress, sadness, **grief/loss**, anxiety, anger, loneliness, academic, suicidal — using rules plus 3 small ML models that vote. Measured against a 120-message counselor-labeled gold key: **85% overall, 100% of suicidal messages routed to the crisis flow.** |
| **Grief as its own reading (new)** | A breakup, a death, or unrequited love is **not** a cognitive distortion, so it does not get the anxiety flow ("here's another way to see it"). It is detected by rule — the ML training labels have no grief class — and gets its own response, its own protocol, and a floor at Moderate. It never pages a counselor on keywords alone, and it stays active until the student says they are better. |
| **Counselor reply craft (new)** | 13 prompt rules and a "being there" section govern how replies read — presence shown by restraint rather than by announcing it, no invented details about the student's life, exactly one question, and a menu of 2–3 moves per severity rather than a fixed script. Backed by 13 worked replies placed in the system prompt as examples (never as fake conversation turns), plus an echo guard that catches and retries a reply that just echoes the student back. |
| Voice anxiety detection | A recording is checked for signs of stress in the voice itself (pitch, jitter/shimmer, pauses, speaking speed, energy) and also typed out by OpenAI's hosted speech-to-text (`gpt-4o-mini-transcribe`). The two results are then combined with the text analysis. |
| Vent mode | A "just listen" mode — GAIDA doesn't try to fix or redirect. Real crisis warnings still break through for safety. |
| Crisis handling | If a student seems to be in crisis, GAIDA shares hotlines (1553, (02) 893-7603, 911) and automatically notifies a human counselor. |
| **Crisis de-escalation hold (new)** | Once anxiety reaches High or Crisis, GAIDA no longer quietly drops back down on the next calm message. It holds at that level and asks "Are you safe right now?" until the student *explicitly* confirms they're safe (e.g. "safe na ako", "I'm safe"). This prevents the system from "forgetting" a crisis state mid-conversation. |
| **Silent-student welfare check (new)** | If a High/Crisis student goes quiet for 30+ minutes, the session is surfaced on the counselor dashboard as needing a welfare check (instead of just disappearing from the active list). Counselors can mark it checked. |
| Counseler takeover | A counselor can jump into a live chat. GAIDA goes quiet, the human takes over, and control can be handed back to GAIDA later. |
| Counselor dashboard | Live alerts, active chats, transcripts, typing indicators, case notes, PDF exports, analytics, a resolved-case archive, and now a welfare-check list. |
| Consent | Students must agree to a consent screen before any of their chat data is saved. |
| Offline mode | Installable app; the app opens when there is no internet and shows a "please reconnect" banner. Past chats are **not** cached offline and offline messages are **not** queued — GAIDA needs a connection to chat. |
| Post-chat check-in | After a session, students rate how they feel (1–4), which counselors can review. |
| **Per-message feedback (new)** | Under every GAIDA reply there are "Helpful / Not helpful" buttons; ratings are stored so the team can see which replies work. |
| **Research participation (new)** | An optional, separate research flow: students enter an anonymous code given by the researcher, take a GAD-7 questionnaire, and can later **delete all their research data by code**. |

---

## How it's built — the big picture

1. **The Browser (what students and counselors see).** A React web app with a portal
   selector, student + counselor login, consent screen, student chat, and the counselor
   dashboard. A background "service worker" caches pages and data for offline use.
2. **The Backend (the brains).** A Python server (FastAPI) that:
   - talks to the frontend over simple web requests, and streams replies as they are typed,
   - runs all the anxiety-detection logic,
   - calls OpenAI for the chat replies and for voice transcription,
   - can speak replies aloud (gTTS — the speak-aloud endpoint exists but is not yet
     switched on in the live chat),
   - saves everything worth keeping into a database.
3. **Storage and outside services.**
   - **Supabase** (a hosted database) permanently stores sessions, chat history, consent
     records, alerts, notes, ratings, research data, and voice-analysis logs.
   - **OpenAI** powers the chat replies (a fine-tuned model) and voice-to-text (`gpt-4o-mini-transcribe`).
   - **gTTS (Google)** can turn text replies into spoken audio.

> ⚠️ **Good to know:** a lot of *live* information — who is currently chatting, login
> tokens, and rate limits — is kept only in the server's short-term memory, not the
> database. If the server restarts (including after an auto-deploy), that all resets:
> active chats close and everyone is logged out. Only the permanent records (chat history,
> consent, notes) live safely in Supabase.

---

## What it's built with

**Backend (Python)**
- FastAPI + Uvicorn — the web server
- scikit-learn — the 3 small ML models that guess the mood of a message
- OpenAI — chat replies (fine-tuned `ft:gpt-3.5-turbo-0125`) and voice transcription (`gpt-4o-mini-transcribe`)
- librosa + numpy (+ OpenSmile) — pull stress signals out of raw audio (pitch, jitter/shimmer,
  pauses, speaking rate, energy)
- gTTS — text-to-speech
- Supabase — the database
- ReportLab — builds PDF session reports

**Frontend (React)**
- React 19 + Vite + Tailwind CSS
- react-router-dom — page navigation
- react-markdown — displays GAIDA's replies nicely
- recharts — charts on the counselor dashboard
- vite-plugin-pwa — makes it installable and offline-capable

**Hosting**
- Backend → **Replit** (deployed from Git — pushing to `main` auto-deploys)
- Frontend → **Vercel** (`https://gaida-system.vercel.app`)
- Database → Supabase (cloud Postgres)

---

## A student's journey, step by step

1. **Pick a portal** — Student or Counselor.
2. **Log in** — student number, @ue.edu.ph email, access code, and a simple on-screen
   CAPTCHA, or **"Sign in with UE Gmail"** (real Google verification against the @ue.edu.ph
   domain). The backend hands back a login token that lasts 12 hours.
3. **Give consent** — must be accepted before any chat data is saved.
4. **Chat** — every message the student sends is analyzed for mood and severity, and GAIDA
   replies. The app quietly checks every 3 seconds to see whether a human counselor has
   joined.
5. **A counselor gets involved two ways:**
   - automatically, when the system detects a High or Crisis situation, or
   - on request, when the student taps "Talk to a Counselor."
   Once a counselor takes over, GAIDA stops replying until control is handed back.
6. **Ending the session** — the student rates how they feel (1–4), and the session closes.

---

## How GAIDA "reads" a message

This is the heart of the system and runs on every single message, in this order:

1. **Crisis keywords, first.** A list of English and Filipino phrases, covering both
   *statements of intent* ("i want to kill myself", "gusto ko na mamatay") and **methods and
   means** ("I'm going to take all these pills", "jumping off the bridge", "lulunukin ko
   lahat ng gamot"). Filipino verbs inflect, so a short set of roots is matched as substrings
   rather than enumerating conjugations — otherwise the list only ever contains the one form
   the author happened to write down. Method verbs must be paired with their object
   ("maghihigpit **ako**" is a student tidying up; "maghihigpit ako ng **tali**" is not), and
   a stem only counts when the student is talking about themselves, so "sana mamatay na lang
   siya" — a death wish aimed at someone else — is not a crisis. Any match is treated as
   crisis instantly and overrides everything else, so a real crisis is never hidden even
   inside a venting message.
2. **"Normal venting" check.** Common study-frustration lines ("ayoko na mag-aral", "pagod
   na ako sa school") are marked as harmless. Safety detail: the crisis check above runs
   first, so this mask can only calm things down, never hide a real emergency. Soft
   "give-up" phrases like "ayoko na ng lahat" are only treated as stress when they are
   clearly about school or work.
3. **Grief detection.** Runs after the crisis hard path and before the ML vote. Grief is not
   a distortion to be corrected, so it gets its own intent, protocol, and response flow
   rather than borrowing the anxiety ladder. It is detected by rule, because the ML training
   labels have no grief class, so a breakup gets voted `sadness` and handed the "interrupt the
   overthinking loop" reframe that quietly implies the student is misthinking their loss. It
   is floored at Moderate (a bereaved student sent a "Normal" conversational check-in reads
   as indifference), it never pages a counselor on keywords alone, and it stays active until
   the student explicitly says they are better.
4. **Machine learning vote.** Three small models (Logistic Regression, Random Forest,
   Neural Network) vote on the mood. If they agree well, that wins. If they're unsure, the
   system falls through to the rules below. **A suicidal vote backed by explicit death or
   self-harm vocabulary is floored to Crisis.** Without that floor the ML path was
   structurally incapable of producing a crisis: it scales as `0.3 + 0.7 × confidence` and
   then caps at 0.98, while the crisis bypass fires at 0.99 — so a message the model was
   *certain* about ("I'm going to take all these pills tonight", voted suicidal at 0.63) was
   answered as an ordinary High, with no hotline numbers and no counselor alerted. Both
   pieces are required, because either alone misfires — see the limitations section.
5. **Keyword rule engine (backup).** A second system scores the message against weighted
   keywords in English and Filipino and picks the strongest mood.
6. **Context correction.** The guess is softened when the message is a joke, about a movie
   or story, in the past tense, about someone else, or hypothetical ("what if"). These
   guards live in the shared resolver so **every** route into a crisis verdict passes the
   same questions, because a matched keyword previously bypassed the past-tense and joke
   checks entirely and "i used to want to die lol" paged a counselor. A hypothetical suicide
   still triggers a High alert, but not the full Crisis response.
7. **Conversation memory + de-escalation hold.** GAIDA tracks the trend over time:
   calming words ("okay na ako", "salamat") ease the detected level back down, repeated
   distress pushes it up, and the level never suddenly drops without a reason. A genuine
   crisis always overrides this. **Important safety hold:** once a High/Crisis is reached,
   the level is *held* there and GAIDA asks "Are you safe right now?" — it only steps back
   down after the student explicitly confirms they're safe.
8. **Severity label.** The final score becomes one label: **Normal, Low, Moderate, High, or
   Crisis**.
9. **Voice fusion (if voice was used).** The voice reading is combined with the text
   reading, and a higher reading can bump the overall level up.
10. **GAIDA replies.** The fine-tuned model is given the severity's flow as a **menu of 2-3
    moves to choose from in priority order** rather than a script to recite, plus 13 worked
    replies as examples and a list of what GAIDA has already said earlier in the
    conversation, so it stops circling the same question. Three deterministic safety nets sit
    underneath the prompt, because a prompt alone cannot guarantee any of them:
    - **Echo guard** - if a reply only parrots the student's own words back it is rejected and
      regenerated once. Crisis replies are exempt: the guard fired there in testing and
      inserted a placeholder hotline line into a real crisis reply.
    - **Closing-question repair** - if the reply ends without something the student can
      actually answer, a question is appended, drawn from a pool matched to the reply's
      language, so a Tagalog reply never gets an English question bolted onto it.
    - **Resource guarantee** - a Crisis reply missing any of the three numbers (1553,
      (02) 893-7603, 911) has them restored. The required lines are derived from the caller's
      own resource block, not a second hardcoded copy that can drift out of sync.
11. **Alert + save.** High/Crisis messages notify the counselor dashboard, and (only if
    consent was given) the interaction is saved to the database.

---

## Voice handling

1. **Recording → stress analysis.** The audio is checked for pitch, a shaky voice
   (jitter/shimmer), pauses, speaking rate, and energy via librosa/OpenSmile, and the
   result is logged as acoustic features.
2. **Recording → text.** The same audio is sent to OpenAI's hosted speech-to-text API
   (`gpt-4o-mini-transcribe`). (The browser also shows a quick live transcript using its built-in speech
   recognition while you talk.)
3. **Result.** An estimated stress level from voice alone that later merges with the
   text-based detection (step 8 above). Backend endpoints: `POST /audio/speech-to-text`,
   `POST /audio/analyze`.
4. **Text-to-speech.** A working endpoint (`GET /audio/tts`) can speak replies aloud via
   gTTS, but the live chat does not auto-play it yet — it's ready for a future toggle.

---

## What gets stored, and where

**Permanent (Supabase):**
- sessions, chat messages, consent records, counselor alerts, session notes, wellbeing
  ratings, voice-analysis logs, research participants + GAD-7 responses, and per-message
  feedback ratings.

**Temporary (server memory only, lost on restart):**
- which sessions are currently active, login tokens, typing indicators, and rate-limit
  counters.

(One quirk worth knowing: two parts of the code label saved sessions slightly differently
— as `session_id` vs `session_token` — which can occasionally make a saved session hard to
look up.)

---

## Frontend pages

| Page | What happens there |
|---|---|
| Portal selection | Choose Student or Counselor. |
| Student login | Credentials + CAPTCHA, plus "Sign in with UE Gmail" (real Google @ue.edu.ph verification). |
| Counselor login | Separate login — currently hard-coded counselor test credentials. |
| Forgot password | Show-only — it doesn't actually send a reset email; it always shows a success message so no one can guess valid emails. |
| Consent | Must be accepted before chatting. |
| Student dashboard | The chat itself, hotline & crisis panel (always visible), voice input, vent mode, per-message "Helpful/Not helpful" buttons, and a color theme picker. |
| Research flow | Optional participation: enter the researcher's anonymous code, consent, take the GAD-7. |
| Counselor dashboard | Alerts, live sessions, welfare-check list (silent High/Crisis students), case notes, PDF export, analytics, and an archive of resolved cases. |

---

## Offline support

- The app caches its core pages (the app shell) so it still opens without internet.
- Chat transcripts and alerts are **not** cached for offline viewing, and there is
  **no offline message queue** — while offline, sending is blocked and a banner tells
  the student to reconnect. This is a deliberate trade-off (see the note in
  `frontend/src/hooks/usePWA.js`): the earlier queue silently posted messages that never
  arrived, so pretending to queue them was judged worse than clearly being offline.
- Developer note: there is no service worker on localhost at all — offline behavior only
  engages when the app is served from a real web location.

---

## Machine learning and training

- The mood-detection models are trained on a labeled dataset of example phrases
  (`anxiety_training.jsonl`, plus anger and suicidal augmentation files).
- Three model types (Logistic Regression, Random Forest, Neural Network) are trained in
  `ml_classifier.py`; they vote and the majority wins. The best model by macro-F1 is also
  saved and pre-loaded at startup.
- GAIDA's chat replies come from a separate fine-tuned OpenAI model —
  `ft:gpt-3.5-turbo-0125:personal::DqH2I32e` — with `finetune.jsonl` example conversations.
  That file has been corrected: 46 of its 179 targets opened by announcing GAIDA's own
  presence ("I'm here", "Nandito ako", "Naririnig kita") and every crisis target carried
  only `1553` — never the second hotline, never `911`. Both taught the model behaviour the
  prompt explicitly forbids, and the missing numbers were the direct cause of crisis replies
  arriving without resources. All 29 resource-bearing targets now carry all three.
- **Detection is measured, not asserted.** `backend/training/expert_validation/score_detection.py`
  runs the real pipeline over the 120-message counselor-labeled `gold_key.csv` (24 per class,
  about half Filipino) and reports safety-critical misses first, then the confusion matrix,
  per-class recall, and the Filipino/English split. It stops after detection — generating a
  reply costs roughly ten times as much and measures something else.

  Current scores:

  | | before | after |
  |---|---|---|
  | Overall accuracy | 79.2% | **85.0%** |
  | Suicidal messages reaching the crisis flow | 15/24 | **24/24** |
  | Filipino | 64.7% | **89.1%** |
  | English | 81.6% | 81.5% |

- **Validation kits for the thesis:** an expert-validation kit
  (`backend/training/expert_validation`: gold-key sample, agreement script, HTML forms for
  counselors) and an acoustic-validation harness
  (`backend/training/acoustic_validation`: `evaluate_acoustic.py` + a labeled-clip template)
  that reports per-emotion accuracy, severity match, and panic/harm recall/false positives.

---

## Research mode (added for the study)

- Run entirely separately from the normal chat flow, for consenting participants only.
- Students enter an **anonymous code** handed out by the researcher; the system stores them
  as `anon_<code>` so the student never needs to expose their identity in the data.
- A **GAD-7** questionnaire is collected for the study.
- **Data withdrawal:** entering the code into the *"Delete my data"* screen
  (`POST /api/research/withdraw`) permanently removes that participant's interactions,
  consents, GAD-7 answers, session ratings, notes, alerts, and voice logs. This makes the
  system able to honor a participant's right to withdraw.
- Researcher contact shown in the app (as configured in the code):
  `reyes.laurienaemanuel@ue.edu.ph`.

---

## Honest limitations (things worth knowing)

**Detection (measured, so these are numbers not guesses)**
- Safety-critical recall is now complete on the gold key — all 24 suicidal messages reach the
  crisis flow — but the other classes are not: anger 83%, anxiety 79%, sadness 71%. Every
  remaining mistake is the same one, **distress read as neutral** (18 of 120 messages). The
  three ML models under-call ordinary distress, and the keyword fallback does not catch up.
  This is the next thing worth fixing, and it is a data problem more than a code one.
- The ML classifier has genuine blind spots that no amount of guarding fully removes: it votes
  `suicidal` on `"safe na ako"` (a student confirming they are safe, 0.645) and on
  `"tinalon ako ng mundo sa saya"` (jumped for joy, 0.656). Both are now caught downstream —
  the crisis floor requires corroborating self-harm vocabulary, and Filipino joy markers were
  added beside the existing `lol|haha` — but the classifier itself is still wrong, and a
  future guard is another patch on top of a patch.
- The gold key is 120 messages. It is enough to catch a regression of this size and not enough
  to be confident about the tail. It has never been rated for *reply quality*, only for
  detection.

**Reply quality (the part nobody has measured yet)**
- GAIDA's replies have been reviewed by counselors, who are being asked the wrong question.
  Counselors can rate clinical adequacy; they cannot tell you whether a reply felt like a
  person. That needs **students**. The cheap version is ten reply pairs and one question —
  which of these two felt more real.
- One known failure the prompt cannot fix on its own: replies sometimes assert the student's
  inner state (`"Your heart is still with him even though he's moved on"`), which promotes a
  suspicion to a fact and is exactly what a bereaved student will object to. The practical
  test is simple and still worth applying by hand: read the last line first — if it does not
  end in something the student could answer, the rest of the reply does not matter.
- Roughly one reply in three in the crisis flow opens in all caps (`"I HEAR YOU."`). This is
  fine-tune behavior rather than prompt behavior and needs a training run to move.

**Security**
- Every endpoint requires a bearer login token, except the deliberately-public list: health check, the three login/consent/forgot-password routes, and the research intake + withdraw-by-code routes (a participant may not hold a token when entering or withdrawing). Counselor-only routes additionally require a *counselor* role token (403 otherwise); student/research routes verify the token owns the session.
- Counselor login is still test credentials (`COUNSELOR01` / `counsel123`), passed through a real `/api/auth/counselor-login` endpoint now — there's no self-service account system yet (counselors hand out access).
- The login CAPTCHA is checked in the browser only.

**Reliability**
- Everything assumes a single server instance — it isn't built to run across multiple
  servers yet.
- Live login sessions and alerts live only in server memory, so a **deploy or restart logs
  everyone out** and clears active sessions.
- Looking up resolved cases currently makes one database query per case, which will slow
  down as data grows.
- There's a slight naming mismatch between two parts of the code for saved sessions (see
  above), which can occasionally cause a session to not be found.

**Cost / models**
- The fine-tuned chat model is on the `gpt-3.5-turbo-0125` lineage, which OpenAI is
  retiring; it will eventually need to be re-trained on a newer model.
- Transcription is a hosted OpenAI API call (`gpt-4o-mini-transcribe`), so there's no local
  model warm-up; voice-detection accuracy is what still needs the labeled-clip validation.
- Voice-based detection accuracy is being quantified via the new acoustic-validation
  harness but still needs labeled recordings to produce final numbers.

**Rough edges**
- Some charts on the counselor dashboard fall back to sample data when there's nothing real
  to show yet.
- "Forgot password" doesn't send real emails (this is intentional, to avoid revealing which
  emails are registered).
- Consent status and the live chat can occasionally get slightly out of sync.

**Not yet built**
- No knowledge-base lookup (RAG) — GAIDA only uses its prompt and the last few messages.
- The backend has a WebSocket chat channel (`/api/session/ws/{session_id}`), but the
  frontend still polls every few seconds instead of using it.
- There are now SQL migration scripts for newer additions (`backend/training/sql/` — the
  research tables and the per-message feedback table), but the base chat schema is still
  assumed to already exist.

---

## Quick start (for developers)

**Backend**
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
# set OPENAI_API_KEY, SUPABASE_URL, SUPABASE_KEY (and optionally GOOGLE_CLIENT_ID) in backend/.env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

**Trying it out**
1. Go to http://localhost:5173 → Student Portal.
2. Log in with student number `2024001`, email `student1@ue.edu.ph`, code `ACCESS123`.
3. Accept consent, then chat with GAIDA.
4. Try something like "I can't breathe, my chest is tight" — it should trigger High severity
   and a counselor alert. Then say "I'm safe now" — GAIDA should confirm before easing the
   level down.
5. Try "I broke up with my partner and I don't know how to cope", then "I'm fine, just tired".
   The reply should stay with the loss rather than offering a reframe or a plan, and the
   level should not drop to a casual check-in while the grief is still disclosed.
6. Try "gusto ko na mamatay" — the reply must carry 1553, (02) 893-7603, and 911, and a
   counselor alert must fire. Then check `backend/training/expert_validation/detection_misses.csv`
   stays empty for that class.
7. Open the Counselor Portal in another tab (`COUNSELOR01` / `counsel123`), check Alerts,
   and take over the session.
8. Rate a reply with the "Helpful / Not helpful" buttons to see feedback logging.

**Re-running the detection score**
```bash
cd backend
venv\Scripts\python.exe training\expert_validation\score_detection.py
```
Prints safety-critical misses first, then overall accuracy, per-class recall, the confusion
matrix, and the Filipino/English split, and writes every miss to `detection_misses.csv`.
Run this after touching anything in `intent_router.py`, `virtual_agent.py`, or the crisis
lexicons — the test suite pins the specific cases, but the score shows what else moved.