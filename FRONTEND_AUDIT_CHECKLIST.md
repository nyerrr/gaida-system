# GAIDA Frontend Audit Checklist

**Last reviewed:** 2026-11-07
**Scope:** `frontend/`

This is the current release checklist. Historical source-level findings that have
already been fixed are intentionally not repeated here.

## 1. Automated validation

- [x] `npm run build` passes.
- [ ] `npm run lint` passes.
  - Current failure: `CounselorDashboard.jsx:187` reports the unused
    `closeSidebarTooltip` symbol.
- [ ] `npm test` passes.
- [ ] `git diff --check` passes.

Run commands from the `frontend/` directory:

```powershell
npm run build
npm run lint
npm test
git diff --check
```

## 2. Authentication and routing

- [ ] Student login works with the approved test account.
- [ ] Counselor login works with the approved counselor account.
- [ ] Invalid credentials display an actionable error.
- [ ] Forgot-password links preserve the correct role.
- [ ] Unauthenticated access to protected dashboards redirects to login.
- [ ] A stale or invalid route renders the not-found page rather than a blank
      screen.
- [ ] Logout clears the relevant role's sensitive local data.

## 3. Student experience

- [ ] Consent terms are readable and the consent decision is saved.
- [ ] Student can start a session and send text messages.
- [ ] Student can use voice input where browser permissions allow it.
- [ ] Voice permission and recognition failures are visible to the user.
- [ ] Chat transcript remains intact after a check-in or refresh.
- [ ] Vent mode is clearly distinguishable from normal support mode.
- [ ] Helpful/not-helpful feedback can be submitted once per reply.
- [ ] Counselor request success and failure states are both visible.
- [ ] Crisis and hotline information is reachable without leaving the student
      experience.
- [ ] Emergency contact links work on a mobile device.
- [ ] Offline messages show a waiting state and are sent after reconnection.

## 4. Counselor experience

- [ ] Overview, Alerts, Active Sessions, Welfare Checks, Detection, Reports,
      and Resolved Cases load.
- [ ] Loading, empty, and error states are visually distinct.
- [ ] Alert severity and pending counts are accurate.
- [ ] Counselor can open a transcript and reply.
- [ ] Takeover and hand-back states are visible and persistent.
- [ ] Welfare checks are removed only after the backend confirms success.
- [ ] Resolve failures remain visible and do not look successful.
- [ ] Case notes and assessment fields save correctly.
- [ ] PDF export downloads an authenticated report.
- [ ] Crisis hotlines and alert chime controls are available.

## 5. Responsive and accessibility checks

- [ ] Test viewport widths of 320px, 375px, 414px, and desktop width.
- [ ] Mobile drawer opens, has a visible close button, and does not show the
      desktop collapse control.
- [ ] Desktop sidebar collapse and expand controls work.
- [ ] Bottom navigation labels and active states remain readable.
- [ ] All buttons and links have accessible names.
- [ ] Keyboard focus is visible and dialogs can be closed with Escape.
- [ ] Modal focus is trapped and restored when the modal closes.
- [ ] Text, status chips, and muted labels meet the intended contrast target.
- [ ] Long IDs, messages, tooltips, and report labels do not overflow narrow
      screens.
- [ ] Reduced-motion and touch interaction behavior remain usable.

## 6. Production and PWA checks

- [ ] `VITE_BACKEND_URL` points to the intended production backend at build time.
- [ ] Backend CORS includes the deployed frontend origin.
- [ ] Service worker registers only in production builds.
- [ ] App shell opens when offline.
- [ ] Queued messages are not duplicated after reconnect.
- [ ] A new deployment refreshes stale route chunks instead of leaving a blank
      error screen.
- [ ] Browser console has no new errors during the smoke test.

## 7. Evidence to record

For each release, record:

- frontend commit and deployment URL;
- backend URL and deployment revision;
- browser and viewport used;
- result of `npm run build`, `npm run lint`, and `npm test`;
- screenshots or console errors for failed checks;
- date and operator initials.
