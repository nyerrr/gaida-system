import { BACKEND_URL } from './config'

// Bearer-token fetch wrapper.
//
// - Attaches `Authorization: Bearer <token>` from the active login
//   (student or counselor) to every request, except public login/health
//   endpoints.
// - Forwards 401 responses to the portal by clearing stored auth state so
//   the route guards bounce the user back to login.
//
// Usage:
//   apiFetch('/api/counselor/alerts')                       // token from localStorage
//   apiFetch(`${BACKEND}/virtual-agent/stream`, { ... })    // absolute URL ok
//   apiFetch('/api/research/gad7', {...}, explicitToken)    // caller-supplied token
export function getAuthToken(targetUrl = null) {
  // Route-first token resolution: determine context from the active authenticated path
  if (typeof window !== 'undefined') {
    const path = window.location.pathname;
    if (path.startsWith('/counselor')) {
      return localStorage.getItem('counselor_token') || null;
    }
    if (path.startsWith('/student') || path.startsWith('/consent') || path.startsWith('/research')) {
      return localStorage.getItem('session_token') || null;
    }
  }

  // Fallback for off-route calls: check if targetUrl targets counselor-only management
  const isCounselorAdminEndpoint = typeof targetUrl === 'string' && (
    targetUrl.includes('/counselor/alerts') ||
    targetUrl.includes('/counselor/sessions') ||
    targetUrl.includes('/counselor/analytics') ||
    targetUrl.includes('/counselor/trend') ||
    targetUrl.includes('/counselor/takeover') ||
    targetUrl.includes('/counselor/resolve') ||
    targetUrl.includes('/counselor/notes')
  );

  if (isCounselorAdminEndpoint) {
    return localStorage.getItem('counselor_token') || localStorage.getItem('session_token') || null;
  }

  return localStorage.getItem('session_token') || localStorage.getItem('counselor_token') || null;
}

// Purge anything sensitive this browser may be holding, so nothing outlives the
// session on a shared device. Called on logout / session end / 401.
//
// Each step is a no-op if the thing it targets isn't there, which is the normal
// case: the service worker no longer caches API responses (deliberately — that
// cache was keyed only by URL, so one student's data could be served to the
// next on a shared profile), and the offline outbox
// (`gaida-offline-queue`, see offlineQueue.js) is empty. Deleting it here is
// what keeps messages queued on a shared device from outliving the login that
// created them.
export async function clearSensitiveLocalData() {
  try {
    if ('caches' in window && typeof caches.keys === 'function') {
      const keys = await caches.keys()
      await Promise.all(keys.filter((k) => k.includes('-data')).map((k) => caches.delete(k)))
    }
  } catch { /* non-secure context or unsupported cache API — ignore */ }
  try {
    if ('indexedDB' in window) {
      await new Promise((resolve) => {
        const req = indexedDB.deleteDatabase('gaida-offline-queue')
        req.onsuccess = req.onerror = req.onblocked = () => resolve()
      })
    }
  } catch { /* ignore */ }
  try {
    navigator.serviceWorker?.controller?.postMessage({ type: 'LOGOUT' })
  } catch { /* ignore */ }
}

export function clearAuth() {
  // Clear all GAIDA localStorage state for both portals, including preferences,
  // so a shared browser profile starts clean for its next user.
  [
    'session_token',
    'counselor_token',
    'counselorData',
    'student_id',
    'session_id',
    'consent_given',
    'is_research_session',
    'gaida_theme',
    'gaida:alert-swipe-hint',
  ].forEach((key) => localStorage.removeItem(key))
  clearSensitiveLocalData()
}

export async function apiFetch(input, options = {}, tokenOverride = null) {
  const isAbsolute = typeof input === 'string' && /^https?:\/\//.test(input)
  const url = isAbsolute ? input : `${BACKEND_URL}${input}`

  // Public auth endpoints still use this wrapper for consistent URL, header,
  // and fetch handling, but must not inherit a stale bearer token or treat an
  // expected login 401 as an expired authenticated session.
  const { skipAuth = false, skipUnauthorizedRedirect = false, ...requestOptions } = options

  const headers = new Headers(requestOptions.headers || {})
  const token = skipAuth ? null : tokenOverride || getAuthToken(url)
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  const body = requestOptions.body
  if (
    body != null &&
    typeof body === 'string' &&
    !(requestOptions.headers instanceof Headers ? requestOptions.headers.has('Content-Type') : headers.has('Content-Type'))
  ) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(url, { ...requestOptions, headers })

  if (response.status === 401 && !tokenOverride && !skipUnauthorizedRedirect) {
    clearAuth()
    if (window.location.pathname !== '/') {
      window.location.href = '/'
    }
  }

  return response
}

export default apiFetch
