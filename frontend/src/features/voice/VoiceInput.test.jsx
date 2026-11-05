import { afterEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';

vi.mock('../../api', () => ({ default: vi.fn() }));

class FakeRecognition {
  static instances = [];
  constructor() { FakeRecognition.instances.push(this); }
  start() {}
  stop() {}
}
class FakeMediaRecorder {
  static isTypeSupported() { return true; }
  state = 'inactive';
  start() { this.state = 'recording'; }
  stop() { this.state = 'inactive'; this.onstop?.(); }
}

describe('VoiceInput recognition errors', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('shows a visible message when live recognition is denied', async () => {
    FakeRecognition.instances = [];
    vi.stubGlobal('SpeechRecognition', FakeRecognition);
    vi.stubGlobal('MediaRecorder', FakeMediaRecorder);
    const track = { stop: vi.fn() };
    const oldMediaDevices = Object.getOwnPropertyDescriptor(navigator, 'mediaDevices');
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: { getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [track] }) },
    });

    try {
      const { default: VoiceInput } = await import('./VoiceInput');
      render(<VoiceInput onTranscript={vi.fn()} />);
      fireEvent.click(screen.getByRole('button', { name: 'Record voice message' }));
      await screen.findByRole('button', { name: 'Confirm and send voice message' });

      FakeRecognition.instances.at(-1).onerror({ error: 'not-allowed' });

      expect(await screen.findByText(/Live transcription permission was denied/)).toBeInTheDocument();
    } finally {
      if (oldMediaDevices) Object.defineProperty(navigator, 'mediaDevices', oldMediaDevices);
      else delete navigator.mediaDevices;
    }
  });
});
