import { useEffect, useRef } from 'react';

// Palette matching GAIDA Counselor workspace
const P = {
  surface: '#FFFFFF',
  panel: '#EEF4F6',
  border: '#DCE7EA',
  navy: '#22303A',
  navyLight: '#33454F',
  accent: '#5E8FBD',
  accentDark: '#4A7699',
  accentSoft: '#DCEAF3',
  green: '#6BA187',
  greenDark: '#54896D',
  greenSoft: '#E2F0E4',
  amber: '#C98B3D',
  amberSoft: '#F5E9D6',
  red: '#B0472F',
  redSoft: '#FBEDEA',
  redBorder: '#F0D2CA',
  textPrimary: '#2E3B44',
  textSecondary: '#5C6F78',
  textMuted: '#95A6AC',
};

/**
 * Canvas-inspired Counselor Profile / Account Drawer.
 * Slides out from the left when the user clicks their avatar.
 * Displays user identity, status, audio alert test, hotlines, and logout.
 */
export default function CounselorAccountDrawer({
  isOpen,
  onClose,
  counselor,
  initials,
  connectionStatus,
  pendingCount = 0,
  onLogout,
  onPlayTestSound,
}) {
  const closeBtnRef = useRef(null);
  const drawerRef = useRef(null);

  // Close on Escape key press
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    // Autofocus close button when drawer opens
    const timer = setTimeout(() => closeBtnRef.current?.focus(), 50);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      clearTimeout(timer);
    };
  }, [isOpen, onClose]);

  // Trap body scroll when drawer is open on mobile
  useEffect(() => {
    if (isOpen) {
      const originalOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      return () => {
        document.body.style.overflow = originalOverflow;
      };
    }
  }, [isOpen]);

  const requestNotification = async () => {
    if ('Notification' in window && Notification.permission !== 'granted') {
      await Notification.requestPermission();
    }
  };

  const notificationStatus = typeof Notification !== 'undefined' ? Notification.permission : 'unsupported';

  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed inset-0 z-40 transition-opacity duration-300 ${
          isOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        }`}
        style={{ background: 'rgba(34, 48, 58, 0.45)', backdropFilter: 'blur(2px)' }}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Slide-out Drawer */}
      <div
        ref={drawerRef}
        role="dialog"
        aria-modal="true"
        aria-label="Counselor Account Menu"
        className={`fixed inset-y-0 left-0 z-50 w-[84vw] sm:w-96 max-w-[85vw] flex flex-col shadow-2xl transition-transform duration-300 ease-in-out ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
        style={{ background: P.surface, borderRight: `1px solid ${P.border}` }}
      >
        {/* Header */}
        <div
          className="h-16 px-5 flex items-center justify-between flex-shrink-0"
          style={{ background: P.navy, borderBottom: `1px solid ${P.navyLight}` }}
        >
          <div className="flex items-center gap-2.5">
            <div
              className="w-2.5 h-2.5 rounded-full"
              style={{
                background:
                  connectionStatus === 'live' ? P.green :
                  connectionStatus === 'connecting' ? '#A5B4FC' :
                  connectionStatus === 'polling' ? P.amber : P.red,
              }}
            />
            <span className="text-white text-sm font-semibold tracking-wide">Counselor Profile</span>
          </div>

          <button
            ref={closeBtnRef}
            onClick={onClose}
            aria-label="Close account menu"
            className="w-8 h-8 rounded-lg flex items-center justify-center text-white/70 hover:text-white hover:bg-white/10 transition-colors focus:outline-none focus:ring-2 focus:ring-[#5E8FBD]"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto px-5 py-6 space-y-6">
          {/* Identity Card */}
          <div className="flex flex-col items-center text-center pb-5" style={{ borderBottom: `1px solid ${P.border}` }}>
            <div className="relative mb-3">
              <div
                className="w-20 h-20 rounded-full flex items-center justify-center shadow-md text-white text-2xl font-bold"
                style={{ background: P.accent, boxShadow: `0 0 0 4px ${P.accentSoft}` }}
              >
                {initials}
              </div>
              <div
                className="absolute bottom-0 right-0 w-5 h-5 rounded-full border-2 border-white flex items-center justify-center"
                style={{
                  background:
                    connectionStatus === 'live' ? P.green :
                    connectionStatus === 'connecting' ? '#818CF8' :
                    connectionStatus === 'polling' ? P.amber : P.red,
                }}
                title={`Status: ${connectionStatus}`}
              />
            </div>

            <h2 className="text-base font-bold" style={{ color: P.textPrimary }}>
              {counselor?.name || 'Guidance Counselor'}
            </h2>
            <p className="text-xs mt-0.5" style={{ color: P.textSecondary }}>
              University of the East • Guidance Office
            </p>

            <div className="mt-3 flex flex-wrap items-center justify-center gap-1.5">
              <span
                className="text-[11px] px-2.5 py-0.5 rounded-full font-medium"
                style={{ background: P.accentSoft, color: P.accentDark }}
              >
                ID: {counselor?.id || counselor?.student_number || 'Faculty'}
              </span>
              <span
                className="text-[11px] px-2.5 py-0.5 rounded-full font-medium"
                style={{ background: P.greenSoft, color: P.greenDark }}
              >
                Authorized Counselor
              </span>
            </div>
          </div>

          {/* Quick Metrics / System State */}
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: P.textMuted }}>
              Session & Alert Status
            </p>
            <div className="grid grid-cols-2 gap-2">
              <div className="p-3 rounded-xl" style={{ background: P.panel, border: `1px solid ${P.border}` }}>
                <p className="text-[11px]" style={{ color: P.textSecondary }}>Connection</p>
                <p className="text-xs font-bold capitalize mt-0.5" style={{ color: P.textPrimary }}>
                  {connectionStatus === 'live' ? 'Realtime (SSE)' :
                   connectionStatus === 'connecting' ? 'Connecting...' :
                   connectionStatus === 'polling' ? 'Polling (2s)' : 'Offline'}
                </p>
              </div>
              <div className="p-3 rounded-xl" style={{ background: pendingCount > 0 ? P.redSoft : P.panel, border: `1px solid ${pendingCount > 0 ? P.redBorder : P.border}` }}>
                <p className="text-[11px]" style={{ color: pendingCount > 0 ? P.red : P.textSecondary }}>Pending Alerts</p>
                <p className="text-xs font-bold mt-0.5" style={{ color: pendingCount > 0 ? P.red : P.textPrimary }}>
                  {pendingCount} {pendingCount === 1 ? 'alert' : 'alerts'}
                </p>
              </div>
            </div>
          </div>

          {/* Preferences & Quick Tools */}
          <div className="space-y-3">
            <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: P.textMuted }}>
              Counselor Controls
            </p>

            {/* Test Alert Sound */}
            <button
              type="button"
              onClick={onPlayTestSound}
              className="w-full flex items-center justify-between p-3 rounded-xl transition-colors duration-200 text-left hover:opacity-95"
              style={{ background: P.panel, border: `1px solid ${P.border}` }}
            >
              <div className="flex items-center gap-2.5">
                <div
                  className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                  style={{ background: P.accentSoft, color: P.accentDark }}
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
                  </svg>
                </div>
                <div>
                  <p className="text-xs font-semibold" style={{ color: P.textPrimary }}>Test Alert Chime</p>
                  <p className="text-[11px]" style={{ color: P.textMuted }}>Verify speaker output for urgent alerts</p>
                </div>
              </div>
              <span className="text-xs font-medium px-2 py-1 rounded" style={{ background: P.surface, color: P.accentDark }}>
                Play
              </span>
            </button>

            {/* Push Notifications */}
            {notificationStatus !== 'granted' && notificationStatus !== 'unsupported' && (
              <button
                type="button"
                onClick={requestNotification}
                className="w-full flex items-center justify-between p-3 rounded-xl transition-colors duration-200 text-left hover:opacity-95"
                style={{ background: P.panel, border: `1px solid ${P.border}` }}
              >
                <div className="flex items-center gap-2.5">
                  <div
                    className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                    style={{ background: P.amberSoft, color: P.amber }}
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-xs font-semibold" style={{ color: P.textPrimary }}>Enable System Alerts</p>
                    <p className="text-[11px]" style={{ color: P.textMuted }}>Allow desktop browser notifications</p>
                  </div>
                </div>
                <span className="text-xs font-medium px-2 py-1 rounded" style={{ background: P.accent, color: '#FFF' }}>
                  Enable
                </span>
              </button>
            )}
          </div>

          {/* Emergency Hotlines Reference */}
          <div className="p-3.5 rounded-xl space-y-2.5" style={{ background: P.redSoft, border: `1px solid ${P.redBorder}` }}>
            <div className="flex items-center gap-2">
              <svg className="w-4 h-4 flex-shrink-0" style={{ color: P.red }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <p className="text-xs font-bold" style={{ color: P.red }}>Emergency Escalation Hotlines</p>
            </div>
            <div className="text-[11px] space-y-1" style={{ color: '#7E2F1C' }}>
              <p><span className="font-semibold">NCMH Crisis Hotline:</span> 1553 (0917-899-8727)</p>
              <p><span className="font-semibold">Hopeline Philippines:</span> (02) 8804-4673</p>
              <p><span className="font-semibold">UE Guidance Office:</span> guidance@ue.edu.ph</p>
            </div>
          </div>

          {/* Policy Links */}
          <div className="pt-2 border-t" style={{ borderColor: P.border }}>
            <a
              href="/privacy"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-between text-xs py-1.5 hover:underline"
              style={{ color: P.textSecondary }}
            >
              <span>Informed Consent & Privacy Policy</span>
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </a>
          </div>
        </div>

        {/* Footer with Logout */}
        <div
          className="p-4 flex-shrink-0"
          style={{ background: P.panel, borderTop: `1px solid ${P.border}` }}
        >
          <button
            type="button"
            onClick={onLogout}
            className="w-full py-2.5 px-4 rounded-xl font-semibold text-xs transition-colors flex items-center justify-center gap-2 shadow-xs"
            style={{
              background: P.red,
              color: '#FFFFFF',
            }}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            Log Out of Counselor Workspace
          </button>
        </div>
      </div>
    </>
  );
}
