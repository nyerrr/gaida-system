import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      // We register the service worker ourselves in src/hooks/usePWA.js.
      // Disabling the injected snippet avoids double registration.
      injectRegister: false,
      manifest: false,
      // NOTE: `strategies` is intentionally left unset, so vite-plugin-pwa uses
      // its default "generateSW" and emits dist/sw.js from workbox. A previous
      // hand-written service worker lived in src/sw.js and assumed the
      // "injectManifest" strategy, which meant it was never built and never ran:
      // its offline message queue, credential stripping, and logout purge were
      // all dead code, and the UI that surfaced them (a queued-message counter in
      // PWABanner) sat permanently at zero. That file has been deleted rather
      // than switched on, because putting a never-executed worker in front of
      // students' messages is a worse trade than having no offline queue.
      //
      // Do NOT set `strategies: 'injectManifest'` to revive it. If the offline
      // queue is wanted as a real feature, recover the worker from commit
      // a0e1e9d, wire up injectManifest, and test it end to end first — in
      // particular that install survives a 404 on any precached URL (it used
      // cache.addAll for the app shell, which fails the whole install).
      workbox: {
        // png is kept deliberately: the self-hosted UE seal + background are
        // the login/portal page's backdrop, so precaching them is what lets the
        // very first (possibly offline) visit paint a complete screen instead
        // of a blank one.
        globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
        // recharts is split into its own chunk by manualChunks below purely so
        // it can be named here. It's the largest dependency in the app and only
        // CounselorDashboard renders charts, so precaching it would have every
        // student and research participant download a charting library on
        // service-worker install for a screen they never open. Excluded from
        // precache; the fetch handler's cacheFirstWithNetwork still caches it
        // normally the first time a counselor loads the dashboard, and because
        // it's same-origin that happens without any change here. The trade-off
        // is deliberate: a counselor on a machine that has never opened the
        // dashboard while offline would get a failed chunk load. Staff
        // workstations have reliable network; students on mobile — who do need
        // the offline chat — keep every chunk they need.
        globIgnores: ['**/recharts-*.js'],
      },
      devOptions: {
        enabled: true,
      },
    }),
  ],
  build: {
    rollupOptions: {
      output: {
        // Split the React runtime into its own long-lived chunk. Without this
        // Rollup folds react + react-dom + the router into the app chunk, so
        // every deploy invalidates ~50 kB of code that never actually changed.
        // (App.jsx additionally lazy-loads each route, which is what moves
        // recharts — counselor-only — out of the initial download entirely.)
        manualChunks: {
          react: ['react', 'react-dom', 'react-router-dom'],
          recharts: ['recharts'],
        },
      },
    },
  },
})