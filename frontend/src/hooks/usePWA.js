/**
 * usePWA.js
 * ─────────────────────────────────────────────────────────────
 * React hook that handles all PWA logic for GAIDA:
 *   - Service worker registration
 *   - Install prompt (Add to Home Screen)
 *   - Online/offline status
 *
 * There is deliberately no offline message queue here. An earlier version of
 * this hook listened for MESSAGE_QUEUED / QUEUED_MESSAGE_SENT messages from a
 * hand-written service worker and replayed failed sends on reconnect, but that
 * worker was never actually built: vite.config.js leaves `strategies` unset, so
 * vite-plugin-pwa emits its own `generateSW` worker and src/sw.js was dead
 * code. Every message it posted went nowhere, so `queuedCount` was permanently
 * 0 and the queue UI could never render. The listeners are removed rather than
 * re-enabled on purpose — see the note in vite.config.js. The worker itself is
 * recoverable from git history (commit a0e1e9d) if the queue is ever wanted
 * back as a tested feature.
 *
 * Usage:
 *   const { isOnline, isInstallable, installApp } = usePWA();
 * ─────────────────────────────────────────────────────────────
 */

import { useState, useEffect, useCallback, useRef } from "react";

export function usePWA() {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [isInstallable, setIsInstallable] = useState(false);
  // Read the initial standalone-mode check lazily instead of setting state
  // inside the install effect — avoids a synchronous setState-in-effect
  // render cascade, and the first-paint value is identical.
  const [isInstalled, setIsInstalled] = useState(
    () => window.matchMedia("(display-mode: standalone)").matches
  );
  const [swReady, setSwReady] = useState(false);

  const deferredPromptRef = useRef(null);

  // ── Register service worker ─────────────────────────────────
  useEffect(() => {
    if (!("serviceWorker" in navigator)) return;

    // Dev is owned by vite-plugin-pwa, not by this hook, so this is skipped in
    // dev. Two separate reasons, both verified:
    //
    // 1. Registering /sw.js here broke the dev worker. The browser keeps one
    //    registration per scope, so this call *replaced* the plugin's. In dev
    //    there is no /sw.js — Vite's SPA fallback answers that path with
    //    index.html as text/html, which the browser refuses with a
    //    SecurityError, leaving the scope registered but workerless. That threw
    //    twice on every dev page load.
    //
    // 2. The plugin's own dev worker is registered at `dev-sw.js?dev-sw` (not
    //    /sw.js), and the dev server does serve that as real JavaScript. But
    //    the plugin only sends the registration when `injectRegister` is
    //    truthy, and vite.config.js sets it to false to avoid a double
    //    registration in production. So in dev no service worker registers at
    //    all — skipping here removes the error without changing that.
    //
    // Consequence: there is no service worker on localhost, so offline and
    // install behaviour can only be exercised against a real build. To enable
    // the dev worker, `injectRegister` in vite.config.js has to be truthy in
    // serve mode only, which needs the config exported as a function of
    // `command`. Not done here because the dev worker is a stub — it is not
    // worth the config restructuring for a no-op.
    //
    // Production is the opposite case and the reason this hook exists: there is
    // no injected script, workbox emits a real dist/sw.js, and registering it
    // here is what gets the worker installed and kept up to date.
    if (import.meta.env.DEV) return;

    navigator.serviceWorker
      .register("/sw.js", { scope: "/" })
      .then((registration) => {
        console.log("[GAIDA PWA] Service worker registered:", registration.scope);
        setSwReady(true);
      })
      .catch((err) => {
        console.error("[GAIDA PWA] Service worker registration failed:", err);
      });
  }, []);

  // ── Online / Offline status ─────────────────────────────────
  useEffect(() => {
    const handleOnline  = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener("online",  handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      window.removeEventListener("online",  handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  // ── Install prompt ──────────────────────────────────────────
  useEffect(() => {
    const handleBeforeInstallPrompt = (e) => {
      e.preventDefault();
      deferredPromptRef.current = e;
      setIsInstallable(true);
    };

    const handleAppInstalled = () => {
      setIsInstalled(true);
      setIsInstallable(false);
      deferredPromptRef.current = null;
      console.log("[GAIDA PWA] App installed to home screen.");
    };

    window.addEventListener("beforeinstallprompt", handleBeforeInstallPrompt);
    window.addEventListener("appinstalled", handleAppInstalled);

    return () => {
      window.removeEventListener("beforeinstallprompt", handleBeforeInstallPrompt);
      window.removeEventListener("appinstalled", handleAppInstalled);
    };
  }, []);

  // ── Trigger install prompt ──────────────────────────────────
  const installApp = useCallback(async () => {
    if (!deferredPromptRef.current) return false;
    deferredPromptRef.current.prompt();
    const { outcome } = await deferredPromptRef.current.userChoice;
    deferredPromptRef.current = null;
    setIsInstallable(false);
    return outcome === "accepted";
  }, []);

  return {
    isOnline,
    isOffline: !isOnline,
    isInstallable,
    isInstalled,
    swReady,
    installApp,
  };
}
