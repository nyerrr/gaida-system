// If VITE_BACKEND_URL isn't set, fall back to whatever host the page itself
// was loaded from (same hostname, port 8000). That makes local LAN testing
// from a phone work automatically.
export const BACKEND_URL =
  import.meta.env.VITE_BACKEND_URL || `http://${window.location.hostname}:8000`