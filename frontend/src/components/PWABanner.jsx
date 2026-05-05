/**
 * PWABanner.jsx
 * ─────────────────────────────────────────────────────────────
 * Shows:
 *   - "Add to Home Screen" install banner (when installable)
 *   - Offline status bar (when connection is lost)
 *   - Queued messages notice (when messages are pending sync)
 *
 * Usage:
 *   <PWABanner />   ← drop anywhere in your App layout
 * ─────────────────────────────────────────────────────────────
 */

import { useState } from "react";
import { usePWA } from "../hooks/usePWA";

export default function PWABanner({ onQueuedMessageSent }) {
  const {
    isOnline,
    isOffline,
    isInstallable,
    isInstalled,
    installApp,
    queuedCount,
  } = usePWA({ onQueuedMessageSent });

  const [installDismissed, setInstallDismissed] = useState(false);
  const [installing, setInstalling] = useState(false);

  const handleInstall = async () => {
    setInstalling(true);
    await installApp();
    setInstalling(false);
  };

  return (
    <div style={styles.wrapper}>

      {/* ── Offline Bar ──────────────────────────────────────── */}
      {isOffline && (
        <div style={{ ...styles.banner, ...styles.offlineBanner }}>
          <span style={styles.dot} />
          <span style={styles.bannerText}>
            You're offline — past chats are available. Messages will send when you reconnect.
          </span>
          {queuedCount > 0 && (
            <span style={styles.queueBadge}>
              {queuedCount} queued
            </span>
          )}
        </div>
      )}

      {/* ── Back Online + Queue Flushing Notice ──────────────── */}
      {isOnline && queuedCount > 0 && (
        <div style={{ ...styles.banner, ...styles.syncBanner }}>
          <span style={{ ...styles.dot, background: "#7c6af7" }} />
          <span style={styles.bannerText}>
            Sending {queuedCount} queued message{queuedCount > 1 ? "s" : ""}…
          </span>
        </div>
      )}

      {/* ── Install Prompt ────────────────────────────────────── */}
      {isInstallable && !isInstalled && !installDismissed && isOnline && (
        <div style={{ ...styles.banner, ...styles.installBanner }}>
          <div style={styles.installLeft}>
            <span style={styles.installIcon}>💙</span>
            <div>
              <div style={styles.installTitle}>Add GAIDA to your home screen</div>
              <div style={styles.installSub}>Chat anytime, even offline</div>
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
  syncBanner: {
    background: "rgba(20, 16, 45, 0.97)",
    borderBottom: "1px solid rgba(124,106,247,0.3)",
    color: "#c4bbff",
  },
  installBanner: {
    background: "rgba(15, 12, 35, 0.97)",
    borderBottom: "1px solid rgba(124,106,247,0.25)",
    color: "#e8e4ff",
    justifyContent: "space-between",
    padding: "12px 16px",
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
  queueBadge: {
    background: "rgba(244,161,153,0.15)",
    border: "1px solid rgba(244,161,153,0.3)",
    color: "#f4a199",
    borderRadius: "999px",
    padding: "2px 10px",
    fontSize: "0.75rem",
    whiteSpace: "nowrap",
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