import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiFetch, clearAuth } from '../../api';
import { BACKEND_URL } from '../../config';

export default function InformedConsent() {
  const navigate = useNavigate();
  const [isChecked, setIsChecked] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [consentError, setConsentError] = useState('');
  const [termsRead, setTermsRead] = useState(false);
  const [termsAtEnd, setTermsAtEnd] = useState(false);

  const createSessionId = () => {
    const cryptoApi = globalThis.crypto;
    if (cryptoApi?.randomUUID) return cryptoApi.randomUUID();
    if (cryptoApi?.getRandomValues) {
      const bytes = cryptoApi.getRandomValues(new Uint8Array(16));
      bytes[6] = (bytes[6] & 0x0f) | 0x40;
      bytes[8] = (bytes[8] & 0x3f) | 0x80;
      const hex = [...bytes].map((byte) => byte.toString(16).padStart(2, '0')).join('');
      return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
    }
    return `gaida-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  };

const handleAccept = async (e) => {
  e.preventDefault();
  if (!isChecked || isSubmitting) return;
  setIsSubmitting(true);
  setConsentError('');

  try {
    // Get session_id from localStorage (set during login)
    const sessionId = localStorage.getItem('session_id') || createSessionId();

    // apiFetch attaches the student's bearer token. The consent endpoint is
    // authenticated: without it the backend rejects the request with 401.
    const response = await apiFetch(`${BACKEND_URL}/api/auth/consent`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        consent_given: true,
      }),
    });

    if (!response.ok) throw new Error('Failed to record consent');

    localStorage.setItem('consent_given', 'true');
    localStorage.setItem('session_id', sessionId);
    navigate('/student-dashboard');

  } catch (error) {
    console.error('Consent error:', error);
    setConsentError('We could not save your consent. Check your connection and try again.');
  } finally {
    setIsSubmitting(false);
  }
};

  const handleDecline = () => {
    // No consent = no session: fully log the user out (clears auth state,
    // the SW data cache, and any queued offline messages).
    clearAuth();
    navigate('/');
  };

  return (
    <div className="relative flex min-h-[100dvh] items-center justify-center overflow-hidden bg-slate-50" style={{ padding: 'calc(16px + env(safe-area-inset-top, 0px)) calc(16px + env(safe-area-inset-right, 0px)) calc(16px + env(safe-area-inset-bottom, 0px)) calc(16px + env(safe-area-inset-left, 0px))' }}>
      {/* Decorative Background Pattern */}
      <div className="absolute inset-0 opacity-10 pointer-events-none">
        <div className="absolute top-10 sm:top-20 left-10 sm:left-20 w-64 sm:w-96 h-64 sm:h-96 border-4 border-red-200 rotate-45 rounded-3xl"></div>
        <div className="absolute bottom-10 sm:bottom-20 right-10 sm:right-20 w-56 sm:w-80 h-56 sm:h-80 border-4 border-red-100 rotate-12 rounded-3xl"></div>
      </div>

      {/* Grid Pattern Overlay */}
      <div className="absolute inset-0 opacity-15 pointer-events-none">
        <svg className="w-full h-full" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#cbd5e1" strokeWidth="0.5"/>
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />
        </svg>
      </div>

      {/* Main Content */}
      <div className="relative z-10 flex min-h-0 w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-gray-200 bg-white p-4 shadow-xl sm:p-6 md:p-8" style={{ maxHeight: 'calc(100dvh - 32px - env(safe-area-inset-top, 0px) - env(safe-area-inset-bottom, 0px))' }}>
        {/* Top Back Navigation */}
        <div className="mb-4">
          <button
            type="button"
            onClick={() => navigate('/student-login')}
            className="inline-flex items-center gap-1.5 text-xs font-medium text-gray-500 hover:text-red-700 transition-colors focus:outline-none"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            <span>Back to Login</span>
          </button>
        </div>

        {/* Header */}
        <div className="mb-4 flex flex-col gap-2 sm:mb-5">
          <div className="min-w-0">
            <h1 className="whitespace-nowrap text-xl font-bold text-gray-900 sm:text-2xl md:text-3xl">Informed Consent</h1>
            <p className="mt-1 text-xs text-[var(--secondary)]">Please review the guidelines below before beginning your session</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-gray-100 text-gray-700 border border-gray-200">
              Guidance, Counseling and Career Services Office (GCCSO)
            </span>
            {localStorage.getItem('student_id') && (
              <span className="rounded-full border px-2.5 py-1 text-xs font-semibold" style={{ color: 'var(--brand)', borderColor: 'var(--brand)', background: '#f3f4f6' }}>
                {localStorage.getItem('student_id')}
              </span>
            )}
          </div>
        </div>

        {/* Consent Content - Scrollable */}
        <div className="relative mb-3 h-[34dvh] max-h-96 min-h-0 flex-none overflow-hidden sm:mb-4">
        <div
          role="region"
          aria-label="Consent terms"
          tabIndex={0}
          onScroll={(event) => {
            const { scrollTop, clientHeight, scrollHeight } = event.currentTarget;
            const atEnd = scrollTop + clientHeight >= scrollHeight - 8;
            setTermsAtEnd(atEnd);
            if (atEnd) setTermsRead(true);
          }}
          className="h-full min-h-0 overflow-y-auto rounded-lg border border-gray-200 bg-gray-50 p-4 no-scrollbar focus:outline-none focus:ring-2 focus:ring-[var(--brand)] sm:p-6"
        >
          <div className="space-y-4 text-sm text-gray-700">
            {/* Purpose */}
            <div>
              <h3 className="font-semibold text-gray-900 mb-2">Purpose:</h3>
              <p>
                GAIDA (Guidance System with Multimodal Anxiety Detection) uses voice, text, and behavioral analysis 
                to detect anxiety levels and provide guidance support. The system analyzes your interactions to 
                identify signs of anxiety and connect you with appropriate counseling resources.
              </p>
            </div>

            {/* Data Collection */}
            <div>
              <h3 className="font-semibold text-gray-900 mb-2">Data Collection:</h3>
              <p>
                We will collect your text messages, interaction patterns, and behavioral
                data during counseling sessions. All data is linked to your student ID for
                session tracking and counselor review. Data collected includes but is not
                limited to: text input, response times, interaction frequency, and detected
                emotional indicators. If you use voice input, your speech is analyzed for
                acoustic patterns (such as pitch and pacing) and transcribed to text in
                real time; the audio recording itself is not stored after this processing.
              </p>
            </div>

            {/* AI Processing */}
            <div>
              <h3 className="font-semibold text-gray-900 mb-2">AI Processing:</h3>
              <p>
                To analyze your messages and generate responses, GAIDA sends your text
                input to a third-party AI service provider that hosts the open-weight
                language model (Qwen) used to write replies. If you use voice input, the
                audio is sent to OpenAI's speech-to-text service to be transcribed, and if
                you tap Listen, the reply text is sent to a text-to-speech service to
                produce audio. This means your messages are processed on those providers'
                servers as part of how GAIDA works. This processing is used only to power
                the conversation and detection features described above, not for any
                other purpose.
              </p>
            </div>

            {/* Privacy */}
            <div>
              <h3 className="font-semibold text-gray-900 mb-2">Privacy:</h3>
              <p>
                Your data is stored using Supabase cloud infrastructure. At this stage of
                the system's development, access controls and encryption-at-rest for this
                data are still being implemented, so please avoid sharing information you
                would consider highly sensitive (such as account numbers or passwords).
                Your data will not be shared with third parties beyond the AI processing
                described above, without your explicit consent, except as required by law
                or in cases of imminent danger to yourself or others.
              </p>
            </div>

            {/* Limitations */}
            <div>
              <h3 className="font-semibold text-gray-900 mb-2">Limitations:</h3>
              <p>
                GAIDA is an assistive tool and does not replace professional mental health care. It is designed 
                to support early anxiety detection and facilitate counselor intervention, not provide medical 
                diagnosis or treatment. Language support is currently restricted to English, Tagalog, and Taglish; detection accuracy may decrease with other regional Philippine dialects. If you are experiencing a mental health emergency, please contact your 
                university counseling center immediately or call emergency services.
              </p>
            </div>

            {/* Session Recording */}
            <div>
              <h3 className="font-semibold text-gray-900 mb-2">Session Recording:</h3>
              <p>
                By accepting, you consent to text and interaction data being recorded during
                your session, and to voice input being analyzed and transcribed in real time
                if you choose to use it (the audio itself is not retained). This data may be
                reviewed by the GCCSO and authorized counselors for assessment
                and support purposes.
              </p>
            </div>

            {/* Counselor Alerts */}
            <div>
              <h3 className="font-semibold text-gray-900 mb-2">Counselor Alerts:</h3>
              <p>
                If GAIDA detects high anxiety levels or concerning patterns, an alert will be sent to counselors 
                who may reach out to provide support. This is for your safety and wellbeing. Response time may 
                vary based on counselor availability.
              </p>
            </div>

            {/* Rights */}
            <div>
              <h3 className="font-semibold text-gray-900 mb-2">Rights:</h3>
              <p>
                You may withdraw consent and end your session at any time without penalty. You have the right 
                to request access to your session data by contacting the GCCSO. You may request
                deletion of your data, subject to university record-keeping requirements. You can review what 
                data has been collected about you upon request by contacting the GCCSO at guidance@ue.edu.ph.
              </p>
            </div>

            {/* Data Retention */}
            <div>
              <h3 className="font-semibold text-gray-900 mb-2">Data Retention:</h3>
              <p>
                Your session data is intended to be retained for counseling continuity and
                quality improvement purposes. Automatic, scheduled deletion after a fixed
                period is not yet implemented in the system; until it is, data is retained
                until you request deletion (see "Rights" above) or the GCCSO
                removes it in line with university record-keeping policy.
              </p>
            </div>

            {/* Contact Information */}
            <div>
              <h3 className="font-semibold text-gray-900 mb-2">Questions or Concerns:</h3>
              <p>
                If you have any questions about this consent form or GAIDA's data practices, please contact the 
                Guidance, Counseling and Career Services Office (GCCSO) at guidance@ue.edu.ph or visit the GCCSO at 2219 C.M. Recto
                Avenue, Sampaloc, Manila.
              </p>
            </div>
          </div>
        </div>
        {!termsAtEnd && <div className="pointer-events-none absolute inset-x-px bottom-px h-14 rounded-b-lg bg-gradient-to-b from-transparent to-gray-50" aria-hidden="true" />}
        {!termsAtEnd && <p className="pointer-events-none absolute inset-x-0 bottom-2 text-center text-xs font-medium text-[var(--secondary)]" aria-hidden="true">Scroll to continue</p>}
        </div>

        {/* Consent Checkbox */}
        <div className="mb-3">
          <label className={`flex items-start gap-3 ${termsRead ? 'cursor-pointer' : 'cursor-not-allowed'}`}>
            <input
              type="checkbox"
              checked={isChecked}
              aria-disabled={!termsRead}
              onChange={(e) => { if (termsRead) setIsChecked(e.target.checked); }}
              className={`mt-1 h-5 w-5 rounded border-gray-300 text-[var(--brand)] focus:ring-[var(--brand)] ${termsRead ? 'cursor-pointer' : 'cursor-not-allowed'}`}
            />
            <span className="text-sm text-gray-700 select-none">
              I have read and understood the terms above. I consent to participate in this session 
              and agree to the collection, use, and storage of my data as described.
            </span>
          </label>
          {!termsRead && <p className="ml-8 mt-1 text-xs text-[var(--secondary)]">Scroll to the end of the terms to enable this box.</p>}
        </div>

        {/* Action Buttons */}
        {consentError && <p role="alert" className="mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{consentError}</p>}
        <div className="flex flex-col sm:flex-row gap-2 sm:gap-3">
          <button
            type="button"
            onClick={handleAccept}
            disabled={!isChecked || isSubmitting}
            className="flex-1 rounded-xl bg-[var(--brand)] px-4 py-2.5 text-sm font-semibold text-white shadow-md transition-all duration-200 hover:shadow-lg active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 sm:px-6 sm:py-3 sm:text-base"
          >
            {isSubmitting ? 'Saving consent…' : 'I Accept - Start Session'}
          </button>
          <button
            type="button"
            onClick={handleDecline}
            className="flex-1 py-2.5 sm:py-3 px-4 sm:px-6 rounded-xl font-semibold border-2 border-gray-200 text-gray-700 hover:bg-gray-50 hover:border-gray-300 transition-all duration-200 active:scale-[0.98] text-sm sm:text-base"
          >
            Decline & Logout
          </button>
        </div>

        {/* Footer Note */}
        <p className="mt-2 text-center text-xs text-[var(--secondary)]">
          By clicking "I Accept", you acknowledge that you have read and agree to the terms outlined above.
        </p>
      </div>
    </div>
  );
}
