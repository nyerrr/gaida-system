# GAIDA — Frontend Work Checklist (Audit)
**Date:** 2026-09-29

**Commit audited:** `01048a6` — *Restyle Withdraw to the Sky theme; correct PWA theme colours* (branch `main`, working tree clean)
**Scope:** `frontend/` (21 source files) + backend route inventory (50 routes) for integration validation
**Method:** full read of config/docs, full read of 12 smaller source files, line-accurate audit of the 3 largest files (`StudentDashboard.jsx` 1317 L, `CounselorDashboard.jsx` 2162 L, `ResearchFlow.jsx` ~620 L). Every claim below is anchored to a `file:line`.

**Status: no code was changed. This document is the proposed scope of work.**

Legend: 🔴 High (blocks release / data loss / safety) · 🟡 Medium (degrades quality or breaks a flow) · 🟢 Low (polish)

---

## 0. Concrete bugs — read this first

Ten defects, each verified in source. These are not stylistic opinions.

| # | Sev | Defect | Location |
|---|-----|--------|----------|
| 1 | 🔴 | `handleMarkWelfareChecked` **ignores the response**. On network failure or 500 the row is still removed from the list. A counselor marks a welfare check done; it was never saved. | `CounselorDashboard.jsx:1819-1828` |
| 2 | 🔴 | `handleResolve` **silently no-ops on `ok:false`**. `if (data.ok) … else if (!res.ok) …` — when the backend returns HTTP 200 with `ok:false`, neither branch runs. Spinner stops, session stays open, no error shown. | `CounselorDashboard.jsx:1096-1102` |
| 3 | 🔴 | Dashboard data fetches swallow **every** error with `catch { }`. A total backend outage renders as "No alerts yet" / "No sessions" — indistinguishable from a genuinely empty state. A counselor can look at this screen during an outage and see nothing wrong. | `CounselorDashboard.jsx:1660` (alerts) + welfare/sessions fetches |
| 4 | 🔴 | `Notification` is referenced **unguarded** at module-effect level. On any non-secure origin (the documented LAN/HTTP test setup) `Notification` is `undefined` → `TypeError` in the mount effect. | `CounselorDashboard.jsx:1631-1635`, also `:1650` |
| 5 | 🔴 | `getAuthToken()` prefers `session_token` over `counselor_token`. A counselor who previously used the student portal on the same browser sends the **student** token → 401 → `api.js` clears auth and hard-redirects to `/`. | `api.js:16` (+ redirect at `:77-82`) |
| 6 | 🔴 | Streaming update uses `prev.slice(0, -1)`, assuming the last array element is always the bot message. A counselor message or a system message arriving mid-stream makes the slice **delete the wrong message** — visible transcript corruption in a clinical tool. | `StudentDashboard.jsx:645` |
| 7 | 🔴 | Check-in uses `setMessages([...])` (replace) instead of appending. Whatever was in the transcript before the check-in resolves is **wiped**. | `StudentDashboard.jsx:415-426` |
| 8 | 🔴 | `request-counselor` has `if (data.ok) { … }` with **no `else`**. Failure of any kind is completely silent — the student believes a counselor was paged. This is the escalation path for a student in distress. | `StudentDashboard.jsx:743-752` |
| 9 | 🔴 | **No crisis / hotline UI exists anywhere in the student experience**, despite hotline copy already existing in other files. The student has no in-app route to help at the moment the system detects a crisis. | absent in `StudentDashboard.jsx`; copy present at `CounselorDashboard.jsx:45` and `ResearchFlow.jsx:279` |
| 10 | 🔴 | `ChatModal` has **no dialog semantics**: no `role="dialog"`, no `aria-modal`, no focus trap, no Escape-to-close, no focus restore. Counselor cannot close the transcript with the keyboard; screen-reader users get no announcement. | `CounselorDashboard.jsx:1117-1118` |

### Systemic accessibility failure (measured)

A repo-wide scan for `role=` / `aria-*` across `frontend/src` returns **three** real attributes in the entire application:

- `App.jsx:148` `role="status"` + `:149` `aria-label="Loading"` (the route Suspense spinner)
- `CounselorDashboard.jsx:1952` `aria-label="Open menu"`
- `PWABanner.jsx:65` `aria-label="Dismiss install prompt"`

