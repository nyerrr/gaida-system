import { describe, expect, it, vi } from 'vitest';
import { stopRecorderIfActive } from './voiceRecorder';

describe('voice recorder cleanup', () => {
  it('safely accepts a missing recorder', () => {
    expect(() => stopRecorderIfActive(null)).not.toThrow();
  });

  it('stops an active recorder and ignores an inactive recorder', () => {
    const active = { state: 'recording', stop: vi.fn() };
    const inactive = { state: 'inactive', stop: vi.fn() };
    stopRecorderIfActive(active);
    stopRecorderIfActive(inactive);
    expect(active.stop).toHaveBeenCalledOnce();
    expect(inactive.stop).not.toHaveBeenCalled();
  });
});
