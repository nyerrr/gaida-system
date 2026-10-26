import { useState } from 'react';

const P = {
  navy: '#22303A',
  navyLight: '#33454F',
  surface: '#FFFFFF',
  border: '#DCE7EA',
  panel: '#EEF4F6',
  accent: '#5E8FBD',
  accentSoft: '#DCEAF3',
  red: '#B0472F',
  textPrimary: '#2E3B44',
  textSecondary: '#5C6F78',
  textMuted: '#8FA3AC',
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
}) {
  const [moreMenuOpen, setMoreMenuOpen] = useState(false);

  const isMoreActive =
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
    {
      id: 'welfare',
      label: 'Welfare',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M6 4c0 8 6 14 14 14l1-4-5-2-2 2c-2.5-1.3-4.7-3.5-6-6l2-2-2-5-4 1z" />
        </svg>
      ),
      badge: welfareCount > 0 ? welfareCount : null,
      badgeColor: '#D97706',
    },
  ];

  const SECONDARY_ITEMS = [
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
      label: 'Reports & Analytics',
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
      {moreMenuOpen && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/50 backdrop-blur-xs transition-opacity lg:hidden"
            onClick={() => setMoreMenuOpen(false)}
            aria-hidden="true"
          />

          <div
            className="fixed bottom-0 left-0 right-0 z-50 rounded-t-2xl shadow-2xl p-4 transition-transform lg:hidden"
            style={{
              background: P.surface,
              borderTop: `1px solid ${P.border}`,
              paddingBottom: 'max(env(safe-area-inset-bottom, 0px), 16px)',
            }}
            role="dialog"
            aria-label="Additional Counselor Navigation"
          >
            {/* Sheet Handle */}
            <div className="w-10 h-1 bg-gray-300 rounded-full mx-auto mb-3" />

            <div className="flex items-center justify-between pb-3 mb-3 border-b" style={{ borderColor: P.border }}>
              <span className="text-xs font-bold uppercase tracking-wider" style={{ color: P.textSecondary }}>
                Additional Workspace Views
              </span>
              <button
                onClick={() => setMoreMenuOpen(false)}
                className="flex h-11 w-11 items-center justify-center rounded-lg text-base text-gray-500 hover:bg-gray-100 hover:text-gray-800"
                aria-label="Close menu"
              >
                ✕
              </button>
            </div>

            <div className="space-y-1.5">
              {SECONDARY_ITEMS.map((item) => {
                const active = activePage === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => handleSelectSecondary(item.id)}
                    className="w-full flex items-center gap-3 p-3 rounded-xl text-left transition-colors active:scale-[0.98]"
                    style={{
                      background: active ? P.accentSoft : P.panel,
                      border: `1px solid ${active ? P.accent : 'transparent'}`,
                    }}
                  >
                    <div
                      className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0"
                      style={{
                        background: active ? P.accent : '#FFFFFF',
                        color: active ? '#FFFFFF' : P.textSecondary,
                        border: `1px solid ${P.border}`,
                      }}
                    >
                      {item.icon}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-semibold" style={{ color: active ? P.accentDark : P.textPrimary }}>
                        {item.label}
                      </p>
                      <p className="text-[11px] truncate" style={{ color: P.textSecondary }}>
                        {item.sub}
                      </p>
                    </div>
                    {active && (
                      <span className="text-xs font-bold" style={{ color: P.accentDark }}>
                        ✓
                      </span>
                    )}
                  </button>
                );
              })}
            </div>

          </div>
        </>
      )}

      {/* Fixed Bottom Bar */}
      <nav
        aria-label="Counselor mobile navigation"
        className="fixed bottom-0 left-0 right-0 z-30 lg:hidden flex items-center justify-around shadow-lg"
        style={{
          background: P.navy,
          borderTop: `1px solid ${P.navyLight}`,
          paddingBottom: 'env(safe-area-inset-bottom, 0px)',
          minHeight: '60px',
        }}
      >
        {PRIMARY_ITEMS.map((item) => {
          const active = activePage === item.id;
          return (
            <button
              key={item.id}
              onClick={() => tap(() => handleSelectPrimary(item.id))}
              aria-current={active ? 'page' : undefined}
              className="flex-1 flex flex-col items-center justify-center py-2 px-1 relative transition-transform active:scale-95 touch-manipulation min-h-[54px]"
            >
              {/* Active top indicator line */}
              {active && (
                <span
                  className="absolute top-0 left-1/2 -translate-x-1/2 w-8 h-1 rounded-b-full"
                  style={{ background: P.accent }}
                />
              )}

              <span className="relative flex items-center justify-center">
                <span style={{ color: active ? '#FFFFFF' : P.textMuted }}>
                  {item.icon}
                </span>

                {item.badge !== null && (
                  <span
                    className="absolute -top-1.5 -right-2 min-w-[16px] h-4 px-1 rounded-full text-white flex items-center justify-center font-bold text-[9px] shadow-sm"
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
                style={{ color: active ? '#FFFFFF' : P.textMuted }}
              >
                {item.label}
              </span>
            </button>
          );
        })}

        {/* More button */}
        <button
          onClick={() => tap(() => setMoreMenuOpen(!moreMenuOpen))}
          aria-expanded={moreMenuOpen}
          aria-current={isMoreActive ? 'page' : undefined}
          aria-label={activeSecondary ? `${activeSecondary.label} — open navigation menu` : 'More navigation options'}
          className="flex-1 flex flex-col items-center justify-center py-2 px-1 relative transition-transform active:scale-95 touch-manipulation min-h-[54px]"
        >
          <span className="relative flex items-center justify-center">
            <span style={{ color: isMoreActive ? '#FFFFFF' : P.textMuted }}>
              {activeSecondary ? activeSecondary.icon : (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="1.5" />
                  <circle cx="19" cy="12" r="1.5" />
                  <circle cx="5" cy="12" r="1.5" />
                </svg>
              )}
            </span>
          </span>

          <span
            className={`text-[10px] mt-1 tracking-tight truncate max-w-[64px] ${
              isMoreActive ? 'font-bold text-white' : 'font-medium'
            }`}
            style={{ color: isMoreActive ? '#FFFFFF' : P.textMuted }}
          >
            {activePage === 'detection' ? 'Detection' :
             activePage === 'reports' ? 'Reports' :
             activePage === 'resolved' ? 'Resolved' : 'More'}
          </span>
        </button>
      </nav>
    </>
  );
}
