import { useState, useRef } from "react";

const BACKEND_URL = "http://localhost:8000";

export default function VoiceInput({ onTranscript, onAgentResponse, sessionId }) {
  const [recording, setRecording] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [statusText, setStatusText] = useState("Press to speak");
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);

  const startRecording = async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        await sendAudio(blob);
      };

      mediaRecorder.start();
      setRecording(true);
      setStatusText("Recording... Press to stop");
    } catch  {
      setError("Mic access denied. Allow microphone in your browser settings.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && recording) {
      mediaRecorderRef.current.stop();
      setRecording(false);
      setStatusText("Processing...");
    }
  };

  const sendAudio = async (blob) => {
    setLoading(true);
    try {
      // Step 1: Transcribe audio with Whisper
      const formData = new FormData();
      formData.append("audio", blob, "recording.webm");

      const sttRes = await fetch(`${BACKEND_URL}/audio/speech-to-text`, {
        method: "POST",
        body: formData,
      });

      if (!sttRes.ok) throw new Error("Transcription failed.");
      const { transcript } = await sttRes.json();
      if (!transcript) throw new Error("No speech detected.");

      setStatusText(`You said: "${transcript}"`);
      if (onTranscript) onTranscript(transcript);

      // Step 2: Send transcript to virtual agent
      const agentRes = await fetch(`${BACKEND_URL}/virtual-agent`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: transcript, session_id: sessionId }),
      });

      if (!agentRes.ok) throw new Error("Agent request failed.");
      const agentData = await agentRes.json();
      if (onAgentResponse) onAgentResponse(agentData);

      // Step 3: Play TTS audio of the agent's response
      const ttsRes = await fetch(
        `${BACKEND_URL}/audio/tts?text=${encodeURIComponent(agentData.response)}`
      );
      if (ttsRes.ok) {
        const audioBlob = await ttsRes.blob();
        const audioUrl = URL.createObjectURL(audioBlob);
        const audio = new Audio(audioUrl);
        audio.play();
      }

      setStatusText("Press to speak");
    } catch (err) {
      setError(err.message);
      setStatusText("Press to speak");
    } finally {
      setLoading(false);
    }
  };

  const handleClick = () => {
    if (recording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  return (
    <div className="flex flex-col items-center gap-4 p-6">
      {/* Mic Button */}
      <button
        onClick={handleClick}
        disabled={loading}
        className={`w-20 h-20 rounded-full flex items-center justify-center shadow-lg transition-all duration-200 disabled:opacity-50 ${
          recording
            ? "bg-red-600 hover:bg-red-700 scale-110 animate-pulse"
            : "bg-gray-700 hover:bg-gray-600"
        }`}
        title={recording ? "Stop recording" : "Start recording"}
      >
        {/* Mic Icon */}
        <svg
          className="w-9 h-9 text-white"
          fill="currentColor"
          viewBox="0 0 24 24"
        >
          {recording ? (
            // Stop icon
            <rect x="6" y="6" width="12" height="12" rx="2" />
          ) : (
            // Mic icon
            <path d="M12 1a4 4 0 014 4v6a4 4 0 01-8 0V5a4 4 0 014-4zm-1 17.93V21H9v2h6v-2h-2v-2.07A8.001 8.001 0 0020 11h-2a6 6 0 01-12 0H4a8.001 8.001 0 007 7.93z" />
          )}
        </svg>
      </button>

      {/* Status */}
      <p className="text-sm text-gray-300 text-center max-w-xs">{statusText}</p>

      {/* Loading spinner */}
      {loading && (
        <div className="w-5 h-5 border-2 border-gray-500 border-t-white rounded-full animate-spin" />
      )}

      {/* Error */}
      {error && (
        <p className="text-xs text-red-400 text-center max-w-xs">{error}</p>
      )}
    </div>
  );
}