import { useState, useEffect, useRef, useCallback, useId } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { createPortal } from 'react-dom';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, PieChart, Pie, Cell, ReferenceLine
} from 'recharts';

import { BACKEND_URL as BACKEND } from '../../config';
import apiFetch, { logoutAndClearAuth, RATE_LIMIT_MESSAGE } from '../../api';
import CounselorBottomNav from './CounselorBottomNav';
import { FALLBACK_POLL_INTERVAL_MS, shouldPollDashboard } from './dashboardPolling';
import ConfirmationDialog from '../../components/ConfirmationDialog';

// ── Shared palette ─────────────────────────────────────────────────────────
// Same cool-blue / soft-green identity as the student interface. Bright red
// is reserved for genuine crisis-level and overdue/unaddressed states, not
// used as a general UI color.
const P = {
  bg: 'var(--bg)',
  surface: 'var(--card)',
  panel: 'var(--bg)',
  border: 'var(--line)',
  navy: 'var(--side)',
  navyLight: 'var(--side)',
  accent: 'var(--brand)',
  accentDark: 'var(--brand)',
  accentSoft: 'color-mix(in srgb, var(--brand) 16%, var(--card))',
  green: 'var(--grn)',
  greenDark: 'var(--grn)',
  greenSoft: 'var(--grnbg)',
  amber: 'var(--amb)',
  amberSoft: 'var(--ambbg)',
  high: 'var(--red)',
  highSoft: 'var(--redbg)',
  teal: 'var(--brand)',
  tealSoft: 'color-mix(in srgb, var(--brand) 16%, var(--card))',
  red: 'var(--red)',
  redSoft: 'var(--redbg)',
  redBorder: 'var(--red)',
  textPrimary: 'var(--ink)',
  textSecondary: 'var(--mut)',
  textMuted: 'var(--mut)',
};

// ── Quick response templates ──────────────────────────────────────────────────
const QUICK_RESPONSES = [
  { label: "I'm here", text: "I'm here with you. You're not alone in this." },
  { label: "Take a breath", text: "Let's take a slow breath together. Inhale for 4 counts, hold for 4, exhale for 4. I'm right here with you." },
  { label: "Help coming", text: "I'm a counselor and I'm here to help you. You reached out at the right time. Can you tell me more about what you're feeling right now?" },
  { label: "Call hotline", text: "Please contact the Philippine NCMH Crisis Hotline at 1553, HOPELINE Philippines at (02) 8804-4673 or 0917-558-4673, or In Touch at (02) 8893-7603 or 0917-800-1123. If you are in immediate danger, call 911. UE Manila GCCSO: Internal Local Number: Local 390 (via the University of the East Telephone Directory); Manila Campus Trunkline: (632) 8735-5471 or (632) 5328-5471; Email Address: guidance@ue.edu.ph; Facebook Page: UE Manila GCCSO; Location: Ground Floor of the SFC Building, UE Manila Campus. I'm staying with you." },
  { label: "Safe?", text: "I want to make sure you're safe right now. Are you in a safe place? Is there anyone with you?" },
  { label: "Follow up", text: "I'd like to schedule a follow-up session with you. You've shown a lot of courage today by reaching out." },
];

// ── Helpers ───────────────────────────────────────────────────────────────────
// Severity ranking for the alert queue. Crisis is always first, then High,
// then Moderate, then a student-requested check-in. High uses a red-orange so
// it stays visibly below Crisis but above Moderate's orange; Crisis keeps the
// reserved emergency red.
const ALERT_SEVERITIES = ['Crisis', 'High', 'Moderate', 'Requested'];
const SEVERITY_RANK = { Crisis: 4, High: 3, Moderate: 2, Requested: 1 };

const severityRank = (s) => SEVERITY_RANK[s] || 0;
const sortBySeverity = (list) => [...list].sort((a, b) => {
  const diff = severityRank(b.severity) - severityRank(a.severity);
  if (diff !== 0) return diff;
  return new Date(a.first_alerted_at || a.timestamp || 0) - new Date(b.first_alerted_at || b.timestamp || 0);
});

const severityColor = (s) => {
  if (s === 'Crisis') return { bg: `bg-[${P.red}]`, text: 'text-white', dot: `bg-[${P.red}]`, border: `border-[${P.redBorder}]`, light: `bg-[${P.redSoft}]`, hex: P.red };
  if (s === 'High') return { bg: `bg-[${P.high}]`, text: 'text-white', dot: `bg-[${P.high}]`, border: `border-[${P.highSoft}]`, light: `bg-[${P.highSoft}]`, hex: P.high };
  if (s === 'Requested') return { bg: `bg-[${P.accent}]`, text: 'text-white', dot: `bg-[${P.accent}]`, border: `border-[${P.accentSoft}]`, light: `bg-[${P.accentSoft}]`, hex: P.accent };
  if (s === 'Moderate') return { bg: `bg-[${P.amber}]`, text: 'text-white', dot: `bg-[${P.amber}]`, border: `border-[${P.amberSoft}]`, light: `bg-[${P.amberSoft}]`, hex: P.amber };
  if (s === 'Low') return { bg: `bg-[${P.green}]`, text: 'text-white', dot: `bg-[${P.green}]`, border: `border-[${P.greenSoft}]`, light: `bg-[${P.greenSoft}]`, hex: P.green };
  return { bg: `bg-[${P.textMuted}]`, text: 'text-white', dot: `bg-[${P.textMuted}]`, border: `border-[${P.border}]`, light: `bg-[${P.panel}]`, hex: P.textMuted };
};

// Dates are formatted in the viewer's local timezone, so midnight, month, and
// year boundaries all resolve to the correct calendar day on their machine.
const RELATIVE_DATE_OPTIONS = { month: 'short', day: 'numeric', year: 'numeric' };

// Human-readable age for alert/case timestamps. Everything is derived from the
// existing timestamp on each render, so values stay current without touching
// stored data. Recent times stay compact; older records fall back to a real
// date instead of ever showing a large hour count like "1163h ago".
const formatRelative = (ts) => {
  if (!ts) return '';
  const date = new Date(ts);
  if (Number.isNaN(date.getTime())) return '';

  const elapsedMs = Date.now() - date.getTime();

  // Future or clock-skewed timestamps never show a negative duration. A date
  // just ahead is still worth showing in full rather than a misleading "Just now".
  if (elapsedMs < 0) {
    if (elapsedMs > -60000) return 'In a moment';
    return date.toLocaleDateString('en-US', RELATIVE_DATE_OPTIONS);
  }

  const minutes = Math.floor(elapsedMs / 60000);
  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;

  const hours = Math.floor(elapsedMs / 3600000);
  if (hours < 24) return `${hours}h ago`;

  // 24h is where hours stop: 24–47h reads "Yesterday", never "24h ago".
  const days = Math.floor(elapsedMs / 86400000);
  if (days < 2) return 'Yesterday';
  if (days < 7) return `${days} days ago`;

  // 7–13 days: the weekday reads more naturally than a date this recent.
  if (days < 14) return date.toLocaleDateString('en-US', { weekday: 'long' });

  return date.toLocaleDateString('en-US', RELATIVE_DATE_OPTIONS);
};

// Re-renders the calling view on an interval so relative timestamps never go
// stale while a page is left open. Kept in one place so every timestamp view
// uses the same cadence instead of owning its own duplicated timer.
function useTimestampTick(intervalMs = 30000) {
  const [, setTick] = useState(0);
  useEffect(() => {
    const interval = setInterval(() => setTick((n) => n + 1), intervalMs);
    return () => clearInterval(interval);
  }, [intervalMs]);
}

const formatDuration = (startedAt, now = Date.now()) => {
  if (!startedAt) return '—';
  const diff = Math.max(0, Math.floor((now - new Date(startedAt)) / 1000));
  const h = Math.floor(diff / 3600);
  const m = Math.floor((diff % 3600) / 60).toString().padStart(2, '0');
  const s = (diff % 60).toString().padStart(2, '0');
  return h > 0 ? `${h}:${m}:${s}` : `${m}:${s}`;
};

const confidenceToSeverity = (c) => {
  if (c >= 0.99) return 'Crisis';
  if (c >= 0.76) return 'High';
  if (c >= 0.71) return 'Moderate';
  if (c >= 0.46) return 'Low';
  return 'Normal';
};

// ── Alert sound ───────────────────────────────────────────────────────────────
// Reuse a single AudioContext instead of constructing one per call — the old
// code spawned a new context on every beep, which browsers eventually gag on
// (and some throw "too many AudioContexts").
let _alertAudioCtx = null;
const playAlertSound = () => {
  try {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return;
    if (!_alertAudioCtx) _alertAudioCtx = new Ctx();
    const ctx = _alertAudioCtx;
    if (ctx.state === 'suspended') ctx.resume();
    [0, 150, 300].forEach((delay) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.frequency.value = 880;
      osc.type = 'sine';
      gain.gain.setValueAtTime(0.3, ctx.currentTime + delay / 1000);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + delay / 1000 + 0.3);
      osc.start(ctx.currentTime + delay / 1000);
      osc.stop(ctx.currentTime + delay / 1000 + 0.3);
    });
  } catch { /* audio output unavailable — the alert beep is best-effort */ }
};

// Which counselor is signed in (matches what /takeover uses).
const getCounselorId = () => {
  try {
    const d = JSON.parse(localStorage.getItem('counselorData') || '{}');
    return d.id || d.student_number || null;
  } catch {
    return null;
  }
};

const notifyDashboard = (message) => {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('gaida:counselor-notice', { detail: message }));
  }
};

