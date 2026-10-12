/**
 * usePWA.js
 * ─────────────────────────────────────────────────────────────
 * React hook that handles all PWA logic for GAIDA:
 *   - Service worker registration
 *   - Install prompt (Add to Home Screen)
 *   - Online/offline status
 *
 * Offline messaging is handled at the app level, not by a service worker:
 * messages composed offline go to the durable outbox in offlineQueue.js and
 * are replayed from StudentDashboard on the `online` event. This hook only
 * registers the generated worker and tracks connectivity / install state.
 *
 * History: an earlier version of this hook listened for MESSAGE_QUEUED /
 * QUEUED_MESSAGE_SENT from a hand-written service worker, but that worker was
 * never built (vite.config.js uses the plugin's generateSW worker), so the
 * queue never worked and was removed. The current outbox is that idea done
 * client-side.
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
  // True when a freshly installed worker is waiting to take control — i.e. a
  // new build has been downloaded. We surface a prompt instead of reloading on
  // our own, so a deploy never yanks the page out from under a conversation.
  const [needRefresh, setNeedRefresh] = useState(false);

  const deferredPromptRef = useRef(null);
  const registrationRef = useRef(null);

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

    let cancelled = false;

    // A waiting worker only means "an update is available" when a controller
    // already exists. On the very first install there is no controller and
    // nothing to prompt for.
    const flagUpdateIfWaiting = (registration) => {
      if (!cancelled && registration.waiting && navigator.serviceWorker.controller) {
        setNeedRefresh(true);
      }
    };

    navigator.serviceWorker
      .register("/sw.js", { scope: "/" })
      .then((registration) => {
        if (cancelled) return;
        console.log("[GAIDA PWA] Service worker registered:", registration.scope);
        setSwReady(true);
        registrationRef.current = registration;

        // An update may already have downloaded on a previous load and be
        // sitting in the waiting state.
        flagUpdateIfWaiting(registration);

        registration.addEventListener("updatefound", () => {
          const installing = registration.installing;
          if (!installing) return;
          installing.addEventListener("statechange", () => {
            if (installing.state === "installed") flagUpdateIfWaiting(registration);
          });
        });
      })
      .catch((err) => {
        console.error("[GAIDA PWA] Service worker registration failed:", err);
      });

    return () => { cancelled = true; };
  }, []);

  // ── Re-check for an update on focus ─────────────────────────
  // The browser checks for a new worker on navigation, but an installed PWA
  // that is only backgrounded never navigates and can otherwise stay on a stale
  // build indefinitely. The generated worker does not skipWaiting, so a
  // downloaded update parks in "waiting" until we trigger it (updateApp).
  useEffect(() => {
    const checkForUpdate = () => {
      if (document.visibilityState !== "visible") return;
      registrationRef.current?.update().catch(() => { /* offline — try again later */ });
    };
    window.addEventListener("focus", checkForUpdate);
    document.addEventListener("visibilitychange", checkForUpdate);
    return () => {
      window.removeEventListener("focus", checkForUpdate);
      document.removeEventListener("visibilitychange", checkForUpdate);
    };
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

  // ── Apply an available update ───────────────────────────────
  const updateApp = useCallback(async () => {
    const registration = registrationRef.current;

    let waiting = registration?.waiting;
    if (!waiting && registration) {
      // The new worker may still be installing; nudge it, then re-check.
      try { await registration.update(); } catch { /* offline — reload regardless */ }
      waiting = registration.waiting;
    }

    if (waiting && navigator.serviceWorker.controller) {
      // Reload once the new worker claims this client. Bounded so the tap
      // always does something even if the handoff never lands.
      await new Promise((resolve) => {
        const timer = setTimeout(resolve, 3000);
        navigator.serviceWorker.addEventListener(
          "controllerchange",
          () => { clearTimeout(timer); resolve(); },
          { once: true },
        );
        try { waiting.postMessage({ type: "SKIP_WAITING" }); }
        catch { clearTimeout(timer); resolve(); }
      });
    }

    setNeedRefresh(false);
    window.location.reload();
  }, []);

  const dismissUpdate = useCallback(() => setNeedRefresh(false), []);

  return {
    isOnline,
    isOffline: !isOnline,
    isInstallable,
    isInstalled,
    swReady,
    installApp,
    needRefresh,
    updateApp,
    dismissUpdate,
  };
}
