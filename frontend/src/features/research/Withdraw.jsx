import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import apiFetch from '../../api';

// Lets an anonymous research participant delete everything tied to their
// code: sessions, chat messages, GAD-7/SUS responses, ratings, notes,
// counselor alerts, acoustic logs, and the participant record itself.
// Backed by POST /api/research/withdraw (backend/app/api/research.py) —
// this page is the only way a participant can actually reach that
// endpoint; it's public (no login/token required), matching the fact that
// an anonymous participant has no account to authenticate with, only the
// code they were shown once.
const STEP = { FORM: 0, SUBMITTING: 1, DONE: 2 };

// Mirrors the "Sky" theme in ResearchFlow.jsx / ResearchSUS.jsx /
// StudentDashboard.jsx. This page used to be a dark-theme outlier
// (bg-gray-900 / bg-red-600) and was the last research screen still on it.
//
// The destructive tones are the reserved ones from CounselorDashboard.jsx,
// not a fresh red. That file documents the rule this follows:
//
//   "Bright red is reserved for genuine crisis-level and
//    overdue/unaddressed states, not used as a general UI color."
//
// A delete-data control is a permanently-destructive action, so it uses the
// same red (#B0472F) that marks Crisis alerts. The amber tones cover the
// partial-deletion outcome, which is a warning rather than an error — the
// request was honoured, just not completely. Keeping it distinct from the
// error red matters here: telling a participant their deletion failed when it
// only partially succeeded would push them into contacting the research team
// unnecessarily.
const T = {
  bg: '#F7FAF9',
  card: '#FFFFFF',
  border: '#DCE7EA',
  // accentDark, not accent, for any filled button with white text.
  // White on accent is 3.42:1, which fails AA at 14px; white on accentDark
  // is 4.84:1. The dark variant is what the token is for — it already exists
  // in the ResearchFlow / ResearchSUS / CounselorDashboard palettes.
  accentDark: '#4A7699',
  textPrimary: '#2E3B44',
  textSecondary: '#5C6F78',
  red: '#B0472F',
  redSoft: '#FBEDEA',
  redBorder: '#F0D2CA',
  amberSoft: '#F5E9D6',
  // Two separate ambers on purpose. The palette's #C98B3D is a *fill* —
  // it clears 3:1 as a button background behind white text, but only 2.9:1
  // as text on the white card, which fails AA at 16px. AmberDark is the
  // text-weight version of the same hue (5.8:1 on white, 4.8:1 on amberSoft),
  // so the warning stays visually distinct from the error red without being
  // unreadable.
  amberDark: '#8A5C22',
};

