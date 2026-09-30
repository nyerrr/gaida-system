import { useState, useRef, useEffect } from "react";

import { BACKEND_URL } from '../../config';
import apiFetch from '../../api';

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const hasSpeechRecognition = !!SpeechRecognition;

export default function VoiceInput({ onTranscript, sessionId, onStatusChange, disabled }) {
  const [recording, setRecording] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [liveTranscript, setLiveTranscript] = useState("");
  const [audioURL, setAudioURL] = useState(null);   // playback URL
  const [playing, setPlaying] = useState(false);    // is audio playing

  const recognitionRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const finalTranscriptRef = useRef("");
  const streamRef = useRef(null);
  const audioRef = useRef(null);  // audio element for playback
  const sentRef = useRef(false);  // whether a transcript was already sent for this recording
  const maxRecordTimerRef = useRef(null);

  const pushStatus = (text) => onStatusChange?.(text);

  // Revoke the generated object URL whenever it changes (and on unmount).
  // audioURL is a dep so the cleanup sees the *current* URL — with `[]` the
  // closure would capture the initial null and never revoke anything.
  useEffect(() => {
    return () => {
      clearTimeout(maxRecordTimerRef.current);
      stopAll();
      if (audioURL) URL.revokeObjectURL(audioURL);
    };
  }, [audioURL]);

  const stopAll = () => {
    clearTimeout(maxRecordTimerRef.current);
    try { recognitionRef.current?.stop(); } catch (e) { void e; }
    if (mediaRecorderRef.current?.state !== "inactive") {
      try { mediaRecorderRef.current?.stop(); } catch (e) { void e; }
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }
  };

  // ── Cancel — discard everything including playback ────────────────────────
  const handleCancel = () => {
    clearTimeout(maxRecordTimerRef.current);
    chunksRef.current = [];
    stopAll();
    setRecording(false);
    setLiveTranscript("");
    finalTranscriptRef.current = "";
    sentRef.current = false;
    pushStatus("");
    setError(null);
    // Clear playback
    if (audioRef.current) audioRef.current.pause();
    if (audioURL) URL.revokeObjectURL(audioURL);
    setAudioURL(null);
    setPlaying(false);
  };

  // ── Confirm — send immediately, process audio in the background ──────────
  const handleConfirm = () => {
    clearTimeout(maxRecordTimerRef.current);
    try { recognitionRef.current?.stop(); } catch (e) { void e; }

    const text = finalTranscriptRef.current.trim() || liveTranscript.trim();
    if (text) {
      sentRef.current = true;
      setRecording(false);
      setLiveTranscript("");
      finalTranscriptRef.current = "";
      pushStatus("");
      onTranscript?.(text);
    }

    if (mediaRecorderRef.current?.state !== "inactive") {
      mediaRecorderRef.current.stop();
    } else if (!text) {
      setError("No speech detected. Try again.");
      setRecording(false);
      pushStatus("");
    }
  };

  // ── Start recording ───────────────────────────────────────────────────────
  const handleStart = async () => {
    if (disabled) return; // low-bandwidth / offline fallback keeps text-only interaction
    clearTimeout(maxRecordTimerRef.current);
    setError(null);
    setLiveTranscript("");
    finalTranscriptRef.current = "";
    sentRef.current = false;
    chunksRef.current = [];
    // Clear previous playback when starting new recording
    if (audioRef.current) audioRef.current.pause();
    if (audioURL) URL.revokeObjectURL(audioURL);
    setAudioURL(null);
    setPlaying(false);

    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
    } catch {
      setError("Mic access denied. Allow microphone in browser settings.");
      return;
    }

    try {
      // Pick the first mimeType this browser's MediaRecorder actually supports.
      // Android Chrome/Firefox support audio/webm; iOS Safari (14.3+, including
      // the installed PWA on iPhone) only supports audio/mp4 — it does NOT
      // support webm or ogg, so a webm/ogg-only fallback throws on iOS and
      // recording silently fails there. Falling through to "" lets the
      // browser pick its own default rather than throwing.
      const MIME_CANDIDATES = [
        "audio/webm;codecs=opus",
        "audio/webm",
        "audio/mp4",
        "audio/mp4;codecs=mp4a.40.2",
        "audio/aac",
        "audio/ogg",
      ];
      const mimeType = MIME_CANDIDATES.find(t => window.MediaRecorder?.isTypeSupported?.(t)) || "";
      const mediaRecorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream); // let the browser pick a default as a last resort
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        clearTimeout(maxRecordTimerRef.current);
        stream.getTracks().forEach(t => t.stop());
        streamRef.current = null;

        if (chunksRef.current.length > 0) {
          // Create local playback URL from recorded chunks
          const mimeType = chunksRef.current[0]?.type || "audio/webm";
          const blob = new Blob(chunksRef.current, { type: mimeType });
          const url = URL.createObjectURL(blob);
          setAudioURL(url);

          // Send to backend for acoustic extraction + transcription
          await extractAcousticsAndSetTranscript();
        }
      };

      mediaRecorder.start();
      // Guard against runaway background recordings: stop and submit automatically after 60s
      maxRecordTimerRef.current = setTimeout(() => {
        if (mediaRecorderRef.current?.state === "recording") {
          handleConfirm();
        }
      }, 60000);
    } catch {
      clearTimeout(maxRecordTimerRef.current);
      setError("Recording failed. Try again.");
      stream.getTracks().forEach(t => t.stop());
      return;
    }

    // Web Speech API for live transcript preview
    if (hasSpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognitionRef.current = recognition;
      recognition.lang = "fil-PH";
      recognition.interimResults = true;
      recognition.continuous = true;
      recognition.maxAlternatives = 1;

      recognition.onresult = (event) => {
        let interim = "";
        let final = finalTranscriptRef.current;
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const t = event.results[i][0].transcript;
          if (event.results[i].isFinal) final += t;
          else interim = t;
        }
        finalTranscriptRef.current = final;
        setLiveTranscript(final || interim);
        pushStatus(final || interim || "Listening...");
      };

      recognition.onerror = () => {};
      try { recognition.start(); } catch { /* already started or recognition unavailable */ }
    }

    setRecording(true);
    pushStatus("Listening...");
  };

  // ── Send audio to backend ─────────────────────────────────────────────────
  const extractAcousticsAndSetTranscript = async () => {
    setLoading(true);
    pushStatus("Extracting voice features...");

    try {
      const mimeType = chunksRef.current[0]?.type || "audio/webm";
      const blob = new Blob(chunksRef.current, { type: mimeType });
      chunksRef.current = [];

      // Give the backend a filename extension that matches the actual
      // recorded container (mp4 on iOS Safari, webm on Android/desktop)
      // so its ffmpeg/Whisper decoding doesn't mismatch the real format.
      const ext = mimeType.includes("mp4") ? "mp4"
        : mimeType.includes("ogg") ? "ogg"
        : mimeType.includes("aac") ? "aac"
        : "webm";

      const formData = new FormData();
      formData.append("audio", blob, `recording.${ext}`);
      if (sessionId) formData.append("session_id", sessionId);

      const res = await apiFetch(`${BACKEND_URL}/audio/speech-to-text`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error("Voice analysis failed.");
      const data = await res.json();
      if (!data.transcript) throw new Error("No speech detected.");

      pushStatus("");
      setRecording(false);
      setLiveTranscript("");
      finalTranscriptRef.current = "";

      if (!sentRef.current) onTranscript?.(data.transcript);

    } catch (err) {
      setError(err.message);
      pushStatus("");
      setRecording(false);

      if (!sentRef.current) {
        const fallback = finalTranscriptRef.current.trim() || liveTranscript.trim();
        if (fallback) onTranscript?.(fallback);
      }
    } finally {
      setLoading(false);
    }
  };

  // ── Playback controls ─────────────────────────────────────────────────────
  const togglePlayback = () => {
    if (!audioRef.current) return;
    if (playing) {
      audioRef.current.pause();
      setPlaying(false);
    } else {
      audioRef.current.play();
      setPlaying(true);
    }
  };

  const handleAudioEnded = () => {
    setPlaying(false);
  };

  return (
    <div className="relative flex items-center gap-1">

      {/* Hidden audio element for playback */}
      {audioURL && (
        <audio
          ref={audioRef}
          src={audioURL}
          onEnded={handleAudioEnded}
          className="hidden"
        />
      )}

      {/* Playback bar — shown after recording when not recording */}
      {audioURL && !recording && !loading && (
        <div className="absolute bottom-full mb-2 right-0 z-20
          flex items-center gap-2 bg-white border border-slate-200
          px-3 py-1.5 rounded-xl shadow-lg whitespace-nowrap text-slate-700">
          {/* Play/pause button */}
          <button
            onClick={togglePlayback}
            className="w-6 h-6 rounded-full bg-emerald-600 hover:bg-emerald-700 text-white flex items-center justify-center flex-shrink-0 transition-colors"
            title={playing ? "Pause" : "Play recording"}
            aria-label={playing ? "Pause recording playback" : "Play recording playback"}
          >
            {playing ? (
              <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 24 24">
                <path d="M6 4h4v16H6zm8 0h4v16h-4z" />
              </svg>
            ) : (
              <svg className="w-3 h-3 text-white ml-0.5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M8 5v14l11-7z" />
              </svg>
            )}
          </button>

          {/* Waveform visual indicator */}
          <div className="flex items-center gap-0.5">
            {[3, 5, 4, 6, 3, 5, 4, 3, 6, 4].map((h, i) => (
              <div
                key={i}
                className={`w-0.5 rounded-full transition-all duration-150 ${
                  playing ? 'bg-emerald-500 animate-pulse' : 'bg-slate-300'
                }`}
                style={{ height: `${h * 2}px` }}
              />
            ))}
          </div>

          <span className="text-xs text-slate-500 font-medium">Voice recorded</span>

          {/* Discard button */}
          <button
            onClick={() => {
              if (audioRef.current) audioRef.current.pause();
              URL.revokeObjectURL(audioURL);
              setAudioURL(null);
              setPlaying(false);
            }}
            className="w-5 h-5 flex items-center justify-center text-slate-400 hover:text-red-500 transition-colors ml-1 rounded-full touch-manipulation"
            title="Discard recording"
            aria-label="Discard recording"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}

      {recording ? (
        <>
          <button
            onClick={handleCancel}
            title="Cancel recording"
            aria-label="Cancel recording"
            className="w-8 h-8 sm:w-9 sm:h-9 rounded-xl flex items-center justify-center bg-red-50 hover:bg-red-100 border border-red-200 transition-all duration-200 flex-shrink-0 touch-manipulation"
          >
            <svg className="w-3.5 h-3.5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>

          {liveTranscript && (
            <div className="absolute bottom-full mb-2 right-0 bg-white border border-slate-200 text-slate-700 text-xs px-3 py-1.5 rounded-xl shadow-lg whitespace-nowrap max-w-[220px] truncate z-20 font-medium">
              {liveTranscript}
            </div>
          )}

          <button
            disabled
            aria-label="Recording voice audio"
            className="w-8 h-8 sm:w-9 sm:h-9 rounded-xl flex items-center justify-center bg-red-500 animate-pulse flex-shrink-0 text-white shadow-sm"
          >
            <svg className="w-3.5 h-3.5 text-white" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 1a4 4 0 014 4v6a4 4 0 01-8 0V5a4 4 0 014-4zm-1 17.93V21H9v2h6v-2h-2v-2.07A8.001 8.001 0 0020 11h-2a6 6 0 01-12 0H4a8.001 8.001 0 007 7.93z" />
            </svg>
          </button>

          <button
            onClick={handleConfirm}
            title="Done — analyze voice and send"
            aria-label="Confirm and send voice message"
            className="w-8 h-8 sm:w-9 sm:h-9 rounded-xl flex items-center justify-center bg-emerald-600 hover:bg-emerald-700 text-white transition-all duration-200 flex-shrink-0 touch-manipulation shadow-sm"
          >
            <svg className="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
            </svg>
          </button>
        </>
      ) : (
        <>
          {disabled && (
          <div className="absolute bottom-full mb-2 right-0 bg-slate-100 border border-slate-200 text-slate-600 text-[11px] px-3 py-1.5 rounded-xl shadow-md whitespace-nowrap z-20 max-w-[240px]">
            Text-only mode — voice input is disabled on this connection.
          </div>
        )}
        <button
          onClick={handleStart}
          disabled={loading || disabled}
          title={disabled ? "Voice input is disabled on this connection — text messages still work" : "Start voice recording"}
          aria-label={disabled ? "Voice input disabled — text messages still work" : "Record voice message"}
          className="w-8 h-8 sm:w-9 sm:h-9 rounded-xl flex items-center justify-center bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-300 transition-all duration-200 flex-shrink-0 disabled:opacity-50 disabled:cursor-not-allowed touch-manipulation"
        >
          {loading ? (
            <div className="w-3.5 h-3.5 border-2 border-slate-400 border-t-slate-700 rounded-full animate-spin" />
          ) : (
            <svg className="w-3.5 h-3.5 text-slate-600" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 1a4 4 0 014 4v6a4 4 0 01-8 0V5a4 4 0 014-4zm-1 17.93V21H9v2h6v-2h-2v-2.07A8.001 8.001 0 0020 11h-2a6 6 0 01-12 0H4a8.001 8.001 0 007 7.93z" />
            </svg>
          )}
        </button>
      </>
      )}

      {error && (
        <div className="absolute bottom-full mb-2 right-0 bg-red-50 border border-red-200 text-red-700 text-xs px-2.5 py-1.5 rounded-xl shadow-md whitespace-nowrap z-20 flex items-center gap-1.5">
          <span>{error}</span>
          <button
            onClick={() => setError(null)}
            aria-label="Dismiss voice error"
            className="ml-1 text-red-500 hover:text-red-700 font-bold p-0.5 touch-manipulation"
          >
            ✕
          </button>
        </div>
      )}
    </div>
  );
}