The `role=` matches in `StudentDashboard.jsx:1140/1155/1168` are React **props** to an `<Avatar>` component, not DOM roles.

**Contrast, computed (WCAG 2.1):**

| Token | Value | On | Ratio | AA (4.5:1) |
|---|---|---|---|---|
| `textMuted` sky | `#95A6AC` | `#FFFFFF` | **2.52:1** | ✗ |
| `textMuted` sage | `#93A899` | `#FFFFFF` | **2.53:1** | ✗ |
| `textMuted` lavender | `#9E9BB8` | `#FFFFFF` | **2.68:1** | ✗ |
| `textMuted` sand | `#A69985` | `#FFFFFF` | **2.79:1** | ✗ |
| Severity chip Crisis | `#9C5A3C` on `#F5E4DA` | | **4.31:1** | ✗ |
| Severity chip High | `#9C7A34` on `#F6ECD6` | | **3.41:1** | ✗ |
| Severity chip Moderate | `#3F7676` on `#DFEFEF` | | **4.36:1** | ✗ |
| Severity chip Low | `#4F7D58` on `#E2F0E4` | | **4.04:1** | ✗ |
| Severity chip Normal | `#6E7A80` on `#E9EDEE` | | **3.74:1** | ✗ |

All 9 fail. `textMuted` is used ~30× in `CounselorDashboard.jsx` alone. Severity chips render at `text-xs`/`text-[11px]` (`:910`, `:1076`) which is "normal text" under WCAG, so the 3:1 large-text allowance does not apply.

`Withdraw.jsx:198` contains a comment explicitly documenting that it avoided `textMuted` for exactly this reason — **that file is the correct model to propagate.**

---

## 1. Completed 🟢

Things that are genuinely done and should not be touched.

| Item | Evidence |
|---|---|
| Route-level code splitting on all 10 routes | `App.jsx:102-135` — every screen is `lazyRoute(...)` behind `<Suspense>` |
| Auth token centralized, 401 → auto-logout + redirect | `api.js:15-16`, `:77-82` |
| Backend endpoint reality check: **all ~40 frontend calls map to real routes**; no phantom paths | 50-route inventory cross-referenced against every `apiFetch` call |
| Two-role portal with separate token namespaces | `session_token` / `counselor_token` (`api.js:16`, `:49-50`) |
| WebSocket live chat (student + counselor) | `StudentDashboard.jsx:515` (`case 'counselor_active'`), `:476`; `CounselorDashboard.jsx` ChatModal |
| Four calm themes, consistently applied, red reserved for emergency-only | `StudentDashboard.jsx:20-90` — comment at `:93-94` is the design rule, and it is honoured |
| Google Sign-In UI complete | `GoogleSignIn.jsx` — **but non-functional in prod, see §3** |
| Forgot-password flow incl. `?role=` branching | `ForgotPassword.jsx`; linked at `StudentLogin.jsx:254`, `CounselorLogin.jsx:213` |
| Error boundary | `ErrorBoundary.jsx` |
| PWA hook + install banner | `usePWA.js`, `PWABanner.jsx` — **with dead state, see §4** |
| `theme-color` already correct | `frontend/index.html` → `#F7FAF9` (HANDOFF.md §D still lists this as open — **doc is stale**) |
| Research withdrawal flow, incl. measured-contrast code comments | `Withdraw.jsx` — best-engineered file in the repo |
| 10-item SUS instrument | `ResearchSUS.jsx` |
| PWA not registered in dev (intentional) | `vite.config` `injectRegister: false` — correct |
| Auth data purged on counselor logout | `CounselorDashboard.jsx:1832-1837` calls `clearSensitiveLocalData()` |
| Root `.gitignore` excludes `venv/`, `node_modules/`, `.env` | verified |

---

## 2. Partially Completed 🟡

Present but incomplete — the visible surface exists, the behaviour does not.

