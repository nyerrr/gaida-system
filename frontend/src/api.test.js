import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { apiFetch, clearAuth, getAuthToken } from './api';

const response = (status = 200) => ({ status, ok: status >= 200 && status < 300 });

beforeEach(() => {
  localStorage.clear();
  window.history.replaceState({}, '', '/');
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response()));
});

afterEach(() => vi.unstubAllGlobals());

describe('authentication storage and API wrapper', () => {
  it('clears all GAIDA identity, session, consent, and preference keys', () => {
    [
      'session_token', 'counselor_token', 'counselorData', 'student_id',
      'session_id', 'consent_given', 'is_research_session', 'gaida_theme',
      'gaida:alert-swipe-hint',
    ].forEach((key) => localStorage.setItem(key, 'value'));

    clearAuth();

    expect(localStorage.length).toBe(0);
  });

  it('uses the counselor token on counselor routes', () => {
    localStorage.setItem('counselor_token', 'counselor-secret');
    localStorage.setItem('session_token', 'student-secret');
    window.history.replaceState({}, '', '/counselor-dashboard');

    expect(getAuthToken()).toBe('counselor-secret');
  });

  it('does not attach stale auth or clear the session for a public login 401', async () => {
    localStorage.setItem('session_token', 'existing-session');
    vi.mocked(fetch).mockResolvedValue(response(401));

    const result = await apiFetch('/api/auth/login', {
      method: 'POST',
      skipAuth: true,
      skipUnauthorizedRedirect: true,
    });

    expect(result.status).toBe(401);
    expect(fetch).toHaveBeenCalledOnce();
    expect(fetch.mock.calls[0][1].headers.get('Authorization')).toBeNull();
    expect(localStorage.getItem('session_token')).toBe('existing-session');
  });

  it('clears auth after an authenticated request returns 401', async () => {
    localStorage.setItem('session_token', 'expired-session');
    vi.mocked(fetch).mockResolvedValue(response(401));

    await apiFetch('/api/session/active');

    expect(localStorage.getItem('session_token')).toBeNull();
  });
});
