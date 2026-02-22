import { useState, useRef, useEffect } from "react";

const BACKEND_URL = "";

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const hasSpeechRecognition = !!SpeechRecognition;

export default function VoiceInput({ onTranscript, onAgentResponse, sessionId, onStatusChange }) {
  const [recording, setRecording] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const recognitionRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const silenceTimerRef = useRef(null);
  const SILENCE_TIMEOUT = 2000;

  // Unified status setter — updates parent and local state
  const pushStatus = (text) => {
    onStatusChange?.(text);
  };

  useEffect(() => {
    return () => {
      clearTimeout(silenceTimerRef.current);
      stopAll();
    };
  }, []);

  const stopAll = () => {
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch (e) { void e; }
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      try { mediaRecorderRef.current.stop(); } catch (e) { void e; }
    }
    clearTimeout(silenceTimerRef.current);
  };

  // ── Method 1: Web Speech API ───────────────────────────────────────────────
  const startWithSpeechRecognition = () => {
    const recognition = new SpeechRecognition();
    recognitionRef.current = recognition;

    recognition.lang = "fil-PH";
    recognition.interimResults = true;
    recognition.continuous = false;
    recognition.maxAlternatives = 1;

    let finalTranscript = "";

    recognition.onstart = () => {
      setRecording(true);
      pushStatus("Listening...");
      setError(null);
    };

    recognition.onspeechstart = () => {
      clearTimeout(silenceTimerRef.current);
      pushStatus("Listening...");
    };

    recognition.onspeechend = () => {
      silenceTimerRef.current = setTimeout(() => {
        recognition.stop();
      }, SILENCE_TIMEOUT);
    };

    recognition.onresult = (event) => {
      clearTimeout(silenceTimerRef.current);
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const t = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += t;
        } else {
          interim = t;
        }
      }
      pushStatus(finalTranscript || interim || "Listening...");
    };

    recognition.onend = async () => {
      setRecording(false);
      clearTimeout(silenceTimerRef.current);

      if (!finalTranscript.trim()) {
        pushStatus("");
        setError("No speech detected. Try again.");
        return;
      }

      pushStatus("");
      if (onTranscript) onTranscript(finalTranscript.trim());
      await sendToAgent(finalTranscript.trim());
    };

    recognition.onerror = (e) => {
      setRecording(false);
      clearTimeout(silenceTimerRef.current);
      pushStatus("");
      if (e.error === "no-speech") {
        setError("No speech detected. Try again.");
      } else if (e.error === "not-allowed") {
        setError("Mic access denied. Allow microphone in browser settings.");
      } else {
        setError(`Error: ${e.error}`);
      }
    };

    try {
      recognition.start();
    } catch {
      recognition.lang = "en-US";
      recognition.start();
    }
  };

  // ── Method 2: MediaRecorder + Whisper fallback ────────────────────────────
  const startWithMediaRecorder = async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      const audioCtx = new AudioContext();
      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 512;
      source.connect(analyser);

      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      let silenceStart = null;

      const checkSilence = () => {
        if (!mediaRecorderRef.current || mediaRecorderRef.current.state === "inactive") return;
        analyser.getByteFrequencyData(dataArray);
        const avg = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;

        if (avg < 5) {
          if (!silenceStart) silenceStart = Date.now();
          else if (Date.now() - silenceStart > SILENCE_TIMEOUT) {
            mediaRecorder.stop();
            audioCtx.close();
            return;
          }
        } else {
          silenceStart = null;
        }
        requestAnimationFrame(checkSilence);
      };

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        setRecording(false);
        pushStatus("Processing...");
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        await sendAudioToWhisper(blob);
      };

      mediaRecorder.start();
      setRecording(true);
      pushStatus("Listening...");
      requestAnimationFrame(checkSilence);
    } catch {
      setError("Mic access denied. Allow microphone in browser settings.");
    }
  };

  const sendAudioToWhisper = async (blob) => {
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append("audio", blob, "recording.webm");

      const sttRes = await fetch(`${BACKEND_URL}/audio/speech-to-text`, {
        method: "POST",
        body: formData,
      });

      if (!sttRes.ok) throw new Error("Transcription failed.");
      const { transcript } = await sttRes.json();
      if (!transcript) throw new Error("No speech detected.");

      pushStatus("");
      if (onTranscript) onTranscript(transcript);
      await sendToAgent(transcript);
    } catch (err) {
      setError(err.message);
      pushStatus("");
    } finally {
      setLoading(false);
    }
  };

  // ── Shared: send to agent + play TTS ─────────────────────────────────────
  const sendToAgent = async (transcript) => {
    setLoading(true);
    try {
      const agentRes = await fetch(`${BACKEND_URL}/virtual-agent`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: transcript, session_id: sessionId }),
      });

      if (!agentRes.ok) throw new Error("Agent request failed.");
      const agentData = await agentRes.json();
      if (onAgentResponse) onAgentResponse(agentData);

      const ttsRes = await fetch(
        `${BACKEND_URL}/audio/tts?text=${encodeURIComponent(agentData.response)}`
      );
      if (ttsRes.ok) {
        const audioBlob = await ttsRes.blob();
        const audio = new Audio(URL.createObjectURL(audioBlob));
        audio.play();
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // ── Click handler ─────────────────────────────────────────────────────────
  const handleClick = () => {
    if (recording) {
      stopAll();
      setRecording(false);
      pushStatus("");
      return;
    }

    if (hasSpeechRecognition) {
      startWithSpeechRecognition();
    } else {
      startWithMediaRecorder();
    }
  };

  return (
    <div className="relative flex items-center">
      <button
        onClick={handleClick}
        disabled={loading}
        title={recording ? "Stop recording" : "Start recording"}
        className={`
          w-8 h-8 sm:w-9 sm:h-9 rounded-xl flex items-center justify-center
          transition-all duration-200 flex-shrink-0
          disabled:opacity-50 disabled:cursor-not-allowed
          ${recording
            ? "bg-red-600 hover:bg-red-700 animate-pulse"
            : "bg-gray-700 hover:bg-gray-600"
          }
        `}
      >
        {loading ? (
          <div className="w-3.5 h-3.5 border-2 border-gray-400 border-t-white rounded-full animate-spin" />
        ) : recording ? (
          <svg className="w-3.5 h-3.5 text-white" fill="currentColor" viewBox="0 0 24 24">
            <rect x="6" y="6" width="12" height="12" rx="2" />
          </svg>
        ) : (
          <svg className="w-3.5 h-3.5 text-white" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 1a4 4 0 014 4v6a4 4 0 01-8 0V5a4 4 0 014-4zm-1 17.93V21H9v2h6v-2h-2v-2.07A8.001 8.001 0 0020 11h-2a6 6 0 01-12 0H4a8.001 8.001 0 007 7.93z" />
          </svg>
        )}
      </button>

      {/* Error tooltip only — status is now rendered by the parent */}
      {error && (
        <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 bg-gray-900 border border-red-700 text-red-400 text-xs px-2 py-1 rounded-lg whitespace-nowrap z-10">
          {error}
          <button
            onClick={() => setError(null)}
            className="ml-2 text-red-600 hover:text-red-400"
          >
            ✕
          </button>
        </div>
      )}
    </div>
  );
}