### 2.1 PWA / offline 🟡
- **What exists:** `usePWA.js` + `PWABanner.jsx`, service worker via `vite-plugin-pwa`, `public/offline.html`.
- **What is missing:**
  - `swReady` is set at `usePWA.js:36` and returned at `:136`, but `PWABanner.jsx:23-27` destructures the hook **without it** → dead state, install prompt never gated on SW readiness.
  - The banner copy **"Chat anytime, even offline" (`PWABanner.jsx:58`) is false.** There is no message queue and no transcript cache. This is a promise to a distressed user that the app cannot keep. The same file's own header comment at `:11` admits "There is no queued-message notice here any more" — the *copy* was never updated to match.
  - Install button can stick: `PWABanner.jsx:34` calls `await installApp()` with no `try/finally`, so a rejected `prompt()` leaves the button spinning.
  - Offline bar has no `role="status"` → not announced.
- **Where:** `frontend/src/hooks/usePWA.js`, `frontend/src/components/PWABanner.jsx`
- **Expected:** either (a) implement the queue, or (b) delete the claim. Option (b) is one line and is the honest fix.
- **Required:** the false claim (🟡). The stuck button (🟡). `swReady` cleanup (🟢).

### 2.2 Captcha on both logins 🟡
- **What exists:** a working captcha challenge on `StudentLogin.jsx` and `CounselorLogin.jsx`.
- **What is missing:** the ~50-line implementation is **duplicated verbatim** across the two files. `CounselorLogin.jsx` additionally keeps a `showCaptcha` state that is never read. Both use raw `fetch` instead of `apiFetch`, bypassing the centralized 401 handling.
- **Where:** `StudentLogin.jsx`, `features/auth/CounselorLogin.jsx`
- **Expected:** extract to `components/Captcha.jsx`; use `apiFetch`; delete `showCaptcha`.
- **Required:** 🟡 (duplication will drift, and one copy is already carrying dead state).

### 2.3 Research flow, 6 steps 🟡
- **What exists:** full 6-step intake, anonymous code, consent, demographics.
- **What is broken:**
  - The consent POST at `:174` sends a **hardcoded `consent_given: true`**. This is currently safe *only* because step 2 gates its Next button with `disabled={!consentChecked}` at `:330`. The guarantee lives ~160 lines away from the value it protects — fragile, not broken.
  - The anonymous-code path is inconsistent: `:89`, `:128`, `:193` derive the code differently.
  - `SAVE_CODE` step (`:591-618`) renders `textMuted` (§0 contrast table).
  - `:228` and `:529` are keyboard-unreachable scroll regions (`overflow-y-auto` with no `tabIndex`).
- **Required:** code consistency 🟡, contrast 🟡, keyboard scroll 🟡. Deriving `consent_given` from `consentChecked` at the call site is 🟢 hardening, not a bug fix.

### 2.4 Severity system 🟡
- The severity model is consistent and the "no alarm red" rule is respected — but **all five chips fail AA** (§0). The design is right; the palette needs one pass.
- **Required:** 🟡. Fix `SEVERITY_CONFIG` at `StudentDashboard.jsx:95-101` and mirror the `Withdraw.jsx:198` approach.

### 2.5 Session lifecycle 🟡
- Sessions are created and messages are sent, but there is **no rehydration**: a student who refreshes mid-session returns to an empty transcript with an active session ID. The backend stores the transcript; the frontend never reads it back.
- **Where:** `StudentDashboard.jsx:411-434` (mount effect fetches only the *check-in flag*)
- **Backend already supports this:** `GET /api/session/{id}` exists and is **not consumed by any frontend file.**
- **Required:** 🟡 — this is a data-loss-class defect from the user's perspective.

### 2.6 Header/CSP config 🟡
- CSP and security headers are defined **twice** — `frontend/vercel.json` and root `vercel.json`. They can and will drift.
- **Required:** 🟡 — pick one.

---

## 3. Missing 🔴

Work that does not exist anywhere in the codebase.

