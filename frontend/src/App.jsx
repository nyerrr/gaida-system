import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { lazy, Suspense } from 'react'

import PortalSelection from './features/auth/PortalSelection'
import PWABanner from './components/PWABanner'
import ErrorBoundary from './components/ErrorBoundary'

// Every other screen is loaded on demand. CounselorDashboard alone pulls in
// recharts, which is the single largest dependency in the app — eagerly
// importing it made every student and research participant download (and the
// service worker precache) a charting library they will never use. Route-level
// splitting keeps the login/portal first paint small; the two dashboards still
// resolve on their own before their route renders.
//
// Route-level splitting has one failure mode that a single bundle did not, so
// it needs handling: chunk filenames are content-hashed, and a tab can be
// holding a stale index.html (served from the service worker's precache, or
// simply opened before a deploy) that points at chunk names the current CDN
// no longer has. The dynamic import rejects, React throws during render, and
// the user lands on the error boundary — where "Reload page" re-fetches that
// same stale index.html from the precache and lands them right back here. The
// only routes that still work are the ones already in the old precache, so the
// trap is easy to hit and impossible to escape without a hard refresh.
const CHUNK_RELOAD_FLAG = 'gaida:chunk-reload'

// Ask the service worker to pick up the new build and wait for it to take
// control, so the reload below is served a fresh index.html rather than the
// stale precached one. Waiting is what makes the self-heal actually work:
// reloading before the new worker claims the page just re-serves the same stale
// index.html, and the chunk 404s a second time. Bounded, because if the update
// never lands the user must still get out of the crash page.
async function refreshServiceWorker() {
  if (!('serviceWorker' in navigator)) return
  try {
    const reg = await navigator.serviceWorker.getRegistration()
    if (!reg) return
    await reg.update()
    // controllerchange fires when the freshly installed worker claims this
    // client. If there is no controller yet (first ever install) there is
    // nothing to wait for and the reload can proceed immediately.
    if (navigator.serviceWorker.controller) {
      await new Promise((resolve) => {
        const timer = setTimeout(resolve, 3000)
        navigator.serviceWorker.addEventListener(
          'controllerchange',
          () => { clearTimeout(timer); resolve() },
          { once: true },
        )
      })
    }
  } catch { /* no worker registered, or update rejected — plain reload still helps */ }
}

// sessionStorage can throw outright — private windows, enterprise policy, or a
// full quota all make these accessors raise. Every use below is wrapped so a
// storage failure degrades the reload guard instead of replacing the chunk
// error it exists to report.
function readChunkReloadFlag() {
  try { return sessionStorage.getItem(CHUNK_RELOAD_FLAG) } catch { return null }
}

// Returns false when the guard could not be armed. That matters: the guard is
// the only thing stopping an endless reload, so a caller that cannot persist it
// must not reload.
function armChunkReloadFlag() {
  try { sessionStorage.setItem(CHUNK_RELOAD_FLAG, '1'); return true } catch { return false }
}

function clearChunkReloadFlag() {
  try { sessionStorage.removeItem(CHUNK_RELOAD_FLAG) } catch { /* storage disabled */ }
}

function lazyRoute(loader) {
  return lazy(async () => {
    try {
      const mod = await loader()
      // The chunk arrived, so the previous failure (if any) really was stale
      // build state and the reload did fix it. Re-arm the guard so a future
      // deploy can self-heal the same way. This must happen here, on a
      // confirmed load, and not on mount: clearing it at mount time races the
      // very import that failed and turns the guard into an endless reload.
      clearChunkReloadFlag()
      return mod
    } catch (err) {
      // Already reloaded once: the reload didn't help, so this is a real load
      // failure (offline, blocked, genuinely broken chunk). Surface it instead
      // of spinning.
      if (readChunkReloadFlag()) throw err
      // Storage is unavailable, so a reload could not be recognised as a retry
      // and would repeat forever. Surface the real error rather than trade a
      // visible failure for a reload loop.
      if (!armChunkReloadFlag()) throw err
      await refreshServiceWorker()
      window.location.reload()
      // Never settles: the reload replaces this page, and resolving would let
      // React paint the error boundary in the meantime.
      return new Promise(() => {})
    }
  })
}

const StudentLogin = lazyRoute(() => import('./features/student/StudentLogin'))
const CounselorLogin = lazyRoute(() => import('./features/auth/CounselorLogin'))
const InformedConsent = lazyRoute(() => import('./features/auth/InformedConsent'))
const StudentDashboard = lazyRoute(() => import('./features/student/StudentDashboard'))
const CounselorDashboard = lazyRoute(() => import('./features/counselor/CounselorDashboard'))
const ForgotPassword = lazyRoute(() => import('./features/auth/ForgotPassword'))
const ResearchFlow = lazyRoute(() => import('./features/research/ResearchFlow'))
const ResearchSUS = lazyRoute(() => import('./features/research/ResearchSUS'))
const Withdraw = lazyRoute(() => import('./features/research/Withdraw'))

function App() {
  return (
    <BrowserRouter>

      <ErrorBoundary>
        {/* PWA Banner — fixed top, visible on all routes */}
        <PWABanner />

        {/* While a lazy route's chunk is in flight. Deliberately plain (no
            branding animation) so it never flashes on top of a screen that's
            about to be replaced by a full-page login/portal layout. */}
        <Suspense fallback={<RouteLoading />}>
          <Routes>
            <Route path="/"                    element={<PortalSelection />} />
            <Route path="/student-login"       element={<StudentLogin />} />
            <Route path="/counselor-login"     element={<CounselorLogin />} />
            <Route path="/forgot-password"     element={<ForgotPassword />} />
            <Route path="/consent"             element={<InformedConsent />} />
            <Route path="/student-dashboard"   element={<StudentDashboard />} />
            <Route path="/counselor-dashboard" element={<CounselorDashboard />} />
            <Route path="/research"            element={<ResearchFlow />} />
            <Route path="/research-sus"        element={<ResearchSUS />} />
            <Route path="/research/withdraw"   element={<Withdraw />} />
          </Routes>
        </Suspense>
      </ErrorBoundary>

    </BrowserRouter>
  )
}

function RouteLoading() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div
        className="w-8 h-8 rounded-full border-2 border-gray-300 border-t-red-700 animate-spin"
        role="status"
        aria-label="Loading"
      />
    </div>
  )
}

export default App