// Authenticated PDF export fallback for the Resolved Cases page — a bare
// window.open() can't carry the Bearer token, so it always got a 401.
const downloadSessionPdf = async (sessionId) => {
  try {
    const res = await apiFetch(`${BACKEND}/api/counselor/export-session/${sessionId}`);
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || 'Export failed');
    }
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `GAIDA_Session_${sessionId.slice(0, 8)}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
    return true;
  } catch (err) {
    notifyDashboard(err.message || 'Could not export PDF.');
    return false;
  }
};

const NAV = [
  { id: 'overview',  label: 'Overview' },
  { id: 'alerts',    label: 'Alerts' },
  { id: 'welfare',   label: 'Welfare Checks' },
  { id: 'sessions',  label: 'Active Sessions' },
  { id: 'detection', label: 'Anxiety Detection' },
  { id: 'reports',   label: 'Reports' },
  { id: 'resolved',  label: 'Resolved Cases' },
];

const NAV_GROUPS = [
  { label: 'Monitor', ids: ['overview', 'alerts', 'sessions', 'detection'] },
  { label: 'Follow-up', ids: ['welfare', 'resolved', 'reports'] },
];

// Mobile drawer: four primary rows mirror the bottom bar, with the remaining
// workspace views grouped behind "More".
const DRAWER_PRIMARY_ITEMS = [
  { id: 'overview', label: 'Overview' },
  { id: 'alerts', label: 'Alerts' },
  { id: 'sessions', label: 'Sessions' },
];
const DRAWER_MORE_IDS = ['welfare', 'detection', 'reports', 'resolved'];

const getAlertStatusLabel = (alert) => {
  const status = String(alert?.status || '').toLowerCase();
  if (['reviewed', 'resolved', 'closed', 'done'].includes(status)) return 'Resolved';
  // "escalated" means a counselor took over the session; it is NOT the same
  // as acknowledging the alert. Only the explicit acknowledgement flag/status
  // may hide the Acknowledge action, because /sessions/resolve still requires
  // that flag for Crisis/High alerts.
  if (alert?.acknowledged || status === 'acknowledged') return 'Acknowledged';
  return 'New';
};

const getFocusableElements = (container) => {
  if (!container) return [];
  const elements = [...container.querySelectorAll('button:not([disabled]), a[href], input:not([disabled]), [tabindex]:not([tabindex="-1"])')];
  const visible = elements.filter((element) => element.getClientRects().length > 0);
  return visible.length ? visible : elements;
};

const isPendingAlert = (alert) => getAlertStatusLabel(alert) !== 'Resolved';

function FocusTooltip({ children, label, className = '' }) {
  const tooltipId = useId();
  return (
    <span className={`focus-tooltip ${className}`} tabIndex={0} aria-describedby={tooltipId}>
      {children}
      <span id={tooltipId} role="tooltip">{label}</span>
    </span>
  );
}

// One shared type scale for every sidebar row (nav + utilities).
const ROW_TEXT = 'text-[13px] font-medium';

// One consistent line-icon set for the sidebar (was a mix of emoji and
// symbol glyphs that rendered at different weights/sizes across browsers).
function NavIcon({ id, size = 18 }) {
  const common = { width: size, height: size, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round', strokeLinejoin: 'round' };
  switch (id) {
    case 'overview':
      return <svg {...common}><rect x="3" y="3" width="7" height="7" rx="1.5" /><rect x="14" y="3" width="7" height="7" rx="1.5" /><rect x="3" y="14" width="7" height="7" rx="1.5" /><rect x="14" y="14" width="7" height="7" rx="1.5" /></svg>;
    case 'alerts':
      return <svg {...common}><path d="M12 4L3 20h18L12 4z" /><path d="M12 10v4" /><circle cx="12" cy="17" r="0.5" fill="currentColor" /></svg>;
    case 'bell':
      return <svg {...common}><path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.73 21a2 2 0 0 1-3.46 0" /></svg>;
    case 'welfare':
      return <svg {...common}><path d="M6 4c0 8 6 14 14 14l1-4-5-2-2 2c-2.5-1.3-4.7-3.5-6-6l2-2-2-5-4 1z" /></svg>;
    case 'sessions':
      return <svg {...common}><circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="2.5" fill="currentColor" stroke="none" /></svg>;
    case 'detection':
      return <svg {...common}><path d="M2 12h4l2 7 3-14 2 9 2-4h7" /></svg>;
    case 'reports':
      return <svg {...common}><line x1="4" y1="7" x2="20" y2="7" /><line x1="4" y1="12" x2="20" y2="12" /><line x1="4" y1="17" x2="14" y2="17" /></svg>;
    case 'resolved':
      return <svg {...common}><circle cx="12" cy="12" r="9" /><path d="M8 12.5l2.5 2.5L16 9.5" /></svg>;
    case 'hotline':
      return <svg {...common}><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6A19.79 19.79 0 0 1 2.12 4.18 2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.91.34 1.85.57 2.81.7A2 2 0 0 1 22 16.92z" /></svg>;
    case 'sound':
      return <svg {...common}><path d="M15.54 8.46a5 5 0 0 1 0 7.07" /><path d="M18.36 5.64a9 9 0 0 1 0 12.73" /><path d="M5.59 15H4a1 1 0 0 1-1-1v-4a1 1 0 0 1 1-1h1.59l4.7-4.71C10.92 3.66 12 4.11 12 5v14c0 .89-1.08 1.34-1.71.71L5.59 15z" /></svg>;
    case 'privacy':
      return <svg {...common}><path d="M9 12l2 2 4-4" /><path d="M12 2.94a11.96 11.96 0 0 1-8.62 3.04A12.02 12.02 0 0 0 3 9c0 5.59 3.82 10.29 9 11.62C17.18 19.29 21 14.59 21 9c0-1.04-.13-2.05-.38-3.02A11.96 11.96 0 0 1 12 2.94z" /></svg>;
    case 'theme':
      return <svg {...common}><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.93 4.93l1.42 1.42m11.3 11.3 1.42 1.42M2 12h2m16 0h2M4.93 19.07l1.42-1.42m11.3-11.3 1.42-1.42" /></svg>;
    case 'more':
      return <svg {...common}><circle cx="12" cy="12" r="1.4" /><circle cx="19" cy="12" r="1.4" /><circle cx="5" cy="12" r="1.4" /></svg>;
    case 'collapse':
      return <svg {...common}><polyline points="15 18 9 12 15 6" /></svg>;
    case 'logout':
      return <svg {...common}><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" /></svg>;
    case 'close':
      return <svg {...common}><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>;
    case 'search':
      return <svg {...common}><circle cx="10.8" cy="10.8" r="6.8" /><path d="m16 16 5 5" /></svg>;
    default:
      return null;
  }
}

// Right-side flyout used by every icon-only row in the collapsed rail.
function RowTooltip({ label }) {
  return (
    <span
      className="pointer-events-none absolute left-full top-1/2 z-50 ml-3 -translate-y-1/2 whitespace-nowrap rounded-lg px-2.5 py-1.5 text-xs font-medium text-white opacity-0 shadow-lg transition-opacity duration-150 group-hover:opacity-100 group-focus-visible:opacity-100"
      style={{ background: P.navyLight }}
    >
      {label}
    </span>
  );
}

function HotlinesModal({ onClose, returnFocusRef }) {
  const dialogRef = useRef(null);
  const closeButtonRef = useRef(null);
  const onCloseRef = useRef(onClose);
  const returnFocusRefHolder = useRef(returnFocusRef);

  useEffect(() => { onCloseRef.current = onClose; }, [onClose]);
  useEffect(() => { returnFocusRefHolder.current = returnFocusRef; }, [returnFocusRef]);

  useEffect(() => {
    const previousActiveElement = returnFocusRefHolder.current?.current || document.activeElement;
    closeButtonRef.current?.focus();
    const onKeyDown = (event) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        event.stopImmediatePropagation();
        onCloseRef.current();
        return;
      }
      if (event.key !== 'Tab' || !dialogRef.current) return;
      const focusable = [...dialogRef.current.querySelectorAll('a[href], button:not([disabled])')];
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (!first || !last) return;
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener('keydown', onKeyDown, true);
    return () => {
      document.removeEventListener('keydown', onKeyDown, true);
      previousActiveElement?.focus?.();
    };
  }, []);

  return (
    <div className="modal open" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section ref={dialogRef} className="dlg" role="dialog" aria-modal="true" aria-labelledby="counselor-hotline-title">
        <button ref={closeButtonRef} className="x" type="button" aria-label="Close crisis hotlines" onClick={onClose}>&times;</button>
        <h2 id="counselor-hotline-title">Crisis hotlines</h2>
        <p className="safety">Call a support line for immediate help.</p>
        <div className="mt-4 flex flex-col gap-3">
          <a className="btn" href="tel:1553">NCMH 1553</a>
          <a className="btn ghost" href="tel:09175584673">HOPELINE Philippines (02) 8804-4673 / 0917-558-4673</a>
          <a className="btn ghost" href="tel:09178001123">In Touch (02) 8893-7603 / 0917-800-1123</a>
          <a className="btn ghost" href="tel:911">Philippine emergency hotline 911</a>
          <a className="btn ghost" href="tel:+63287355471">UE Manila GCCSO (632) 8735-5471</a>
          <a className="btn ghost" href="tel:+63253285471">UE Manila GCCSO (632) 5328-5471</a>
        </div>
        <p className="safety mt-4">
          UE Manila GCCSO: Internal Local Number: Local 390 (via the University of the East Telephone Directory).
          Email Address: <a href="mailto:guidance@ue.edu.ph">guidance@ue.edu.ph</a>; Facebook Page: UE Manila GCCSO.
          Location: Ground Floor of the SFC Building, UE Manila Campus.
        </p>
      </section>
    </div>
  );
}

// ── Small shared UI pieces ───────────────────────────────────────────────────
function Card({ children, className = '', style = {} }) {
  return (
    <div
      className={`box rounded-2xl shadow-sm ${className}`}
      style={{ background: P.surface, border: `1px solid ${P.border}`, ...style }}
    >
      {children}
    </div>
  );
}

function EmptyState({ icon, title, sub }) {
  return (
    <div className="counselor-empty-state" style={{ color: P.textMuted }}>
      {typeof icon === 'string' ? (
        <p className="text-4xl mb-3">{icon}</p>
      ) : (
        <div className="mb-3 flex justify-center">{icon}</div>
      )}
      <p className="text-sm font-semibold" style={{ color: P.textSecondary }}>{title}</p>
      {sub && <p className="text-xs mt-1">{sub}</p>}
    </div>
  );
}

function usePullToRefresh(onRefresh) {
  const startTouch = useRef(null);
  const pullDistanceRef = useRef(0);
  const [pullDistance, setPullDistance] = useState(0);

  const onTouchStart = (event) => {
    startTouch.current = event.touches.length === 1
      ? { x: event.touches[0].clientX, y: event.touches[0].clientY }
      : null;
  };
  const onTouchMove = (event) => {
    if (startTouch.current === null || event.touches.length !== 1) return;
    const deltaX = event.touches[0].clientX - startTouch.current.x;
    const deltaY = event.touches[0].clientY - startTouch.current.y;
    if (Math.abs(deltaX) > Math.abs(deltaY)) {
      pullDistanceRef.current = 0;
      setPullDistance(0);
      return;
    }
    const distance = Math.max(0, deltaY);
    pullDistanceRef.current = Math.min(distance, 72);
    setPullDistance(pullDistanceRef.current);
  };
  const onTouchEnd = () => {
    if (pullDistanceRef.current > 52) onRefresh?.();
    startTouch.current = null;
    pullDistanceRef.current = 0;
    setPullDistance(0);
  };

  return {
    onTouchStart,
    onTouchMove,
    onTouchEnd,
    style: { transform: `translateY(${pullDistance * 0.18}px)`, transition: pullDistance ? 'none' : 'transform 200ms ease' },
    indicator: pullDistance > 0 ? (pullDistance > 52 ? 'Release to refresh' : 'Pull to refresh') : '',
  };
}

// A neutral, non-error placeholder for chart cards. The page-level banner is
// the only place that explains a failed request.
function ChartEmptyState({ label = 'No data available', guidance }) {
  return (
    <p className="empty" style={{ color: P.textMuted }}>
      {label}
      {guidance && <span className="mt-1 block text-xs">{guidance}</span>}
    </p>
  );
}

function ChartSkeleton() {
  return <div className="chart-skeleton" role="status" aria-label="Loading chart data"><span /><span /><span /><span /><span /></div>;
}

function ChartErrorState({ onRetry, label = 'Trend data unavailable' }) {
  return (
    <div className="empty" role="alert">
      <p>{label}</p>
      <button type="button" className="btn ghost mt-3" onClick={onRetry}>Try again</button>
    </div>
  );
}

// ── Overview Page ─────────────────────────────────────────────────────────────
function OverviewPage({ alerts, sessions, alertsLoading, alertsError, onNavigate, onAcknowledge, onViewSession }) {
  const [analytics, setAnalytics] = useState(null);
  const [analyticsError, setAnalyticsError] = useState('');
  const [analyticsLoading, setAnalyticsLoading] = useState(true);
  const analyticsTimerRef = useRef(null);

  // Keep the Recent Alerts timestamps current even when no new alert arrives.
  useTimestampTick();

  const loadAnalytics = useCallback(() => {
    clearTimeout(analyticsTimerRef.current);
    setAnalyticsError('');
    setAnalyticsLoading(true);
    analyticsTimerRef.current = setTimeout(() => {
      setAnalyticsError('Analytics took too long to load. Please try again.');
      setAnalyticsLoading(false);
    }, 10000);
    apiFetch(`${BACKEND}/api/counselor/analytics/overview`)
      .then(async (r) => {
        if (!r.ok) throw new Error('Unable to load analytics.');
        return r.json();
      })
      .then(data => {
        clearTimeout(analyticsTimerRef.current);
        setAnalyticsLoading(false);
        if (data && data.error) {
          console.error('Analytics overview error from backend:', data.error);
          setAnalyticsError('Unable to load analytics right now. Please try again later.');
        } else {
          setAnalyticsError('');
          setAnalytics(data);
        }
      })
      .catch((err) => {
        clearTimeout(analyticsTimerRef.current);
        setAnalyticsLoading(false);
        console.error('Analytics overview fetch failed:', err);
        setAnalyticsError('Unable to load analytics right now. Please try again later.');
      });
  }, []);

  useEffect(() => {
    const initialRequest = setTimeout(loadAnalytics, 0);
    return () => {
      clearTimeout(initialRequest);
      clearTimeout(analyticsTimerRef.current);
    };
  }, [loadAnalytics]);

  const pending = alerts.filter(isPendingAlert).length;
  const highSessions = sessions.filter(s => ['Moderate', 'High', 'Crisis'].includes(s.severity)).length;
  const weekChanges = analytics?.week_over_week || {};
  const formatWeekChange = (key, label) => {
    const change = weekChanges[key];
    if (typeof change !== 'number' || !Number.isFinite(change)) return 'Last week comparison unavailable';
    return `${label}: ${change > 0 ? '+' : ''}${change} vs last week`;
  };

  const DISTRIBUTION_COLORS = {
    Low: P.green,
    Moderate: P.amber,
    High: P.high,
    Normal: P.textMuted,
    Crisis: P.red,
  };

  const distributionData = analytics?.anxiety_distribution?.map(d => ({
    ...d,
    color: DISTRIBUTION_COLORS[d.name] || P.textMuted,
  })) || [];
  const hasDistributionData = distributionData.some((entry) => Number(entry.value) > 0);

  const weekData = analytics?.sessions_this_week || [
    { day: 'Mon', count: 0 }, { day: 'Tue', count: 0 },
    { day: 'Wed', count: 0 }, { day: 'Thu', count: 0 }, { day: 'Fri', count: 0 },
    { day: 'Sat', count: 0 }, { day: 'Sun', count: 0 },
  ];
  const hasWeekSessions = weekData.some((day) => Number(day.count) > 0);
  const crisisAlert = alerts.find((alert) => isPendingAlert(alert) && alert.severity === 'Crisis');

  const trendData = analytics?.monthly_trends || [];
  const hasTrendData = trendData.some(m =>
    (m.normal || 0) + (m.low || 0) + (m.moderate || 0) + (m.high || 0) + (m.crisis || 0) > 0
  );
  return (
    <div className="pb-8 lg:pb-0">
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight" style={{ color: P.textPrimary }}>Counselor dashboard</h1>
        <p className="text-sm mt-0.5" style={{ color: P.textSecondary }}>A clear view of what matters. A thoughtful next step.</p>
      </div>
      {pending > 0 && (
        <div className="banner" role="status">
          <span>{pending === 1 ? '1 alert needs review. Status unknown.' : `${pending} alerts need review. Status unknown.`}</span>
          <button type="button" className="btn ghost" onClick={() => onNavigate('alerts')}>Review alert</button>
        </div>
      )}
      {alertsError && (
        <div className="dashboard-data-warning" role="alert">
          <strong>Alert status needs verification</strong>
          <span>{alerts.length > 0 ? 'The dashboard is showing the last alert data received. New alerts may be delayed.' : 'The alert service could not be reached, so an empty count does not confirm safety.'}</span>
          <button type="button" onClick={() => onNavigate('alerts')}>Open Alerts</button>
        </div>
      )}
      {crisisAlert && (
        <section className="crisis" aria-live="polite" aria-label="Crisis alert">
          <div>
            <span className="tag">Crisis</span>
            <span className={`status-tag status-${getAlertStatusLabel(crisisAlert).toLowerCase()}`}>{getAlertStatusLabel(crisisAlert)}</span>
            <strong>Immediate review needed</strong>
            <p className="mut">
              Alert: <FocusTooltip label="Full session code" className="alert-code-tooltip">
                <span className="alert-code">{crisisAlert.session_id || 'Code unavailable'}</span>
              </FocusTooltip>
            </p>
            <p className="mut">A crisis alert is waiting for counselor attention.</p>
          </div>
          <div className="flex gap-2 flex-wrap">
            {getAlertStatusLabel(crisisAlert) === 'New' && (
              <button type="button" className="btn ghost" onClick={() => onAcknowledge(crisisAlert.session_id)}>Acknowledge</button>
            )}
            <button type="button" className="btn ghost" onClick={() => onViewSession(crisisAlert.session_id)}>View session</button>
            <button type="button" className="btn red" onClick={() => onNavigate('alerts')}>Review alert</button>
          </div>
        </section>
      )}
      <div className="kpis">
        {[
          { label: 'Active Sessions', value: sessions.length, sub: 'right now', change: formatWeekChange('sessions_started', 'Sessions started'), color: P.accent, icon: 'sessions', page: 'sessions' },
          { label: 'Pending Alerts', value: pending, sub: 'need attention', change: formatWeekChange('alerts_created', 'Alerts created'), color: pending > 0 ? P.red : P.textMuted, icon: 'alerts', page: 'alerts', risk: pending > 0 },
          { label: 'At-Risk Sessions', value: highSessions, sub: 'Moderate and above', change: formatWeekChange('at_risk_sessions', 'At-risk sessions'), color: highSessions > 0 ? P.red : P.textMuted, icon: 'detection', page: 'detection', risk: highSessions > 0 },
          { label: 'Total Alerts', value: analytics?.total_alerts ?? alerts.length, sub: 'all time', change: formatWeekChange('alerts_created', 'Alerts created'), color: P.navy, icon: 'bell', page: 'alerts' },
        ].map((s) => (
          <button key={s.label} type="button" className={`kpi flex items-center justify-between gap-2 ${s.risk ? 'risk' : ''}`} onClick={() => onNavigate(s.page)}>
            <div className="min-w-0">
              <p className="mut mb-1">{s.label}</p>
              <b>{s.value}</b>
              <p className="mut mt-0.5">{s.sub}</p>
              <p className="kpi-change">{s.change}</p>
            </div>
            <div
              className="kpi-icon"
              style={{ background: s.color, color: '#FFFFFF' }}
              aria-hidden="true"
            >
              <NavIcon id={s.icon} size={20} />
            </div>
          </button>
        ))}
      </div>
      {analyticsError && (
        <div
          className="mb-5 flex flex-col items-start gap-2 rounded-xl p-3 text-xs sm:flex-row sm:items-center sm:justify-between"
          style={{ background: P.amberSoft, border: `1px solid ${P.amber}`, color: P.amber }}
          role="alert"
        >
          <span>{analyticsError}</span>
          <button
            type="button"
            onClick={() => { setAnalyticsError(''); loadAnalytics(); }}
            className="inline-flex min-h-[44px] w-full flex-shrink-0 items-center justify-center rounded-lg px-3 font-semibold text-white transition-opacity hover:opacity-90 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#5E8FBD] sm:w-auto"
            style={{ background: P.navy }}
          >
            Retry
          </button>
        </div>
      )}
      <div className="dashboard-grid-12 mb-5">
        <Card className="p-5">
          <h3 className="text-sm font-semibold mb-4" style={{ color: P.textPrimary }}>Anxiety Level Trends</h3>
          {analyticsError ? (
            <div className="empty">
              <p>Trend data unavailable</p>
              <button type="button" className="btn ghost mt-3" onClick={() => { setAnalyticsError(''); loadAnalytics(); }}>Try again</button>
            </div>
          ) : analyticsLoading && !analytics ? (
            <ChartSkeleton />
          ) : !analytics ? (
            <ChartEmptyState label="Trend data unavailable" />
          ) : !hasTrendData ? (
            <div className="empty">
              <p>Trend data unavailable</p>
              <button type="button" className="btn ghost mt-3" onClick={loadAnalytics}>Try again</button>
            </div>
          ) : (
            <>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" stroke={P.border} />
                  <XAxis dataKey="month" tick={{ fontSize: 11, fill: P.textSecondary }} />
                  <YAxis tick={{ fontSize: 11, fill: P.textSecondary }} allowDecimals={false} />
                  <Tooltip />
                  <Line type="monotone" dataKey="normal" stroke={P.textMuted} strokeWidth={2} dot={{ r: 3 }} />
                  <Line type="monotone" dataKey="low" stroke={P.green} strokeWidth={2} dot={{ r: 3 }} />
                  <Line type="monotone" dataKey="moderate" stroke={P.amber} strokeWidth={2} dot={{ r: 3 }} />
                  <Line type="monotone" dataKey="high" stroke={P.high} strokeWidth={2} dot={{ r: 3 }} />
                  <Line type="monotone" dataKey="crisis" stroke={P.red} strokeWidth={2} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
              <div className="flex flex-wrap gap-3 mt-3">
                {[
                  { label: 'Normal',  color: P.textMuted },
                  { label: 'Low',     color: P.green },
                  { label: 'Moderate', color: P.amber },
                  { label: 'High',    color: P.high },
                  { label: 'Crisis',  color: P.red },
                ].map(l => (
                  <div key={l.label} className="flex items-center gap-1">
                    <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: l.color }} />
                    <span className="text-xs" style={{ color: P.textSecondary }}>{l.label}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </Card>
        <Card className="p-5">
          <h3 className="text-sm font-semibold mb-4" style={{ color: P.textPrimary }}>Sessions This Week</h3>
          {analyticsError ? <ChartErrorState onRetry={loadAnalytics} /> : analyticsLoading && !analytics ? <ChartSkeleton /> : !analytics ? <ChartEmptyState label="Trend data unavailable" /> : hasWeekSessions ? (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={weekData}>
                <CartesianGrid strokeDasharray="3 3" stroke={P.border} />
                <XAxis dataKey="day" tick={{ fontSize: 11, fill: P.textSecondary }} />
                <YAxis tick={{ fontSize: 11, fill: P.textSecondary }} />
                <Tooltip />
                <Bar dataKey="count" fill={P.accent} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : <p className="empty">No sessions this week.</p>}
        </Card>
      </div>
      <div className="dashboard-grid-12">
        <Card className="p-5">
          <h3 className="text-sm font-semibold mb-4" style={{ color: P.textPrimary }}>Anxiety Distribution</h3>
          {analyticsError ? <ChartErrorState onRetry={loadAnalytics} /> : analyticsLoading && !analytics ? <ChartSkeleton /> : !analytics ? <ChartEmptyState label="Trend data unavailable" /> : hasDistributionData ? <div className="flex flex-col sm:flex-row items-center gap-4">
            <ResponsiveContainer width={160} height={160}>
              <PieChart>
                <Pie data={distributionData} cx="50%" cy="50%" innerRadius={45} outerRadius={70} dataKey="value">
                  {distributionData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
            <div className="space-y-2">
              {distributionData.map((d) => (
                <div key={d.name} className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: d.color }} />
                  <span className="text-xs" style={{ color: P.textSecondary }}>{d.name}</span>
                  <span className="text-xs font-semibold ml-auto pl-4" style={{ color: P.textPrimary }}>{d.value}</span>
                </div>
              ))}
            </div>
          </div> : <p className="empty">No data</p>}
        </Card>
        <Card className="p-5">
          <h3 className="text-sm font-semibold mb-4" style={{ color: P.textPrimary }}>Recent Alerts</h3>
          {alertsLoading && alerts.length === 0 ? (
            <p className="text-xs text-center py-6" style={{ color: P.textMuted }}>Loading alerts...</p>
          ) : alertsError && alerts.length === 0 ? (
            <p className="text-xs text-center py-6 text-red-500">Unable to load alerts right now</p>
          ) : alerts.length === 0 ? (
            <p className="text-xs text-center py-6" style={{ color: P.textMuted }}>No alerts yet</p>
          ) : (
            <div className="space-y-3">
              {alerts.slice(0, 5).map((a, i) => {
                const sc = severityColor(a.severity);
                return (
                  <div key={i} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full" style={{ background: sc.hex }} />
                      <div>
                        <p className="text-xs font-semibold" style={{ color: P.textPrimary }}>{a.session_id.slice(0, 8)}...</p>
                        <p className="text-xs" style={{ color: P.textMuted }}>{a.severity} - {a.intent}</p>
                      </div>
                    </div>
                    <span className="text-xs" style={{ color: P.textMuted }}>{formatRelative(a.timestamp)}</span>
                  </div>
                );
              })}
            </div>
          )}
        </Card>
      </div>
      <div className="dashboard-grid-12 mb-5">
        <Card className="p-5">
          <div className="flex items-start gap-3">
            <div
              className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl"
              style={{ background: P.accentSoft, color: P.accent }}
            >
              <NavIcon id="resolved" size={20} />
            </div>
            <div>
              <h3 className="text-sm font-semibold" style={{ color: P.textPrimary }}>
                A thoughtful next step
              </h3>
              <p className="mt-1 text-xs leading-relaxed" style={{ color: P.textSecondary }}>
                Automated signals support professional judgment; they do not confirm a
                student&apos;s safety or provide a diagnosis.
              </p>
            </div>
          </div>
          <ol className="mt-5 grid gap-3 sm:grid-cols-3">
            {[
              'Review new signals and assess urgency.',
              'Acknowledge the alert and follow campus protocol.',
              'Document the action and next step before resolving.',
            ].map((step, index) => (
              <li key={step} className="flex items-start gap-2 text-xs leading-relaxed" style={{ color: P.textSecondary }}>
                <span
                  className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full text-[10px] font-bold"
                  style={{ background: P.accentSoft, color: P.accent }}
                >
                  {index + 1}
                </span>
                <span>{step}</span>
              </li>
            ))}
          </ol>
        </Card>
        <Card className="p-5">
          <div className="flex items-start gap-3">
            <div
              className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl"
              style={{ background: P.greenSoft, color: P.green }}
            >
              <NavIcon id="privacy" size={20} />
            </div>
            <div>
              <h3 className="text-sm font-semibold" style={{ color: P.textPrimary }}>
                Privacy reminder
              </h3>
              <p className="mt-1 text-xs leading-relaxed" style={{ color: P.textSecondary }}>
                Keep notes factual and limited to actions taken and follow-up needs.
                Avoid passwords, account numbers, and unnecessary identifying details.
              </p>
            </div>
          </div>
          <button
            type="button"
            className="btn ghost mt-5 w-full"
            onClick={() => onNavigate('resolved')}
          >
            View case records
          </button>
        </Card>
      </div>
    </div>
  );
}

// ── Escalation helpers ────────────────────────────────────────────────────────
// Prefers the server-computed escalation state (which also drives re-notification
// emails); falls back to a client-side calculation for older payloads.
const getEscalationState = (a) => {
  if (a.escalation_level) {
    return { level: a.escalation_level, ageMinutes: a.age_minutes ?? 0, isOffHours: !!a.is_off_hours };
  }
  // Server not stamped yet (fresh alert, up to the monitor's next tick) —
  // approximate from the age anchor. first_alerted_at is the frozen creation
  // time; timestamp is refreshed on every student message.
  const timestamp = a.first_alerted_at || a.timestamp;
  const now = Date.now();
  const alertTime = new Date(timestamp).getTime();
  const ageMinutes = Math.floor((now - alertTime) / 60000);

  const hour = new Date().getHours();
  const day = new Date().getDay();
  const isOffHours = hour < 8 || hour >= 17 || day === 0 || day === 6;

  const warnThreshold    = isOffHours ? 5  : 10;
  const urgentThreshold  = isOffHours ? 15 : 30;
  const overdueThreshold = isOffHours ? 45 : 60;

  if (ageMinutes >= overdueThreshold) return { level: 'overdue',  ageMinutes, isOffHours };
  if (ageMinutes >= urgentThreshold)  return { level: 'urgent',   ageMinutes, isOffHours };
  if (ageMinutes >= warnThreshold)    return { level: 'warning',  ageMinutes, isOffHours };
  return { level: 'normal', ageMinutes, isOffHours };
};


// ── Alert Row ─────────────────────────────────────────────────────────────────
// Defined at module scope (not inside AlertsPage) so the 2-second polling
// re-render doesn't remount every row and drop mid-click button presses.
function AlertRow({ a, onViewChat, onUpdateStatus, onAcknowledge }) {
  const pointerStart = useRef(null);
  const sc  = severityColor(a.severity);
  const esc = getEscalationState(a);
  const statusLabel = getAlertStatusLabel(a);
  const actionable = statusLabel !== 'Resolved';

  // Overdue/urgent are genuinely time-critical — this is the one place on
  // the dashboard that intentionally borrows the reserved emergency red.
  const borderColor =
    esc.level === 'overdue' ? P.red :
    esc.level === 'urgent'  ? P.red :
    esc.level === 'warning' ? P.amber :
    a.severity === 'Crisis' ? P.red :
    a.severity === 'High'   ? P.high :
    a.severity === 'Moderate' ? P.amber :
    a.severity === 'Requested' ? P.accent :
    P.amber;

  const bgColor =
    esc.level === 'overdue' ? P.redSoft :
    esc.level === 'urgent'  ? P.redSoft :
    esc.level === 'warning' ? P.amberSoft :
    a.severity === 'Crisis' ? P.redSoft :
    a.severity === 'High'   ? P.highSoft :
    a.severity === 'Moderate' ? P.amberSoft :
    a.severity === 'Requested' ? P.accentSoft :
    P.amberSoft;

  return (
    <div
      className="counselor-list-row p-4 rounded-r-xl mb-3"
      style={{ borderLeft: `4px solid ${borderColor}`, background: bgColor }}
      onPointerDown={(e) => {
        if (e.pointerType !== 'touch' || !e.isPrimary) return;
        pointerStart.current = {
          id: e.pointerId,
          x: e.clientX,
          y: e.clientY,
        };
        try { e.currentTarget.setPointerCapture(e.pointerId); } catch { /* unsupported pointer capture */ }
      }}
      onPointerUp={(e) => {
        if (!pointerStart.current || pointerStart.current.id !== e.pointerId) return;
        const deltaX = e.clientX - pointerStart.current.x;
        const deltaY = e.clientY - pointerStart.current.y;
        pointerStart.current = null;
        if (Math.abs(deltaX) < 50 || Math.abs(deltaX) <= Math.abs(deltaY) * 1.2) return;
        if (navigator.vibrate) navigator.vibrate(12);
        if (deltaX > 0 && actionable && statusLabel === 'New') onAcknowledge(a.session_id);
        if (deltaX < 0) onViewChat(a.session_id);
      }}
      onPointerCancel={() => { pointerStart.current = null; }}
    >
      <div className="alert-row-layout flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${sc.text}`} style={{ background: sc.hex }}>{a.severity}</span>
            <span className={`status-tag status-${statusLabel.toLowerCase()}`}>{statusLabel}</span>
            <span className="text-xs" style={{ color: P.textSecondary }}>{a.intent}</span>
            <span className="text-xs" style={{ color: P.textMuted }}>{formatRelative(a.timestamp)}</span>

            {/* Escalation badge */}
            {esc.level === 'overdue' && (
              <span className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-semibold text-white" style={{ background: P.red }}>
                Overdue {esc.ageMinutes}m
              </span>
            )}
            {esc.level === 'urgent' && (
              <span className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-semibold text-white" style={{ background: P.red }}>
                Unattended {esc.ageMinutes}m
              </span>
            )}
            {esc.level === 'warning' && (
              <span className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium text-white" style={{ background: P.amber }}>
                Waiting {esc.ageMinutes}m+
              </span>
            )}

            {/* Needs-supervisor badge (alert passed the overdue deadline) */}
            {a.needs_supervisor && (
              <span className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium text-white" style={{ background: P.navy }}>
                Needs supervisor
              </span>
            )}

            {/* Off-hours tag */}
            {esc.isOffHours && (
              <span className="text-xs px-2 py-0.5 rounded-full font-medium text-white" style={{ background: P.navyLight }}>
                Off-hours
              </span>
            )}
          </div>
          <p className="text-xs font-semibold mb-1" style={{ color: P.textSecondary }}>
            Alert code: <FocusTooltip label="Full alert code" className="alert-code-tooltip">
              <span className="alert-code">{a.session_id || 'Code unavailable'}</span>
            </FocusTooltip>
          </p>
          <p className="text-xs truncate" style={{ color: P.textSecondary }}>"{a.message}"</p>
          {a.acknowledged && (
            <p className="text-xs mt-1" style={{ color: P.greenDark }}>
              Acknowledged{a.acknowledged_at ? ` ${formatRelative(a.acknowledged_at)}` : ''}
            </p>
          )}
        </div>
        <div className="alert-actions flex flex-col gap-2 flex-shrink-0">
          <button
            onClick={() => onViewChat(a.session_id)}
            className="text-xs px-3 py-1.5 rounded-lg font-medium text-white transition-colors duration-200"
            style={{ background: P.navy }}
          >
            View session
          </button>
          {actionable && statusLabel === 'New' && (
            <button
              onClick={() => onAcknowledge(a.session_id)}
              className="text-xs px-3 py-1.5 rounded-lg font-semibold text-white transition-colors duration-200"
              style={{ background: P.red }}
            >
              Acknowledge
            </button>
          )}
          {actionable && statusLabel === 'Acknowledged' && (
            <button
              onClick={() => onUpdateStatus(a.session_id, 'reviewed')}
              className="text-xs px-3 py-1.5 rounded-lg font-medium transition-colors duration-200"
              style={{ border: `1px solid ${P.border}`, color: P.textSecondary, background: P.surface }}
            >
              Mark Reviewed
            </button>
          )}
        </div>
      </div>

      {/* Urgent warning bar */}
      {(esc.level === 'urgent' || esc.level === 'overdue') && (
        <div className="mt-3 pt-3 flex items-center gap-2" style={{ borderTop: `1px solid ${P.redBorder}` }}>
          <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: P.red }} />
          <p className="text-xs font-medium" style={{ color: P.red }}>
            This alert has been waiting {esc.ageMinutes} minutes without a response.
            {esc.isOffHours && ' Session occurred outside office hours.'}
          </p>
        </div>
      )}

      {/* Overdue → supervisor notice (server also re-notifies by email) */}
      {esc.level === 'overdue' && (
        <div className="mt-2 pt-2 flex items-start gap-2" style={{ borderTop: `1px solid ${P.redBorder}` }}>
          <div className="w-2 h-2 rounded-full flex-shrink-0 mt-0.5" style={{ background: P.red }} />
          <p className="text-xs font-semibold" style={{ color: P.red }}>
            Past the escalation deadline — supervisor/backup has been notified by email. Acknowledge this alert immediately.
          </p>
        </div>
      )}
    </div>
  );
}