export default function Withdraw() {
  const navigate = useNavigate();
  const [step, setStep] = useState(STEP.FORM);
  const [code, setCode] = useState('');
  const [confirmChecked, setConfirmChecked] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!code.trim() || !confirmChecked) return;
    setError('');
    setStep(STEP.SUBMITTING);

    try {
      const res = await apiFetch('/api/research/withdraw', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ participant_code: code.trim() }),
      });
      if (!res.ok) throw new Error('Request failed');
      const data = await res.json();
      setResult(data);
      setStep(STEP.DONE);
    } catch (err) {
      console.error('Withdraw error:', err);
      setError('Something went wrong submitting your request. Please try again, or email the research team directly if this keeps happening.');
      setStep(STEP.FORM);
    }
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center p-4"
      style={{ background: T.bg, color: T.textPrimary }}
    >
      <div
        className="w-full max-w-md rounded-2xl p-8"
        style={{ background: T.card, border: `1px solid ${T.border}`, boxShadow: '0 1px 3px rgba(46,59,68,0.06)' }}
      >
        <h1 className="text-2xl font-bold mb-1" style={{ color: T.textPrimary }}>Withdraw From the Study</h1>
        <p className="text-sm mb-6" style={{ color: T.textSecondary }}>
          For participants who joined anonymously. Entering your code below permanently
          deletes every session, message, and response tied to it — there's no way to
          undo this once it's done.
        </p>

        {step === STEP.FORM && (
          <form onSubmit={handleSubmit}>
            <label htmlFor="withdraw-code" className="block text-sm font-medium" style={{ color: T.textPrimary }}>
              Your anonymous code
            </label>
            <p className="text-xs mt-1 mb-2" style={{ color: T.textSecondary }}>
              The code you were shown after your first session.
            </p>
            <input
              id="withdraw-code"
              type="text"
              placeholder="e.g. anon_4f2a9c"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              className="w-full rounded-lg px-3 py-2 text-sm font-mono outline-none focus:border-[#5E8FBD]"
              style={{ background: T.card, border: `1px solid ${T.border}`, color: T.textPrimary }}
            />

            <label
              htmlFor="withdraw-confirm"
              className="flex items-start gap-2 mt-4 text-sm rounded-lg px-3 py-2.5 cursor-pointer"
              style={{ background: T.redSoft, border: `1px solid ${T.redBorder}`, color: T.textPrimary }}
            >
              <input
                id="withdraw-confirm"
                type="checkbox"
                checked={confirmChecked}
                onChange={(e) => setConfirmChecked(e.target.checked)}
                className="mt-0.5 shrink-0"
              />
              <span>
                I understand this permanently deletes all data tied to this code, and
                cannot be undone.
              </span>
            </label>

            {error && (
              <p className="text-sm mt-4 rounded-lg px-3 py-2" style={{ color: T.red, background: T.redSoft }}>
                {error}
              </p>
            )}

            <div className="flex gap-3 mt-6">
              <button
                type="button"
                onClick={() => navigate('/')}
                className="flex-1 py-2 rounded-lg text-sm font-medium transition-colors"
                style={{ background: T.card, border: `1px solid ${T.border}`, color: T.textSecondary }}
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!code.trim() || !confirmChecked}
                className="flex-1 py-2 rounded-lg font-semibold text-sm transition-opacity disabled:opacity-40"
                style={{ background: T.red, color: '#FFFFFF' }}
              >
                Delete My Data
              </button>
            </div>
          </form>
        )}

        {step === STEP.SUBMITTING && (
          <p className="text-center py-10" style={{ color: T.textSecondary }}>Processing your request…</p>
        )}

        {step === STEP.DONE && (
          <div className="text-center py-4">
            {result?.ok === false ? (
              <>
                <p className="font-semibold mb-2" style={{ color: T.amberDark }}>Partially completed</p>
                <p className="mb-2 text-sm" style={{ color: T.textPrimary }}>
                  {result?.deleted_sessions
                    ? `${result.deleted_sessions} session${result.deleted_sessions === 1 ? '' : 's'} were deleted, but some data could not be removed automatically.`
                    : 'Some data could not be removed automatically.'}
                  {' '}Please contact the research team below with your code so they can
                  finish the deletion manually.
                </p>
                {Array.isArray(result?.errors) && result.errors.length > 0 && (
                  <p
                    className="text-xs mb-4 break-words rounded-lg px-3 py-2 text-left"
                    style={{ color: T.textPrimary, background: T.amberSoft }}
                  >
                    Details: {result.errors.join('; ')}
                  </p>
                )}
              </>
            ) : (
              <>
                <p className="mb-2" style={{ color: T.textPrimary }}>
                  {result?.deleted_sessions
                    ? `Done — ${result.deleted_sessions} session${result.deleted_sessions === 1 ? '' : 's'} and all associated data have been deleted.`
                    : 'Done — no data was found for that code, so there was nothing to delete.'}
                </p>
                {/* textSecondary, not the palette's textMuted (#95A6AC, 2.5:1) —
                    that tone is fine for a 10px tooltip label but this sentence
                    tells a participant how to reach the research team. */}
                <p className="text-xs mb-6" style={{ color: T.textSecondary }}>
                  If you believe this is a mistake, contact the research team — but note the
                  deletion itself cannot be reversed.
                </p>
              </>
            )}
            <button
              onClick={() => navigate('/')}
              className="w-full py-2 rounded-lg font-semibold text-sm transition-opacity"
              style={{ background: T.accentDark, color: '#FFFFFF' }}
            >
              Return to Portal
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