### 3.1 Crisis / hotline interface — 🔴 **HIGHEST PRIORITY**
- **What:** No crisis panel, hotline card, or hotline number appears anywhere in the student experience. `GAIDA_OVERVIEW.md:192` claims "hotline & crisis panel (always visible)" — **this is false documentation of a feature that was never built.** (`GAIDA_OVERVIEW.md:24` also claims the bot itself surfaces 1553 / (02) 893-7603 / 911 — that depends on the model prompt, not on any UI guarantee.)
- **Partially there:** the "End session" exit **does** exist (`:775-792`, button at `:1038-1042`) and correctly purges local data via `clearSensitiveLocalData()` (`:801`). So the user can leave. What they cannot do is *see help* before leaving.
- **Where:** add to `StudentDashboard.jsx` (student-facing) and surface consistently in the counselor dashboard.
- **Why:** The system classifies messages as `Crisis` severity (`:96`, `:421`). A student in crisis gets a bot reply, a severity chip, and an "End session" button — and no hotline number. The content already exists in `CounselorDashboard.jsx:45` ("Call the National Crisis Hotline at 1553…") and `ResearchFlow.jsx:279`; only the student-facing UI is missing. (`InformedConsent.jsx` contains **no** hotline reference — verified.)
- **Expected:** always-visible, theme-consistent panel; hotline numbers; explicit "this is not an emergency service" framing; a deliberate, non-guilt-inducing exit path.
- **Required: YES.** Non-negotiable for a mental-health product.

### 3.2 404 / catch-all route — 🔴
- **What:** `App.jsx:125-135` defines 10 routes and no `*`. Any typo'd or stale URL renders a **blank page**.
- **Expected:** `<Route path="*" element={<NotFound />} />` with a link back to `/`.
- **Required:** 🟡 functionally, but it is 3 lines and currently produces a silent white screen — treat as 🔴 quick win.

### 3.3 Route-level auth guards — 🔴
- **What:** No `RequireAuth` / `RequireRole` wrapper. `/student-dashboard` and `/counselor-dashboard` render for anyone who navigates there; protection relies entirely on a `useEffect` in the component body that redirects after first paint.
- **Where:** `App.jsx:124-135`
- **Why:** Defense in depth, and it removes the flash-of-protected-content. Also makes §0 bug #5 (token precedence) less catastrophic.
- **Required:** 🟡

### 3.4 Accessible dialog for `ChatModal` — 🔴
- **What:** `role="dialog"`, `aria-modal="true"`, labelled title, focus trap, Escape handler, focus restore on close.
- **Where:** `CounselorDashboard.jsx:1117-1118`
- **Required:** 🟡 (but see §0 — listed high because it is a keyboard dead-end)