function AlertsPage({ alerts, alertsLoading, alertsError, alertsLastSynced, onRetryAlerts, onViewChat, onUpdateStatus, onAcknowledge, sessions, theme }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [severityFilter, setSeverityFilter] = useState('all');
  const [filterOpen, setFilterOpen] = useState(false);
  const filterButtonRef = useRef(null);
  const filterSheetRef = useRef(null);
  const closeFilterSheet = useCallback(() => setFilterOpen(false), []);
  const [showSwipeHint, setShowSwipeHint] = useState(() => {
    try { return !localStorage.getItem('gaida:alert-swipe-hint'); } catch { return true; }
  });
  const pull = usePullToRefresh(onRetryAlerts);

  // Alert rows show relative ages; refresh them on a fixed cadence so values
  // like "23h ago" advance to "Yesterday" without waiting for a poll event.
  useTimestampTick();
  useEffect(() => {
    document.body.classList.toggle('filter-sheet-open', filterOpen);
    const main = document.getElementById('counselor-main');
    const previousBodyOverflow = document.body.style.overflow;
    const previousHtmlOverflow = document.documentElement.style.overflow;
    const previousMainOverflow = main?.style.overflowY ?? '';
    const returnFocusTarget = filterButtonRef.current;

    if (filterOpen) {
      document.body.style.overflow = 'hidden';
      document.documentElement.style.overflow = 'hidden';
      if (main) main.style.overflowY = 'visible';
      filterSheetRef.current?.focus();
      const onKeyDown = (event) => {
        if (event.key === 'Escape') {
          event.preventDefault();
          closeFilterSheet();
          return;
        }
        if (event.key !== 'Tab') return;
        const sheet = filterSheetRef.current;
        if (!sheet) return;
        const focusable = getFocusableElements(sheet);
        if (!focusable.length) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (event.shiftKey && (document.activeElement === first || document.activeElement === sheet)) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && (document.activeElement === last || document.activeElement === sheet)) {
          event.preventDefault();
          first.focus();
        }
      };
      document.addEventListener('keydown', onKeyDown);
      return () => {
        document.removeEventListener('keydown', onKeyDown);
        document.body.classList.remove('filter-sheet-open');
        document.body.style.overflow = previousBodyOverflow;
        document.documentElement.style.overflow = previousHtmlOverflow;
        if (main) main.style.overflowY = previousMainOverflow;
        returnFocusTarget?.focus();
      };
    }

    return () => {
      document.body.classList.remove('filter-sheet-open');
      document.body.style.overflow = previousBodyOverflow;
      document.documentElement.style.overflow = previousHtmlOverflow;
      if (main) main.style.overflowY = previousMainOverflow;
    };
  }, [filterOpen, closeFilterSheet]);
  // Tick every 30 seconds so escalation badges update without a poll.
  const [, setNow] = useState(() => Date.now());
  useEffect(() => {
    const interval = setInterval(() => setNow(Date.now()), 30000);
    return () => clearInterval(interval);
  }, []);

  const visibleAlerts = alerts.filter(a => ALERT_SEVERITIES.includes(a.severity));

  const filtered = visibleAlerts.filter(a => {
    const term = searchTerm.toLowerCase().trim();
    const matchTerm = !term ||
      (a.initial_message && a.initial_message.toLowerCase().includes(term)) ||
      (a.trigger_reason && a.trigger_reason.toLowerCase().includes(term));
    const matchSev = severityFilter === 'all' || a.severity?.toLowerCase() === severityFilter.toLowerCase();
    return matchTerm && matchSev;
  });

  const overdue = sortBySeverity(filtered.filter((a) => getEscalationState(a).level === 'overdue'));
  const overdueIds = new Set(overdue.map((a) => a.session_id));
  const pending = sortBySeverity(filtered.filter(a => getAlertStatusLabel(a) === 'New' && !overdueIds.has(a.session_id)));
  const acknowledged = sortBySeverity(filtered.filter(a => getAlertStatusLabel(a) === 'Acknowledged' && !overdueIds.has(a.session_id)));
  const resolved = sortBySeverity(filtered.filter(a => getAlertStatusLabel(a) === 'Resolved' && !overdueIds.has(a.session_id)));

  return (
    <div onTouchStart={pull.onTouchStart} onTouchMove={pull.onTouchMove} onTouchEnd={pull.onTouchEnd} className="counselor-mobile-page counselor-alerts-page" aria-busy={alertsLoading} style={pull.style}>
      {pull.indicator && <div className="counselor-pull-indicator">{pull.indicator}</div>}
      {sessions?.some((session) => session.severity === 'Crisis') && (
        <button
          type="button"
          className="counselor-crisis-banner"
          onClick={() => onViewChat(sessions.find((session) => session.severity === 'Crisis').session_id)}
        >
          <span><strong>Crisis session live</strong><br />Open the session now</span>
          <span aria-hidden="true">›</span>
        </button>
      )}
      <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: P.textPrimary }}>Alerts</h1>
          <p className="text-sm mt-0.5" style={{ color: P.textSecondary }}>Moderate, High and Crisis sessions requiring attention</p>
          <p className="mt-1 text-xs" style={{ color: P.textMuted }}>Alerts update automatically while this workspace is open.</p>
        </div>

        {/* Search & Filter Bar */}
        <div className="flex flex-wrap items-center gap-2 counselor-filter-controls">
          <label htmlFor="alerts-search-input" className="sr-only">Search alerts</label>
          <button type="button" className="counselor-icon-button" aria-label="Search alerts" onClick={() => document.getElementById('alerts-search-input')?.focus()}>
            <NavIcon id="search" size={20} />
          </button>
          <input
            id="alerts-search-input"
            name="alerts-search-input"
            aria-label="Search alerts"
            type="text"
            placeholder="Search alerts..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="px-3 py-1.5 text-xs rounded-lg border focus:outline-none w-44 sm:w-56"
            style={{ background: P.surface, borderColor: P.border, color: P.textPrimary }}
          />
          <label htmlFor="alerts-severity-filter" className="sr-only">Filter alerts by severity</label>
          <button ref={filterButtonRef} type="button" className="counselor-filter-button" onClick={() => setFilterOpen(true)}>
            Filter{severityFilter !== 'all' ? `: ${severityFilter}` : ''}
          </button>
          <select
            id="alerts-severity-filter"
            name="alerts-severity-filter"
            aria-label="Filter alerts by severity"
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="px-2.5 py-1.5 text-xs rounded-lg border focus:outline-none"
            style={{ background: P.surface, borderColor: P.border, color: P.textPrimary }}
          >
            <option value="all">All Severities</option>
            <option value="crisis">Crisis only</option>
            <option value="high">High only</option>
            <option value="moderate">Moderate only</option>
            <option value="requested">Requested only</option>
          </select>
        </div>
      </div>
      {alertsError ? (
        <div className="alert-feed-status alert-feed-status-error" role="alert">
          <div>
            <strong>Alert feed unavailable</strong>
            <p>{alerts.length > 0 ? 'Showing the last successful alert data. New alerts may not appear until the connection is restored.' : 'The system could not verify whether there are alerts.'}</p>
          </div>
          <button type="button" onClick={onRetryAlerts}>Retry now</button>
        </div>
      ) : alertsLoading ? (
        <div className="alert-feed-status alert-feed-status-syncing" role="status">
          <span className="alert-feed-status-dot" aria-hidden="true" />
          <span>Checking for the latest alerts…</span>
        </div>
      ) : alertsLastSynced ? (
        <div className="alert-feed-status alert-feed-status-ok" role="status">
          <span className="alert-feed-status-dot" aria-hidden="true" />
          <span>Alert feed synced {alertsLastSynced.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
        </div>
      ) : null}
      <div className="alert-legend mb-4" aria-label="Alert severity legend">
        <span className="alert-legend-item">
          <span className="alert-legend-label"><span className="alert-legend-dot" style={{ background: P.red }} />Crisis <b>{visibleAlerts.filter((a) => a.severity === 'Crisis').length}</b></span>
          <span className="alert-legend-description">Immediate response</span>
        </span>
        <span className="alert-legend-item">
          <span className="alert-legend-label"><span className="alert-legend-dot" style={{ background: P.high }} />High <b>{visibleAlerts.filter((a) => a.severity === 'High').length}</b></span>
          <span className="alert-legend-description">Urgent attention</span>
        </span>
        <span className="alert-legend-item">
          <span className="alert-legend-label"><span className="alert-legend-dot" style={{ background: P.amber }} />Moderate <b>{visibleAlerts.filter((a) => a.severity === 'Moderate').length}</b></span>
          <span className="alert-legend-description">Monitor and follow up</span>
        </span>
        <span className="alert-legend-note">Highest risk appears first</span>
      </div>
      {showSwipeHint && alerts.length > 0 && (
        <button
          type="button"
          className="counselor-swipe-hint"
          onClick={() => { setShowSwipeHint(false); try { localStorage.setItem('gaida:alert-swipe-hint', '1'); } catch { /* private storage */ } }}
        >
          Swipe right to acknowledge · swipe left to open chat <span>Got it</span>
        </button>
      )}

      {alertsLoading && alerts.length === 0 ? (
        <div className="py-20 text-center">
          <div className="inline-block w-6 h-6 border-2 border-gray-300 border-t-red-600 rounded-full animate-spin mb-3" />
          <p className="text-xs" style={{ color: P.textMuted }}>Loading alerts...</p>
        </div>
      ) : alertsError && alerts.length === 0 ? (
        <div className="p-6 rounded-2xl text-center border my-6" style={{ background: P.amberSoft, borderColor: P.amber }}>
          <p className="text-sm font-semibold mb-1" style={{ color: P.amber }}>Unable to load alerts right now</p>
          <p className="text-xs mb-4" style={{ color: P.amber }}>The alerts service encountered a problem. It will automatically retry, or you can retry now.</p>
          {onRetryAlerts && (
            <button
              onClick={onRetryAlerts}
              className="px-4 py-1.5 rounded-lg text-xs font-semibold text-white transition-opacity hover:opacity-90"
              style={{ background: P.accent }}
            >
              Retry
            </button>
          )}
        </div>
      ) : (
        <>
          {overdue.length > 0 && (
            <div className="mb-6">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-2 h-2 rounded-full" style={{ background: P.red }} />
                <h3 className="text-sm font-semibold" style={{ color: P.red }}>Overdue ({overdue.length})</h3>
              </div>
              {overdue.map((a) => <AlertRow key={a.session_id} a={a} onViewChat={onViewChat} onUpdateStatus={onUpdateStatus} onAcknowledge={onAcknowledge} />)}
            </div>
          )}
          {pending.length > 0 && (
            <div className="mb-6">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-2 h-2 rounded-full" style={{ background: P.red }} />
                <h3 className="text-sm font-semibold" style={{ color: P.textPrimary }}>Pending ({pending.length})</h3>
              </div>
              {pending.map((a) => <AlertRow key={a.session_id} a={a} onViewChat={onViewChat} onUpdateStatus={onUpdateStatus} onAcknowledge={onAcknowledge} />)}
            </div>
          )}
          {acknowledged.length > 0 && (
            <div className="mb-6">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-2 h-2 rounded-full" style={{ background: P.accent }} />
                <h3 className="text-sm font-semibold" style={{ color: P.textPrimary }}>Acknowledged ({acknowledged.length})</h3>
              </div>
              {acknowledged.map((a) => <AlertRow key={a.session_id} a={a} onViewChat={onViewChat} onUpdateStatus={onUpdateStatus} onAcknowledge={onAcknowledge} />)}
            </div>
          )}
          {resolved.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold mb-3" style={{ color: P.textMuted }}>Reviewed / Resolved ({resolved.length})</h3>
              {resolved.map((a) => <AlertRow key={a.session_id} a={a} onViewChat={onViewChat} onUpdateStatus={onUpdateStatus} onAcknowledge={onAcknowledge} />)}
            </div>
          )}
          {visibleAlerts.length === 0 && (
            <div className="alert-empty-state">
              <div className="alert-empty-icon" aria-hidden="true"><NavIcon id="resolved" size={24} /></div>
              <h2>No alerts yet</h2>
              <p>Moderate, High and Crisis sessions will appear here when they need attention.</p>
              <button type="button" className="btn ghost" onClick={onRetryAlerts}>
                Refresh alerts
              </button>
            </div>
          )}
          {visibleAlerts.length > 0 && filtered.length === 0 && (
            <EmptyState icon="🔍" title="No matching alerts" sub="Try changing your search or filter criteria" />
          )}
        </>
      )}
      {filterOpen && createPortal(
        <div className="counselor-portal counselor-filter-portal" data-theme={theme}>
          <div className="counselor-sheet-backdrop" onClick={closeFilterSheet} aria-hidden="true" />
          <div
            ref={filterSheetRef}
            className="counselor-bottom-sheet"
            role="dialog"
            aria-label="Filter alerts"
            aria-modal="true"
            tabIndex={-1}
            style={{ background: P.surface, color: P.textPrimary, borderColor: P.border }}
          >
            <button type="button" className="counselor-sheet-handle" aria-label="Close filter alerts" onClick={closeFilterSheet} />
            <div className="counselor-filter-title-row">
              <h2 style={{ color: P.textPrimary }}>Filter alerts</h2>
              <button type="button" className="counselor-sheet-close" aria-label="Close filter alerts" onClick={closeFilterSheet}>
                <NavIcon id="close" size={18} />
              </button>
            </div>
            <div className="counselor-filter-options">
              {['all', 'crisis', 'high', 'moderate', 'requested'].map((value) => (
                <button
                  type="button"
                  key={value}
                  className={severityFilter === value ? 'selected' : ''}
                  onClick={() => { setSeverityFilter(value); closeFilterSheet(); }}
                >
                  {value === 'all' ? 'All severities' : value[0].toUpperCase() + value.slice(1)}
                  <span className="filter-count">
                    {value === 'all' ? visibleAlerts.length : visibleAlerts.filter((a) => a.severity?.toLowerCase() === value).length}
                  </span>
                  <span>{severityFilter === value ? '✓' : '›'}</span>
                </button>
              ))}
            </div>
          </div>
        </div>,
        document.body,
      )}
    </div>
  );
}

