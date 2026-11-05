export const FALLBACK_POLL_INTERVAL_MS = 30000;

export function shouldPollDashboard(connectionStatus) {
  return connectionStatus !== 'live';
}
