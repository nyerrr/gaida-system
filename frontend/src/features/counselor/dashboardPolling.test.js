import { describe, expect, it } from 'vitest';
import { FALLBACK_POLL_INTERVAL_MS, shouldPollDashboard } from './dashboardPolling';

describe('counselor dashboard update mode', () => {
  it('prefers SSE and only polls while connecting or disconnected', () => {
    expect(shouldPollDashboard('live')).toBe(false);
    expect(shouldPollDashboard('connecting')).toBe(true);
    expect(shouldPollDashboard('polling')).toBe(true);
    expect(FALLBACK_POLL_INTERVAL_MS).toBeGreaterThanOrEqual(30000);
    expect(FALLBACK_POLL_INTERVAL_MS).toBeLessThanOrEqual(60000);
  });
});
