/**
 * PWABanner.jsx
 * ─────────────────────────────────────────────────────────────
 * Shows, stacked at the very top of the app:
 *   - Update prompt, when a new build has downloaded and is waiting (usePWA)
 *   - Offline status bar, with the count of messages waiting to send
 *   - "Add to Home Screen" install banner (when installable)
 *
 * Usage:
 *   <PWABanner />   ← drop anywhere in your App layout
 * ─────────────────────────────────────────────────────────────
 */

import { useState, useEffect } from "react";
import { usePWA } from '../hooks/usePWA';
import { subscribe as subscribeOfflineQueue } from '../offlineQueue';

export default function PWABanner() {
  const {
    isOnline,
    isOffline,
    isInstallable,
    isInstalled,
    installApp,
    needRefresh,
    updateApp,
    dismissUpdate,
  } = usePWA();

  const [installDismissed, setInstallDismissed] = useState(false);
  const [installing, setInstalling] = useState(false);
  const [queuedCount, setQueuedCount] = useState(0);

  // Number of messages written offline that are still waiting to send.
  useEffect(() => subscribeOfflineQueue(setQueuedCount), []);

  const handleInstall = async () => {
    setInstalling(true);
    try {
      await installApp();
    } catch { /* prompt rejected or unavailable — just stop the spinner */ } finally {
      setInstalling(false);
    }
  };

  return (
    <div style={styles.wrapper}>

      {/* ── Offline Bar ──────────────────────────────────────── */}
      {isOffline && (
        <div style={{ ...styles.banner, ...styles.offlineBanner }} role="status">
          <span style={styles.dot} />
          <span style={styles.bannerText}>
            You're offline. Messages you write are saved and will send when you reconnect
            {queuedCount > 0 ? ` (${queuedCount} waiting to send)` : ''}.
            {' '}If this is an emergency, call 1553 (NCMH) or 911.
          </span>
        </div>
      )}

      {/* ── Update Prompt ────────────────────────────────────── */}
      {needRefresh && (
        <div style={{ ...styles.banner, ...styles.updateBanner }} role="status">
          <span style={styles.updateIcon}>✨</span>
          <span style={styles.bannerText}>A new version of GAIDA is available.</span>
          <div style={styles.installActions}>
            <button
              style={styles.dismissBtn}
              onClick={dismissUpdate}
              aria-label="Remind me later"
            >
              Later
            </button>
            <button
              style={styles.installBtn}
              onClick={updateApp}
              aria-label="Refresh to update GAIDA"
            >
              Refresh
            </button>
          </div>
        </div>
      )}

      {/* ── Install Prompt ────────────────────────────────────── */}
      {isInstallable && !isInstalled && !installDismissed && isOnline && (
        <div style={{ ...styles.banner, ...styles.installBanner }}>
          <div style={styles.installLeft}>
            <span style={styles.installIcon}>💙</span>
            <div>
              <div style={styles.installTitle}>Add GAIDA to your home screen</div>
              <div style={styles.installSub}>Install for quick and easy access</div>
            </div>
          </div>
          <div style={styles.installActions}>
            <button
              style={styles.dismissBtn}
              onClick={() => setInstallDismissed(true)}
              aria-label="Dismiss install prompt"
            >
              Not now
            </button>
            <button
              style={styles.installBtn}
              onClick={handleInstall}
              disabled={installing}
            >
              {installing ? "Installing…" : "Install"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Styles ────────────────────────────────────────────────────
const styles = {
  wrapper: {
    position: "fixed",
    top: 0,
    left: 0,
    right: 0,
    zIndex: 9999,
    display: "flex",
    flexDirection: "column",
    gap: "2px",
    pointerEvents: "none",
  },
  banner: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
    padding: "10px 16px",
    fontSize: "0.82rem",
    pointerEvents: "all",
    backdropFilter: "blur(8px)",
  },
  offlineBanner: {
    background: "rgba(30, 25, 55, 0.97)",
    borderBottom: "1px solid rgba(255,100,80,0.25)",
    color: "#f4a199",
  },
  installBanner: {
    background: "rgba(15, 12, 35, 0.97)",
    borderBottom: "1px solid rgba(124,106,247,0.25)",
    color: "#e8e4ff",
    justifyContent: "space-between",
    padding: "12px 16px",
  },
  updateBanner: {
    background: "rgba(15, 12, 35, 0.97)",
    borderBottom: "1px solid rgba(124,106,247,0.35)",
    color: "#e8e4ff",
    justifyContent: "space-between",
  },
  updateIcon: {
    fontSize: "1.05rem",
    lineHeight: 1,
    flexShrink: 0,
  },
  dot: {
    width: "7px",
    height: "7px",
    borderRadius: "50%",
    background: "#f4a199",
    flexShrink: 0,
  },
  bannerText: {
    flex: 1,
    lineHeight: 1.4,
  },
  installLeft: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
  },
  installIcon: {
    fontSize: "1.4rem",
    lineHeight: 1,
  },
  installTitle: {
    fontWeight: 600,
    fontSize: "0.85rem",
    color: "#e8e4ff",
  },
  installSub: {
    fontSize: "0.75rem",
    color: "#8b82c0",
    marginTop: "2px",
  },
  installActions: {
    display: "flex",
    gap: "8px",
    alignItems: "center",
    flexShrink: 0,
  },
  dismissBtn: {
    background: "transparent",
    border: "none",
    color: "#8b82c0",
    fontSize: "0.8rem",
    cursor: "pointer",
    padding: "6px 10px",
    borderRadius: "6px",
  },
  installBtn: {
    background: "linear-gradient(135deg, #7c6af7, #5b4fcf)",
    border: "none",
    color: "#fff",
    fontSize: "0.82rem",
    fontWeight: 600,
    cursor: "pointer",
    padding: "7px 18px",
    borderRadius: "8px",
    transition: "opacity 0.2s",
  },
};