// ── Welfare Checks Page ───────────────────────────────────────────────────────
// Surfaces High/Crisis sessions that went silent (see
// get_sessions_needing_welfare_check in session_manager.py) — a student who
// hit a severe reading and then stopped responding, rather than one who
// calmly ended the session. Backend logic already existed; this page is
// what actually makes it visible to a counselor.
function WelfarePage({ welfare, welfareLoading, welfareError, onViewChat, onMarkChecked, onRefresh }) {
  const pull = usePullToRefresh(onRefresh);
  const sortedWelfare = [...welfare].sort((a, b) => {
    const severityRank = { Crisis: 0, High: 1, Moderate: 2 };
    return (severityRank[a.peak_severity] ?? 3) - (severityRank[b.peak_severity] ?? 3)
      || (Number(b.idle_minutes) || 0) - (Number(a.idle_minutes) || 0);
  });
  return (
    <div onTouchStart={pull.onTouchStart} onTouchMove={pull.onTouchMove} onTouchEnd={pull.onTouchEnd} className="counselor-mobile-page counselor-welfare-page" aria-busy={welfareLoading} style={pull.style}>
      {pull.indicator && <div className="counselor-pull-indicator">{pull.indicator}</div>}
      <div className="mb-6">
        <h1 className="text-2xl font-bold" style={{ color: P.textPrimary }}>Welfare Checks</h1>
        <p className="text-sm mt-0.5" style={{ color: P.textSecondary }}>
          High/Crisis sessions that went silent with no follow-up — worth a human check-in
        </p>
      </div>
      {welfareError && (
        <div role="alert" className="dashboard-data-warning mb-4">
          <strong>Welfare checks may be out of date</strong>
          <span>{welfare.length > 0 ? 'Showing the last successful results.' : welfareError}</span>
          <button type="button" onClick={onRefresh} className="mt-2 rounded-lg border border-amber-700 px-3 py-1.5 font-semibold">Retry</button>
        </div>
      )}
      {welfareLoading && (
        <p role="status" aria-live="polite" className="py-3 text-center text-sm" style={{ color: P.textSecondary }}>
          {welfare.length === 0 ? 'Loading welfare checks…' : 'Refreshing welfare checks…'}
        </p>
      )}
      {welfare.length > 0 ? (
        sortedWelfare.map((w) => {
          const sc = severityColor(w.peak_severity);
          const isOverdue = Number(w.idle_minutes) >= 30;
          return (
            <div key={w.session_id} className="p-4 rounded-r-xl mb-3" style={{ borderLeft: `4px solid ${isOverdue ? P.red : P.amber}`, background: isOverdue ? P.redSoft : P.amberSoft }}>
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className="text-xs px-2 py-0.5 rounded-full font-medium text-white" style={{ background: sc.hex }}>
                      Peak: {w.peak_severity}
                    </span>
                    <span className="text-xs px-2 py-0.5 rounded-full font-medium text-white" style={{ background: P.navyLight }}>
                      Silent {w.idle_minutes}m
                    </span>
                    <span className="text-xs px-2 py-0.5 rounded-full font-semibold" style={{ background: isOverdue ? P.red : P.amber, color: '#FFFFFF' }}>
                      {isOverdue ? 'Overdue' : 'Due for check'}
                    </span>
                  </div>
                  <p className="text-xs font-semibold mb-1" style={{ color: P.textSecondary }}>Session: {w.session_id.slice(0, 16)}...</p>
                  {w.last_message && <p className="text-xs truncate" style={{ color: P.textSecondary }}>Last message: "{w.last_message}"</p>}
                </div>
                <div className="flex flex-col gap-2 flex-shrink-0">
                  <button onClick={() => onViewChat(w.session_id)} className="text-xs px-3 py-1.5 rounded-lg font-medium text-white" style={{ background: P.navy }}>View Chat</button>
                  <button onClick={() => onMarkChecked(w.session_id)} className="text-xs px-3 py-1.5 rounded-lg font-medium" style={{ border: `1px solid ${P.border}`, color: P.textSecondary, background: P.surface }}>Mark Checked</button>
                </div>
              </div>
            </div>
          );
        })
      ) : !welfareLoading && !welfareError ? (
        <div className="counselor-empty-state" style={{ color: P.textMuted }}>
          <div className="mb-3 flex justify-center"><NavIcon id="hotline" size={40} /></div>
          <p className="text-sm font-semibold" style={{ color: P.textSecondary }}>No welfare checks needed</p>
          <p className="text-xs mt-1">Silent High/Crisis sessions will appear here.</p>
          <button type="button" className="btn ghost mt-4" onClick={onRefresh}>Refresh checks</button>
        </div>
      ) : null}
    </div>
  );
}

