import { useEffect, useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import VoiceInput from "../voice/VoiceInput";
import ReactMarkdown from 'react-markdown';

// ─────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────

import { BACKEND_URL as BACKEND } from '../../config';
import apiFetch, { clearSensitiveLocalData } from '../../api';
const POLL_INTERVAL = 3000;
const TYPING_DEBOUNCE = 2000;

// Calm, light palettes. Cool blues and soft greens lead; lavender and sand
// are softer secondary options. Keys stay stable so any saved preference
// still resolves to a theme.
const THEMES = {
  sky: {
    name: 'sky',
    label: 'Sky',
    preview: '#6E9BC2',
    bg: '#F7FAF9',
    sidebar: '#EEF4F6',
    card: '#FFFFFF',
    border: '#DCE7EA',
    accent: '#5E8FBD',
    accentDark: '#4A7699',
    textPrimary: '#2E3B44',
    textSecondary: '#5C6F78',
    textMuted: '#95A6AC',
    userBubble: '#DCEAF3',
    userText: '#28414F',
    botBubble: '#FFFFFF',
    botText: '#2E3B44',
  },
  sage: {
    name: 'sage',
    label: 'Sage',
    preview: '#7FAE93',
    bg: '#F7FAF6',
    sidebar: '#EEF5EF',
    card: '#FFFFFF',
    border: '#DCEBDF',
    accent: '#6BA187',
    accentDark: '#54896D',
    textPrimary: '#2C3B32',
    textSecondary: '#57695D',
    textMuted: '#93A899',
    userBubble: '#DCF0E3',
    userText: '#25402F',
    botBubble: '#FFFFFF',
    botText: '#2C3B32',
  },
  lavender: {
    name: 'lavender',
    label: 'Lavender',
    preview: '#9490C9',
    bg: '#F9F8FB',
    sidebar: '#F0EEF7',
    card: '#FFFFFF',
    border: '#E3E0F1',
    accent: '#8480BD',
    accentDark: '#6A66A0',
    textPrimary: '#33314A',
    textSecondary: '#615E7D',
    textMuted: '#9E9BB8',
    userBubble: '#E5E3F5',
    userText: '#332F52',
    botBubble: '#FFFFFF',
    botText: '#33314A',
  },
  sand: {
    name: 'sand',
    label: 'Sand',
    preview: '#C9A876',
    bg: '#FBF8F1',
    sidebar: '#F5EFE2',
    card: '#FFFFFF',
    border: '#EBE0CB',
    accent: '#BC9A63',
    accentDark: '#9C7E4E',
    textPrimary: '#40372A',
    textSecondary: '#6C6151',
    textMuted: '#A69985',
    userBubble: '#F1E5CD',
    userText: '#40372A',
    botBubble: '#FFFFFF',
    botText: '#40372A',
  },
};

// Calm severity treatment. Nothing here uses alarm red; red is reserved for
// the emergency / end-session exit only.
const SEVERITY_CONFIG = {
  Crisis:   { fill: '#C97B57', text: '#9C5A3C', chip: '#F5E4DA', width: '100%' },
  High:     { fill: '#D4A24C', text: '#9C7A34', chip: '#F6ECD6', width: '80%'  },
  Moderate: { fill: '#5FA6A6', text: '#3F7676', chip: '#DFEFEF', width: '50%'  },
  Low:      { fill: '#7FB088', text: '#4F7D58', chip: '#E2F0E4', width: '25%'  },
  Normal:   { fill: '#A9B3B8', text: '#6E7A80', chip: '#E9EDEE', width: '6%'   },
};

const VALID_SEVERITIES = ['Crisis', 'High', 'Moderate', 'Low', 'Normal'];

function normalizeSeverity(val) {
  if (!val || typeof val !== 'string') return null;
  const match = VALID_SEVERITIES.find(s => s.toLowerCase() === val.trim().toLowerCase());
  return match || null;
}

const QUICK_START_PROMPTS = [
  { icon: 'school',      text: "I'm stressed about my exams" },
  { icon: 'message-2',   text: "I just want to talk to someone" },
  { icon: 'cloud-rain',  text: "Things have been hard lately" },
];

const CRISIS_HOTLINES = [
  {
    name: 'National Center for Mental Health (NCMH) Crisis Hotline',
    number: '1553',
    tel: '1553',
    desc: 'Toll-free nationwide, 24/7 mental health crisis support',
    badge: '24/7 Free',
  },
  {
    name: 'HOPELINE Philippines',
    number: '(02) 8804-4673 / 0917-558-4673',
    tel: '09175584673',
    desc: 'Toll-free for Globe/TM subscribers, 24/7 suicide prevention',
    badge: '24/7',
  },
  {
    name: 'In Touch Community Services: Crisis Line',
    number: '(02) 8893-7603 / 0917-800-1123',
    tel: '09178001123',
    desc: 'Free, confidential crisis counseling & emotional support',
    badge: '24/7',
  },
  {
    name: 'Philippine National Emergency Hotline',
    number: '911',
    tel: '911',
    desc: 'For immediate life-threatening physical danger and emergencies',
    badge: 'Emergency',
  },
  {
    name: 'UE Guidance and Counseling Office (Manila)',
    number: '(02) 8735-5471 loc. 462 / 366',
    tel: '0287355471',
    desc: 'University counselors on campus (Mon-Fri 8:00 AM - 5:00 PM)',
    badge: 'UE Campus',
  },
  {
    name: 'UE Guidance and Counseling Office (Caloocan)',
    number: '(02) 8367-4572 loc. 175',
    tel: '0283674572',
    desc: 'Caloocan campus guidance office (Mon-Fri 8:00 AM - 5:00 PM)',
    badge: 'UE Campus',
  },
];

// ─────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────

const formatTime = (seconds) => {
  const m = Math.floor(seconds / 60).toString().padStart(2, '0');
  const s = (seconds % 60).toString().padStart(2, '0');
  return `${m}:${s}`;
};

const formatMsgTime = (date) => {
  if (!date) return '';
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

// ─────────────────────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────────────────────

// Shared keyframes for the agent's idle "breathing" animation and other
// gentle transitions. Injected once via a plain <style> tag so no build
// config changes are needed.
function GaidaStyleTag() {
  return (
    <style>{`
      @keyframes gaida-breathe {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.06); }
      }
      @keyframes gaida-blink {
        0%, 92%, 100% { opacity: 1; }
        96% { opacity: 0.35; }
      }
      .gaida-breathing {
        animation: gaida-breathe 4.2s ease-in-out infinite;
      }
      .gaida-eyes {
        animation: gaida-blink 5.5s ease-in-out infinite;
      }
      @media (prefers-reduced-motion: reduce) {
        .gaida-breathing, .gaida-eyes { animation: none !important; }
      }
    `}</style>
  );
}

function TypingBubble({ color }) {
  return (
    <div className="flex gap-1 items-center h-4">
      {[0, 150, 300].map((delay) => (
        <div
          key={delay}
          className="w-1.5 h-1.5 rounded-full animate-bounce"
          style={{ background: color, animationDelay: `${delay}ms` }}
        />
      ))}
    </div>
  );
}

// Soft, non-human agent mark: a rounded blob with two simple dot "eyes".
// Used for the bot avatar everywhere in the chat. Counselor keeps a plain
// initial mark since a person is on the other end.
function GaidaMark({ size = 32, accent, breathing = false }) {
  return (
    <div
      className={breathing ? 'gaida-breathing' : ''}
      style={{ width: size, height: size, display: 'inline-flex' }}
    >
      <svg width={size} height={size} viewBox="0 0 40 40" fill="none">
        <path
          d="M20 4c8.8 0 15 6.3 15 14.5S30.2 34 21.3 34c-2 0-3.5.7-5.2 1.9-1 .7-2.3-.1-2.1-1.3l.5-3.1C9.2 29 5 24.2 5 18.5 5 10.3 11.2 4 20 4z"
          fill={accent}
          opacity="0.16"
        />
        <path
          d="M20 7c7.2 0 12.3 5.1 12.3 11.7 0 6.6-5.1 11.6-12.6 11.6-1.6 0-2.9.55-4.2 1.5-.8.55-1.9-.1-1.7-1.05l.4-2.5C9.6 26.4 6.3 22.5 6.3 18.7 6.3 12.1 12.8 7 20 7z"
          fill={accent}
        />
        <circle className="gaida-eyes" cx="15.6" cy="18.5" r="1.8" fill="white" />
        <circle className="gaida-eyes" cx="24.4" cy="18.5" r="1.8" fill="white" />
        <path d="M16.5 23c1.8 1.4 5.2 1.4 7 0" stroke="white" strokeWidth="1.6" strokeLinecap="round" fill="none" />
      </svg>
    </div>
  );
}

function Avatar({ role, accent, breathing = false }) {
  if (role === 'counselor') {
    return (
      <div
        className="w-7 h-7 sm:w-8 sm:h-8 rounded-full flex items-center justify-center flex-shrink-0 mb-0.5"
        style={{ background: '#E7EEF5', border: '1px solid #C9DAE8' }}
      >
        <span className="text-xs sm:text-sm font-bold" style={{ color: '#4A7699' }}>C</span>
      </div>
    );
  }
  return (
    <div className="flex-shrink-0 mb-0.5">
      <GaidaMark size={30} accent={accent} breathing={breathing} />
    </div>
  );
}

function MessageBubble({ message, theme, onFeedback, feedback, onPlayTTS, isPlayingTTS }) {
  const { role, text, isVoice, acoustic, timestamp } = message;

  const bubbleStyle =
    role === 'user'
      ? { background: theme.userBubble, color: theme.userText, borderRadius: '20px 20px 4px 20px' }
      : role === 'counselor'
      ? { background: '#F1F6FA', color: '#2E4A5E', border: '1px solid #DCE8F1', borderRadius: '4px 20px 20px 20px' }
      : { background: theme.botBubble, color: theme.botText, border: `1px solid ${theme.border}`, borderRadius: '4px 20px 20px 20px' };

  return (
    <div className={`flex flex-col gap-1 max-w-[85%] sm:max-w-[72%] lg:max-w-[65%] ${role === 'user' ? 'items-end' : 'items-start'}`}>
      <div className="px-4 py-3 sm:px-5 sm:py-3.5 text-[15px] sm:text-sm leading-relaxed shadow-sm" style={{ ...bubbleStyle, lineHeight: 1.65 }}>
        {isVoice && (
          <div className="flex items-center gap-1.5 mb-1.5" style={{ opacity: 0.65 }}>
            <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 1a4 4 0 014 4v6a4 4 0 01-8 0V5a4 4 0 014-4zm-1 17.93V21H9v2h6v-2h-2v-2.07A8.001 8.001 0 0020 11h-2a6 6 0 01-12 0H4a8.001 8.001 0 007 7.93z" />
            </svg>
            <span className="text-xs font-medium">Voice</span>
          </div>
        )}

        {role === 'user' ? (
          <span>{text}</span>
        ) : (
          <ReactMarkdown
            components={{
              p:          ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
              strong:     ({ children }) => <strong className="font-bold">{children}</strong>,
              em:         ({ children }) => <em className="italic">{children}</em>,
              ul:         ({ children }) => <ul className="list-disc list-inside mt-2 space-y-1">{children}</ul>,
              ol:         ({ children }) => <ol className="list-decimal list-inside mt-2 space-y-1">{children}</ol>,
              li:         ({ children }) => <li className="text-[15px] sm:text-sm">{children}</li>,
              blockquote: ({ children }) => <blockquote className="border-l-2 pl-3 my-2 italic opacity-85" style={{ borderColor: theme.accent }}>{children}</blockquote>,
              code:       ({ children }) => <code className="px-1.5 py-0.5 rounded text-xs font-mono" style={{ background: theme.sidebar }}>{children}</code>,
              h1: () => null,
              h2: () => null,
              h3: () => null,
            }}
          >
            {text}
          </ReactMarkdown>
        )}
      </div>

      <div className="flex items-center gap-2 px-1">
        {timestamp && (
          <span className="text-[11px]" style={{ color: theme.textMuted }}>
            {formatMsgTime(timestamp)}
          </span>
        )}

        {role === 'bot' && onPlayTTS && (
          <button
            onClick={onPlayTTS}
            className="text-[11px] px-2 py-0.5 rounded-full border transition-colors duration-200 touch-manipulation flex items-center gap-1"
            style={{
              background: isPlayingTTS ? theme.accentDark : 'transparent',
              color: isPlayingTTS ? '#FFFFFF' : theme.textSecondary,
              border: `1px solid ${theme.border}`,
            }}
            title={isPlayingTTS ? "Stop voice audio" : "Listen to GAIDA's reply"}
            aria-label={isPlayingTTS ? "Stop reading reply aloud" : "Read reply aloud"}
          >
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              {isPlayingTTS ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
              )}
            </svg>
            <span className="text-[10px] hidden sm:inline">{isPlayingTTS ? "Playing" : "Listen"}</span>
          </button>
        )}
      </div>

      {role === 'bot' && acoustic && (
        <div className="flex flex-wrap items-center gap-2 px-1 mt-0.5">
          <span className="text-[11px]" style={{ color: theme.textMuted }}>Voice detected:</span>
          <span
            className="text-[11px] px-2.5 py-1 rounded-full font-medium"
            style={{
              color:
                acoustic.emotion === 'anxious'   ? '#9C7A34' :
                acoustic.emotion === 'sad'       ? '#4A7699' :
                acoustic.emotion === 'angry'     ? '#9C5A3C' :
                acoustic.emotion === 'stressed'  ? '#B0793F' :
                acoustic.emotion === 'calm'      ? '#4F7D58' :
                acoustic.emotion === 'withdrawn' ? '#6A66A0' :
                                                    theme.textSecondary,
              background:
                acoustic.emotion === 'anxious'   ? '#F6ECD6' :
                acoustic.emotion === 'sad'       ? '#DCEAF3' :
                acoustic.emotion === 'angry'     ? '#F5E4DA' :
                acoustic.emotion === 'stressed'  ? '#F3E6D4' :
                acoustic.emotion === 'calm'      ? '#E2F0E4' :
                acoustic.emotion === 'withdrawn' ? '#E5E3F5' :
                                                    theme.sidebar,
            }}
          >
            {acoustic.emotion}
          </span>
          <span className="text-[11px]" style={{ color: theme.textMuted }}>{acoustic.severity}</span>
        </div>
      )}

      {role === 'bot' && onFeedback && (
        <div className="flex items-center gap-2 px-1 pt-1">
          {[
            { k: 'up', label: 'Helpful' },
            { k: 'down', label: 'Not helpful' },
          ].map((opt) => (
            <button
              key={opt.k}
              onClick={() => onFeedback(opt.k)}
              disabled={!!feedback}
              className="text-[12px] px-3 py-1.5 rounded-full border transition-colors duration-200 disabled:opacity-45 touch-manipulation"
              style={{
                background: feedback === opt.k ? theme.accentDark : 'transparent',
                color: feedback === opt.k ? '#FFFFFF' : theme.textSecondary,
                border: `1px solid ${theme.border}`,
              }}
            >
              {feedback === opt.k ? '\u2713 ' : ''}{opt.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Main Component
// ─────────────────────────────────────────────────────────────

export default function StudentDashboard() {
  const navigate = useNavigate();

  // ── State ────────────────────────────────────────────────────
  const [messages,          setMessages]          = useState([]);
  const [input,             setInput]             = useState('');
  const [sending,           setSending]           = useState(false);
  const [severity,          setSeverity]          = useState('Normal');
  const [sessionTime,       setSessionTime]       = useState(0);
  const [sidebarOpen,       setSidebarOpen]       = useState(false);
  const [voiceStatus,       setVoiceStatus]       = useState('');
  const [counselorTyping,   setCounselorTyping]   = useState(false);
  const [counselorActive,   setCounselorActive]   = useState(false);
  const [ventMode,          setVentMode]          = useState(false);
  const [showSettings,      setShowSettings]      = useState(false);
  const [requestingCounselor, setRequestingCounselor] = useState(false);
  const [counselorRequested,  setCounselorRequested]  = useState(false);
  const [streamingStarted,    setStreamingStarted]    = useState(false);
  const [showCrisisHotlines,  setShowCrisisHotlines]  = useState(false);
  const [playingTTSIndex,     setPlayingTTSIndex]     = useState(null);
  const [loadingTranscript,   setLoadingTranscript]   = useState(false);
  const [transcriptError,     setTranscriptError]     = useState(false);

  const crisisTriggerRef = useRef(null);
  const crisisModalRef = useRef(null);
  const crisisCloseBtnRef = useRef(null);

  const openCrisisHotlines = useCallback((e) => {
    crisisTriggerRef.current = e?.currentTarget || document.activeElement;
    setShowCrisisHotlines(true);
  }, []);

  const closeCrisisHotlines = useCallback(() => {
    setShowCrisisHotlines(false);
    requestAnimationFrame(() => {
      if (crisisTriggerRef.current && typeof crisisTriggerRef.current.focus === 'function') {
        crisisTriggerRef.current.focus();
      }
    });
  }, []);

  const loadTranscript = useCallback(async (sid) => {
    if (!sid) return false;
    setLoadingTranscript(true);
    setTranscriptError(false);
    try {
      const res = await apiFetch(`${BACKEND}/api/counselor/chat/${sid}`);
      if (!res.ok) {
        throw new Error(`Transcript fetch failed with status ${res.status}`);
      }
      const data = await res.json();
      if (data.messages && data.messages.length > 0) {
        const rehydrated = data.messages.map(m => ({
          role: m.sender === 'user' ? 'user' : m.sender === 'counselor' ? 'counselor' : m.sender === 'system' ? 'system' : 'bot',
          text: m.text,
          timestamp: m.timestamp ? new Date(m.timestamp) : new Date(),
        }));
        setMessages(rehydrated);
        lastCounselorCount.current = data.messages.filter(m => m.sender === 'counselor').length;
        const normSev = normalizeSeverity(data.severity);
        if (normSev) setSeverity(normSev);
        if (data.counselor_active) {
          setCounselorActive(true);
          wasCounselorActive.current = true;
        }
        return true;
      }
      return false;
    } catch (e) {
      console.error('Failed to restore chat transcript:', e);
      setTranscriptError(true);
      return false;
    } finally {
      setLoadingTranscript(false);
    }
  }, []);

  // Mirror of localStorage['session_id'] as React state so the realtime
  // WebSocket (re)connects the moment a session is created/restored.
  const [sessionId,          setSessionId]          = useState(() => localStorage.getItem('session_id'));

  // ── Rating state ─────────────────────────────────────────────
  const [showRating,        setShowRating]        = useState(false);
  const [ratingSubmitted,   setRatingSubmitted]   = useState(false);
  const [hoveredRating,     setHoveredRating]     = useState(null);

  // Per-message helpfulness feedback: message index -> 'up' | 'down'
  const [messageRatings, setMessageRatings] = useState({});

  const [theme, setTheme] = useState(
    () => THEMES[localStorage.getItem('gaida_theme')] || THEMES.sky
  );

  // ── Refs ─────────────────────────────────────────────────────
  const containerRef       = useRef(null);
  const timerRef           = useRef(null);
  const inputRef           = useRef(null);
  const lastCounselorCount = useRef(0);
  const typingTimeout      = useRef(null);
  const typingActiveRef    = useRef(false);
  const wasCounselorActive = useRef(false);
  const audioRef           = useRef(null);
  const audioUrlRef        = useRef(null);

  // ── Counselor-chat helpers ───────────────────────────────────
  // Shared by BOTH the 3s poll and the realtime WebSocket so the two paths
  // agree on state (no duplicate "joined"/"resumed" system bubbles) no matter
  // which one delivers an update first.
  const appendCounselorMessages = (counselorMsgs) => {
    if (!counselorMsgs.length) return;
    const firstUnseen = lastCounselorCount.current;
    if (counselorMsgs.length <= firstUnseen) return;
    setMessages(prev => [
      ...prev,
      ...(firstUnseen === 0 ? [{ role: 'system', text: 'A counselor has joined your session.' }] : []),
      ...counselorMsgs.slice(firstUnseen).map(m => ({
        role: 'counselor', text: m.text, timestamp: new Date(),
      })),
    ]);
    lastCounselorCount.current = counselorMsgs.length;
  };

  const appendCounselorMessage = (msg) => {
    const idx = lastCounselorCount.current;
    setMessages(prev => [
      ...prev,
      ...(idx === 0 ? [{ role: 'system', text: 'A counselor has joined your session.' }] : []),
      { role: 'counselor', text: msg.text, timestamp: new Date() },
    ]);
    lastCounselorCount.current = idx + 1;
  };

  const applyCounselorActive = (active) => {
    if (wasCounselorActive.current && !active) {
      setMessages(prev => [...prev, { role: 'system', text: 'GAIDA has resumed the conversation.' }]);
    }
    wasCounselorActive.current = active;
    setCounselorActive(active);
  };

  const validSeverity = normalizeSeverity(severity) || 'Normal';
  const severityConfig = SEVERITY_CONFIG[validSeverity];

  // ── Wellbeing rating options ──────────────────────────────────
  const WELLBEING_OPTIONS = [
    { value: 1, emoji: '😔', label: 'Much worse' },
    { value: 2, emoji: '😐', label: 'About the same' },
    { value: 3, emoji: '🙂', label: 'A little better' },
    { value: 4, emoji: '😊', label: 'Much better' },
  ];

  // ── Auth + session rehydration on mount ────────────────────────────
  useEffect(() => {
    const token   = localStorage.getItem('session_token');
    const studentId = localStorage.getItem('student_id');
    const sid = localStorage.getItem('session_id');
    const consent = localStorage.getItem('consent_given');
    if (!token)   { navigate('/student-login'); return; }
    if (!consent) { navigate('/consent');       return; }

    setSidebarOpen(window.innerWidth >= 1024);
    timerRef.current = setInterval(() => setSessionTime(t => t + 1), 1000);

    const initSession = async () => {
      let hasMessages = false;
      if (sid) {
        hasMessages = await loadTranscript(sid);
      }

      // Check-in is only offered on clean start when there are no messages in the current session
      if (!hasMessages && studentId) {
        try {
          const r = await apiFetch(`${BACKEND}/api/counselor/student/checkin/${studentId}`);
          if (r.ok) {
            const data = await r.json();
            if (data.needs_checkin) {
              setMessages([{
                role: 'bot',
                text: data.peak_severity === 'Crisis'
                  ? "Kumusta ka na? Last time we talked, you were going through something really heavy. How have you been feeling since then?"
                  : "Hey, kumusta? It's been a few days since we last talked - just checking in. How are you feeling today?",
                timestamp: new Date(),
                isCheckin: true,
              }]);
            }
          }
        } catch { /* ignore check-in errors */ }
      }
    };

    initSession();

    return () => clearInterval(timerRef.current);
  }, [navigate, loadTranscript]);

  useEffect(() => {
    const notifyLeave = () => {
      const sessionId = localStorage.getItem('session_id');
      if (!sessionId) return;
      try {
        apiFetch(`${BACKEND}/api/session/${sessionId}/end`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          keepalive: true,
        }).catch(() => {});
      } catch { /* pagehide flush failed — nothing to recover */ }
    };
    window.addEventListener('pagehide', notifyLeave);
    return () => window.removeEventListener('pagehide', notifyLeave);
  }, []);

  useEffect(() => {
    containerRef.current?.scrollTo({ top: containerRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, voiceStatus, counselorTyping]);

  useEffect(() => {
    const poll = async () => {
      const sid = localStorage.getItem('session_id');
      if (!sid) return;

      try {
        const res  = await apiFetch(`${BACKEND}/api/counselor/chat/${sid}`);
        if (!res.ok) return;
        const data = await res.json();
        if (!data.messages) return;

        setCounselorTyping(data.counselor_typing || false);

        // Keep "counselor is with you" honest even if the server's meta flag
        // lags behind: any counselor message implies a live takeover.
        const anyCounselorMsg = data.messages.some(m => m.sender === 'counselor');
        applyCounselorActive(!!(data.counselor_active || anyCounselorMsg));

        appendCounselorMessages(data.messages.filter(m => m.sender === 'counselor'));
      } catch (e) {
        console.error('Poll chat error:', e);
      }
    };

    const interval = setInterval(poll, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, []);

  // ── Realtime session updates ─────────────────────────────────
  // The backend pushes new interactions / typing / takeover state over a
  // per-session WebSocket (GET /api/session/ws/{id}?token=...). The 3s poll
  // above stays as a fallback for missed events (reconnect gaps, offline
  // tabs, service-worker cached responses).
  useEffect(() => {
    if (!sessionId) return undefined;
    const token = localStorage.getItem('session_token');
    if (!token) return undefined;

    let ws = null;
    let closed = false;
    let retryDelay = 1000;
    let retryTimer = null;

    const handleRealtimeMessage = (msg) => {
      if (!msg || typeof msg !== 'object') return;
      switch (msg.type) {
        case 'interaction':
          if (msg.sender === 'counselor') {
            applyCounselorActive(true);
            appendCounselorMessage(msg);
          }
          break;
        case 'typing':
          if (msg.sender === 'counselor') setCounselorTyping(!!msg.is_typing);
          break;
        case 'counselor_active':
          applyCounselorActive(!!msg.active);
          break;
        default:
          break;
      }
    };

    const connect = () => {
      const wsUrl = `${BACKEND.replace(/^http/, 'ws')}/api/session/ws/${sessionId}?token=${encodeURIComponent(token)}`;
      try {
        ws = new WebSocket(wsUrl);
      } catch {
        scheduleRetry();
        return;
      }

      ws.onopen = () => { retryDelay = 1000; };

      ws.onmessage = (ev) => {
        let msg;
        try { msg = JSON.parse(ev.data); } catch { return; }
        handleRealtimeMessage(msg);
      };

      ws.onclose = () => {
        ws = null;
        if (!closed) scheduleRetry();
      };

      ws.onerror = () => {
        try { if (ws) ws.close(); } catch { /* onclose schedules the retry */ }
      };
    };

    const scheduleRetry = () => {
      clearTimeout(retryTimer);
      retryTimer = setTimeout(() => {
        retryDelay = Math.min(retryDelay * 2, 15000);
        connect();
      }, retryDelay);
    };

    connect();

    return () => {
      closed = true;
      clearTimeout(retryTimer);
      if (ws) {
        try { ws.onclose = null; ws.close(); } catch { /* socket already gone */ }
        ws = null;
      }
    };
  }, [sessionId]);

  const fireTyping = useCallback((isTyping) => {
    const sessionId = localStorage.getItem('session_id');
    if (!sessionId) return;
    apiFetch(`${BACKEND}/api/counselor/typing/${sessionId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sender: 'student', is_typing: isTyping }),
    }).catch((e) => { console.error('Typing indicator error:', e); });
  }, []);

  const handleInputChange = (e) => {
    setInput(e.target.value);
    // Fire the "typing" indicator once per burst instead of on every
    // keystroke (avoids spamming the backend for each character).
    if (!typingActiveRef.current) {
      typingActiveRef.current = true;
      fireTyping(true);
    }
    clearTimeout(typingTimeout.current);
    typingTimeout.current = setTimeout(() => {
      typingActiveRef.current = false;
      fireTyping(false);
    }, TYPING_DEBOUNCE);
  };

  const sendMessage = async (textOverride) => {
    const text = (typeof textOverride === 'string' ? textOverride : input).trim();
    if (!text || sending) return;

    clearTimeout(typingTimeout.current);
    fireTyping(false);
    typingActiveRef.current = false;

    setMessages(prev => [...prev, { role: 'user', text, timestamp: new Date() }]);
    setInput('');
    setSending(true);
    setStreamingStarted(false);
    if (window.innerWidth < 1024) setSidebarOpen(false);

    const sessionId = localStorage.getItem('session_id');
    const token     = localStorage.getItem('session_token');
    let botMsg = null;

    try {
      const res = await apiFetch(`${BACKEND}/virtual-agent/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token && { Authorization: `Bearer ${token}` }),
        },
        body: JSON.stringify({
          message:    text,
          session_id: sessionId,
          user_id: localStorage.getItem('student_id'),
          intent:    ventMode ? 'venting' : 'unknown',
          vent_mode:  ventMode,
        }),
      });

      if (!res.ok || !res.body) {
        const err = await res.text().catch(() => String(res.status));
        setMessages(prev => [...prev, { role: 'bot', text: `Error: ${err || res.status}`, timestamp: new Date() }]);
        return;
      }

      const reader  = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      const appendOrUpdateBot = (next) => {
        if (!botMsg) {
          botMsg = next;
          setMessages(prev => [...prev, botMsg]);
        } else {
          botMsg = next;
          setMessages(prev => [...prev.slice(0, -1), botMsg]);
        }
      };

      const processLine = (line) => {
        const trimmed = line.trim();
        if (!trimmed) return;

        let event;
        try { event = JSON.parse(trimmed); } catch { return; }

        if (event.type === 'delta') {
          setStreamingStarted(true);
          const prevText = botMsg ? botMsg.text : '';
          appendOrUpdateBot({
            role: 'bot',
            text: prevText + event.text,
            timestamp: botMsg ? botMsg.timestamp : new Date(),
          });
        } else if (event.type === 'done') {
          const result = event.result || {};
          if (result.session_id) {
            localStorage.setItem('session_id', result.session_id);
            setSessionId(result.session_id);
          }
          const normSev = normalizeSeverity(result.severity);
          if (normSev) setSeverity(normSev);
          if (result.counselor_active) setCounselorActive(true);

          if (!result.counselor_active && (!botMsg || !botMsg.text) && result.response) {
            appendOrUpdateBot({ role: 'bot', text: result.response, timestamp: new Date() });
          }
        }
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split('\n');
        buffer = lines.pop();
        lines.forEach(processLine);
      }

      if (buffer.trim()) processLine(buffer);
    } catch (err) {
      if (botMsg && botMsg.text) {
        setMessages(prev => [...prev, {
          role: 'system',
          text: `Connection interrupted: ${err.message || 'Stream closed'}.`,
          timestamp: new Date(),
        }]);
      } else {
        setMessages(prev => [...prev, {
          role: 'bot', text: `Connection error: ${err.message}`, timestamp: new Date(),
        }]);
      }
    } finally {
      setSending(false);
      // Only auto-focus input on non-touch devices to avoid keyboard pop-ups
      if (window.matchMedia("(pointer: fine)").matches) {
        inputRef.current?.focus();
      }
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  };

  const handleRequestCounselor = async () => {
    if (requestingCounselor) return;

    // If the student hasn't sent a message yet there is no session to attach
    // the counselor request to. Auto-create one first so the button always
    // visibly does something instead of silently doing nothing.
    let sessionId = localStorage.getItem('session_id');
    if (!sessionId) {
      try {
        const res = await apiFetch(`${BACKEND}/api/session/start`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_id: localStorage.getItem('student_id') }),
        });
        if (!res.ok) throw new Error('Could not start a session.');
        const data = await res.json();
        sessionId = data.session_id;
        localStorage.setItem('session_id', sessionId);
        setSessionId(sessionId);
      } catch (e) {
        console.error('Start session error:', e);
        setMessages(prev => [...prev, {
          role: 'system',
          text: "Couldn't reach the counselor right now. Try sending a message first.",
        }]);
        return;
      }
    }

    setRequestingCounselor(true);
    try {
      const res = await apiFetch(`${BACKEND}/api/counselor/request-counselor`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId }),
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok && data.ok) {
        setCounselorRequested(true);
        setMessages(prev => [...prev, {
          role: 'system',
          text: 'A counselor has been notified and will join shortly.',
        }]);
      } else {
        const errMsg = data.error || data.detail || 'Could not notify counselor at this time.';
        setMessages(prev => [...prev, {
          role: 'system',
          text: `Counselor request failed: ${errMsg}`,
        }]);
      }
    } catch (e) {
      console.error('Request counselor error:', e);
      setMessages(prev => [...prev, {
        role: 'system',
        text: 'Network error requesting counselor. Please check your connection or try again.',
      }]);
    } finally {
      setRequestingCounselor(false);
    }
  };

  const stopTTS = useCallback(() => {
    if (audioRef.current) {
      try {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
      } catch { /* ignore pause error */ }
      audioRef.current = null;
    }
    if (audioUrlRef.current) {
      try {
        URL.revokeObjectURL(audioUrlRef.current);
      } catch { /* ignore revoke error */ }
      audioUrlRef.current = null;
    }
    setPlayingTTSIndex(null);
  }, []);

  const handlePlayTTS = async (index, text) => {
    if (playingTTSIndex === index) {
      stopTTS();
      return;
    }
    stopTTS();
    setPlayingTTSIndex(index);

    try {
      const plainText = text
        .replace(/[#*`_~>[\]()]/g, '')
        .replace(/\n+/g, ' ')
        .trim();

      if (!plainText) {
        setPlayingTTSIndex(null);
        return;
      }

      const res = await apiFetch(`${BACKEND}/api/voice/tts?text=${encodeURIComponent(plainText)}`);
      if (!res.ok) {
        throw new Error('TTS service unavailable');
      }

      const blob = await res.blob();
      const audioUrl = URL.createObjectURL(blob);
      audioUrlRef.current = audioUrl;

      const audio = new Audio(audioUrl);
      audioRef.current = audio;

      audio.onended = () => {
        stopTTS();
      };
      audio.onerror = () => {
        console.error('Audio playback error');
        stopTTS();
      };

      await audio.play();
    } catch (err) {
      console.error('TTS playback error:', err);
      stopTTS();
    }
  };

  useEffect(() => {
    return () => {
      stopTTS();
    };
  }, [stopTTS]);

  useEffect(() => {
    if (!showCrisisHotlines) return;

    const focusTimer = requestAnimationFrame(() => {
      if (crisisCloseBtnRef.current) {
        crisisCloseBtnRef.current.focus();
      } else if (crisisModalRef.current) {
        crisisModalRef.current.focus();
      }
    });

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        e.stopPropagation();
        closeCrisisHotlines();
        return;
      }
      if (e.key === 'Tab') {
        const modal = crisisModalRef.current;
        if (!modal) return;
        const focusable = modal.querySelectorAll(
          'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
        );
        if (focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];

        if (e.shiftKey) {
          if (document.activeElement === first || document.activeElement === modal) {
            e.preventDefault();
            last.focus();
          }
        } else {
          if (document.activeElement === last) {
            e.preventDefault();
            first.focus();
          }
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      cancelAnimationFrame(focusTimer);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [showCrisisHotlines, closeCrisisHotlines]);

  const rateMessage = useCallback((index, value) => {
    if (messageRatings[index]) return;
    const m = messages[index];
    const sessionId = localStorage.getItem('session_id');
    setMessageRatings(prev => ({ ...prev, [index]: value }));
    apiFetch(`${BACKEND}/api/session/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        message_index: index,
        message_text: m?.text || '',
        rating: value === 'up' ? 'helpful' : 'not_helpful',
      }),
    }).catch(() => {});
  }, [messageRatings, messages]);

  const endSession = () => {
    if (messages.length > 0) {
      setShowRating(true);
    } else {
      confirmEndSession();
    }
  };

  const confirmEndSession = async () => {
    const sessionId = localStorage.getItem('session_id');
    if (sessionId) {
      try {
        await apiFetch(`${BACKEND}/api/session/${sessionId}/end`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        });
      } catch (e) {
        console.error('End session error:', e);
      }
    }
    const wasResearchSession = localStorage.getItem('is_research_session') === 'true';

    const keysToClear = wasResearchSession
      ? ['student_id', 'consent_given', 'is_research_session']
      : ['session_token', 'student_id', 'consent_given', 'session_id', 'is_research_session'];
    keysToClear.forEach(k => localStorage.removeItem(k));
    clearSensitiveLocalData(); // purge cached chat data & offline queue

    setSessionId(null); // closes the realtime WebSocket for this session

    navigate(wasResearchSession ? '/research-sus' : '/student-login');
  };

  const handleWellbeingRating = async (value) => {
    setRatingSubmitted(true);
    const sessionId = localStorage.getItem('session_id');
    if (sessionId) {
      try {
        await apiFetch(`${BACKEND}/api/counselor/session/rate`,
          {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            session_id: sessionId,
            wellbeing_rating: value,
            severity_at_end: severity,
          }),
        });
      } catch (e) {
        console.error('Wellbeing rating error:', e);
      }
    }
    setTimeout(() => confirmEndSession(), 1800);
  };

  const switchTheme = (key) => {
    setTheme(THEMES[key]);
    localStorage.setItem('gaida_theme', key);
  };

  return (
    <div
      className="min-h-dvh max-h-dvh flex overflow-hidden font-sans"
      style={{ background: theme.bg, color: theme.textPrimary }}
    >
      <GaidaStyleTag />

      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 lg:hidden touch-none transition-opacity duration-300"
          style={{ background: 'rgba(40,50,55,0.35)' }}
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* ── Sidebar ──────────────────────────────────────────── */}
      <aside
        className={`
          fixed lg:relative z-50 lg:z-auto top-0 left-0
          transition-transform duration-300 ease-in-out
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
          w-[82vw] max-w-xs lg:w-72 flex flex-col flex-shrink-0 h-dvh
        `}
        style={{ background: theme.sidebar, borderRight: `1px solid ${theme.border}` }}
      >
        {/* Logo */}
        <div className="p-5 flex items-center justify-between flex-shrink-0" style={{ borderBottom: `1px solid ${theme.border}` }}>
          <div className="flex items-center gap-3">
            <GaidaMark size={38} accent={theme.accent} breathing />
            <div>
              <p className="font-bold tracking-wide text-sm" style={{ color: theme.textPrimary }}>GAIDA</p>
              <p className="text-xs" style={{ color: theme.textMuted }}>Guidance System</p>
            </div>
          </div>
 
        </div>

        {/* Scrollable middle area: on short/mobile viewports this region scrolls
            so the End Session button below stays pinned to the bottom. */}
        <div className="flex-1 overflow-y-auto min-h-0 overscroll-contain no-scrollbar">
        {/* Session stats */}
        <div className="p-5" style={{ borderBottom: `1px solid ${theme.border}` }}>
          <p className="text-xs font-medium tracking-wide mb-3" style={{ color: theme.textMuted }}>Session</p>
          <div
            className="rounded-2xl p-4 space-y-2.5"
            style={{ background: theme.card, border: `1px solid ${theme.border}` }}
          >
            {[
              ['Duration', formatTime(sessionTime)],
              ['Messages', transcriptError ? '—' : loadingTranscript ? '...' : messages.length]
            ].map(([label, value]) => (
              <div key={label} className="flex justify-between items-center">
                <span className="text-sm" style={{ color: theme.textSecondary }}>{label}</span>
                <span className="text-sm font-semibold" style={{ color: theme.textPrimary }}>{value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Anxiety Level */}
        <div className="p-5" style={{ borderBottom: `1px solid ${theme.border}` }}>
          <p className="text-xs font-medium tracking-wide mb-3" style={{ color: theme.textMuted }}>How you're doing</p>
          <div
            className="p-4 rounded-2xl"
            style={{ background: theme.card, border: `1px solid ${theme.border}` }}
          >
            <div className="flex justify-between items-center mb-3">
              <span className="text-sm" style={{ color: theme.textSecondary }}>Detected level</span>
              <span
                className="text-xs font-semibold px-2.5 py-1 rounded-full"
                style={{ color: severityConfig.text, background: severityConfig.chip }}
              >
                {validSeverity}
              </span>
            </div>
            <div className="w-full rounded-full h-2" style={{ background: theme.border }}>
              <div
                className="h-2 rounded-full transition-all duration-700 ease-out"
                style={{ background: severityConfig.fill, width: severityConfig.width }}
              />
            </div>
          </div>
        </div>

        {/* Vent Mode Toggle */}
        <div className="p-5" style={{ borderBottom: `1px solid ${theme.border}` }}>
          <p className="text-xs font-medium tracking-wide mb-3" style={{ color: theme.textMuted }}>Mode</p>
          <div
            className="flex rounded-full overflow-hidden p-1"
            style={{ background: theme.card, border: `1px solid ${theme.border}` }}
          >
            <button
              onClick={() => setVentMode(false)}
              className="flex-1 py-2.5 text-sm font-semibold rounded-full transition-all duration-200 touch-manipulation"
              style={{
                background: !ventMode ? theme.accent : 'transparent',
                color: !ventMode ? '#FFFFFF' : theme.textSecondary,
              }}
            >
              Talk
            </button>
            <button
              onClick={() => setVentMode(true)}
              className="flex-1 py-2.5 text-sm font-semibold rounded-full transition-all duration-200 touch-manipulation"
              style={{
                background: ventMode ? theme.accent : 'transparent',
                color: ventMode ? '#FFFFFF' : theme.textSecondary,
              }}
            >
              Vent
            </button>
          </div>
          {ventMode && (
            <p className="text-xs mt-2.5 leading-relaxed" style={{ color: theme.textMuted }}>
              GAIDA will just listen. No advice, no redirects.
            </p>
          )}
        </div>

        {/* Talk to a Counselor */}
        <div className="p-5" style={{ borderBottom: `1px solid ${theme.border}` }}>
          {counselorRequested || counselorActive ? (
            <div
              className="w-full py-3 px-3 text-sm rounded-full text-center font-medium"
              style={{ background: theme.card, border: `1px solid ${theme.border}`, color: theme.textSecondary }}
            >
              {counselorActive ? 'A counselor is with you' : 'Counselor notified'}
            </div>
          ) : (
            <button
              onClick={handleRequestCounselor}
              disabled={requestingCounselor}
              className="w-full py-3 px-3 text-sm font-semibold rounded-full transition-all duration-200 disabled:opacity-50 shadow-sm touch-manipulation"
              style={{ background: theme.accent, color: '#FFFFFF' }}
            >
              {requestingCounselor ? 'Requesting…' : 'Talk to a counselor'}
            </button>
          )}
        </div>

        {/* Settings */}
        <div className="p-5">
          <button
            onClick={() => setShowSettings(p => !p)}
            className="flex items-center justify-between w-full py-1 touch-manipulation"
          >
            <p className="text-xs font-medium tracking-wide" style={{ color: theme.textMuted }}>Settings</p>
            <svg
              className={`w-4 h-4 transition-transform duration-300 ${showSettings ? 'rotate-180' : ''}`}
              fill="none" stroke="currentColor" viewBox="0 0 24 24"
              style={{ color: theme.textMuted }}
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {showSettings && (
            <div className="mt-4 space-y-5">
              {/* Theme Picker */}
              <div>
                <p className="text-xs mb-3 font-medium" style={{ color: theme.textSecondary }}>Colors</p>
                <div className="flex gap-3">
                  {Object.entries(THEMES).map(([key, t]) => (
                    <button
                      key={key}
                      onClick={() => switchTheme(key)}
                      title={t.label}
                      className="touch-manipulation transition-transform duration-200"
                      style={{
                        width: '28px', height: '28px', borderRadius: '50%',
                        background: t.preview,
                        border: theme.name === key ? `2px solid ${theme.textPrimary}` : '2px solid transparent',
                        outline: theme.name === key ? `2px solid ${t.preview}` : 'none',
                        outlineOffset: '2px', cursor: 'pointer',
                      }}
                    />
                  ))}
                </div>
              </div>

              {/* Quick Tips */}
              <div>
                <p className="text-xs mb-2 font-medium" style={{ color: theme.textSecondary }}>Tips</p>
                <div className="space-y-2 text-xs leading-relaxed" style={{ color: theme.textMuted }}>
                  <p>Press Enter to send a message.</p>
                  <p>Use the mic button for voice input.</p>
                  <p>This conversation is kept confidential to help your counselor support you.</p>
                </div>
              </div>
            </div>
          )}
        </div>
        </div>

        {/* Crisis Hotlines & End Session */}
        <div className="p-5 flex-shrink-0 space-y-2.5" style={{ borderTop: `1px solid ${theme.border}`, paddingBottom: 'calc(1.25rem + env(safe-area-inset-bottom))' }}>
          <button
            onClick={(e) => openCrisisHotlines(e)}
            className="w-full py-2.5 px-4 text-xs font-semibold rounded-full transition-all duration-200 touch-manipulation flex items-center justify-center gap-1.5"
            style={{ background: '#FFF5F2', border: '1px solid #F5D5CB', color: '#B0472F' }}
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
            </svg>
            <span>Emergency Hotlines</span>
          </button>
          <button
            onClick={endSession}
            className="w-full py-3 px-4 text-sm font-semibold rounded-full transition-all duration-200 touch-manipulation"
            style={{ background: '#FBEDEA', border: '1px solid #F0D2CA', color: '#B0472F' }}
          >
            End session
          </button>
        </div>
      </aside>

      {/* ── Main ─────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0 h-dvh relative">

        {/* Topbar */}
        <div
          className="h-14 sm:h-16 flex items-center px-3 sm:px-6 gap-2.5 sm:gap-3 flex-shrink-0 z-10"
          style={{
            background: theme.sidebar,
            borderBottom: `1px solid ${theme.border}`,
            paddingTop: 'env(safe-area-inset-top)',
            height: 'calc(3.5rem + env(safe-area-inset-top))',
          }}
        >
          {/* Hide hamburger on large screens since sidebar is permanently open */}
          <button
            onClick={() => setSidebarOpen(p => !p)}
            className="flex-shrink-0 p-2 -ml-1 transition-colors duration-200 lg:hidden touch-manipulation rounded-full"
            style={{ color: theme.textSecondary }}
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>

          <span className="text-sm font-semibold tracking-wide truncate" style={{ color: theme.textPrimary }}>
            Virtual Counselor
          </span>

          <button
            onClick={(e) => openCrisisHotlines(e)}
            className="ml-auto px-2.5 py-1.5 rounded-full text-xs font-semibold flex items-center gap-1.5 transition-all duration-200 active:scale-95 touch-manipulation"
            style={{ background: '#FBEDEA', border: '1px solid #F0D2CA', color: '#B0472F' }}
            title="Crisis & Emergency Hotlines"
            aria-label="View crisis hotlines and emergency contacts"
          >
            <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
            </svg>
            <span className="hidden xs:inline sm:inline">Hotlines</span>
          </button>

          <div
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11px] font-semibold"
            style={{ background: severityConfig.chip, color: severityConfig.text }}
          >
            <div className="w-1.5 h-1.5 rounded-full" style={{ background: severityConfig.fill }} />
            <span className="hidden sm:inline">{severity}</span>
          </div>

          <div className="flex items-center gap-1.5 flex-shrink-0 ml-1 sm:ml-2">
            <div className="w-2 h-2 rounded-full" style={{ background: theme.accent }} />
            <span className="text-xs hidden sm:inline font-medium" style={{ color: theme.textSecondary }}>
              {ventMode ? 'Vent mode' : counselorActive ? 'Counselor active' : 'Online'}
            </span>
          </div>
        </div>

        {/* Chat */}
        <div
          ref={containerRef}
          className="flex-1 overflow-y-auto px-4 sm:px-8 py-6 space-y-4"
          style={{ background: theme.bg }}
        >
          {/* Loading Transcript state */}
          {loadingTranscript && messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center py-12">
              <div
                className="w-8 h-8 border-2 border-t-transparent rounded-full animate-spin mb-3"
                style={{ borderColor: theme.border, borderTopColor: theme.accent }}
              />
              <p className="text-sm font-medium" style={{ color: theme.textSecondary }}>
                Loading conversation history...
              </p>
            </div>
          )}

          {/* Transcript Fetch Error state */}
          {transcriptError && messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center px-4 py-12">
              <div className="w-12 h-12 rounded-2xl flex items-center justify-center mb-3" style={{ background: '#FDE8E8', color: '#E02424' }}>
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <p className="text-base font-semibold mb-1" style={{ color: theme.textPrimary }}>
                Unable to load conversation history
              </p>
              <p className="text-sm max-w-sm mb-4" style={{ color: theme.textSecondary }}>
                We could not retrieve your previous messages. Please check your connection and try again.
              </p>
              <button
                onClick={() => loadTranscript(localStorage.getItem('session_id'))}
                className="px-5 py-2.5 rounded-xl text-xs font-semibold shadow-sm transition-all duration-200 active:scale-95 text-white focus:outline-none focus:ring-2 focus:ring-offset-2"
                style={{ background: theme.accent }}
              >
                Retry Loading
              </button>
            </div>
          )}

          {/* Empty state & Mobile Quick Starts */}
          {messages.length === 0 && !voiceStatus && !loadingTranscript && !transcriptError && (
            <div className="flex flex-col items-center justify-center h-full text-center px-2 py-8">
              <GaidaMark size={64} accent={theme.accent} breathing />
              <p className="text-base font-semibold mt-5 mb-1" style={{ color: theme.textPrimary }}>Start the conversation.</p>
              <p className="text-sm mb-8" style={{ color: theme.textSecondary }}>This space is private and confidential.</p>

              {/* Quick Start Buttons for Mobile Friendliness */}
              <div className="w-full max-w-sm flex flex-col gap-3">
                {QUICK_START_PROMPTS.map((prompt, idx) => (
                  <button
                    key={idx}
                    onClick={() => {
                      setInput(prompt.text);
                      sendMessage(prompt.text);
                    }}
                    className="w-full text-left px-5 py-4 rounded-2xl text-[15px] sm:text-sm font-medium shadow-sm transition-all duration-200 active:scale-[0.98] touch-manipulation"
                    style={{ background: theme.card, border: `1px solid ${theme.border}`, color: theme.textPrimary }}
                  >
                    {prompt.text}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Message list */}
          {messages.map((m, i) => {
            if (m.role === 'system') {
              return (
                <div key={i} className="flex justify-center my-2">
                  <span
                    className="text-xs px-4 py-1.5 rounded-full shadow-sm"
                    style={{ color: theme.textSecondary, background: theme.card, border: `1px solid ${theme.border}` }}
                  >
                    {m.text}
                  </span>
                </div>
              );
            }
            return (
              <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'} items-end gap-2 sm:gap-3`}>
                {(m.role === 'bot' || m.role === 'counselor') && (
                  <Avatar role={m.role} accent={theme.accent} />
                )}
                <MessageBubble
                  message={m}
                  theme={theme}
                  onFeedback={m.role === 'bot' ? (v) => rateMessage(i, v) : undefined}
                  feedback={messageRatings[i]}
                  onPlayTTS={m.role === 'bot' ? () => handlePlayTTS(i, m.text) : undefined}
                  isPlayingTTS={playingTTSIndex === i}
                />
              </div>
            );
          })}

          {/* Counselor typing */}
          {counselorTyping && (
            <div className="flex justify-start items-end gap-2 sm:gap-3">
              <Avatar role="counselor" accent={theme.accent} />
              <div
                className="px-5 py-4 shadow-sm"
                style={{ background: '#F1F6FA', border: '1px solid #DCE8F1', borderRadius: '4px 20px 20px 20px' }}
              >
                <TypingBubble color="#4A7699" />
              </div>
            </div>
          )}

          {/* Bot typing */}
          {sending && !counselorActive && !streamingStarted && (
            <div className="flex justify-start items-end gap-2 sm:gap-3">
              <Avatar role="bot" accent={theme.accent} breathing />
              <div
                className="px-5 py-4 shadow-sm"
                style={{ background: theme.botBubble, border: `1px solid ${theme.border}`, borderRadius: '4px 20px 20px 20px' }}
              >
                <TypingBubble color={theme.accent} />
              </div>
            </div>
          )}

          {/* Voice status */}
          {voiceStatus && (
            <div className="flex justify-center my-2">
              <span
                className="flex items-center gap-2.5 text-xs font-medium px-4 py-2 rounded-full shadow-sm"
                style={{ color: theme.textSecondary, background: theme.card, border: `1px solid ${theme.border}` }}
              >
                <span className="w-2 h-2 rounded-full" style={{ background: theme.accent }} />
                {voiceStatus}
              </span>
            </div>
          )}
        </div>

        {/* Input */}
        <div
          className="px-3 sm:px-6 pt-3 sm:pt-4 flex-shrink-0"
          style={{
            background: theme.sidebar,
            borderTop: `1px solid ${theme.border}`,
            paddingBottom: 'calc(0.75rem + env(safe-area-inset-bottom))',
          }}
        >
          <div
            className="flex items-end gap-2 sm:gap-3 rounded-2xl px-3 py-2 sm:p-2 border transition-all"
            style={{ background: theme.card, borderColor: theme.border }}
          >
            <label htmlFor="student-chat-input" className="sr-only">Type your message</label>
            <textarea
              id="student-chat-input"
              name="student-chat-input"
              aria-label="Type your message"
              ref={inputRef}
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder="Type your message..."
              rows={1}
              // IMPORTANT: Using text-base (16px) specifically on mobile prevents iOS Safari auto-zoom
              className="flex-1 resize-none py-2 text-base sm:text-[15px] leading-relaxed focus:outline-none focus-visible:ring-1 focus-visible:ring-[#5E8FBD] rounded-lg px-1.5"
              style={{ minHeight: '40px', maxHeight: '120px', background: 'transparent', color: theme.textPrimary }}
            />
            <div className="flex items-center gap-1.5 sm:gap-2 flex-shrink-0 pb-1">
              <VoiceInput
                sessionId={localStorage.getItem('session_id')}
                onTranscript={(text) => { setInput(text); sendMessage(text); }}
                onStatusChange={setVoiceStatus}
              />
              <button
                onClick={() => sendMessage()}
                disabled={sending || !input.trim()}
                aria-label="Send message"
                className="w-10 h-10 sm:w-11 sm:h-11 rounded-full flex items-center justify-center transition-all duration-200 flex-shrink-0 touch-manipulation focus:outline-none focus:ring-2 focus:ring-[#5E8FBD]"
                style={
                  input.trim()
                    ? { background: theme.accent, color: '#FFFFFF' }
                    : { background: theme.border, color: theme.textMuted, cursor: 'not-allowed' }
                }
              >
                {sending ? (
                  <div
                    className="w-4 h-4 border-2 rounded-full animate-spin"
                    style={{ borderColor: 'rgba(255,255,255,0.4)', borderTopColor: '#FFFFFF' }}
                  />
                ) : (
                  <svg className="w-5 h-5 ml-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                  </svg>
                )}
              </button>
            </div>
          </div>
          <p className="text-[11px] text-center mt-2.5 hidden sm:block" style={{ color: theme.textMuted }}>
            Press Enter to send. Shift+Enter for new line.
          </p>
        </div>
      </div>

      {/* ── Post-Session Wellbeing Rating Modal ───────────────── */}
      {showRating && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="rating-modal-title"
          className="fixed inset-0 z-[100] flex items-center justify-center p-4 transition-opacity duration-300"
          style={{ background: 'rgba(40,50,55,0.45)' }}
        >
          <div
            className="w-full max-w-sm rounded-3xl p-7 flex flex-col items-center gap-6 shadow-xl"
            style={{ background: theme.card, border: `1px solid ${theme.border}` }}
          >
            {ratingSubmitted ? (
              <div className="flex flex-col items-center gap-3 py-4">
                <GaidaMark size={48} accent={theme.accent} breathing />
                <p id="rating-modal-title" className="text-base font-semibold text-center" style={{ color: theme.textPrimary }}>
                  Thank you for sharing.
                </p>
                <p className="text-sm text-center" style={{ color: theme.textSecondary }}>
                  Take care of yourself.
                </p>
              </div>
            ) : (
              <>
                <div className="text-center w-full">
                  <h2 id="rating-modal-title" className="text-base font-semibold mb-2" style={{ color: theme.textPrimary }}>
                    Before you go
                  </h2>
                  <p className="text-sm leading-relaxed" style={{ color: theme.textSecondary }}>
                    How are you feeling right now compared to when we started?
                  </p>
                </div>

                <div className="flex gap-2 sm:gap-3 w-full justify-between">
                  {WELLBEING_OPTIONS.map((opt) => (
                    <button
                      key={opt.value}
                      onClick={() => handleWellbeingRating(opt.value)}
                      onMouseEnter={() => setHoveredRating(opt.value)}
                      onMouseLeave={() => setHoveredRating(null)}
                      className="flex flex-col items-center justify-start gap-2 p-3 sm:p-2 rounded-2xl transition-all duration-200 flex-1 touch-manipulation"
                      style={{
                        background: hoveredRating === opt.value ? theme.sidebar : 'transparent',
                        border: `1px solid ${hoveredRating === opt.value ? theme.accent : theme.border}`,
                      }}
                    >
                      <span className="text-3xl mb-1">{opt.emoji}</span>
                      <span className="text-[11px] text-center leading-tight font-medium" style={{ color: theme.textSecondary }}>
                        {opt.label}
                      </span>
                    </button>
                  ))}
                </div>

                <button
                  onClick={() => handleWellbeingRating(0)}
                  className="text-sm font-medium transition-colors duration-200 py-2 px-4 touch-manipulation"
                  style={{ color: theme.textMuted }}
                >
                  Skip
                </button>
              </>
            )}
          </div>
        </div>
      )}

      {/* ── Crisis Hotlines Modal ─────────────────────────────── */}
      {showCrisisHotlines && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="crisis-hotlines-title"
          className="fixed inset-0 z-[110] flex items-center justify-center p-4 transition-opacity duration-300"
          style={{ background: 'rgba(40,50,55,0.45)' }}
          onClick={(e) => { if (e.target === e.currentTarget) closeCrisisHotlines(); }}
        >
          <div
            ref={crisisModalRef}
            tabIndex={-1}
            className="w-full max-w-lg rounded-3xl p-6 sm:p-7 flex flex-col gap-5 shadow-2xl max-h-[88vh] overflow-y-auto no-scrollbar outline-none"
            style={{
              background: theme.card,
              border: `1px solid ${theme.border}`,
              scrollbarWidth: 'none',
              msOverflowStyle: 'none',
            }}
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 id="crisis-hotlines-title" className="text-lg font-bold" style={{ color: '#B0472F' }}>
                  Emergency & Crisis Hotlines
                </h2>
                <p className="text-xs mt-1" style={{ color: theme.textSecondary }}>
                  Free, confidential support is available 24/7. Tap a number to call directly.
                </p>
              </div>
              <button
                ref={crisisCloseBtnRef}
                onClick={closeCrisisHotlines}
                className="p-2 -mr-2 text-gray-400 hover:text-gray-600 rounded-full touch-manipulation transition-colors flex-shrink-0 focus:outline-none focus:ring-2 focus:ring-red-400"
                aria-label="Close crisis hotlines modal"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="space-y-3">
              {CRISIS_HOTLINES.map((hotline, idx) => (
                <div
                  key={idx}
                  className="p-3.5 sm:p-4 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-3 transition-colors"
                  style={{ background: theme.sidebar, border: `1px solid ${theme.border}` }}
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full" style={{ background: '#FBEDEA', color: '#B0472F' }}>
                        {hotline.badge}
                      </span>
                      <h3 className="text-sm font-semibold truncate" style={{ color: theme.textPrimary }}>
                        {hotline.name}
                      </h3>
                    </div>
                    <p className="text-xs leading-relaxed" style={{ color: theme.textMuted }}>
                      {hotline.desc}
                    </p>
                  </div>
                  <a
                    href={`tel:${hotline.tel}`}
                    className="inline-flex items-center justify-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold shadow-sm transition-all duration-200 active:scale-95 touch-manipulation flex-shrink-0"
                    style={{ background: '#B0472F', color: '#FFFFFF' }}
                  >
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                    </svg>
                    <span>{hotline.number}</span>
                  </a>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}