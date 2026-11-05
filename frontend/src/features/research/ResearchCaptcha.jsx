import { useCallback, useEffect, useRef, useState } from 'react';
import { BACKEND_URL } from '../../config';

// Shared CAPTCHA for the two anonymous research entry points (intake and
// withdrawal). The research endpoints are gated by a short-lived access token
// obtained by solving this challenge, so participants never need an account.
const T = {
  card: '#FFFFFF',
  border: '#DCE7EA',
  textPrimary: '#2E3B44',
  textSecondary: '#5C6F78',
  accent: '#5E8FBD',
  errorText: '#9C5A3C',
};

export default function ResearchCaptcha({
  onChange,
  refreshSignal = 0,
  disabled = false,
}) {
  const [token, setToken] = useState('');
  const [image, setImage] = useState('');
  const [answer, setAnswer] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Keep the latest callback without making it an effect dependency — a new
  // inline handler on every parent render would otherwise reload the image.
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;
  const lastRefreshRef = useRef(refreshSignal);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${BACKEND_URL}/api/auth/captcha`, { cache: 'no-store' });
      if (!res.ok) throw new Error(String(res.status));
      const data = await res.json();
      setToken(data.token);
      setImage(data.image);
      setAnswer('');
    } catch {
      setToken('');
      setImage('');
      setError('Could not load the verification image. Please press refresh.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (refreshSignal !== lastRefreshRef.current) {
      lastRefreshRef.current = refreshSignal;
      load();
    }
  }, [refreshSignal, load]);

  useEffect(() => {
    onChangeRef.current?.({ token, answer });
  }, [token, answer]);

  return (
    <div className="mt-4">
      <label
        htmlFor="research-antibot"
        className="block text-sm font-medium mb-1"
        style={{ color: T.textPrimary }}
      >
        Verification code
      </label>
      <div className="flex gap-2">
        <div
          className="flex-shrink-0 rounded-lg overflow-hidden flex items-center justify-center p-0.5"
          style={{ border: `1px solid ${T.border}`, background: T.card }}
        >
          {image ? (
            <img
              src={image}
              alt="Verification code"
              width={140}
              height={47}
              className="rounded"
              draggable={false}
            />
          ) : (
            <div
              style={{ width: 140, height: 47 }}
              className="rounded bg-slate-100"
              aria-hidden="true"
            />
          )}
        </div>
        <div className="relative flex-1">
          <input
            id="research-antibot"
            type="text"
            value={answer}
            onChange={(e) => {
              setAnswer(e.target.value);
              setError('');
            }}
            autoComplete="off"
            spellCheck={false}
            disabled={disabled || loading}
            placeholder="Type code"
            className="w-full rounded-lg p-2.5 pr-9 text-sm outline-none"
            style={{ background: T.card, border: `1px solid ${T.border}`, color: T.textPrimary }}
          />
          <button
            type="button"
            onClick={load}
            disabled={disabled || loading}
            aria-label="Get a new verification image"
            title="Get a new verification image"
            className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700 disabled:opacity-50"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
          </button>
        </div>
      </div>
      {error && (
        <p className="text-xs mt-1" style={{ color: T.errorText }}>
          {error}
        </p>
      )}
      {loading && !error && (
        <p className="text-xs mt-1" style={{ color: T.textSecondary }}>
          Loading verification image…
        </p>
      )}
    </div>
  );
}
