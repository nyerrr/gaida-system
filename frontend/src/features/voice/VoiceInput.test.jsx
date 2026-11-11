import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

vi.mock('../../api', () => ({ default: vi.fn() }));
import apiFetch from '../../api';

class FakeRecognition {
  static instances = [];
  constructor() { FakeRecognition.instances.push(this); }
  start() {}
  stop() {}
}
class FakeMediaRecorder {
  static instances = [];
  static isTypeSupported() { return true; }
  state = 'inactive';
  constructor() { FakeMediaRecorder.instances.push(this); }
  start() {
    this.state = 'recording';
    this.ondataavailable?.({ data: new Blob(['recorded audio'], { type: 'audio/webm' }) });
  }
  stop() { this.state = 'inactive'; this.onstop?.(); }
}

describe('VoiceInput recognition errors', () => {
  beforeEach(() => vi.clearAllMocks());
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

  it('sends the transcript only after backend voice analysis completes', async () => {
    FakeRecognition.instances = [];
    FakeMediaRecorder.instances = [];
    vi.stubGlobal('SpeechRecognition', FakeRecognition);
    vi.stubGlobal('MediaRecorder', FakeMediaRecorder);
    const track = { stop: vi.fn() };
    const oldMediaDevices = Object.getOwnPropertyDescriptor(navigator, 'mediaDevices');
    const oldCreateObjectURL = Object.getOwnPropertyDescriptor(URL, 'createObjectURL');
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: { getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [track] }) },
    });
    Object.defineProperty(URL, 'createObjectURL', {
      configurable: true,
      value: vi.fn(() => 'blob:recording'),
    });

    let finishRequest;
    apiFetch.mockReturnValue(new Promise(resolve => { finishRequest = resolve; }));
    const onTranscript = vi.fn();

    try {
      const { default: VoiceInput } = await import('./VoiceInput');
      render(<VoiceInput onTranscript={onTranscript} />);
      fireEvent.click(screen.getByRole('button', { name: 'Record voice message' }));
      await screen.findByRole('button', { name: 'Confirm and send voice message' });

      FakeRecognition.instances.at(-1).onresult({
        resultIndex: 0,
        results: [{ 0: { transcript: 'live transcript' }, isFinal: true }],
      });
      fireEvent.click(screen.getByRole('button', { name: 'Confirm and send voice message' }));

      await waitFor(() => expect(apiFetch).toHaveBeenCalled());
      expect(onTranscript).not.toHaveBeenCalled();

      finishRequest({
        ok: true,
        json: async () => ({
          transcript: 'backend transcript',
          acoustic_log_saved: true,
        }),
      });
      await waitFor(() => expect(onTranscript).toHaveBeenCalledWith('backend transcript'));
    } finally {
      if (oldMediaDevices) Object.defineProperty(navigator, 'mediaDevices', oldMediaDevices);
      else delete navigator.mediaDevices;
      if (oldCreateObjectURL) Object.defineProperty(URL, 'createObjectURL', oldCreateObjectURL);
      else delete URL.createObjectURL;
    }
  });

  it('discards a canceled recording without uploading or sending a transcript', async () => {
    FakeRecognition.instances = [];
    FakeMediaRecorder.instances = [];
    vi.stubGlobal('SpeechRecognition', FakeRecognition);
    vi.stubGlobal('MediaRecorder', FakeMediaRecorder);
    const track = { stop: vi.fn() };
    const oldMediaDevices = Object.getOwnPropertyDescriptor(navigator, 'mediaDevices');
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: { getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [track] }) },
    });
    const onTranscript = vi.fn();

    try {
      const { default: VoiceInput } = await import('./VoiceInput');
      render(<VoiceInput onTranscript={onTranscript} />);
      fireEvent.click(screen.getByRole('button', { name: 'Record voice message' }));
      await screen.findByRole('button', { name: 'Confirm and send voice message' });

      const recorder = FakeMediaRecorder.instances.at(-1);
      fireEvent.click(screen.getByRole('button', { name: 'Cancel recording' }));

      recorder.ondataavailable({ data: new Blob(['late audio'], { type: 'audio/webm' }) });
      recorder.onstop();

      expect(apiFetch).not.toHaveBeenCalled();
      expect(onTranscript).not.toHaveBeenCalled();
    } finally {
      if (oldMediaDevices) Object.defineProperty(navigator, 'mediaDevices', oldMediaDevices);
      else delete navigator.mediaDevices;
    }
  });
});
