# GAIDA — Frontend Work Checklist & QA Audit

**Last Updated:** 2026-09-29  
**Status:** In Progress / QA Fixes Verified  
**Scope:** `frontend/` (React 19, Vite, Tailwind CSS)  
**Backend Integrity:** No backend files, routes, database migrations, or API contracts modified.

---

## 1. Newly Added / Updated in Current Task 🚀

### Privacy and Consent Scrollbar
* **Visually Hidden Scrollbar:** The scroll container on the public Privacy and Consent page (`frontend/src/features/auth/PrivacyPolicy.jsx`) now uses the scoped `.no-scrollbar` utility (`scrollbar-width: none`, `-ms-overflow-style: none`, `::-webkit-scrollbar { display: none }`).
* **Full Scrollability Preserved:** Vertical mouse wheel, trackpad, and touch scrolling remain completely functional.
* **Keyboard Navigation & Accessibility:** Added `tabIndex={0}`, `role="region"`, and `aria-label="Privacy and consent content"`, enabling native keyboard navigation (Arrow Up/Down, Page Up/Down, Home, End) with a subtle brand focus ring (`focus-visible:ring-1 focus-visible:ring-[#608AB6]`).
* **Zero Layout Shift / No Horizontal Scroll:** Horizontal overflow is contained (`scrollWidth === clientWidth`). Content is never clipped.
* **Isolated Scope:** Only applies to the Privacy & Consent scroll container. The authenticated Informed Consent page (`InformedConsent.jsx`), dashboards, modals, and global browser scrollbars are untouched.
* **Navigation Polish:** Removed the redundant top "Back to Login" button; primary action button cleanly formatted as "I Understand".

---

## 2. Completed QA Fixes (Previous & Current Sessions) 🟢

The following concrete bugs and requirements identified during previous audits have been investigated, fixed, and verified in code:

| # | Item | Status | Verification & Resolution |
|---|------|--------|---------------------------|
| 1 | `handleMarkWelfareChecked` response check | **Fixed** | Verifies response `ok` and status code before removing row from list; surfaces error on network failure. (`CounselorDashboard.jsx`) |
| 2 | `handleResolve` silent no-op | **Fixed** | Explicitly checks and handles `ok: false`, halts spinner, and surfaces error state. (`CounselorDashboard.jsx`) |
| 3 | Dashboard fetch error handling | **Fixed** | Replaced empty `catch {}` with dedicated error states (`analyticsError`, `reportsError`, `sessionsError`) and retry actions. (`CounselorDashboard.jsx`) |
| 4 | `Notification` API unguarded on HTTP | **Fixed** | Guarded with `typeof window !== 'undefined' && 'Notification' in window` for LAN testing. (`CounselorDashboard.jsx`) |
| 5 | Token selection collision (`getAuthToken`) | **Fixed** | Route-aware token resolution prioritizes counselor token on `/counselor` routes and student session token on student routes. (`api.js`) |
| 6 | Streaming update message slice | **Fixed** | Targets specific streaming message placeholder rather than naive `slice(0, -1)`, preventing transcript corruption. (`StudentDashboard.jsx`) |
| 7 | Check-in message transcript wipe | **Fixed** | Appends check-in greeting rather than replacing entire transcript array. (`StudentDashboard.jsx`) |
| 8 | `request-counselor` silent failure | **Fixed** | Added explicit `else` block, error toast/card, and retry mechanism. (`StudentDashboard.jsx`) |
| 9 | Crisis hotline UI in student experience | **Fixed** | Accessible Crisis Hotline Modal implemented with emergency numbers (1553, 911, Hopeline), focus trap, Escape listener, and focus restore. (`StudentDashboard.jsx`) |
| 10 | `ChatModal` dialog accessibility | **Fixed** | Added `role="dialog"`, `aria-modal="true"`, focus trap, Escape key handling, and focus restoration to trigger element. (`CounselorDashboard.jsx`) |
| 11 | Public Privacy & Consent separation | **Fixed** | Public `PrivacyPolicy.jsx` created: role-neutral header, 0 token mutation, separated from authenticated `InformedConsent.jsx`. |
| 12 | Research SUS route guard | **Fixed** | `ProtectedRoute.jsx` strictly requires *both* `session_id` AND `session_token` for access. |
| 13 | 404 Route Catch-All | **Fixed** | `<Route path="*" element={<NotFound />} />` configured with direct portal navigation. (`App.jsx`) |
| 14 | Production Build Verification | **Fixed** | `npm run build` runs cleanly in ~2.9s with content hashing and PWA generation. |
| 15 | Network Host Binding | **Fixed** | Configured `server: { host: '0.0.0.0', port: 5173 }` in `vite.config.js` to allow IPv4 (`127.0.0.1`), IPv6 (`::1`), and LAN access without connection refusal. |

---

## 3. Partially Completed / Remaining Frontend Polish 🟡

These items do not block primary user flows but represent open polish and optimization opportunities:

* **WCAG 2.1 AA Color Contrast Polish:** A few small secondary text tokens (`textMuted`) in dashboard subheadings and severity chips could benefit from darker contrast ratios.
* **Captcha Duplication:** Captcha logic is currently present in both `StudentLogin.jsx` and `CounselorLogin.jsx`; can eventually be unified into a shared component.
* **PWA Banner Copy Alignment:** PWA install banner displays "Install for quick and easy access", but offline queue is disabled by design in `vite-plugin-pwa`. Copy should remain clearly informative about online connectivity requirements.
* **VoiceInput Tap Targets:** Minor mobile tap target padding adjustments on smaller viewport sizes (<360px).
* **Vercel Config Deduplication:** Security headers currently declared in both root `vercel.json` and `frontend/vercel.json`.

---

## 4. Items Blocked by External / Backend Dependencies 🔴

These items are owned outside the frontend codebase and cannot be resolved by frontend changes alone:

| Blocker | Impact | Notes |
|---------|--------|-------|
| **Google Cloud OAuth Origins** | Google Sign-In popup opens blank or throws `origin_mismatch` | Requires adding `http://localhost:5173` and `http://127.0.0.1:5173` to Authorized JavaScript Origins in Google Cloud Console. |
| **Pending SQL Migrations** | Advanced alert logging & session analytics | Backend migrations in `backend/training/sql/` pending execution on Supabase. |
| **Supabase Local Service Role / URL** | Local backend full integration tests | `backend/.env` requires live Supabase API credentials for end-to-end counselor alert dispatch. |

---

## 5. Items Not Yet Tested (Testing Matrix) ⚪

The following tests require specific physical devices or test environments and have not yet been executed:

* **Physical Mobile Screen Readers:** VoiceOver on iOS Safari and TalkBack on Android Chrome across chat flows.
* **Physical Device Orientation:** Soft-keyboard interaction in landscape viewports on physical mobile devices.
* **High-Volume Transcript Stress Test:** Live transcripts exceeding 500+ messages without UI stutter.
* **Contract Tests with Unconsumed Backend Endpoints:** Verification of optional endpoints (`/audio/tts`, `/api/counselor/severity/{anxiety_score}`).

---

## 6. Build & Lint Verification Status

* **Linter:** `npm run lint` — **PASS** (0 errors, 0 warnings).
* **Production Build:** `npm run build` — **PASS** (`vite v7.3.6`, built in ~2.9s).
* **Development Servers:** 
  - Backend: FastAPI / Uvicorn running on `http://127.0.0.1:8000` (HTTP 200).
  - Frontend: Vite dev server running on `http://localhost:5173` and `http://127.0.0.1:5173` (HTTP 200).
