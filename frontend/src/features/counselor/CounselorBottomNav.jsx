import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';

const P = {
  navy: 'var(--side)',
  navyLight: 'var(--line)',
  surface: 'var(--card)',
  border: 'var(--line)',
  panel: 'var(--bg)',
  accent: 'var(--brand)',
  accentSoft: 'color-mix(in srgb, var(--brand) 18%, var(--card))',
  red: 'var(--red)',
  textPrimary: 'var(--ink)',
  textSecondary: 'var(--mut)',
  textMuted: 'var(--mut)',
};

/**
 * Mobile Bottom Navigation for GAIDA Counselor.
 * Follows Canvas Student app bottom-nav pattern:
 * - Fixed bottom position, visible during scrolling
 * - 4 primary items + More menu for secondary sections
 * - Safe area inset padding
 * - Clear active states and badges
 */
export default function CounselorBottomNav({
  activePage,
  setActivePage,
  pendingCount = 0,
  welfareCount = 0,
  sessionsCount = 0,
  drawerOpen = false,
  theme = 'light',
}) {
  const [moreMenuOpen, setMoreMenuOpen] = useState(false);
  const moreTriggerRef = useRef(null);
  const moreSheetRef = useRef(null);

  useEffect(() => {
    if (!moreMenuOpen || drawerOpen) return undefined;
    const trigger = moreTriggerRef.current;
    const frame = window.requestAnimationFrame(() => {
      moreSheetRef.current?.querySelector('[data-more-initial-focus]')?.focus();
    });
    const onKeyDown = (event) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        setMoreMenuOpen(false);
        return;
      }
      if (event.key !== 'Tab') return;
      const elements = [...(moreSheetRef.current?.querySelectorAll('button:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])') || [])];
      const visible = elements.filter((element) => element.getClientRects().length > 0);
      const focusable = visible.length ? visible : elements;
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
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
      window.cancelAnimationFrame(frame);
      document.removeEventListener('keydown', onKeyDown, true);
      if (!drawerOpen && trigger?.isConnected) trigger.focus();
    };
  }, [moreMenuOpen, drawerOpen]);

  // The side drawer is the active navigation surface while it is open; keeping
  // the bottom bar mounted underneath it would leave a second, tappable nav
  // layer at the bottom edge of the screen.
  if (drawerOpen) return null;

  const isMoreActive =
    activePage === 'welfare' ||
    activePage === 'detection' ||
    activePage === 'reports' ||
    activePage === 'resolved';

  const PRIMARY_ITEMS = [
    {
      id: 'overview',
      label: 'Overview',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="3" width="7" height="7" rx="1.5" />
          <rect x="14" y="3" width="7" height="7" rx="1.5" />
          <rect x="3" y="14" width="7" height="7" rx="1.5" />
          <rect x="14" y="14" width="7" height="7" rx="1.5" />
        </svg>
      ),
      badge: null,
    },
    {
      id: 'alerts',
      label: 'Alerts',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 4L3 20h18L12 4z" />
          <path d="M12 10v4" />
          <circle cx="12" cy="17" r="0.5" fill="currentColor" />
        </svg>
      ),
      badge: pendingCount > 0 ? pendingCount : null,
      badgeColor: P.red,
    },
    {
      id: 'sessions',
      label: 'Sessions',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="8" />
          <circle cx="12" cy="12" r="2.5" fill="currentColor" stroke="none" />
        </svg>
      ),
      badge: sessionsCount > 0 ? sessionsCount : null,
      badgeColor: P.accent,
    },
  ];

  const SECONDARY_ITEMS = [
    {
      id: 'welfare',
      label: 'Welfare Checks',
      sub: welfareCount > 0 ? `${welfareCount} checks need attention` : 'Follow-up checks for students',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M6 4c0 8 6 14 14 14l1-4-5-2-2 2c-2.5-1.3-4.7-3.5-6-6l2-2-2-5-4 1z" />
        </svg>
      ),
    },
    {
      id: 'detection',
      label: 'Anxiety Detection',
      sub: 'Multimodal ML thresholds & live classification',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M2 12h4l2 7 3-14 2 9 2-4h7" />
        </svg>
      ),
    },
    {
      id: 'reports',
      label: 'Reports',
      sub: 'Monthly anxiety trends & severity breakdowns',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <line x1="4" y1="7" x2="20" y2="7" />
          <line x1="4" y1="12" x2="20" y2="12" />
          <line x1="4" y1="17" x2="14" y2="17" />
        </svg>
      ),
    },
    {
      id: 'resolved',
      label: 'Resolved Cases',
      sub: 'Case notes, session history & PDF exports',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="9" />
          <path d="M8 12.5l2.5 2.5L16 9.5" />
        </svg>
      ),
    },
  ];

  const activeSecondary =
    SECONDARY_ITEMS.find((item) => item.id === activePage) || null;

  const tap = (callback) => {
    if (navigator.vibrate) navigator.vibrate(8);
    callback();
  };

  const handleSelectPrimary = (id) => {
    setActivePage(id);
    setMoreMenuOpen(false);
  };

  const handleSelectSecondary = (id) => {
    setActivePage(id);
    setMoreMenuOpen(false);
  };

  return (
    <>
      {/* "More" Slide-up Sheet */}
      {moreMenuOpen && createPortal(
        <div className="counselor-portal" data-theme={theme}>
          <div
            className="counselor-sheet-backdrop fixed inset-0"
            onClick={() => setMoreMenuOpen(false)}
            aria-hidden="true"
          />

          <div
            ref={moreSheetRef}
            className="counselor-more-sheet counselor-bottom-sheet fixed bottom-0 left-0 right-0 rounded-t-2xl shadow-2xl transition-transform lg:hidden"
            style={{
              background: P.surface,
              borderTop: `1px solid ${P.border}`,
              paddingBottom: 'max(env(safe-area-inset-bottom, 0px), 16px)',
            }}
            role="dialog"
            aria-label="Additional Counselor Navigation"
            aria-modal="true"
          >
            {/* Sheet Handle */}
            <div className="counselor-more-handle" aria-hidden="true" />

            <div className="counselor-more-header">
              <div className="counselor-more-heading">
                <p className="counselor-sheet-eyebrow">Workspace views</p>
                <h2 className="counselor-sheet-title">Additional workspace views</h2>
              </div>
              <button
                type="button"
                onClick={() => setMoreMenuOpen(false)}
                data-more-initial-focus
                className="counselor-more-close"
                aria-label="Close menu"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
                  <path d="M6 6l12 12M18 6L6 18" />
                </svg>
              </button>
            </div>

            <div className="counselor-more-divider" aria-hidden="true" />

            <div className="counselor-more-list">
              {SECONDARY_ITEMS.map((item) => {
                const active = activePage === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => handleSelectSecondary(item.id)}
                    className={`counselor-more-card${active ? ' is-active' : ''}`}
                    aria-current={active ? 'page' : undefined}
                  >
                    <span className="counselor-more-icon" aria-hidden="true">
                      {item.icon}
                    </span>
                    <span className="counselor-more-text">
                      <span className="counselor-more-label">{item.label}</span>
                      <span className="counselor-more-sub">{item.sub}</span>
                    </span>
                    {item.id === 'welfare' && welfareCount > 0 && (
                      <span className="counselor-sheet-count" aria-label={`${welfareCount} welfare checks`}>
                        {welfareCount}
                      </span>
                    )}
                    {active && (
                      <span className="counselor-sheet-selected" aria-label="Current view">
                        ✓
                      </span>
                    )}
                  </button>
                );
              })}
            </div>

          </div>
        </div>,
        document.body,
      )}

      {/* Fixed Bottom Bar */}
      <nav
        aria-label="Counselor mobile navigation"
        className="tabbar fixed bottom-0 left-0 right-0 z-50 lg:hidden flex items-center justify-around shadow-lg"
        style={{
          background: 'var(--card)',
          borderTop: '1px solid var(--line)',
          paddingBottom: 'env(safe-area-inset-bottom, 0px)',
        }}
      >
        {PRIMARY_ITEMS.map((item) => {
          const active = activePage === item.id;
          return (
            <button
              key={item.id}
              onClick={() => tap(() => handleSelectPrimary(item.id))}
              aria-current={active ? 'page' : undefined}
            className={`flex-1 flex flex-col items-center justify-center py-2 px-1 relative transition-transform active:scale-95 touch-manipulation min-h-[54px] ${active ? 'on' : ''}`}
            >
              <span className="relative flex items-center justify-center">
                <span style={{ color: active ? 'var(--brand)' : 'var(--mut)' }}>
                  {item.icon}
                </span>

                {item.badge !== null && (
                  <span
                    className="cnt absolute -top-1.5 -right-2 min-w-[16px] h-4 px-1 text-white flex items-center justify-center font-bold text-[9px] shadow-sm"
                    style={{ background: item.badgeColor || P.red }}
                  >
                    {item.badge}
                  </span>
                )}
              </span>

              <span
                className={`text-[10px] mt-1 tracking-tight truncate max-w-[64px] ${
                  active ? 'font-bold text-white' : 'font-medium'
                }`}
                style={{ color: active ? 'var(--brand)' : 'var(--mut)' }}
              >
                {item.label}
              </span>
            </button>
          );
        })}

        {/* More button */}
        <button
          ref={moreTriggerRef}
          onClick={() => tap(() => setMoreMenuOpen(!moreMenuOpen))}
          aria-expanded={moreMenuOpen}
          aria-current={isMoreActive ? 'page' : undefined}
          aria-label={activeSecondary ? `${activeSecondary.label} — open navigation menu` : 'More navigation options'}
          className={`flex-1 flex flex-col items-center justify-center py-2 px-1 relative transition-transform active:scale-95 touch-manipulation min-h-[54px] ${isMoreActive ? 'on' : ''}`}
        >
          <span className="relative flex items-center justify-center">
            <span style={{ color: isMoreActive ? 'var(--brand)' : 'var(--mut)' }}>
              {activeSecondary ? activeSecondary.icon : (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="1.5" />
                  <circle cx="19" cy="12" r="1.5" />
                  <circle cx="5" cy="12" r="1.5" />
                </svg>
              )}
            </span>
            {welfareCount > 0 && (
              <span
                className="cnt absolute -top-1.5 -right-2 min-w-[16px] h-4 px-1 text-white flex items-center justify-center font-bold text-[9px] shadow-sm"
                style={{ background: P.red }}
              >
                {welfareCount}
              </span>
            )}
          </span>

          <span
            className={`text-[10px] mt-1 tracking-tight truncate max-w-[64px] ${
              isMoreActive ? 'font-bold text-white' : 'font-medium'
            }`}
            style={{ color: isMoreActive ? 'var(--brand)' : 'var(--mut)' }}
          >
            {activePage === 'welfare' ? 'Welfare' :
             activePage === 'detection' ? 'Detection' :
             activePage === 'reports' ? 'Reports' :
             activePage === 'resolved' ? 'Resolved' : 'More'}
          </span>
        </button>
      </nav>
    </>
  );
}