### 3.5 Error + empty states for every async surface — 🔴
- **What:** Because fetches `catch {}` (§0 #3), there is no distinction between "loading", "loaded, empty", and "failed". The dashboard currently shows the empty state for a network outage.
- **Expected:** each panel renders one of `loading | empty | error(+retry)`.
- **Where:** alerts, sessions, welfare, resolved, trends, reports panels in `CounselorDashboard.jsx`
- **Required:** 🔴 — a counselor cannot safely act on a screen that lies about its own state.

### 3.6 Production build / bundle verification — 🔴
- **No evidence of a successful production build in the repo.** The dev server and a Vercel build are different code paths (SW registration, CSP, minification). Everything above is a source-level finding only.
- **Required:** 🔴 as a *process* item — build once before any of the fixes land.

---

## 4. Needs Fixing 🔴 / 🟡

### 4.1 Blocking dependencies owned outside `frontend/` 🔴
These make local end-to-end testing impossible and are **not** frontend tasks. They must be resolved by the backend owner before the checklist below can be verified.

| Blocker | Detail |
|---|---|
| 7 unapplied DB migrations | `backend/training/sql/` — per HANDOFF.md §1 |
| Google OAuth client IDs unauthorized for their own origins | HANDOFF.md §B → Google Sign-In is non-functional in prod |
| `backend/.env` `SUPABASE_URL` points at the Supabase **dashboard URL**, not the API host | every local test that touches the DB fails |
| No service worker in dev | by design — do not "fix" |

### 4.2 Correctness 🔴
See §0 items #1, #2, #3, #5, #6, #7, #8. Each fix is small; the aggregate is what matters.

### 4.3 `VoiceInput.jsx` 🟡
- **Null-deref:** `:79` tests `mediaRecorderRef.current?.state !== "inactive"`; when `current` is `null`, `undefined !== "inactive"` is `true`, so `:80` executes `mediaRecorderRef.current.stop()` → `TypeError`. Guard with `mediaRecorderRef.current?.state`.
- **Silent recognition errors:** `:180` `recognition.onerror = () => {}` — a denied microphone or unsupported browser produces **no user feedback at all**.
- **Tap targets:** `:316` `w-4 h-4` (16px) and `:319` `w-3 h-3` (12px) icon buttons — below the 44px / 24px minimums.
- **Tooltips:** `:273`, `:339`, `:381` use `whitespace-nowrap` with no width cap → overflow the viewport on narrow phones.
- **Required:** 🟡 all four.

### 4.4 `InformedConsent.jsx` 🟡
- **`:16` `crypto.randomUUID()` is unavailable on insecure origins.** The documented LAN-HTTP test path throws. Use a `getRandomValues` fallback.
- **`:35` `alert()` for an error** — inconsistent with every other screen, and not announced.
- **`:77`** legal text is a keyboard-unreachable scroll region — no `tabIndex`, no `role="region"`, no label. A keyboard-only user cannot read the consent text they are consenting to.
- **Required:** 🟡 all three. (The insecure-origin one is 🔴 *if* LAN testing is part of the deliverable.)

### 4.5 Responsive layout 🟡
- **`min-h-screen` + `items-center` clips content in landscape** on `StudentLogin`, `CounselorLogin`, `InformedConsent`, `ForgotPassword`. Use `min-h-dvh` + `py-*` and allow scroll.
- **Fixed-pixel rows with no `md:`/`lg:` breakpoints:** `DetectionPage` (`:1494-1501`, `w-16` + `w-24` fixed columns), `AlertRow` (`:422`), `WelfarePage` (`:611`), `SessionsPage` (`:654`), `ResolvedCases` header, `ChatModal` header.
- **Android soft keyboard covers the composer.** `frontend/index.html` viewport meta lacks `interactive-widget=resizes-content`. This is the single most common way chat UIs break on Android.
- **Required:** 🟡 — with the viewport-meta fix first, it is one attribute.

### 4.6 Documentation drift 🟡
Docs currently assert behaviour that does not exist. Anyone reading them will build the wrong thing.
- `GAIDA_OVERVIEW.md:30`, `:200-205` — used to claim an **offline message queue** and **offline chat caching**. Both removed; not in the codebase. ✅ **Corrected** — `GAIDA_SYSTEM.md` + `GAIDA_OVERVIEW.md` now state plainly that there is no offline queue and no offline transcript cache.
- `GAIDA_OVERVIEW.md:192` — claims an always-visible hotline & crisis panel. Does not exist (§3.1).
- `GAIDA_OVERVIEW.md:278` — claims the frontend "still polls instead of WebSocket". WebSocket **is** implemented; both mechanisms run.
- `HANDOFF.md` §D — lists `theme-color` as open. Already fixed.
- **Required:** 🟡 — a wrong doc is a defect.

### 4.7 Dead / duplicated files 🟢
Unreferenced leftovers to delete or promote:
- `frontend/src/App.css` — not imported by any file
- `frontend/src/assets/react.svg` — Vite scaffold
- `frontend/public/manifest_icons_snippet.json` — snippet, not consumed
- `frontend/public/generate_favicons.py`, `generate_icons.py`, `generate_icons_v2.py` — build helpers checked in
- **Two byte-identical icon sets** — `frontend/public/*.png` and `frontend/public/icons/*.png` (9 files each, same byte sizes, plus a duplicate `manifest.json` / `site.webmanifest`). Confirm which one `manifest.json` actually references, then delete the other.
- root `package.json`, `eslint.config.js`, `postcss.config.js`, `public/vite.svg` — stale duplicates of the `frontend/` originals. Vite's public dir is `frontend/public`, so root `public/vite.svg` can never be served.
- `requirements.txt~` (0 bytes) — editor backup artifact
- `frontend/public/offline.html` — confirm the SW actually references it; if not, dead
- **Required:** 🟢

---

## 5. Needs Testing 🟡

Nothing below has been executed. The audit is static, source-level only.

### 5.1 Must test before shipping 🔴
1. **Production build succeeds** (§3.6) — never verified.
2. **Counselor outage test** — kill the backend, load `/counselor-dashboard`, confirm it shows an error state and not "No alerts" (§0 #3). This is the test that would have caught the most dangerous bug in this document.
3. **Cross-role token test** — student logs in, logout not completed, counselor logs in on the same browser (§0 #5).
4. **Mid-stream counselor interjection** — counselor replies while the student bot is streaming (§0 #6).
5. **Refresh mid-session** — confirm transcript loss is real, then confirm the fix (§2.5).
6. **Request-counselor failure path** — force a 500, confirm the student is told (§0 #8).
7. **Crisis flow end-to-end** — student message → Crisis severity → counselor alert → resolve. Blocked by §4.1 migrations.
8. **HTTPS requirement** — load on LAN HTTP and confirm `Notification` / `crypto.randomUUID` do not throw (§0 #4, §4.4).

### 5.2 Standard matrix 🟡
- **Viewports:** 320 / 375 / 390 / 768 / 1024 / 1440 — plus **landscape phone** (the `min-h-screen` clip).
- **Browsers:** Chrome, Safari iOS, Firefox, Android Chrome, Samsung Internet.
- **Keyboard-only pass** on every screen (WCAG 2.1 AA, 2.1.1 / 2.4.3 / 2.4.7).
- **Screen-reader pass:** VoiceOver (iOS) + NVDA (Windows) on student chat, counselor dashboard, ChatModal, consent.
- **Theme pass:** all 4 themes (`StudentDashboard.jsx:20-90`) at both viewports.
- **Long-content pass:** 200-char names, 500-message transcripts, long research comments.
- **Offline pass:** airplane mode on each screen — note that this currently exposes the false PWA copy (§2.1).
- **Axe DevTools** on all 10 routes — expect non-zero violations given §0.

### 5.3 Contract tests 🟡
Backend exposes **7 endpoints no frontend file consumes**:
- `GET /api/counselor/severity/{anxiety_score}`
- `GET /api/counselor/alerts/pending`
- `POST /api/session/message`
- `GET /api/session/{id}` ← would fix §2.5
- `GET /audio/tts`
- `POST /audio/analyze`
- alert fields `notifications[]`, `last_escalation_email_at`, `acknowledged_by`, `deleted_by`

These are cheap, high-value frontend work already paid for on the backend side.

---

## 6. Optional Improvements 🟢

None of these are release blockers.

| Idea | Rationale |
|---|---|
| **Error telemetry** (Sentry or equivalent) | §0 #3 shows the failure mode is *silent failure*. Instrumenting `apiFetch` would have caught bugs #1, #2, #8 automatically. Highest leverage-per-hour item in this list. |
| **Student session rehydration** beyond check-in | Restore the full transcript on mount. Backend already supports it. |
| **Adopt `Withdraw.jsx` as the a11y reference** | It already contains the measured-contrast reasoning the other files lack. Extract its palette to a shared module. |
| **Extract shared theme tokens** | The palette is duplicated across `StudentDashboard.jsx:20-90`, `ResearchFlow.jsx:50`, `ResearchSUS.jsx:44`, `CounselorDashboard.jsx:37`. A single source prevents the contrast bugs from re-appearing in a new file. |
| **Dark mode** | Themes are already data-driven; this is mostly token work. |
| **WebSocket reconnect + backoff** | Verify current behaviour on a dropped connection. |
| **Virtualized transcript** | Required beyond roughly 1,000 messages; not urgent. |
| **i18n** | Hardcoded English and Taglish strings. |
| **Formal test suite** | No test runner is configured. At minimum, add a smoke test per route — every bug in §0 is unit-testable. |
| **Component library** | With `StudentDashboard.jsx` at 1,317 lines and `CounselorDashboard.jsx` at 2,162, extraction into `components/` is the structural fix. |

---

## Suggested order of work

1. **§4.1** — unblock the backend owner. Nothing downstream can be verified until this clears.
2. **§3.6** — one production build. Establishes a working baseline.
3. **§0** — the ten bugs. Mostly one-to-five-line fixes.
4. **§3.1** — crisis UI. The only item here that is both missing *and* safety-critical.
5. **§3.5, §3.2, §3.3, §3.4** — error states, 404, guards, dialog semantics.
6. **§2.5** — session rehydration.
7. **§0 contrast table** — one palette pass, propagated everywhere.
8. **§4.5, §4.6, §4.7** — responsive, doc correction, dead-code removal.
9. **§5** — full test pass.

**Estimate shape:** items 1–3 are small. Item 4 is the only genuinely new build in the list. Items 5–7 are medium refactors. Items 8–9 are cleanup and verification.
