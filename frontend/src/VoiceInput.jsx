import { useState, useRef, useEffect } from "react";

const BACKEND_URL = "http://127.0.0.1:8000";

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const hasSpeechRecognition = !!SpeechRecognition;

export default function VoiceInput({ onTranscript, onAgentResponse, sessionId, onStatusChange }) {
  const [recording, setRecording] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [liveTranscript, setLiveTranscript] = useState("");

  const recognitionRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const finalTranscriptRef = useRef("");
  const streamRef = useRef(null);

  const pushStatus = (text) => onStatusChange?.(text);

  useEffect(() => {
    return () => stopAll();
  }, []);

  const stopAll = () => {
    try { recognitionRef.current?.stop(); } catch (e) { void e; }
    if (mediaRecorderRef.current?.state !== "inactive") {
      try { mediaRecorderRef.current?.stop(); } catch (e) { void e; }
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }
  };

  // ── Cancel — discard everything ──────────────────────────────────────────
  const handleCancel = () => {
    chunksRef.current = [];
    stopAll();
    setRecording(false);
    setLiveTranscript("");
    finalTranscriptRef.current = "";
    pushStatus("");
    setError(null);
  };

  // ── Confirm — stop recording, send audio to backend, put transcript in box
  const handleConfirm = () => {
    try { recognitionRef.current?.stop(); } catch (e) { void e; }

    if (mediaRecorderRef.current?.state !== "inactive") {
      mediaRecorderRef.current.stop(); // triggers onstop → sends audio
    } else {
      // MediaRecorder already stopped — just put transcript in input box
      const text = finalTranscriptRef.current.trim() || liveTranscript.trim();
      if (text) onTranscript?.(text);
      else setError("No speech detected. Try again.");
      setRecording(false);
      setLiveTranscript("");
      finalTranscriptRef.current = "";
      pushStatus("");
    }
  };

  // ── Start recording ───────────────────────────────────────────────────────
  const handleStart = async () => {
    setError(null);
    setLiveTranscript("");
    finalTranscriptRef.current = "";
    chunksRef.current = [];

    // Get mic stream
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
    } catch {
      setError("Mic access denied. Allow microphone in browser settings.");
      return;
    }

    // Start MediaRecorder — always, for acoustic feature extraction
    try {
      const mimeType = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "audio/ogg";
      const mediaRecorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        streamRef.current = null;

        if (chunksRef.current.length > 0) {
          // Send audio to backend for acoustic extraction
          // Put transcript in input box for user review
          await extractAcousticsAndSetTranscript();
        }
      };

      mediaRecorder.start();
    } catch {
      setError("Recording failed. Try again.");
      stream.getTracks().forEach(t => t.stop());
      return;
    }

    // Start Web Speech API for live transcript preview
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

      try { recognition.start(); } catch { }
    }

    setRecording(true);
    pushStatus("Listening...");
  };

  // ── Send audio to backend for acoustic extraction ─────────────────────────
  // Acoustic features saved to session on backend
  // Transcript put in input box for user to review before sending
  const extractAcousticsAndSetTranscript = async () => {
    setLoading(true);
    pushStatus("Extracting voice features...");

    try {
      const mimeType = chunksRef.current[0]?.type || "audio/webm";
      const blob = new Blob(chunksRef.current, { type: mimeType });
      chunksRef.current = [];

      const formData = new FormData();
      formData.append("audio", blob, "recording.webm");
      if (sessionId) formData.append("session_id", sessionId);

      const res = await fetch(`${BACKEND_URL}/audio/speech-to-text`, {
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

      // Put transcript in input box — user reviews and decides to send
      // Acoustic features already saved to session on backend
      onTranscript?.(data.transcript);

    } catch (err) {
      setError(err.message);
      pushStatus("");
      setRecording(false);

      // Fallback — use Web Speech transcript if available
      const fallback = finalTranscriptRef.current.trim() || liveTranscript.trim();
      if (fallback) onTranscript?.(fallback);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative flex items-center gap-1">
      {recording ? (
        <>
          <button
            onClick={handleCancel}
            title="Cancel recording"
            className="w-8 h-8 sm:w-9 sm:h-9 rounded-xl flex items-center justify-center bg-gray-700 hover:bg-gray-600 transition-all duration-200 flex-shrink-0"
          >
            <svg className="w-3.5 h-3.5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>

          {liveTranscript && (
            <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 bg-gray-800 border border-gray-600 text-gray-300 text-xs px-3 py-1.5 rounded-xl whitespace-nowrap max-w-[200px] truncate z-10">
              {liveTranscript}
            </div>
          )}

          <button
            disabled
            className="w-8 h-8 sm:w-9 sm:h-9 rounded-xl flex items-center justify-center bg-red-600 animate-pulse flex-shrink-0"
          >
            <svg className="w-3.5 h-3.5 text-white" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 1a4 4 0 014 4v6a4 4 0 01-8 0V5a4 4 0 014-4zm-1 17.93V21H9v2h6v-2h-2v-2.07A8.001 8.001 0 0020 11h-2a6 6 0 01-12 0H4a8.001 8.001 0 007 7.93z" />
            </svg>
          </button>

          <button
            onClick={handleConfirm}
            title="Done — analyze voice and review transcript"
            className="w-8 h-8 sm:w-9 sm:h-9 rounded-xl flex items-center justify-center bg-emerald-700 hover:bg-emerald-600 transition-all duration-200 flex-shrink-0"
          >
            <svg className="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
            </svg>
          </button>
        </>
      ) : (
        <button
          onClick={handleStart}
          disabled={loading}
          title="Start recording"
          className="w-8 h-8 sm:w-9 sm:h-9 rounded-xl flex items-center justify-center bg-gray-700 hover:bg-gray-600 transition-all duration-200 flex-shrink-0 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? (
            <div className="w-3.5 h-3.5 border-2 border-gray-400 border-t-white rounded-full animate-spin" />
          ) : (
            <svg className="w-3.5 h-3.5 text-white" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 1a4 4 0 014 4v6a4 4 0 01-8 0V5a4 4 0 014-4zm-1 17.93V21H9v2h6v-2h-2v-2.07A8.001 8.001 0 0020 11h-2a6 6 0 01-12 0H4a8.001 8.001 0 007 7.93z" />
            </svg>
          )}
        </button>
      )}

      {error && (
        <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 bg-gray-900 border border-red-700 text-red-400 text-xs px-2 py-1 rounded-lg whitespace-nowrap z-10">
          {error}
          <button onClick={() => setError(null)} className="ml-2 text-red-600 hover:text-red-400">✕</button>
        </div>
      )}
    </div>
  );
}