// ── Active Sessions Page ──────────────────────────────────────────────────────
function SessionsPage({ sessions, sessionsLoading, sessionsError, onRetrySessions, onViewChat, lastUpdated }) {
  const [now, setNow] = useState(() => Date.now());
  const [searchQuery, setSearchQuery] = useState('');
  const [severityFilter, setSeverityFilter] = useState('all');
  const pull = usePullToRefresh(onRetrySessions);

  useEffect(() => {
    const interval = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(interval);
  }, []);

  const visibleSessions = sessions.filter((session) => {
    const query = searchQuery.trim().toLowerCase();
    const matchesSearch = !query || session.session_id.toLowerCase().includes(query) || (session.intent || '').toLowerCase().includes(query);
    const matchesSeverity = severityFilter === 'all' || session.severity === severityFilter;
    return matchesSearch && matchesSeverity;
  });

  return (
    <div onTouchStart={pull.onTouchStart} onTouchMove={pull.onTouchMove} onTouchEnd={pull.onTouchEnd} className="counselor-mobile-page" style={pull.style}>
      {pull.indicator && <div className="counselor-pull-indicator">{pull.indicator}</div>}
      <div className="mb-6">
        <h1 className="text-2xl font-bold" style={{ color: P.textPrimary }}>Active Sessions</h1>
        <p className="text-sm mt-0.5" style={{ color: P.textSecondary }}>Severity levels visible - chat content only shown for flagged sessions</p>
      </div>
      {sessionsLoading && sessions.length === 0 ? (
        <p className="text-xs text-center py-20" style={{ color: P.textMuted }}>Loading active sessions...</p>
      ) : sessionsError && sessions.length === 0 ? (
        <div className="text-center py-20" style={{ color: P.textSecondary }}>
          <p className="text-sm font-medium">{sessionsError}</p>
          {onRetrySessions && (
            <button
              onClick={onRetrySessions}
              className="mt-3 text-xs px-3 py-1.5 rounded-lg text-white font-medium"
              style={{ background: P.accent }}
            >
              Retry
            </button>
          )}
        </div>
      ) : sessionsError ? (
        <div className="dashboard-data-warning mb-4" role="alert">
          <strong>Active sessions may be out of date</strong>
          <span>Showing the last successful session list. New sessions may not appear.</span>
          <button type="button" onClick={onRetrySessions}>Refresh sessions</button>
        </div>
      ) : sessions.length === 0 ? (
        <EmptyState icon="◉" title="No active sessions" sub="Sessions appear here when students are chatting" />
      ) : (
        <Card className="overflow-hidden">
          <div className="px-5 py-3 flex flex-wrap items-center justify-between gap-2" style={{ borderBottom: `1px solid ${P.border}` }}>
            <span className="text-sm font-semibold" style={{ color: P.textPrimary }}>Sessions ({visibleSessions.length} of {sessions.length})</span>
            <div className="flex flex-wrap items-center gap-2">
              <label htmlFor="active-session-search" className="sr-only">Search active sessions</label>
              <input id="active-session-search" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} placeholder="Search ID or intent" className="min-h-[40px] w-40 rounded-lg border px-2.5 text-xs" style={{ background: P.surface, borderColor: P.border, color: P.textPrimary }} />
              <label htmlFor="active-session-severity" className="sr-only">Filter active sessions by severity</label>
              <select id="active-session-severity" value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value)} className="min-h-[40px] rounded-lg border px-2.5 text-xs" style={{ background: P.surface, borderColor: P.border, color: P.textPrimary }}>
                <option value="all">All severity</option>
                <option value="Crisis">Crisis</option>
                <option value="High">High</option>
                <option value="Moderate">Moderate</option>
                <option value="Low">Low</option>
              </select>
              <span className="text-xs" style={{ color: P.textMuted }}>{lastUpdated ? `Updated ${lastUpdated.toLocaleTimeString()}` : 'Auto-refreshing...'}</span>
            </div>
          </div>
          <div>
            {visibleSessions.map((s, idx) => {
              const sc = severityColor(s.severity);
              return (
                <div
                  key={s.session_id}
                  className="px-4 py-3.5 sm:px-5 sm:py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4"
                  style={{ borderTop: idx === 0 ? 'none' : `1px solid ${P.panel}` }}
                >
                  <div className="flex items-start sm:items-center gap-3 min-w-0">
                    <div className="w-3 h-3 rounded-full flex-shrink-0 mt-1 sm:mt-0" style={{ background: sc.hex }} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5 flex-wrap">
                        <span className="text-sm font-semibold truncate" style={{ color: P.textPrimary }}>{s.session_id.slice(0, 16)}...</span>
                        <span className="text-xs px-2 py-0.5 rounded-full font-medium text-white flex-shrink-0" style={{ background: sc.hex }}>{s.severity}</span>
                        {s.has_alert && <span className="text-xs px-2 py-0.5 rounded-full font-medium flex-shrink-0" style={{ background: P.redSoft, color: P.red }}>Alert</span>}
                        {s.assigned_counselor_id && <span className="text-xs px-2 py-0.5 rounded-full font-medium flex-shrink-0" style={{ background: P.accentSoft, color: P.accentDark }}>Assigned</span>}
                      </div>
                      <p className="text-xs truncate" style={{ color: P.textMuted }}>{s.message_count} messages • {formatDuration(s.started_at, now)} • intent: {s.intent}</p>
                    </div>
                  </div>
                  <div className="flex items-center justify-between sm:justify-end gap-3 flex-shrink-0 pl-6 sm:pl-0">
                    <div className="text-left sm:text-right">
                      <p className="text-[11px]" style={{ color: P.textMuted }}>Confidence</p>
                      <p className="text-xs sm:text-sm font-bold" style={{ color: P.textPrimary }}>{(s.confidence * 100).toFixed(0)}%</p>
                    </div>
                    {(s.severity === 'High' || s.severity === 'Crisis' || s.has_alert) && (
                      <button
                        onClick={() => onViewChat(s.session_id)}
                        className="text-xs px-3 py-1.5 rounded-lg font-medium text-white transition-opacity hover:opacity-90 active:scale-95"
                        style={{ background: P.accent }}
                      >
                        View Chat
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
            {visibleSessions.length === 0 && (
              <p className="px-5 py-10 text-center text-sm" style={{ color: P.textMuted }}>No sessions match these filters.</p>
            )}
          </div>
        </Card>
      )}
    </div>
  );
}

// ── Chat Modal ────────────────────────────────────────────────────────────────
function ChatModal({ sessionId, alert, onAcknowledge, onClose }) {
  const [messages, setMessages] = useState([]);
  const messagesRef = useRef([]); // mirror used to dedupe realtime WS appends vs the 3s poll
  const [loading, setLoading] = useState(true);
  const [takeoverMsg, setTakeoverMsg] = useState('');
  const [sending, setSending] = useState(false);
  const [tookOver, setTookOver] = useState(false);
  const [activeTab, setActiveTab] = useState('chat');
  const [studentTyping, setStudentTyping] = useState(false);
  const [returningToGaida, setReturningToGaida] = useState(false);
  const bottomRef = useRef(null);
  const scrollRef = useRef(null);       // chat tab scroll container
  const stickToBottomRef = useRef(true); // stays true unless counselor scrolls up
  const typingTimeoutRef = useRef(null);
  const modalContainerRef = useRef(null);
  const closeBtnRef = useRef(null);
  const previousActiveElementRef = useRef(null);
  const [resolving, setResolving] = useState(false);
  const [resolveConfirmOpen, setResolveConfirmOpen] = useState(false);
  const [resolved, setResolved] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [acknowledging, setAcknowledging] = useState(false);
  const [acknowledgedLocally, setAcknowledgedLocally] = useState(false);

  // Keeps the saved-note timestamp current while the modal stays open.
  useTimestampTick();

  // ── Case Notes state ──────────────────────────────────────────────────────
  const [noteText, setNoteText] = useState('');
  const [noteOutcome, setNoteOutcome] = useState('');
  const [noteAssessment, setNoteAssessment] = useState('');
  const [savedNote, setSavedNote] = useState(null);
  const [savingNote, setSavingNote] = useState(false);
  const [noteError, setNoteError] = useState('');
  // Visible failure feedback for takeover/return-to-GAIDA (previously these
  // errors were only logged to the console or shown on the wrong tab).
  const [actionError, setActionError] = useState('');

  const OUTCOMES = [
    { value: 'resolved',          label: 'Resolved',           desc: 'Handled, no further action needed' },
    { value: 'false_alarm',       label: 'False alarm',        desc: 'Flagged by system but not concerning' },
    { value: 'referred',          label: 'Referred',           desc: 'Escalated to in-person guidance office' },
    { value: 'follow_up',         label: 'Follow-up scheduled',desc: 'Counselor will check in again' },
    { value: 'ongoing',           label: 'Ongoing',            desc: 'Still being monitored' },
  ];

  const OUTCOME_COLORS = {
    resolved:    { dot: P.green,  badge: { bg: P.greenSoft, color: P.greenDark } },
    false_alarm: { dot: P.textMuted, badge: { bg: P.panel, color: P.textSecondary } },
    referred:    { dot: P.accent, badge: { bg: P.accentSoft, color: P.accentDark } },
    follow_up:   { dot: P.amber,  badge: { bg: P.amberSoft, color: P.amber } },
    ongoing:     { dot: P.red,    badge: { bg: P.redSoft, color: P.red } },
  };


  useEffect(() => {
    fetchChat();
    const interval = setInterval(fetchChat, 3000);
    return () => clearInterval(interval);
    // fetchChat is intentionally omitted: it's recreated each render, and
    // adding it would reset the 3s poll on every render. The interval keeps
    // the first closure, which is fine — it only touches refs + stable setters.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  // Realtime live-chat updates: student messages, typing, and takeover state
  // arrive over the per-session WebSocket (same feed the student uses), so a
  // live conversation updates instantly instead of waiting for the 3s poll.
  // The poll stays as the fallback for dropped/reconnecting sockets.
  useEffect(() => {
    const token = localStorage.getItem('counselor_token');
    if (!token) return undefined;

    let ws = null;
    let closed = false;
    let retryDelay = 1000;
    let retryTimer = null;

    const handleRealtime = (msg) => {
      if (!msg || typeof msg !== 'object') return;
      switch (msg.type) {
        case 'interaction':
          // Mirror the new message (student, bot reply, system, or this
          // counselor's own echo — the dedupe in appendRealtimeMessage
          // prevents overlaps with the poll).
          appendRealtimeMessage(msg);
          break;
        case 'typing':
          if (msg.sender === 'student') setStudentTyping(!!msg.is_typing);
          break;
        case 'counselor_active':
          if (typeof msg.active === 'boolean') {
            const myId = getCounselorId();
            const mine = !msg.assigned_counselor_id || msg.assigned_counselor_id === myId;
            setTookOver(msg.active && mine);
          }
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
        handleRealtime(msg);
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

  // Load existing note when modal opens
  useEffect(() => {
    apiFetch(`${BACKEND}/api/counselor/session-notes/${sessionId}`)
      .then(r => r.json())
      .then(data => {
        if (data.notes && data.notes.length > 0) {
          const latest = data.notes[0]; // already ordered desc
          setSavedNote(latest);
          setNoteText(latest.note || '');
          setNoteOutcome(latest.outcome || '');
          setNoteAssessment(latest.counselor_assessment || '');
        }
      })
      .catch(() => {});
  }, [sessionId]);

  // Treat "near the bottom" (within ~80px) as pinned-to-newest. Scrolling up
  // to read the transcript switches this off so new messages don't yank the
  // view back down.
  const handleChatScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    stickToBottomRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
  };

  // (Re)opening the chat tab starts pinned at the newest message.
  useEffect(() => {
    if (activeTab !== 'chat') return;
    stickToBottomRef.current = true;
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activeTab]);

  // New messages / typing indicators only auto-scroll while the counselor is
  // already at the bottom; while reading history the view is left alone.
  useEffect(() => {
    if (activeTab !== 'chat') return;
    if (!stickToBottomRef.current) return;
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, studentTyping, activeTab]);

  // onClose is an inline arrow in the parent, so it is a new function on every
  // parent render (the dashboard re-renders every couple of seconds while
  // polling). Keeping it in a ref stops this effect from re-running, which
  // used to steal focus back to the close button and drop the counselor's
  // cursor out of the message box mid-typing.
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    previousActiveElementRef.current = document.activeElement;
    const focusTimer = requestAnimationFrame(() => {
      closeBtnRef.current?.focus?.();
    });

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onCloseRef.current();
        return;
      }
      if (e.key === 'Tab') {
        const modal = modalContainerRef.current;
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
      if (previousActiveElementRef.current && typeof previousActiveElementRef.current.focus === 'function') {
        requestAnimationFrame(() => {
          previousActiveElementRef.current.focus();
        });
      }
    };
  }, []);

  // Append a message pushed over the realtime WebSocket, deduped against the
  // transcript the poll returns (matched by sender + timestamp + text, all
  // sourced from the same server-side entry, so keys are stable).
  const appendRealtimeMessage = (msg) => {
    if (!msg || !msg.text) return;
    const key = `${msg.sender}|${msg.timestamp}|${msg.text}`;
    if (messagesRef.current.some(m => `${m.sender}|${m.timestamp}|${m.text}` === key)) return;
    const next = [...messagesRef.current, {
      sender: msg.sender,
      text: msg.text,
      timestamp: msg.timestamp,
      intent: msg.analysis?.intent,
      confidence: msg.analysis?.confidence,
    }];
    messagesRef.current = next;
    setMessages(next);
  };

  const fetchChat = async () => {
    try {
      const res = await apiFetch(`${BACKEND}/api/counselor/chat/${sessionId}`);
      const data = await res.json();
      if (data.messages) {
        setMessages(data.messages);
        messagesRef.current = data.messages;
      }
      setStudentTyping(data.student_typing || false);

      // Keep the "you have joined" state truthful across modal re-opens:
      // taken over = a counselor (ideally this one) is actively chatting.
      if (typeof data.counselor_active === 'boolean') {
        const myId = getCounselorId();
        const mine = !data.assigned_counselor_id || data.assigned_counselor_id === myId;
        setTookOver(data.counselor_active && mine);
      }
    } catch { /* ignore */ } finally {
      setLoading(false);
    }
  };

  const fireCounselorTyping = (isTyping) => {
    apiFetch(`${BACKEND}/api/counselor/typing/${sessionId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sender: 'counselor', is_typing: isTyping }),
    }).catch(() => {});
  };

  // Add this ref at the top of ChatModal
const typingThrottleRef = useRef(null);

  const handleInputChange = (e) => {
    setTakeoverMsg(e.target.value);
    if (actionError) setActionError('');

    // Only fire typing signal if not already throttled
    if (!typingThrottleRef.current) {
      fireCounselorTyping(true);
      typingThrottleRef.current = setTimeout(() => {
        typingThrottleRef.current = null;
      }, 2000); // fire at most once every 2 seconds
    }

    // Reset the "stop typing" timer
    clearTimeout(typingTimeoutRef.current);
    typingTimeoutRef.current = setTimeout(() => {
      fireCounselorTyping(false);
      typingThrottleRef.current = null;
    }, 2000);
  };

  const sendTakeover = async (msg) => {
    const text = msg || takeoverMsg;
    if (!text.trim()) return;
    clearTimeout(typingTimeoutRef.current);
    fireCounselorTyping(false);
    setSending(true);
    setActionError('');
    try {
      const res = await apiFetch(`${BACKEND}/api/counselor/takeover`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message: text, counselor_id: getCounselorId() }),
      });
      const data = await res.json().catch(() => ({}));
      if (res.status === 429) {
        setActionError(RATE_LIMIT_MESSAGE);
      } else if (data.ok) {
        setTookOver(true);
        setTakeoverMsg('');
        fetchChat();
      } else if (data.error === 'already_assigned') {
        setActionError('Another counselor is already handling this session.');
      } else {
        setActionError(data.error || 'Could not send your message. Please try again.');
      }
    } catch {
      setActionError('Connection error sending your message. Please try again.');
    } finally {
      setSending(false);
    }
  };

  const handleReturnToGaida = async () => {
    setReturningToGaida(true);
    setActionError('');
    try {
      const res = await apiFetch(`${BACKEND}/api/counselor/return-to-gaida`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, counselor_id: getCounselorId() }),
      });
      const data = await res.json().catch(() => ({}));
      if (data.ok) {
        setTookOver(false);
        fetchChat();
      } else if (data.error === 'already_assigned') {
        setActionError('This session is being handled by another counselor — they need to return it to GAIDA first.');
      } else {
        setActionError(data.error || data.detail || 'Could not hand the session back to GAIDA.');
      }
    } catch {
      setActionError('Connection error returning the session. Please try again.');
    } finally {
      setReturningToGaida(false);
    }
  };


  const handleSaveNote = async () => {
    if (!noteOutcome) { setNoteError('Please select an outcome.'); return; }
    setNoteError('');
    setSavingNote(true);
    try {
      const res = await apiFetch(`${BACKEND}/api/counselor/session-notes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          note: noteText,
          outcome: noteOutcome,
          counselor_assessment: noteAssessment,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (data.ok) {
        setSavedNote({ note: noteText, outcome: noteOutcome, counselor_assessment: noteAssessment, updated_at: new Date().toISOString(), created_at: new Date().toISOString() });
      } else {
        setNoteError(data.error || 'Failed to save. Please try again.');
      }
    } catch {
      setNoteError('Failed to save. Please try again.');
    } finally {
      setSavingNote(false);
    }
  };

  const severityHistory = messages
    .filter(m => m.sender === 'user' && m.confidence)
    .map((m, i) => ({
      msg: i + 1,
      confidence: Math.round((m.confidence || 0) * 100),
      severity: confidenceToSeverity(m.confidence || 0),
      text: m.text?.slice(0, 30) + (m.text?.length > 30 ? '...' : ''),
    }));

  const CustomDot = (props) => {
    const { cx, cy, payload } = props;
    const colors = { Crisis: P.red, High: P.high, Moderate: P.amber, Low: P.green, Normal: P.textMuted };
    return <circle cx={cx} cy={cy} r={4} fill={colors[payload.severity] || P.textMuted} stroke="white" strokeWidth={1.5} />;
  };

  const TABS = [
    { id: 'chat',  label: 'Chat Transcript' },
    { id: 'graph', label: 'Anxiety Progression' },
    { id: 'notes', label: 'Case Notes' },
  ];
  
  const needsAcknowledgment = Boolean(
    alert
    && ['High', 'Crisis'].includes(alert.severity)
    && !alert.acknowledged
    && !acknowledgedLocally
  );

  const handleAcknowledge = async () => {
    if (!onAcknowledge) return;
    setAcknowledging(true);
    const ok = await onAcknowledge(sessionId);
    setAcknowledging(false);
    if (ok) setAcknowledgedLocally(true);
  };

  const handleResolve = async () => {
    setResolveConfirmOpen(false);
    setResolving(true);
    try {
      const res = await apiFetch(`${BACKEND}/api/counselor/sessions/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          resolved_by: getCounselorId() || undefined,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok && data.ok) {
        setResolved(true);
        setTimeout(() => onClose(), 1500);
      } else {
        notifyDashboard(data.detail || data.error || 'Could not resolve this session. It may need acknowledgment first.');
      }
    } catch (e) {
      console.error('Resolve session error:', e);
      notifyDashboard('Network error resolving session. Please check your connection.');
    } finally {
      setResolving(false);
    }
  };

  const handleExportSession = async () => {
    setExporting(true);
    try {
      await downloadSessionPdf(sessionId);
    } finally {
      setExporting(false);
    }
  };

  return (
    <>
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="chat-modal-title"
      ref={modalContainerRef}
      tabIndex={-1}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 outline-none"
      style={{ background: 'rgba(34,48,58,0.55)' }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="rounded-2xl w-full max-w-2xl max-h-[90vh] flex flex-col shadow-xl" style={{ background: P.surface }}>

        {/* Header */}
        <div className="px-4 py-3 sm:px-5 sm:py-4 flex flex-wrap items-start justify-between gap-3 flex-shrink-0" style={{ borderBottom: `1px solid ${P.border}` }}>
          <div className="min-w-0">
            <h3 id="chat-modal-title" className="text-sm font-bold" style={{ color: P.textPrimary }}>Live Session</h3>
            <p className="text-xs" style={{ color: P.textSecondary }}>{sessionId.slice(0, 24)}...</p>
          </div>
          <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto sm:justify-end">
            <button
              onClick={handleExportSession}
              disabled={exporting}
              className="flex min-h-11 flex-1 items-center justify-center gap-1.5 whitespace-nowrap rounded-lg px-3 py-1.5 text-xs transition-colors duration-200 disabled:opacity-50 sm:flex-none"
              style={{ background: P.panel, color: P.textSecondary, border: `1px solid ${P.border}` }}
            >
              {exporting ? (
                '...'
              ) : (
                <>
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Export
                </>
              )}
            </button>
            {needsAcknowledgment && (
              <button
                type="button"
                onClick={handleAcknowledge}
                disabled={acknowledging}
                className="order-first min-h-11 w-full whitespace-nowrap rounded-lg px-3 py-1.5 text-xs font-semibold text-white transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed sm:order-none sm:w-auto"
                style={{ background: P.red }}
              >
                {acknowledging ? 'Acknowledging...' : 'Acknowledge'}
              </button>
            )}
            {resolved ? (
              <span className="text-xs font-medium" style={{ color: P.greenDark }}>Session resolved</span>
            ) : (
              <button
                onClick={() => setResolveConfirmOpen(true)}
                disabled={resolving || !savedNote || needsAcknowledgment}
                title={needsAcknowledgment ? 'Acknowledge this Crisis/High alert before resolving' : !savedNote ? 'Save a case note before resolving' : undefined}
                className="min-h-11 flex-1 whitespace-nowrap rounded-lg px-3 py-1.5 text-xs font-medium text-white transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed sm:flex-none"
                style={{ background: P.green }}
              >
                {resolving ? 'Resolving...' : 'Resolve session'}
              </button>
            )}
            <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: P.green }} />
            <span className="text-xs mr-2" style={{ color: P.textMuted }}>Live</span>
            <button
              ref={closeBtnRef}
              onClick={onClose}
              aria-label="Close session details"
              className="h-11 w-11 flex-shrink-0 flex items-center justify-center rounded-lg text-sm font-bold transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-[#5E8FBD]"
              style={{ border: `1px solid ${P.border}`, color: P.textSecondary }}
            >
              ✕
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex flex-shrink-0" style={{ borderBottom: `1px solid ${P.border}` }}>
          {TABS.map(t => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className="flex-1 py-2.5 text-xs font-medium transition-colors duration-200 relative"
              style={
                activeTab === t.id
                  ? { background: P.panel, color: P.textPrimary, borderBottom: `2px solid ${P.accent}` }
                  : { color: P.textMuted }
              }
            >
              {t.label}
              {t.id === 'notes' && savedNote && (
                <span className="absolute top-1.5 right-3 w-1.5 h-1.5 rounded-full" style={{ background: P.accent }} />
              )}
            </button>
          ))}
        </div>

        {/* Chat Tab */}
        {activeTab === 'chat' && (
          <div ref={scrollRef} onScroll={handleChatScroll} className="flex-1 overflow-y-auto p-4 space-y-3 min-h-0" style={{ background: P.bg }}>
            {loading ? (
              <p className="text-xs text-center py-8" style={{ color: P.textMuted }}>Loading chat...</p>
            ) : messages.length === 0 ? (
              <p className="text-xs text-center py-8" style={{ color: P.textMuted }}>No messages yet</p>
            ) : (
              messages
                .filter((m, i, arr) => {
                  if (i === 0) return true;
                  const prev = arr[i - 1];
                  return !(prev.sender === m.sender && prev.text === m.text);
                })
                .map((m, i) => (
                  <div key={i} className={`flex ${m.sender === 'student' || m.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div
                      className="max-w-[75%] px-3 py-2 rounded-xl text-xs leading-relaxed break-words [overflow-wrap:anywhere]"
                      style={
                        m.sender === 'student' || m.sender === 'user'
                          ? { background: P.navy, color: '#FFFFFF', borderTopRightRadius: '4px' }
                          : m.sender === 'counselor'
                          ? { background: P.accent, color: '#FFFFFF', borderTopLeftRadius: '4px' }
                          : { background: P.surface, color: P.textPrimary, border: `1px solid ${P.border}`, borderTopLeftRadius: '4px' }
                      }
                    >
                      {m.sender === 'counselor' && <p className="text-xs font-semibold mb-1" style={{ color: '#E3EEF6' }}>You (Counselor)</p>}
                      {m.sender === 'bot' && <p className="text-xs font-semibold mb-1" style={{ color: P.textMuted }}>GAIDA</p>}
                      <p>{m.text}</p>
                      {(m.sender === 'user' || m.sender === 'student') && m.confidence && (
                        <div className="flex items-center gap-1 mt-1">
                          <div className="w-1.5 h-1.5 rounded-full" style={{
                            background:
                              confidenceToSeverity(m.confidence) === 'High' ? P.amber :
                              confidenceToSeverity(m.confidence) === 'Moderate' ? P.teal :
                              confidenceToSeverity(m.confidence) === 'Low' ? P.green : P.textMuted
                          }} />
                          <p className="text-xs" style={{ color: '#C3CDD2' }}>{m.intent} • {(m.confidence * 100).toFixed(0)}% • {confidenceToSeverity(m.confidence)}</p>
                        </div>
                      )}
                    </div>
                  </div>
                ))
            )}
            {studentTyping && (
              <div className="flex justify-end">
                <div className="px-3 py-2 rounded-xl" style={{ background: P.navyLight, borderTopRightRadius: '4px' }}>
                  <div className="flex gap-1 items-center h-4">
                    <div className="w-1.5 h-1.5 rounded-full animate-bounce" style={{ background: '#C3CDD2', animationDelay:'0ms'}}></div>
                    <div className="w-1.5 h-1.5 rounded-full animate-bounce" style={{ background: '#C3CDD2', animationDelay:'150ms'}}></div>
                    <div className="w-1.5 h-1.5 rounded-full animate-bounce" style={{ background: '#C3CDD2', animationDelay:'300ms'}}></div>
                  </div>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        )}

        {/* Severity Graph Tab */}
        {activeTab === 'graph' && (
          <div className="flex-1 overflow-y-auto p-4 min-h-0">
            <div className="mb-3">
              <p className="text-xs font-semibold mb-1" style={{ color: P.textPrimary }}>Anxiety Confidence Over Session</p>
              <p className="text-xs" style={{ color: P.textMuted }}>Each point = one student message. Color = detected severity.</p>
            </div>
            {severityHistory.length === 0 ? (
              <p className="text-xs text-center py-8" style={{ color: P.textMuted }}>No data yet - waiting for student messages</p>
            ) : (
              <>
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={severityHistory} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={P.border} />
                    <XAxis dataKey="msg" tick={{ fontSize: 10, fill: P.textSecondary }} label={{ value: 'Message #', position: 'insideBottom', offset: -2, fontSize: 10, fill: P.textSecondary }} />
                    <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: P.textSecondary }} tickFormatter={v => `${v}%`} />
                    <Tooltip
                      formatter={(val) => [`${val}%`, 'Confidence']}
                      labelFormatter={(label, payload) => payload?.[0]?.payload?.text || `Message ${label}`}
                    />
                    <ReferenceLine y={75} stroke={P.amber} strokeDasharray="3 3" label={{ value: 'High', fill: P.amber, fontSize: 10 }} />
                    <ReferenceLine y={60} stroke={P.teal} strokeDasharray="3 3" label={{ value: 'Moderate', fill: P.teal, fontSize: 10 }} />
                    <ReferenceLine y={45} stroke={P.green} strokeDasharray="3 3" label={{ value: 'Low', fill: P.green, fontSize: 10 }} />
                    <Line type="monotone" dataKey="confidence" stroke={P.textSecondary} strokeWidth={2} dot={<CustomDot />} />
                  </LineChart>
                </ResponsiveContainer>
                <div className="flex flex-wrap gap-3 mt-3">
                  {[
                    { label: 'Normal', color: P.textMuted },
                    { label: 'Low', color: P.green },
                    { label: 'Moderate', color: P.teal },
                    { label: 'High', color: P.amber },
                    { label: 'Crisis', color: P.red },
                  ].map(l => (
                    <div key={l.label} className="flex items-center gap-1">
                      <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: l.color }} />
                      <span className="text-xs" style={{ color: P.textSecondary }}>{l.label}</span>
                    </div>
                  ))}
                </div>
                {severityHistory.length > 0 && (() => {
                  const last = severityHistory[severityHistory.length - 1];
                  const sc = severityColor(last.severity);
                  return (
                    <div className="mt-3 p-3 rounded-xl" style={{ background: sc.light, border: `1px solid ${sc.hex}33` }}>
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-xs font-semibold" style={{ color: P.textPrimary }}>Current Status</p>
                          <p className="text-xs" style={{ color: P.textMuted }}>Based on latest message</p>
                        </div>
                        <div className="text-right">
                          <span className="text-sm font-bold px-3 py-1 rounded-full text-white" style={{ background: sc.hex }}>{last.severity}</span>
                          <p className="text-xs mt-1" style={{ color: P.textMuted }}>{last.confidence}% confidence</p>
                        </div>
                      </div>
                    </div>
                  );
                })()}
              </>
            )}
          </div>
        )}

        {/* Case Notes Tab */}
        {activeTab === 'notes' && (
          <div className="flex-1 overflow-y-auto p-4 min-h-0">

            {/* Saved note banner */}
            {savedNote && (
              <div className="mb-4 p-3 rounded-xl flex items-center justify-between" style={{ background: P.accentSoft, border: `1px solid ${P.accent}55` }}>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium" style={{ color: P.accentDark }}>Note saved</span>
                  {(savedNote.updated_at || savedNote.created_at) && (
                    <span className="text-xs" style={{ color: P.accentDark, opacity: 0.7 }}>{formatRelative(savedNote.updated_at || savedNote.created_at)}</span>
                  )}
                </div>
                {savedNote.outcome && (() => {
                  const oc = OUTCOME_COLORS[savedNote.outcome];
                  const outcomeLabel = OUTCOMES.find(o => o.value === savedNote.outcome)?.label;
                  return (
                    <span className="text-xs px-2 py-0.5 rounded-full font-medium" style={{ background: oc?.badge.bg, color: oc?.badge.color }}>
                      {outcomeLabel}
                    </span>
                  );
                })()}
              </div>
            )}

            {/* Outcome selector */}
            <div className="mb-4">
              <p className="text-xs font-semibold mb-2" style={{ color: P.textPrimary }}>Outcome</p>
              <div className="space-y-2">
                {OUTCOMES.map(o => {
                  const oc = OUTCOME_COLORS[o.value];
                  const selected = noteOutcome === o.value;
                  return (
                    <button
                      key={o.value}
                      onClick={() => setNoteOutcome(o.value)}
                      className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-left transition-colors duration-200"
                      style={selected ? { border: `1px solid ${P.accent}`, background: P.accentSoft } : { border: `1px solid ${P.border}` }}
                    >
                      <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: oc.dot }} />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-semibold" style={{ color: selected ? P.textPrimary : P.textSecondary }}>{o.label}</p>
                        <p className="text-xs" style={{ color: P.textMuted }}>{o.desc}</p>
                      </div>
                      {selected && <span className="text-xs flex-shrink-0" style={{ color: P.accentDark }}>✓</span>}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Notes textarea */}
            <div className="mb-4">
              <label htmlFor="counselor-session-notes" className="block text-xs font-semibold mb-2" style={{ color: P.textPrimary }}>Notes</label>
              <textarea
                id="counselor-session-notes"
                name="counselor-session-notes"
                aria-label="Counselor session notes"
                value={noteText}
                onChange={e => setNoteText(e.target.value)}
                placeholder="Document what happened, what was said, and any follow-up actions..."
                rows={5}
                className="w-full text-xs px-3 py-2 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#5E8FBD] resize-none leading-relaxed"
                style={{ border: `1px solid ${P.border}`, color: P.textPrimary }}
              />
            </div>

            {/* Independent professional assessment (override field — Ch3) */}
            <div className="mb-4">
              <label htmlFor="counselor-assessment" className="block text-xs font-semibold mb-2" style={{ color: P.textPrimary }}>
                Independent assessment <span className="font-normal" style={{ color: P.textMuted }}>(optional)</span>
              </label>
              <textarea
                id="counselor-assessment"
                name="counselor-assessment"
                aria-label="Counselor independent assessment"
                value={noteAssessment}
                onChange={e => setNoteAssessment(e.target.value)}
                placeholder="Record your own assessment of the student's anxiety level and the action you intend to take (kept separate from GAIDA's automated classification)..."
                rows={3}
                className="w-full text-xs px-3 py-2 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#5E8FBD] resize-none leading-relaxed"
                style={{ border: `1px solid ${P.border}`, color: P.textPrimary }}
              />
            </div>

            {noteError && (
              <p className="text-xs mb-3" style={{ color: P.red }}>{noteError}</p>
            )}

            <button
              onClick={handleSaveNote}
              disabled={savingNote}
              className="w-full py-2.5 text-white text-xs font-medium rounded-xl disabled:opacity-50 transition-colors duration-200"
              style={{ background: P.navy }}
            >
              {savingNote ? 'Saving...' : savedNote ? 'Update note' : 'Save note'}
            </button>
          </div>
        )}

        {/* Quick Responses + Input — hidden on notes tab */}
        {activeTab !== 'notes' && (
          <div className="px-4 pt-3 flex-shrink-0" style={{ borderTop: `1px solid ${P.border}` }}>
            {actionError && (
              <p className="text-xs mb-2 rounded-lg px-3 py-2" style={{ color: P.red, background: P.redSoft, border: `1px solid ${P.redBorder}` }}>{actionError}</p>
            )}
            <p className="text-xs mb-2" style={{ color: P.textMuted }}>Quick responses:</p>
            <div className="flex flex-wrap gap-1.5 mb-3">
              {QUICK_RESPONSES.map((r) => (
                <button
                  key={r.label}
                  onClick={() => sendTakeover(r.text)}
                  disabled={sending}
                  className="text-xs px-2.5 py-1 rounded-full transition-colors duration-200 disabled:opacity-50"
                  style={{ background: P.panel, color: P.textSecondary, border: `1px solid ${P.border}` }}
                >
                  {r.label}
                </button>
              ))}
            </div>
            {tookOver && (
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs font-medium" style={{ color: P.accentDark }}>You have joined this session</p>
                <button
                  onClick={handleReturnToGaida}
                  disabled={returningToGaida}
                  className="text-xs px-3 py-1 rounded-full transition-colors duration-200 disabled:opacity-50"
                  style={{ background: P.panel, color: P.textSecondary, border: `1px solid ${P.border}` }}
                >
                  {returningToGaida ? 'Returning...' : '← Return to GAIDA'}
                </button>
              </div>
            )}
            <div className="flex gap-2 pb-3">
              <label htmlFor="counselor-takeover-message" className="sr-only">Message to student</label>
              <input
                id="counselor-takeover-message"
                name="counselor-takeover-message"
                aria-label="Message to student"
                value={takeoverMsg}
                onChange={handleInputChange}
                onKeyDown={e => e.key === 'Enter' && sendTakeover()}
                placeholder="Type a message to the student..."
                className="flex-1 text-xs px-3 py-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#5E8FBD]"
                style={{ border: `1px solid ${P.border}`, color: P.textPrimary }}
              />
              <button
                onClick={() => sendTakeover()}
                disabled={sending || !takeoverMsg.trim()}
                aria-label="Send message to student"
                className="px-4 py-2 text-white text-xs rounded-lg disabled:opacity-50 font-medium transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-[#5E8FBD]"
                style={{ background: P.accent }}
              >
                {sending ? '...' : 'Send'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
    {resolveConfirmOpen && (
      <ConfirmationDialog
        title="Resolve session?"
        description="This session will leave active alerts and appear in resolved cases."
        cancelLabel="Keep session active"
        confirmLabel="Resolve session"
        onCancel={() => setResolveConfirmOpen(false)}
        onConfirm={handleResolve}
      />
    )}
    </>
  );
}

// ── Detection Page ────────────────────────────────────────────────────────────
function DetectionPage() {
  const thresholds = [
    { level: 'Normal', range: '< 0.46', color: P.textMuted, desc: 'GPT responds freely' },
    { level: 'Low', range: '0.46 – 0.71', color: P.green, desc: 'Counselor protocol injected' },
    { level: 'Moderate', range: '0.71 – 0.76', color: P.teal, desc: 'Stronger protocol injected' },
    { level: 'High', range: '0.76 – 0.98', color: P.amber, desc: 'Counselor alert fired' },
    { level: 'Crisis', range: '0.99 – 1.00', color: P.red, desc: 'Immediate intervention' },
  ];

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold" style={{ color: P.textPrimary }}>Multimodal Anxiety Detection</h1>
        <p className="text-sm mt-0.5" style={{ color: P.textSecondary }}>Real-time anxiety monitoring using voice and text analysis</p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
        {[
          { label: 'Voice Analysis', sub: 'Pitch, Energy, Jitter, Speech Rate, Pauses', status: 'Active' },
          { label: 'Text Analysis', sub: 'ML Ensemble: LR + RF + Neural Network', status: 'Active' },
        ].map((m) => (
          <Card key={m.label} className="p-5">
            <div className="flex items-center gap-2 mb-1">
              <div className="w-2 h-2 rounded-full" style={{ background: P.green }} />
              <p className="text-xs" style={{ color: P.textSecondary }}>{m.label}</p>
            </div>
            <p className="text-xl font-bold mb-1" style={{ color: P.textPrimary }}>{m.status}</p>
            <p className="text-xs" style={{ color: P.textMuted }}>{m.sub}</p>
          </Card>
        ))}
      </div>
      <Card className="p-4 sm:p-5">
        <h3 className="text-sm font-semibold mb-3" style={{ color: P.textPrimary }}>Anxiety Level Thresholds</h3>
        <p className="mb-4 text-xs leading-relaxed" style={{ color: P.textSecondary }}>
          These are support signals, not a medical diagnosis. Higher levels trigger stronger counselor review and safety procedures.
        </p>

        {/* Mobile cards keep each threshold readable at one-hand width. */}
        <div className="sm:hidden">
          <div className="space-y-2.5">
            {thresholds.map((t) => (
              <div key={t.level} className="counselor-threshold-card" style={{ borderLeftColor: t.color }}>
                <div>
                  <p className="text-sm font-bold" style={{ color: P.textPrimary }}>{t.level}</p>
                  <p className="text-xs" style={{ color: P.textMuted }}>{t.range}</p>
                </div>
                <p className="min-w-0 break-words text-xs font-medium leading-snug" style={{ color: P.textSecondary }}>{t.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Desktop layout is unchanged. */}
        <div className="hidden space-y-3 sm:block">
          {thresholds.map((t) => (
            <div key={t.level} className="flex items-center gap-3">
              <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ background: t.color }} />
              <span className="text-xs font-semibold w-16" style={{ color: P.textPrimary }}>{t.level}</span>
              <span className="text-xs w-24" style={{ color: P.textMuted }}>{t.range}</span>
              <span className="text-xs" style={{ color: P.textSecondary }}>{t.desc}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

// ── Reports Page ──────────────────────────────────────────────────────────────
function ReportsPage({ connection, lastUpdated }) {
  const [reports, setReports] = useState(null);
  const [reportsError, setReportsError] = useState('');
  const [reportsLoading, setReportsLoading] = useState(true);
  const [reportsLastUpdated, setReportsLastUpdated] = useState(null);
  const [reportPeriod, setReportPeriod] = useState('7d');
  const [periodMenuOpen, setPeriodMenuOpen] = useState(false);
  const periodOptions = [
    ['7d', 'Last 7 days'],
    ['30d', 'Last 30 days'],
    ['term', 'This term'],
    ['custom', 'Custom range'],
  ];
  const reportsTimerRef = useRef(null);

  const loadReports = useCallback(() => {
    clearTimeout(reportsTimerRef.current);
    setReportsError('');
    setReportsLoading(true);
    reportsTimerRef.current = setTimeout(() => {
      setReportsLoading(false);
      setReportsError('Reports could not load. Monthly Trends and Severity Breakdown are unavailable.');
    }, 10000);
    apiFetch(`${BACKEND}/api/counselor/analytics/reports`)
      .then(r => {
        if (!r.ok) throw new Error('Unable to load reports.');
        return r.json();
      })
      .then(data => {
        clearTimeout(reportsTimerRef.current);
        setReportsLoading(false);
        if (data && data.error) {
          console.error('Reports analytics error from backend:', data.error);
          setReportsError('Reports could not load. Monthly Trends and Severity Breakdown are unavailable.');
        } else {
          setReports(data);
          setReportsLastUpdated(new Date());
        }
      })
      .catch((err) => {
        clearTimeout(reportsTimerRef.current);
        setReportsLoading(false);
        console.error('Reports fetch error:', err);
        setReportsError('Reports could not load. Monthly Trends and Severity Breakdown are unavailable.');
      });
  }, []);

  useEffect(() => {
    const initialRequest = setTimeout(loadReports, 0);
    return () => {
      clearTimeout(initialRequest);
      clearTimeout(reportsTimerRef.current);
    };
  }, [loadReports]);

  const trendData = reports?.monthly_reports || [];
  const hasTrendData = trendData.some(m => (m.sessions || 0) + (m.alerts || 0) > 0);

  return (
    <div className="w-full max-w-[1240px]">
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="mb-2 text-xs" style={{ color: P.textMuted }}>Guidance system / Reports</p>
          <h1 className="text-2xl font-bold" style={{ color: P.textPrimary }}>Reports & Analytics</h1>
          <p className="text-sm mt-0.5" style={{ color: P.textSecondary }}>System performance and anxiety detection analytics</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className={`badge ${connection.label === 'Live' ? '' : connection.label === 'Offline' ? 'risk' : 'amb'}`}>
            <i aria-hidden="true" />{connection.label}
          </span>
          {lastUpdated && (
            <span className="mut">
              Updated {lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
          )}
          {reportsLastUpdated && (
            <span className="mut">
              Reports synced {reportsLastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
          )}
          <button type="button" className="btn ghost" onClick={loadReports}>
            Refresh reports
          </button>
        </div>
      </div>
      {reportsError && (
        <div
          className="mb-5 flex flex-col items-start gap-2 rounded-xl p-3 text-xs sm:flex-row sm:items-center sm:justify-between"
          style={{ background: P.amberSoft, border: `1px solid ${P.amber}`, color: P.amber }}
          role="alert"
        >
          <span>{reportsError}</span>
          <button
            type="button"
            disabled={reportsLoading}
            onClick={loadReports}
            className="inline-flex min-h-[44px] w-full flex-shrink-0 items-center justify-center rounded-lg px-3 font-semibold text-white transition-opacity hover:opacity-90 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#5E8FBD] sm:w-auto"
            style={{ background: P.navy }}
          >
            {reportsLoading ? 'Retrying...' : 'Retry'}
          </button>
        </div>
      )}
      <div className="mb-5 flex items-center justify-between gap-3">
        <label htmlFor="report-period" className="text-sm font-semibold" style={{ color: P.textPrimary }}>
          Reporting period
        </label>
        <select
          id="report-period"
          value={reportPeriod}
          onChange={(event) => setReportPeriod(event.target.value)}
          className="report-period-native hidden min-h-[44px] rounded-lg border px-3 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-[#5E8FBD] sm:block"
          style={{ background: P.surface, borderColor: P.border, color: P.textPrimary }}
        >
          {periodOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
        <div className="report-period-mobile relative sm:hidden">
          <button type="button" className="mobile-select-button" onClick={() => setPeriodMenuOpen((open) => !open)} aria-expanded={periodMenuOpen} aria-haspopup="listbox">
            {periodOptions.find(([value]) => value === reportPeriod)?.[1]} <span aria-hidden="true">⌄</span>
          </button>
          {periodMenuOpen && (
            <div className="mobile-select-menu" role="listbox" aria-label="Reporting period">
              {periodOptions.map(([value, label]) => (
                <button type="button" role="option" aria-selected={reportPeriod === value} className={reportPeriod === value ? 'selected' : ''} key={value} onClick={() => { setReportPeriod(value); setPeriodMenuOpen(false); }}>
                  {label}<span>{reportPeriod === value ? '✓' : ''}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
      <div className="grid grid-cols-12 gap-5">
      <Card className="col-span-12 p-5 lg:col-span-6">
        <h3 className="text-sm font-semibold mb-4" style={{ color: P.textPrimary }}>Monthly Trends</h3>
        {reportsLoading ? (
          <ChartSkeleton />
        ) : reportsError ? (
          <ChartErrorState label="Couldn't load Monthly Trends" onRetry={loadReports} />
        ) : !reports ? (
          <ChartEmptyState guidance="Reports appear when sessions are recorded." />
        ) : !hasTrendData ? (
          <ChartEmptyState guidance="Reports appear when sessions are recorded." />
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={trendData}>
              <CartesianGrid strokeDasharray="3 3" stroke={P.border} />
              <XAxis dataKey="month" tick={{ fontSize: 11, fill: P.textSecondary }} />
              <YAxis tick={{ fontSize: 11, fill: P.textSecondary }} allowDecimals={false} />
              <Tooltip />
              <Line type="monotone" dataKey="sessions" stroke={P.navy} strokeWidth={2} dot={{ r: 3 }} />
              <Line type="monotone" dataKey="alerts" stroke={P.red} strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </Card>
      <Card className="col-span-12 p-5 lg:col-span-6">
        <h3 className="text-sm font-semibold mb-4" style={{ color: P.textPrimary }}>Severity Breakdown by Month</h3>
        {reportsLoading ? (
          <ChartSkeleton />
        ) : reportsError ? (
          <ChartErrorState label="Couldn't load Severity Breakdown" onRetry={loadReports} />
        ) : !reports ? (
          <ChartEmptyState guidance="Reports appear when sessions are recorded." />
        ) : !hasTrendData ? (
          <ChartEmptyState guidance="Reports appear when sessions are recorded." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr style={{ borderBottom: `1px solid ${P.border}` }}>
                  <th className="text-left py-2 pr-4 font-semibold" style={{ color: P.textMuted }}>Month</th>
                  <th className="text-right py-2 px-3 font-semibold" style={{ color: P.textMuted }}>Sessions</th>
                  <th className="text-right py-2 px-3 font-semibold" style={{ color: P.textMuted }}>Alerts</th>
                  <th className="text-right py-2 px-3 font-semibold" style={{ color: P.textMuted }}>Normal</th>
                  <th className="text-right py-2 px-3 font-semibold" style={{ color: P.green }}>Low</th>
                  <th className="text-right py-2 px-3 font-semibold" style={{ color: P.teal }}>Moderate</th>
                  <th className="text-right py-2 px-3 font-semibold" style={{ color: P.amber }}>High</th>
                  <th className="text-right py-2 pl-3 font-semibold" style={{ color: P.red }}>Crisis</th>
                </tr>
              </thead>
              <tbody>
                {trendData.map((m, i) => (
                  <tr key={i} style={i < trendData.length - 1 ? { borderBottom: `1px solid ${P.panel}` } : {}}>
                    <td className="py-2 pr-4 font-medium" style={{ color: P.textPrimary }}>{m.month}</td>
                    <td className="py-2 px-3 text-right" style={{ color: P.textSecondary }}>{m.sessions || 0}</td>
                    <td className="py-2 px-3 text-right" style={{ color: P.textSecondary }}>{m.alerts || 0}</td>
                    <td className="py-2 px-3 text-right" style={{ color: P.textSecondary }}>{m.normal || 0}</td>
                    <td className="py-2 px-3 text-right" style={{ color: P.textSecondary }}>{m.low || 0}</td>
                    <td className="py-2 px-3 text-right" style={{ color: P.textSecondary }}>{m.moderate || 0}</td>
                    <td className="py-2 px-3 text-right" style={{ color: P.textSecondary }}>{m.high || 0}</td>
                    <td className="py-2 pl-3 text-right font-semibold" style={{ color: P.textPrimary }}>{m.crisis || 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      </div>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────
export default function CounselorDashboard() {
  const navigate = useNavigate();
  const [dashboardTheme, setDashboardTheme] = useState(() => {
    try { return localStorage.getItem('gaida_counselor_theme') === 'dark' ? 'dark' : 'light'; }
    catch { return 'light'; }
  });

  // ── Auth guard ────────────────────────────────────────────────
  // Unlike StudentDashboard, this component previously had no check at
  // all — anyone could reach /counselor-dashboard directly by URL.
  useEffect(() => {
    const token = localStorage.getItem('counselor_token');
    if (!token) {
      navigate('/counselor-login');
    }
  }, [navigate]);
  const [activePage, setActivePage] = useState('overview');
  const [alerts, setAlerts] = useState([]);
  const [alertsLoading, setAlertsLoading] = useState(true);
  const [alertsError, setAlertsError] = useState(null);
  const [alertsLastSynced, setAlertsLastSynced] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [sessionsError, setSessionsError] = useState(null);
  const [welfare, setWelfare] = useState([]);
  const [welfareLoading, setWelfareLoading] = useState(true);
  const [welfareError, setWelfareError] = useState(null);
  const [dashboardNotice, setDashboardNotice] = useState('');
  const [chatSessionId, setChatSessionId] = useState(null);
  const [logoutConfirmOpen, setLogoutConfirmOpen] = useState(false);
  const [hotlinesOpen, setHotlinesOpen] = useState(false);
  const [chimeFlash, setChimeFlash] = useState(false);
  const chimeTimerRef = useRef(null);
  const hotlinesTriggerRef = useRef(null);
  const logoutTriggerRef = useRef(null);
  // On desktop start with the full panel open so the profile and labels are
  // visible immediately; phones always start with it closed.
  const [expanded, setExpanded] = useState(
    () => {
      if (typeof window === 'undefined') return false;
      try {
        const saved = localStorage.getItem('gaida:counselor-sidebar');
        if (saved === 'collapsed') return false;
        if (saved === 'expanded') return true;
      } catch { /* use the desktop default */ }
      return window.innerWidth >= 1024;
    }
  );
  // Phone-only state for the single combined drawer (profile + navigation).
  // On desktop the same panel is a persistent rail, so `expanded` controls
  // its width; on mobile this controls whether it slides in from the left.
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [drawerMoreOpen, setDrawerMoreOpen] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState('connecting'); // 'live' | 'connecting' | 'polling' | 'offline'
  const prevPendingIdsRef = useRef(new Set());
  // Pending alerts that have already rung the dashboard (everything except Moderate),
  // so a Moderate alert that later turns High still rings once.
  const prevLoudIdsRef = useRef(new Set());
  const alertsRef = useRef(alerts);
  // Drawer a11y refs: remember what opened the overlay, return focus there on
  // close, and lock the real scroll container (not just <body>) while open.
  const mainRef = useRef(null);
  const menuButtonRef = useRef(null);
  const drawerRef = useRef(null);
  const sidebarProfileRef = useRef(null);
  const lastTriggerRef = useRef(null);
  // Mirror latest alerts for the 5-minute reminder check (must happen in an
  // effect — updating a ref during render violates the rules of React).
  useEffect(() => {
    alertsRef.current = alerts;
  }, [alerts]);
  const [lastUpdated, setLastUpdated] = useState(null);

  useEffect(() => {
    try { localStorage.setItem('gaida:counselor-sidebar', expanded ? 'expanded' : 'collapsed'); }
    catch { /* private storage */ }
  }, [expanded]);

  useEffect(() => {
    let timer;
    const onNotice = (event) => {
      setDashboardNotice(String(event.detail || ''));
      clearTimeout(timer);
      timer = setTimeout(() => setDashboardNotice(''), 8000);
    };
    window.addEventListener('gaida:counselor-notice', onNotice);
    return () => {
      clearTimeout(timer);
      window.removeEventListener('gaida:counselor-notice', onNotice);
    };
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.Notification !== 'function' || !window.isSecureContext) return;
    try {
      if (window.Notification.permission === 'default') {
        Promise.resolve(window.Notification.requestPermission()).catch(() => {});
      }
    } catch { /* notifications are optional and may be blocked by the browser */ }
  }, []);

  const fetchAlerts = async () => {
    try {
      const res = await apiFetch(`${BACKEND}/api/counselor/alerts`);
      if (!res.ok) {
        setAlertsError('Unable to load alerts. Retrying...');
        setAlertsLoading(false);
        return;
      }
      const data = await res.json();
      if (data.alerts) {
        setAlertsError(null);
        setAlertsLoading(false);
        setAlertsLastSynced(new Date());
        // Detect NEW pending alerts by ID (count-based logic missed a replaced
        // alert with the same count, and re-beeped every poll because the
        // effect ran on every 2s fetch).
        const pendingNow = data.alerts.filter(a => getAlertStatusLabel(a) === 'New');
        const pendingNowIds = pendingNow.map(a => a.session_id);
        // Moderate alerts are listed silently; only High, Crisis and a student's
        // own counselor request ring the dashboard.
        const loudNow = pendingNow.filter(a => a.severity !== 'Moderate');
        const freshLoud = loudNow.filter(a => !prevLoudIdsRef.current.has(a.session_id));
        if (freshLoud.length > 0) {
          playAlertSound();
          try {
            if (typeof window !== 'undefined' && typeof window.Notification === 'function' && window.isSecureContext && window.Notification.permission === 'granted') {
              new window.Notification('GAIDA Alert', {
                body: `${freshLoud.length} new alert${freshLoud.length > 1 ? 's' : ''} need attention`,
                icon: '/favicon.ico',
              });
            }
          } catch { /* sound and in-app alerts remain available */ }
        }
        prevPendingIdsRef.current = new Set(pendingNowIds);
        prevLoudIdsRef.current = new Set(loudNow.map(a => a.session_id));
        setAlerts(data.alerts);
      }
    } catch (err) {
      console.error('Fetch alerts error:', err);
      setAlertsError('Network error loading alerts. Retrying...');
      setAlertsLoading(false);
    }
  };

  // Every 5 minutes, re-remind with a sound while any pending alert is still
  // urgent or overdue (moved here from AlertsPage so it works on every tab and
  // doesn't double-beep with fetchAlerts above).
  useEffect(() => {
    const check = () => {
      const anyUrgent = alertsRef.current.some(a => {
        if (a.status !== 'pending') return false;
        const esc = getEscalationState(a);
        return esc.level === 'urgent' || esc.level === 'overdue';
      });
      if (anyUrgent) playAlertSound();
    };
    const interval = setInterval(check, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const fetchSessions = async () => {
    setSessionsLoading(true);
    setSessionsError(null);
    try {
      const res = await apiFetch(`${BACKEND}/api/counselor/sessions/active`);
      if (!res.ok) {
        setSessionsError('Unable to load active sessions. Please try again.');
        return;
      }
      const data = await res.json();
      if (data.sessions) setSessions(data.sessions);
      setLastUpdated(new Date());
    } catch {
      setSessionsError('Network error loading active sessions. Please check your connection.');
    } finally {
      setSessionsLoading(false);
    }
  };

  const handleUpdateStatus = async (sessionId, status) => {
    try {
      const res = await apiFetch(`${BACKEND}/api/counselor/alerts/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, status }),
      });
      const data = await res.json().catch(() => ({}));
      // The endpoint can return HTTP 200 with ok:false (e.g. not found, or a
      // High/Crisis alert that needs acknowledging first) — treat both the
      // same instead of silently doing nothing.
      if (!res.ok || data.ok === false) {
        notifyDashboard(data.detail || data.error || 'This alert needs to be acknowledged first.');
        return;
      }
      fetchAlerts();
    } catch (e) {
      console.error('Update alert status error:', e);
      notifyDashboard('Network error updating alert status. Please check your connection.');
    }
  };

  const handleAcknowledge = async (sessionId) => {
    try {
      const res = await apiFetch(`${BACKEND}/api/counselor/alerts/acknowledge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.ok === false) {
        notifyDashboard(data.detail || data.error || 'Could not acknowledge this alert.');
        return false;
      }
      fetchAlerts();
      return true;
    } catch (e) {
      console.error('Acknowledge alert error:', e);
      notifyDashboard('Network error acknowledging alert. Please check your connection.');
      return false;
    }
  };

  const fetchWelfare = async () => {
    setWelfareLoading(true);
    setWelfareError(null);
    try {
      const res = await apiFetch(`${BACKEND}/api/counselor/sessions/welfare`);
      if (!res.ok) throw new Error('Unable to load welfare checks.');
      const data = await res.json();
      if (data.sessions) setWelfare(data.sessions);
    } catch {
      setWelfareError('Could not load welfare checks. Check your connection and retry.');
    } finally {
      setWelfareLoading(false);
    }
  };

  // Realtime push via SSE: the backend broadcasts named events when alerts,
  // active sessions, or welfare checks change, so an open dashboard updates —
  // and beeps/notifies on new alerts — without a reload, even in a background
  // tab (browsers throttle setInterval there but not live network streams).
  // Declared after the fetch* consts so the listeners can reference them
  // (react-hooks/immutability). The 2s poll below is the fallback.
  //
  // Auth here is a short-lived, single-use ticket (POST /events/ticket,
  // normal Authorization header) rather than the long-lived counselor
  // bearer token in the URL — a token in the querystring can sit in
  // server/proxy access logs and browser history for as long as that
  // token stays valid (hours); a ticket is worthless within ~30s.
  // EventSource's built-in auto-reconnect can't fetch a fresh ticket on
  // its own, so reconnection is handled manually below instead.
  useEffect(() => {
    let es = null;
    let retryTimer = null;
    let cancelled = false;

    const connect = async () => {
      if (cancelled) return;
      const token = localStorage.getItem('counselor_token');
      if (!token) return;
      let ticket;
      try {
        const res = await apiFetch(`${BACKEND}/api/counselor/events/ticket`, { method: 'POST' });
        if (!res.ok) throw new Error('ticket request failed');
        ({ ticket } = await res.json());
      } catch {
        setConnectionStatus(navigator.onLine ? 'polling' : 'offline');
        // Backend unreachable / not a counselor anymore — the 2s poll
        // fallback still covers updates; just retry the SSE connection.
        retryTimer = setTimeout(connect, 5000);
        return;
      }
      if (cancelled) return;

      es = new EventSource(`${BACKEND}/api/counselor/events?ticket=${encodeURIComponent(ticket)}`);
      es.addEventListener('alerts', fetchAlerts);
      es.addEventListener('sessions', fetchSessions);
      es.addEventListener('welfare', fetchWelfare);
      es.onopen = () => {
        setConnectionStatus('live');
        fetchAlerts();
        fetchSessions();
        fetchWelfare();
      };
      // A ticket is single-use, so once this connection drops (network
      // blip, server restart, expired ticket) it can't just be retried —
      // close it and fetch a fresh ticket for a new connection.
      es.onerror = () => {
        setConnectionStatus(navigator.onLine ? 'polling' : 'offline');
        es?.close();
        es = null;
        if (!cancelled) retryTimer = setTimeout(connect, 3000);
      };
    };

    const onOffline = () => setConnectionStatus('offline');
    const onOnline = () => {
      setConnectionStatus('connecting');
      connect();
    };
    window.addEventListener('offline', onOffline);
    window.addEventListener('online', onOnline);
    connect();

    return () => {
      cancelled = true;
      window.removeEventListener('offline', onOffline);
      window.removeEventListener('online', onOnline);
      if (retryTimer) clearTimeout(retryTimer);
      if (es) es.close();
    };
  }, []);

  // Poll for alert/session/welfare changes every 30 seconds as a fallback to
  // the SSE push. Placed after the fetch* consts so the effect body never
  // references them before they're initialized (react-hooks/immutability);
  // effects still run in order after mount.
  useEffect(() => {
    if (!shouldPollDashboard(connectionStatus)) return undefined;
    // Initial load + 30s cadence. The first fetch is deferred a tick so the
    // setState inside the fetch* functions doesn't run synchronously in the
    // effect body (react-hooks/set-state-in-effect).
    let cancelled = false;
    const tick = () => {
      if (cancelled) return;
      fetchAlerts();
      fetchSessions();
      fetchWelfare();
    };
    const initial = setTimeout(tick, 0);
    const interval = setInterval(tick, FALLBACK_POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearTimeout(initial);
      clearInterval(interval);
    };
  }, [connectionStatus]);

  const handleMarkWelfareChecked = async (sessionId) => {
    try {
      const res = await apiFetch(`${BACKEND}/api/counselor/sessions/welfare-checked`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId }),
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok && data.ok) {
        setWelfare(prev => prev.filter(w => w.session_id !== sessionId));
      } else {
        notifyDashboard(data.detail || data.error || 'Failed to mark welfare check. Please try again.');
      }
    } catch (err) {
      console.error('Welfare check error:', err);
      notifyDashboard('Network error marking welfare check. Please check your connection.');
    }
  };

  const pendingCount = alerts.filter(isPendingAlert).length;

  const logout = async () => {
    await logoutAndClearAuth();
    navigate('/counselor-login');
  };

  const counselor = JSON.parse(localStorage.getItem('counselorData') || '{}');
  const initials = counselor.name
    ? counselor.name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
    : 'CR';

  // True whenever the combined panel is wide enough to show labels/profile.
  const panelWide = expanded || mobileNavOpen;
  const counselorId = counselor.id || counselor.student_number || 'Faculty';
  const connection = {
    live: { color: P.green, label: 'Live' },
    connecting: { color: P.amber, label: 'Reconnecting' },
    polling: { color: P.amber, label: 'Reconnecting' },
    offline: { color: P.red, label: 'Offline' },
  }[connectionStatus] || { color: P.red, label: 'Offline' };

  const handleTestChime = () => {
    playAlertSound();
    setChimeFlash(true);
    clearTimeout(chimeTimerRef.current);
    chimeTimerRef.current = setTimeout(() => setChimeFlash(false), 650);
  };

  const openHotlines = (event) => {
    hotlinesTriggerRef.current = event.currentTarget;
    setHotlinesOpen(true);
  };

  const openLogoutConfirm = (event) => {
    logoutTriggerRef.current = event.currentTarget;
    setLogoutConfirmOpen(true);
  };

  const toggleDashboardTheme = () => {
    setDashboardTheme((current) => {
      const next = current === 'dark' ? 'light' : 'dark';
      try { localStorage.setItem('gaida_counselor_theme', next); } catch { /* keep this session's selection */ }
      return next;
    });
  };

  const openMobileNav = (trigger) => {
    lastTriggerRef.current = trigger || (typeof document !== 'undefined' ? document.activeElement : null);
    setDrawerMoreOpen(DRAWER_MORE_IDS.includes(activePage));
    setMobileNavOpen(true);
  };

  // The same overlay rules apply at any breakpoint: when the panel is open as
  // an overlay, Escape/backdrop closes it, focus returns to the trigger, and
  // the page behind it cannot scroll. On desktop it is normally a persistent
  // rail, so this state is simply never set.
  const closeMobileNav = useCallback(() => {
    setMobileNavOpen(false);
    // Only hand focus back when an overlay was actually open. On desktop the
    // mobile trigger is hidden, so focusing it would silently lose focus.
    if (!mobileNavOpen) return;
    window.requestAnimationFrame(() => {
      // Prefer the element that opened the drawer, then the mobile trigger,
      // then the sidebar avatar if the viewport crossed into desktop while the
      // drawer was open (the mobile trigger is display:none there).
      const target = [menuButtonRef.current, lastTriggerRef.current, sidebarProfileRef.current]
        .find((el) => el && el.isConnected && el.offsetParent !== null);
      target?.focus?.();
    });
  }, [mobileNavOpen]);

  useEffect(() => {
    if (!mobileNavOpen) return undefined;

    const onKeyDown = (e) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        closeMobileNav();
        return;
      }
      if (e.key !== 'Tab') return;
      const drawer = drawerRef.current;
      const focusable = getFocusableElements(drawer);
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    window.addEventListener('keydown', onKeyDown);

    // <main> is the actual scroll container in this layout, so lock both it and
    // the document (the latter covers iOS rubber-banding / any page-level scroll).
    const main = mainRef.current;
    const prevBodyOverflow = document.body.style.overflow;
    const prevHtmlOverflow = document.documentElement.style.overflow;
    const prevMainOverflow = main ? main.style.overflowY : '';
    document.body.style.overflow = 'hidden';
    document.documentElement.style.overflow = 'hidden';
    if (main) main.style.overflowY = 'hidden';

    return () => {
      window.removeEventListener('keydown', onKeyDown);
      document.body.style.overflow = prevBodyOverflow;
      document.documentElement.style.overflow = prevHtmlOverflow;
      if (main) main.style.overflowY = prevMainOverflow;
    };
  }, [mobileNavOpen, closeMobileNav]);

  // Move keyboard focus into the drawer when it opens. The close button is the
  // first intentional stop; the fallback keeps this working if that control is
  // ever hidden at a breakpoint.
  useEffect(() => {
    if (!mobileNavOpen) return undefined;
    const frame = window.requestAnimationFrame(() => {
      const drawer = drawerRef.current;
      const first = drawer?.querySelector('[data-drawer-initial-focus]')
        || drawer?.querySelector('button, a[href], [tabindex]:not([tabindex="-1"])');
      first?.focus?.();
    });
    return () => window.cancelAnimationFrame(frame);
  }, [mobileNavOpen]);

  return (
    <div data-theme={dashboardTheme} className={`counselor-dashboard h-[100dvh] min-h-0 flex overflow-hidden w-full ${chimeFlash ? 'chime-flash-active' : ''}`} style={{ background: P.bg, color: 'var(--ink)' }}>
      {dashboardNotice && (
        <div role="alert" className="fixed left-1/2 top-4 z-[100] flex w-[min(92vw,42rem)] -translate-x-1/2 items-start justify-between gap-3 rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-950 shadow-lg">
          <span>{dashboardNotice}</span>
          <button type="button" onClick={() => setDashboardNotice('')} className="shrink-0 font-semibold underline">Dismiss</button>
        </div>
      )}
      {/* Single combined panel: on phones this is the profile/utility drawer
          (navigation lives in the bottom bar and its sheet); on desktop it
          stays as the full collapsible navigation rail. */}
      {createPortal(
        <div className="counselor-portal" data-theme={dashboardTheme}>
          {mobileNavOpen && (
            <div
              className="counselor-drawer-backdrop fixed inset-0"
              onPointerDown={closeMobileNav}
              aria-hidden="true"
            />
          )}
          <aside
            ref={drawerRef}
            role={mobileNavOpen ? 'dialog' : undefined}
            aria-modal={mobileNavOpen ? 'true' : undefined}
            aria-label={mobileNavOpen ? 'Counselor navigation' : undefined}
            className={`
              side ${mobileNavOpen ? 'open' : ''} ${panelWide ? 'side-wide' : ''} fixed top-0 left-0 h-full z-[60] flex flex-col shadow-lg transition-all duration-300
              ${mobileNavOpen ? '' : 'lg:z-30'}
              w-[84vw] max-w-[320px] ${expanded ? 'lg:w-64' : 'lg:w-20'}
              ${mobileNavOpen ? 'translate-x-0' : '-translate-x-full'} lg:translate-x-0
            `}
            style={{ background: 'var(--side)', paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
            onClick={(e) => e.stopPropagation()}
          >
        {/* ── Zone 1: profile ───────────────────────────────────────────── */}
        {/* Mobile drawer profile: full name, status dot on the avatar corner,
            and only the counselor ID inside the badge. */}
        <div
          className="counselor-mobile-profile relative flex-shrink-0 px-4 py-4 lg:hidden"
          style={{ borderBottom: `1px solid ${P.navyLight}` }}
        >
          <div className="flex items-start gap-3">
            <div className="relative flex-shrink-0">
              <div
                className="flex h-11 w-11 items-center justify-center rounded-full"
                style={{ background: P.accent, boxShadow: `0 0 0 3px ${P.navyLight}` }}
              >
                <span className="text-xs font-bold text-white">{initials}</span>
              </div>
              <span
                className="absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2"
                style={{ background: connection.color, borderColor: P.navy }}
                title={`Connection: ${connection.label}`}
                aria-label={`Connection: ${connection.label}`}
              />
            </div>

            <div className="min-w-0 flex-1">
              <p className="break-words pr-10 text-sm font-semibold leading-snug text-white">
                {counselor.name || 'Counselor'}
              </p>
              <p className="mt-0.5 text-[11px]" style={{ color: '#8FA3AC' }}>
                Guidance Counselor
              </p>
              <p
                className="counselor-sidebar-id mt-1.5 inline-block max-w-full truncate rounded-full px-2 py-0.5 text-[10px] font-medium"
                style={{ background: 'rgba(255,255,255,0.08)', color: '#BBD6EA' }}
                title={`Workspace ID: ${counselorId}`}
              >
                <FocusTooltip label={`Workspace ID: ${counselorId}`} className="workspace-id-tooltip">ID: {counselorId}</FocusTooltip>
              </p>
            </div>

            {mobileNavOpen && (
              <button
                type="button"
                data-drawer-initial-focus
                onClick={closeMobileNav}
                className="absolute right-3 top-3 flex h-12 w-12 items-center justify-center rounded-lg text-white/70 hover:bg-white/10 hover:text-white focus:outline-none focus:ring-2 focus:ring-[#5E8FBD]"
                title="Close menu"
                aria-label="Close menu"
              >
                <NavIcon id="close" size={18} />
              </button>
            )}
          </div>
        </div>

        {/* Desktop sidebar profile (layout unchanged). */}
        <div
          className="hidden flex-shrink-0 px-3 py-4 lg:block"
          style={{ borderBottom: `1px solid ${P.navyLight}` }}
        >
          <div className={`flex items-start gap-3 ${panelWide ? '' : 'justify-center'}`}>
            <button
              ref={sidebarProfileRef}
              type="button"
              onClick={() => { if (!mobileNavOpen) setExpanded(!expanded); }}
              className="w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0 transition-transform hover:scale-105 active:scale-95 focus:outline-none focus:ring-2 focus:ring-[#5E8FBD]"
              style={{ background: P.accent, boxShadow: `0 0 0 3px ${P.navyLight}` }}
              title={mobileNavOpen ? `${counselor.name || 'Counselor'} — Guidance Counselor` : expanded ? 'Collapse sidebar' : 'Expand sidebar'}
              aria-label={mobileNavOpen ? 'Counselor profile' : 'Toggle sidebar'}
            >
              <span className="text-white text-xs font-bold">{initials}</span>
            </button>

            {panelWide && (
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5">
                  <p
                    className="truncate text-sm font-semibold text-white"
                    title={counselor.name || 'Counselor'}
                  >
                    {counselor.name || 'Counselor'}
                  </p>
                  <span
                    className="h-1.5 w-1.5 flex-shrink-0 rounded-full"
                    style={{ background: connection.color }}
                    title={`Connection: ${connection.label}`}
                    aria-label={`Connection: ${connection.label}`}
                  />
                </div>
                <p
                  className="mt-0.5 truncate text-[11px]"
                  style={{ color: '#8FA3AC' }}
                  title="Guidance Counselor"
                >
                  Guidance Counselor
                </p>
                <p
                  className="counselor-sidebar-id mt-1.5 inline-block max-w-full truncate rounded-full px-2 py-0.5 text-[10px] font-medium"
                  style={{ background: 'rgba(255,255,255,0.08)', color: '#BBD6EA' }}
                >
                  <FocusTooltip label={`Workspace ID: ${counselorId}`} className="workspace-id-tooltip">ID: {counselorId}</FocusTooltip>
                </p>
              </div>
            )}

            {mobileNavOpen && (
              <button
                type="button"
                onClick={closeMobileNav}
                className="-mr-1 mt-0.5 flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-lg text-white/70 hover:bg-white/10 hover:text-white focus:outline-none focus:ring-2 focus:ring-[#5E8FBD]"
                title="Close menu"
                aria-label="Close menu"
              >
                <NavIcon id="close" size={18} />
              </button>
            )}
          </div>
        </div>

        {/* ── Zone 2: navigation (its own scroll area) ──────────────────── */}
        <div
          className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden py-3 pl-2 pr-3 overscroll-contain no-scrollbar"
        >
          {/* Phone drawer navigation: the same four primary destinations as the
              bottom bar, plus the remaining views behind "More". */}
          <nav className="space-y-1 lg:hidden" aria-label="Counselor drawer navigation">
            {DRAWER_PRIMARY_ITEMS.map((item) => {
              const active = activePage === item.id;
              const badgeCount = item.id === 'alerts' ? pendingCount : 0;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => { setActivePage(item.id); closeMobileNav(); }}
                  aria-current={active ? 'page' : undefined}
                  aria-label={item.label}
                  className={`nav ${active ? 'on' : ''} px-3`}
                >
                  <span className="flex h-[18px] w-[18px] flex-shrink-0 items-center justify-center">
                    <NavIcon id={item.id} size={18} />
                  </span>
                  <span className={`${ROW_TEXT} whitespace-nowrap`}>{item.label}</span>
                  {badgeCount > 0 && <span className="cnt">{badgeCount}</span>}
                </button>
              );
            })}

            <button
              type="button"
              onClick={() => setDrawerMoreOpen((open) => !open)}
              aria-expanded={drawerMoreOpen}
              aria-controls="counselor-drawer-more"
              aria-current={DRAWER_MORE_IDS.includes(activePage) ? 'page' : undefined}
              className={`nav ${DRAWER_MORE_IDS.includes(activePage) ? 'on' : ''} px-3`}
            >
              <span className="flex h-[18px] w-[18px] flex-shrink-0 items-center justify-center">
                <NavIcon id="more" size={18} />
              </span>
              <span className={`${ROW_TEXT} whitespace-nowrap`}>More</span>
              <span
                aria-hidden="true"
                className={`text-[11px] transition-transform duration-200 ${drawerMoreOpen ? 'rotate-180' : ''}`}
              >
                ⌄
              </span>
            </button>

            {drawerMoreOpen && (
              <div id="counselor-drawer-more" className="space-y-1">
                {DRAWER_MORE_IDS.map((id) => {
                  const navItem = NAV.find((item) => item.id === id);
                  const active = activePage === id;
                  return (
                    <button
                      key={id}
                      type="button"
                      onClick={() => { setActivePage(id); closeMobileNav(); }}
                      aria-current={active ? 'page' : undefined}
                      aria-label={navItem.label}
                      className={`nav ${active ? 'on' : ''} px-3`}
                    >
                      <span className="flex h-[18px] w-[18px] flex-shrink-0 items-center justify-center">
                        <NavIcon id={id} size={18} />
                      </span>
                      <span className={`${ROW_TEXT} whitespace-nowrap`}>{navItem.label}</span>
                    </button>
                  );
                })}
              </div>
            )}
          </nav>

          <nav className="hidden space-y-3 lg:block" aria-label="Workspace navigation">
            {NAV_GROUPS.map((group, groupIndex) => (
              <div key={group.label} className={!panelWide && groupIndex > 0 ? 'collapsed-sidebar-group-divider' : ''}>
                {panelWide && <p className="grp">{group.label}</p>}
                <div className="space-y-1">
                  {group.ids.map((id) => {
                    const navItem = NAV.find((item) => item.id === id);
                    const active = activePage === id;
                    const badgeCount = id === 'alerts' ? pendingCount : 0;
                    return (
                      <button
                        key={id}
                        type="button"
                        onClick={() => { setActivePage(id); closeMobileNav(); }}
                        title={!panelWide ? navItem.label : undefined}
                        aria-label={navItem.label}
                        aria-current={active ? 'page' : undefined}
                        className={`nav ${active ? 'on' : ''} group relative min-h-[44px] ${panelWide ? 'px-3' : 'justify-center px-0'}`}
                      >
                        <span className="relative flex h-[18px] w-[18px] flex-shrink-0 items-center justify-center">
                          <NavIcon id={id} size={18} />
                        </span>
                        {panelWide && <span className={`${ROW_TEXT} whitespace-nowrap`}>{navItem.label}</span>}
                        {id === 'alerts' && badgeCount > 0 && <span className="cnt">{badgeCount}</span>}
                        {!panelWide && <RowTooltip label={`${navItem.label}${badgeCount > 0 ? ` (${badgeCount})` : ''}`} />}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
            <div>
              {panelWide && <p className="grp">Settings</p>}
              <div className="space-y-1">
                <Link to="/privacy" state={{ from: 'counselor' }} className={`nav ${panelWide ? 'px-3' : 'justify-center px-0'}`} title={!panelWide ? 'Informed Consent' : undefined} aria-label="Informed Consent">
                  <span className="flex h-[18px] w-[18px] items-center justify-center"><NavIcon id="privacy" size={18} /></span>
                  {panelWide && <span className={ROW_TEXT}>Informed Consent</span>}
                  {!panelWide && <RowTooltip label="Informed Consent" />}
                </Link>
                <button type="button" className={`nav ${panelWide ? 'px-3' : 'justify-center px-0'} ${chimeFlash ? 'chime-flash' : ''}`} onClick={handleTestChime} title={!panelWide ? 'Test Alert Chime' : undefined} aria-label="Test Alert Chime">
                  <span className="flex h-[18px] w-[18px] items-center justify-center"><NavIcon id="sound" size={18} /></span>
                  {panelWide && <span className={ROW_TEXT}>Test Alert Chime</span>}
                  {!panelWide && <RowTooltip label="Test Alert Chime" />}
                </button>
              </div>
            </div>
          </nav>
        </div>

        {/* ── Zone 3a: desktop pinned utilities (unchanged) ────────────── */}
        <div
          className="hidden flex-shrink-0 border-t px-2 py-2 lg:block"
          style={{
            borderColor: P.navyLight,
            paddingBottom: 'max(0.5rem, env(safe-area-inset-bottom))',
          }}
        >
          <div className="space-y-0.5">
            <button type="button" className={`hot group relative min-h-[44px] ${panelWide ? 'w-full flex items-center gap-3' : 'collapsed-hotline flex items-center justify-center'} `} onClick={openHotlines} aria-label="Open crisis hotlines" title={!panelWide ? 'Crisis hotlines' : undefined}>
              <NavIcon id="hotline" size={18} />
              {panelWide && <span>Crisis hotlines</span>}
              {!panelWide && <RowTooltip label="Crisis hotlines" />}
            </button>

            {/* Collapse (desktop only) */}
            <button
              type="button"
              onClick={() => setExpanded(!expanded)}
              title={!panelWide ? 'Expand sidebar' : undefined}
              aria-label={panelWide ? 'Collapse sidebar' : 'Expand sidebar'}
              className={`group relative hidden w-full min-h-[44px] items-center rounded-lg py-2.5 transition-colors duration-200 hover:bg-white/[0.06] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#5E8FBD] lg:flex ${
                panelWide ? 'gap-3 px-3' : 'justify-center px-0'
              }`}
              style={{ color: '#93A6AE' }}
            >
              <span
                className="flex h-[18px] w-[18px] flex-shrink-0 items-center justify-center transition-transform duration-300"
                style={{ transform: expanded ? 'none' : 'rotate(180deg)' }}
              >
                <NavIcon id="collapse" size={18} />
              </span>
              {panelWide && <span className={`${ROW_TEXT} whitespace-nowrap`}>Collapse</span>}
              {!panelWide && <RowTooltip label="Expand sidebar" />}
            </button>

            <div className="border-t" style={{ borderColor: P.navyLight }} />

            {/* Logout */}
            <button
              type="button"
              onClick={openLogoutConfirm}
              title={!panelWide ? 'Logout' : undefined}
              aria-label="Logout"
              className={`out group relative flex w-full min-h-[44px] items-center rounded-lg transition-colors duration-200 hover:bg-white/[0.06] focus-visible:ring-2 focus-visible:ring-[#5E8FBD] ${
                panelWide ? 'gap-3 px-3' : 'justify-center px-0'
              }`}
              style={{ color: '#93A6AE' }}
            >
              <span className="flex h-[18px] w-[18px] flex-shrink-0 items-center justify-center">
                <NavIcon id="logout" size={18} />
              </span>
              {panelWide && <span className={`${ROW_TEXT} whitespace-nowrap`}>Logout</span>}
              {!panelWide && <RowTooltip label="Logout" />}
            </button>
          </div>
        </div>

        {/* ── Zone 3b: mobile drawer utilities (pinned to the bottom) ──── */}
        <div
          className="flex-shrink-0 border-t px-3 py-2 lg:hidden"
          style={{
            borderColor: P.navyLight,
            paddingBottom: '0.75rem',
          }}
        >
          <div className="flex flex-col gap-1">
            <button
              type="button"
              className="hot flex h-11 min-h-[44px] w-full items-center gap-3"
              style={{ gap: 12 }}
              onClick={openHotlines}
            >
              <NavIcon id="hotline" size={18} />
              <span>Crisis hotlines</span>
            </button>

            {/* Smaller, quieter utilities. */}
            <button
              type="button"
              onClick={handleTestChime}
              className={`flex min-h-[44px] w-full items-center gap-3 rounded-lg px-2 py-2 text-[14px] transition-colors hover:bg-white/[0.06] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#5E8FBD] ${chimeFlash ? 'chime-flash' : ''}`}
              style={{ color: '#d6e0ea' }}
            >
              <span className="flex h-4 w-4 flex-shrink-0 items-center justify-center">
                <NavIcon id="sound" size={16} />
              </span>
              <span>Test Alert Chime</span>
            </button>

            <button
              type="button"
              onClick={toggleDashboardTheme}
              aria-pressed={dashboardTheme === 'dark'}
              className="nav min-h-[44px] gap-3 px-2 py-2 text-[11px]"
            >
              <span className="flex h-4 w-4 flex-shrink-0 items-center justify-center"><NavIcon id="theme" size={16} /></span>
              <span>Switch to {dashboardTheme === 'dark' ? 'light' : 'dark'} mode</span>
            </button>

            <Link
              to="/privacy"
              state={{ from: 'counselor' }}
              className="flex min-h-[44px] w-full items-center gap-3 rounded-lg px-2 py-2 text-[14px] transition-colors hover:bg-white/[0.06] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#5E8FBD]"
              style={{ color: '#d6e0ea' }}
            >
              <span className="flex h-4 w-4 flex-shrink-0 items-center justify-center">
                <NavIcon id="privacy" size={16} />
              </span>
              <span>Privacy &amp; Consent</span>
            </Link>

            <div className="border-t" style={{ borderColor: P.navyLight }} />

            <button
              type="button"
              onClick={openLogoutConfirm}
              className="out flex min-h-[44px] w-full items-center gap-3 rounded-lg px-2 py-2 text-[13px] font-medium transition-colors hover:bg-white/[0.06] focus-visible:ring-2 focus-visible:ring-[#5E8FBD]"
              style={{ color: '#93A6AE' }}
            >
              <span className="flex h-[18px] w-[18px] flex-shrink-0 items-center justify-center">
                <NavIcon id="logout" size={18} />
              </span>
              <span>Logout</span>
            </button>
          </div>
        </div>
          </aside>
        </div>,
        document.body,
      )}

      <a className="counselor-skip-link" href="#counselor-main">
        Skip to main content
      </a>

      {/* Main content wrapper */}
      <div className={`flex-1 flex flex-col min-w-0 w-full overflow-hidden transition-[margin] duration-300 ${expanded ? 'lg:ml-64' : 'lg:ml-16'}`}>
        {/* Mobile top bar */}
        <div
          className="dashboard-topbar flex lg:hidden items-center justify-between px-3.5 h-14 flex-shrink-0 z-10"
          style={{ background: P.navy, color: '#FFF' }}
        >
          {/* Avatar button opening the profile/utility drawer */}
          <div className="flex items-center gap-2.5">
            <button
              ref={menuButtonRef}
              type="button"
              onClick={(e) => openMobileNav(e.currentTarget)}
              className="w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0 transition-transform active:scale-95 focus:outline-none focus:ring-2 focus:ring-[#5E8FBD]"
              style={{ background: P.accent, boxShadow: `0 0 0 2px ${P.navyLight}` }}
              title="Open profile and utilities"
              aria-label="Open profile and utilities"
              aria-expanded={mobileNavOpen}
            >
              <span className="text-white text-xs font-bold">{initials}</span>
            </button>
            <div className="flex flex-col">
              <span className="text-white font-bold text-sm tracking-wide leading-tight">GAIDA</span>
              <span className="text-[10px] leading-tight" style={{ color: '#8FA3AC' }}>Counselor Portal</span>
            </div>
          </div>

          {/* Connection status badge */}
          <div className="flex items-center gap-2">
            <button ref={hotlinesTriggerRef} type="button" className="counselor-icon-button" onClick={openHotlines} aria-label="Open crisis hotlines">
              <NavIcon id="hotline" size={18} />
            </button>
            <span className={`badge ${connectionStatus === 'live' ? '' : connectionStatus === 'offline' ? 'risk' : 'amb'}`}>
              <i aria-hidden="true" />{connection.label}
            </span>
            {lastUpdated && <span className="counselor-mobile-updated">Updated {lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>}
          </div>
        </div>

        {/* Desktop top bar with realtime status */}
        <div
          className="dashboard-topbar hidden lg:flex items-center justify-between px-6 py-2.5 border-b flex-shrink-0"
          style={{ background: P.surface, borderColor: P.border }}
        >
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold tracking-wider uppercase" style={{ color: P.textMuted }}>
              Counselor Workspace
            </span>
          </div>
          <div className="flex items-center gap-3">
            <button ref={hotlinesTriggerRef} type="button" className="counselor-icon-button" onClick={openHotlines} aria-label="Open crisis hotlines">
              <NavIcon id="hotline" size={18} />
            </button>
            <button type="button" className="theme-toggle" onClick={toggleDashboardTheme} aria-label={`Switch to ${dashboardTheme === 'dark' ? 'light' : 'dark'} mode`} aria-pressed={dashboardTheme === 'dark'}>
              <NavIcon id="theme" size={17} />
              <span>{dashboardTheme === 'dark' ? 'Light mode' : 'Dark mode'}</span>
            </button>
            <span className={`badge ${connectionStatus === 'live' ? '' : connectionStatus === 'offline' ? 'risk' : 'amb'}`}>
              <i aria-hidden="true" />{connection.label}
            </span>
            {lastUpdated && (
              <span className="text-[11px]" style={{ color: P.textMuted }}>
                Updated {lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
              </span>
            )}
          </div>
        </div>

        {/* Scrollable page content - padded at bottom on mobile for fixed bottom nav */}
        <main ref={mainRef} id="counselor-main" tabIndex="-1" className="flex-1 overflow-y-auto pb-[11rem] lg:pb-6 no-scrollbar">
          <div className="w-full max-w-[77.5rem] mx-auto p-3.5 sm:p-6 min-w-0">
            {activePage === 'overview'  && <OverviewPage alerts={alerts} sessions={sessions} alertsLoading={alertsLoading} alertsError={alertsError} onNavigate={setActivePage} onAcknowledge={handleAcknowledge} onViewSession={setChatSessionId} />}
            {activePage === 'alerts'    && <AlertsPage alerts={alerts} alertsLoading={alertsLoading} alertsError={alertsError} alertsLastSynced={alertsLastSynced} onRetryAlerts={fetchAlerts} onViewChat={setChatSessionId} onUpdateStatus={handleUpdateStatus} onAcknowledge={handleAcknowledge} sessions={sessions} theme={dashboardTheme} />}
            {activePage === 'welfare'   && <WelfarePage welfare={welfare} welfareLoading={welfareLoading} welfareError={welfareError} onViewChat={setChatSessionId} onMarkChecked={handleMarkWelfareChecked} onRefresh={fetchWelfare} />}
            {activePage === 'sessions' && (
              <SessionsPage
                sessions={sessions}
                sessionsLoading={sessionsLoading}
                sessionsError={sessionsError}
                onRetrySessions={fetchSessions}
                onViewChat={setChatSessionId}
                lastUpdated={lastUpdated}
              />
            )}
            {activePage === 'detection' && <DetectionPage />}
            {activePage === 'reports'   && <ReportsPage connection={connection} lastUpdated={lastUpdated} />}
            {activePage === 'resolved'  && <ResolvedCasesPage />}
            <p className="safety-note" role="note">A zero count does not confirm safety. Follow your campus emergency procedure.</p>
          </div>
        </main>
      </div>

      {/* Counselor Mobile Bottom Navigation (Canvas Student-inspired) */}
      <CounselorBottomNav
        key={mobileNavOpen ? 'drawer-open' : 'drawer-closed'}
        activePage={activePage}
        setActivePage={setActivePage}
        pendingCount={pendingCount}
        welfareCount={welfare.length}
        sessionsCount={sessions.length}
        drawerOpen={mobileNavOpen}
        theme={dashboardTheme}
      />

      {chatSessionId && (
        <ChatModal
          sessionId={chatSessionId}
          alert={alerts.find((item) => item.session_id === chatSessionId)}
          onAcknowledge={handleAcknowledge}
          onClose={() => setChatSessionId(null)}
        />
      )}
      {logoutConfirmOpen && (
        <ConfirmationDialog
          title="Log out of workspace?"
          description="You’ll be signed out of this counselor account on this device."
          cancelLabel="Keep session"
          confirmLabel="Log out"
          destructive
          returnFocusRef={logoutTriggerRef}
          onCancel={() => setLogoutConfirmOpen(false)}
          onConfirm={() => {
            setLogoutConfirmOpen(false);
            closeMobileNav();
            logout();
          }}
        />
      )}
      {hotlinesOpen && <HotlinesModal onClose={() => setHotlinesOpen(false)} returnFocusRef={hotlinesTriggerRef} />}
    </div>
  );
}

// ── Resolved Cases Page ───────────────────────────────────────────────────────
function ResolvedCasesPage() {
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(null);
  const [deleteCaseTarget, setDeleteCaseTarget] = useState(null);
  const [casesError, setCasesError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [outcomeFilter, setOutcomeFilter] = useState('all');
  const [outcomeMenuOpen, setOutcomeMenuOpen] = useState(false);
  const [casesRequestVersion, setCasesRequestVersion] = useState(0);

  // Re-render every 30s so the relative timestamps stay accurate while this
  // page is left open (e.g. "23h ago" becomes "Yesterday", "6 days ago"
  // becomes a weekday or date). Formatting itself is handled by formatRelative.
  useTimestampTick();

  const handleDelete = async (sessionId, e) => {
    e.stopPropagation();
    setDeleteCaseTarget(sessionId);
  };

  const confirmDeleteCase = async () => {
    const sessionId = deleteCaseTarget;
    setDeleteCaseTarget(null);
    if (!sessionId) return;
    try {
      const res = await apiFetch(`${BACKEND}/api/counselor/sessions/delete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId }),
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok && data.ok) {
        setCases(prev => prev.filter(c => c.session_id !== sessionId));
      } else {
        notifyDashboard(data.detail || data.error || 'Failed to remove case from the list.');
      }
    } catch (err) {
      console.error('Delete failed:', err);
      notifyDashboard('Network error removing case. Please check your connection.');
    }
  };

  const OUTCOME_COLORS = {
    resolved:    { bg: P.greenSoft, color: P.greenDark },
    false_alarm: { bg: P.panel, color: P.textSecondary },
    referred:    { bg: P.accentSoft, color: P.accentDark },
    follow_up:   { bg: P.amberSoft, color: P.amber },
    ongoing:     { bg: P.redSoft, color: P.red },
  };

  const OUTCOME_LABELS = {
    resolved:    'Resolved',
    false_alarm: 'False alarm',
    referred:    'Referred',
    follow_up:   'Follow-up scheduled',
    ongoing:     'Ongoing',
  };

  const retryLoadCases = () => {
    setLoading(true);
    setCasesError('');
    setCasesRequestVersion((version) => version + 1);
  };

  useEffect(() => {
    apiFetch(`${BACKEND}/api/counselor/sessions/resolved`)
      .then(async (r) => {
        const data = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(data.detail || 'Resolved cases are temporarily unavailable.');
        return data;
      })
      .then(data => {
        if (data && data.error) {
          throw new Error(data.error);
        } else if (data.sessions) {
          setCases(data.sessions);
        }
      })
      .catch((err) => {
        console.error('Resolved cases fetch error:', err);
        setCasesError(err.message || 'Unable to load resolved cases right now. Please try again later.');
      })
      .finally(() => setLoading(false));
  }, [casesRequestVersion]);

  const filteredCases = cases.filter(c => {
    const q = searchQuery.toLowerCase().trim();
    const matchQuery = !q ||
      (c.note?.note && c.note.note.toLowerCase().includes(q));
    const matchOutcome = outcomeFilter === 'all' || (c.note?.outcome === outcomeFilter);
    return matchQuery && matchOutcome;
  });

  return (
    <div>
      <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: P.textPrimary }}>Resolved Cases</h1>
          <p className="text-sm mt-0.5" style={{ color: P.textSecondary }}>Closed sessions with case notes and transcripts</p>
        </div>

        {/* Search & Filter Bar */}
        <div className="flex flex-wrap items-center gap-2">
          <label htmlFor="resolved-search-input" className="sr-only">Search cases or notes</label>
          <input
            id="resolved-search-input"
            name="resolved-search-input"
            aria-label="Search cases or notes"
            type="text"
            placeholder="Search cases or notes..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="px-3 py-1.5 text-xs rounded-lg border focus:outline-none w-44 sm:w-56"
            style={{ background: P.surface, borderColor: P.border, color: P.textPrimary }}
          />
          <label htmlFor="resolved-outcome-filter" className="sr-only">Filter cases by outcome</label>
          <select
            id="resolved-outcome-filter"
            name="resolved-outcome-filter"
            aria-label="Filter cases by outcome"
            value={outcomeFilter}
            onChange={(e) => setOutcomeFilter(e.target.value)}
            className="resolved-outcome-native hidden px-2.5 py-1.5 text-xs rounded-lg border focus:outline-none sm:block"
            style={{ background: P.surface, borderColor: P.border, color: P.textPrimary }}
          >
            <option value="all">All Outcomes</option>
            <option value="resolved">Resolved</option>
            <option value="referred">Referred</option>
            <option value="follow_up">Follow-up</option>
            <option value="false_alarm">False alarm</option>
            <option value="ongoing">Ongoing</option>
          </select>
          <div className="resolved-outcome-mobile relative sm:hidden">
            <button type="button" className="mobile-select-button" onClick={() => setOutcomeMenuOpen((open) => !open)} aria-expanded={outcomeMenuOpen} aria-haspopup="listbox">
              {outcomeFilter === 'all' ? 'All Outcomes' : OUTCOME_LABELS[outcomeFilter]} <span aria-hidden="true">⌄</span>
            </button>
            {outcomeMenuOpen && (
              <div className="mobile-select-menu" role="listbox" aria-label="Filter cases by outcome">
                {[['all', 'All Outcomes'], ...Object.entries(OUTCOME_LABELS)].map(([value, label]) => (
                  <button type="button" role="option" aria-selected={outcomeFilter === value} className={outcomeFilter === value ? 'selected' : ''} key={value} onClick={() => { setOutcomeFilter(value); setOutcomeMenuOpen(false); }}>
                    {label}<span>{outcomeFilter === value ? '✓' : ''}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {loading ? (
        <p className="text-xs text-center py-20" style={{ color: P.textMuted }}>Loading...</p>
      ) : casesError ? (
        <div className="counselor-error-state" style={{ color: P.textSecondary }}>
          <p className="text-sm font-medium">Could not load resolved cases.</p>
          <p className="text-xs mt-1 text-red-500">Please try again later.</p>
          <button type="button" className="btn ghost mt-4" onClick={retryLoadCases}>Retry</button>
        </div>
      ) : cases.length === 0 ? (
        <EmptyState icon="✓" title="No resolved cases yet" sub="Sessions marked as resolved will appear here" />
      ) : filteredCases.length === 0 ? (
        <EmptyState icon="🔍" title="No matching cases" sub="Try changing your search or outcome filter" />
      ) : (
        <div className="space-y-3">
          {filteredCases.map((c, i) => {
            const sc = severityColor(c.severity);
            const isOpen = expanded === i;
            const oc = OUTCOME_COLORS[c.note?.outcome];
            return (
              <Card key={i} className="overflow-hidden">
                {/* Case header */}
                <div
                  className="px-4 py-3.5 sm:px-5 sm:py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4 cursor-pointer transition-colors duration-200"
                  onClick={() => setExpanded(isOpen ? null : i)}
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className="text-sm font-semibold truncate" style={{ color: P.textPrimary }}>Resolved session</span>
                      <span className="text-xs px-2 py-0.5 rounded-full font-medium text-white flex-shrink-0" style={{ background: sc.hex }}>{c.severity}</span>
                      {c.note?.outcome && (
                        <span className="text-xs px-2 py-0.5 rounded-full font-medium flex-shrink-0" style={{ background: oc?.bg, color: oc?.color }}>
                          {OUTCOME_LABELS[c.note.outcome]}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 sm:gap-3 flex-wrap text-xs" style={{ color: P.textMuted }}>
                      <span>•</span>
                      <span>{formatRelative(c.timestamp)}</span>
                      <span>•</span>
                      <span>{c.transcript?.length || 0} messages</span>
                    </div>
                  </div>
                  <div className="flex items-center justify-between sm:justify-end gap-2 flex-shrink-0 pt-2 sm:pt-0 border-t sm:border-t-0" style={{ borderColor: P.panel }}>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          downloadSessionPdf(c.session_id);
                        }}
                        className="text-xs px-2.5 py-1 rounded-lg transition-colors duration-200"
                        style={{ background: P.panel, color: P.textSecondary, border: `1px solid ${P.border}` }}
                      >
                        Export PDF
                      </button>
                      <button
                        onClick={(e) => handleDelete(c.session_id, e)}
                        className="text-xs px-2.5 py-1 rounded-lg transition-colors duration-200"
                        style={{ background: P.redSoft, color: P.red, border: `1px solid ${P.redBorder}` }}
                      >
                        Delete
                      </button>
                    </div>

                    <span className="text-sm ml-2" style={{ color: P.textMuted }}>{isOpen ? '▲' : '▼'}</span>
                  </div>
                </div>

                {/* Expanded content */}
                {isOpen && (
                  <div style={{ borderTop: `1px solid ${P.border}` }}>
                    {/* Case note */}
                    {c.note && (
                      <div className="px-5 py-4" style={{ borderBottom: `1px solid ${P.panel}` }}>
                        <p className="text-xs font-semibold mb-1" style={{ color: P.textPrimary }}>Case Note</p>
                        <p className="text-xs leading-relaxed" style={{ color: P.textSecondary }}>{c.note.note || '—'}</p>
                      </div>
                    )}

                    {/* Transcript */}
                    <div className="px-5 py-4 max-h-80 overflow-y-auto space-y-2" style={{ background: P.bg }}>
                      <p className="text-xs font-semibold mb-2" style={{ color: P.textPrimary }}>Transcript</p>
                      {c.transcript?.length === 0 ? (
                        <p className="text-xs" style={{ color: P.textMuted }}>No messages recorded</p>
                      ) : (
                        c.transcript?.map((m, j) => (
                          <div key={j} className={`flex ${m.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                            <div
                              className="max-w-[75%] px-3 py-2 rounded-xl text-xs leading-relaxed break-words [overflow-wrap:anywhere]"
                              style={
                                m.sender === 'user'
                                  ? { background: P.navy, color: '#FFFFFF', borderTopRightRadius: '4px' }
                                  : m.sender === 'counselor'
                                  ? { background: P.accent, color: '#FFFFFF', borderTopLeftRadius: '4px' }
                                  : { background: P.surface, color: P.textPrimary, border: `1px solid ${P.border}`, borderTopLeftRadius: '4px' }
                              }
                            >
                              {m.sender === 'counselor' && <p className="text-xs font-semibold mb-1" style={{ color: '#E3EEF6' }}>Counselor</p>}
                              {m.sender === 'bot' && <p className="text-xs font-semibold mb-1" style={{ color: P.textMuted }}>GAIDA</p>}
                              {m.sender === 'system' && <p className="text-xs font-semibold mb-1" style={{ color: P.textMuted }}>System</p>}
                              <p>{m.message || m.text}</p>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      )}
      {deleteCaseTarget && (
        <ConfirmationDialog
          title="Remove resolved case?"
          description={`Session ${deleteCaseTarget.slice(0, 16)} will be removed from the resolved cases list.`}
          cancelLabel="Keep case"
          confirmLabel="Remove case"
          destructive
          onCancel={() => setDeleteCaseTarget(null)}
          onConfirm={confirmDeleteCase}
        />
      )}
    </div>
  );
}
