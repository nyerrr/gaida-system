import { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import VoiceInput from './VoiceInput';

export default function StudentDashboard() {
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [severity, setSeverity] = useState('Normal');
  const [sessionTime, setSessionTime] = useState(0);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [voiceStatus, setVoiceStatus] = useState(''); // CHANGE 1: added voiceStatus state
  const containerRef = useRef(null);
  const timerRef = useRef(null);
  const inputRef = useRef(null);
  

  useEffect(() => {
    const token = localStorage.getItem('session_token');
    const consent = localStorage.getItem('consent_given');
    if (!token) { navigate('/student-login'); return; }
    if (!consent) { navigate('/consent'); return; }

    setSidebarOpen(window.innerWidth >= 1024);

    timerRef.current = setInterval(() => {
      setSessionTime(prev => prev + 1);
    }, 1000);

    return () => clearInterval(timerRef.current);
  }, [navigate]);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [messages, voiceStatus]); // CHANGE 2: added voiceStatus to scroll dependency

  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60).toString().padStart(2, '0');
    const s = (seconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  // Poll for counselor takeover messages every 3 seconds
  const lastMessageCountRef = useRef(0);
  useEffect(() => {
    const pollCounselor = async () => {
      const sessionId = localStorage.getItem('session_id');
      if (!sessionId) return;
      try {
        const res = await fetch(`http://127.0.0.1:8000/api/counselor/chat/${sessionId}`);
        if (!res.ok) return;
        const data = await res.json();
        if (!data.messages) return;
        const counselorMsgs = data.messages.filter(m => m.sender === 'counselor');
        if (counselorMsgs.length > lastMessageCountRef.current) {
          const newMsgs = counselorMsgs.slice(lastMessageCountRef.current);
          newMsgs.forEach(m => {
            setMessages(prev => [...prev, {
              role: 'counselor',
              text: m.text,
            }]);
          });
          lastMessageCountRef.current = counselorMsgs.length;
        }
      } catch (e) {}
    };
    const interval = setInterval(pollCounselor, 3000);
    return () => clearInterval(interval);
  }, []);

  const getSeverityColor = (level) => {
  if (level === 'High') return { bar: 'bg-red-500', text: 'text-red-400', border: 'border-red-800', glow: 'shadow-red-500/20' };
  if (level === 'Moderate') return { bar: 'bg-yellow-500', text: 'text-yellow-400', border: 'border-yellow-800', glow: 'shadow-yellow-500/20' };
  if (level === 'Low') return { bar: 'bg-emerald-500', text: 'text-emerald-400', border: 'border-emerald-800', glow: 'shadow-emerald-500/20' };
  // Normal — default neutral gray
  return { bar: 'bg-gray-500', text: 'text-gray-400', border: 'border-gray-700', glow: 'shadow-gray-500/10' };
};

  const getSeverityWidth = (level) => {
  if (level === 'High') return 'w-4/5';
  if (level === 'Moderate') return 'w-2/4';
  if (level === 'Low') return 'w-1/4';
  return 'w-0';  // Normal — empty bar
};


  const sendMessage = async () => {
    const text = input.trim();
    if (!text) return;

    setMessages(prev => [...prev, { role: 'user', text }]);
    setInput('');
    setSending(true);

    if (window.innerWidth < 1024) setSidebarOpen(false);

    try {
      const sessionId = localStorage.getItem('session_id');
      const token = localStorage.getItem('session_token');
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const res = await fetch('/virtual-agent', {
        method: 'POST',
        headers,
        body: JSON.stringify({ message: text, session_id: sessionId }),
      });

      if (!res.ok) {
        const err = await res.text();
        setMessages(prev => [...prev, { role: 'bot', text: `Error: ${err || res.status}` }]);
      } else {
        const data = await res.json();
        if (data.session_id) localStorage.setItem('session_id', data.session_id);
        if (data.severity) setSeverity(data.severity);
        setMessages(prev => [...prev, { role: 'bot', text: data.response || 'No response from backend' }]);
      }
    } catch (err) {
      setMessages(prev => [...prev, { role: 'bot', text: `Connection error: ${err.message}` }]);
    } finally {
      setSending(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const endSession = () => {
    localStorage.removeItem('session_token');
    localStorage.removeItem('student_id');
    localStorage.removeItem('consent_given');
    localStorage.removeItem('session_id');
    navigate('/student-login');
  };

  const toggleSidebar = () => setSidebarOpen(prev => !prev);

  const severityColors = getSeverityColor(severity);

  return (
    <div className="min-h-screen max-h-screen bg-gray-950 flex overflow-hidden font-mono relative">

      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-20 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed lg:relative z-30 lg:z-auto
          top-0 left-0 h-full
          transition-transform duration-300 ease-in-out
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0 lg:hidden'}
          w-64 bg-gray-900 border-r border-gray-800 flex flex-col flex-shrink-0
        `}
      >
        <div className="p-5 border-b border-gray-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-gradient-to-br from-red-600 to-red-800 rounded-full flex items-center justify-center relative flex-shrink-0">
              <div className="absolute -top-1.5 left-1/2 -translate-x-1/2 flex flex-col items-center">
                <div className="w-1.5 h-1.5 bg-white rounded-full"></div>
                <div className="w-0.5 h-2 bg-white"></div>
              </div>
              <div className="flex flex-col items-center">
                <div className="flex gap-1 mb-0.5">
                  <div className="w-1 h-1 bg-white rounded-full"></div>
                  <div className="w-1 h-1 bg-white rounded-full"></div>
                </div>
                <div className="w-3 h-1.5 border-b border-white rounded-b-full"></div>
              </div>
            </div>
            <div>
              <p className="text-white font-bold tracking-widest text-sm">GAIDA</p>
              <p className="text-gray-500 text-xs">Guidance System</p>
            </div>
          </div>
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden text-gray-500 hover:text-white transition-colors p-1"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-4 border-b border-gray-800">
          <p className="text-gray-500 text-xs uppercase tracking-widest mb-3">Session</p>
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-gray-400 text-xs">Duration</span>
              <span className="text-white text-xs font-bold">{formatTime(sessionTime)}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-400 text-xs">Messages</span>
              <span className="text-white text-xs font-bold">{messages.length}</span>
            </div>
          </div>
        </div>

        <div className="p-4 border-b border-gray-800">
          <p className="text-gray-500 text-xs uppercase tracking-widest mb-3">Anxiety Level</p>
          <div className={`p-3 rounded-lg bg-gray-800 border ${severityColors.border} shadow-lg ${severityColors.glow}`}>
            <div className="flex justify-between items-center mb-2">
              <span className="text-gray-400 text-xs">Detected</span>
              <span className={`text-xs font-bold ${severityColors.text}`}>{severity}</span>
            </div>
            <div className="w-full bg-gray-700 rounded-full h-1.5">
              <div className={`${severityColors.bar} h-1.5 rounded-full transition-all duration-700 ${getSeverityWidth(severity)}`}></div>
            </div>
          </div>
        </div>

        <div className="p-4 flex-1">
          <p className="text-gray-500 text-xs uppercase tracking-widest mb-3">Quick Tips</p>
          <div className="space-y-2 text-xs text-gray-400 leading-relaxed">
            <p>Press Enter to send a message.</p>
            <p>Use the mic button for voice input.</p>
            <p>Your session is private and encrypted.</p>
          </div>
        </div>

        <div className="p-4 border-t border-gray-800">
          <button
            onClick={endSession}
            className="w-full py-2 px-4 bg-red-900/50 hover:bg-red-700 border border-red-800 hover:border-red-600 text-red-400 hover:text-white text-xs font-bold rounded-lg transition-all duration-200 tracking-widest uppercase"
          >
            End Session
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0 h-screen">

        <div className="h-14 bg-gray-900 border-b border-gray-800 flex items-center px-4 gap-3 flex-shrink-0">
          <button
            onClick={toggleSidebar}
            className="text-gray-400 hover:text-white transition-colors flex-shrink-0 p-1"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <span className="text-white text-xs sm:text-sm font-bold tracking-widest truncate">VIRTUAL COUNSELOR</span>

          <div className={`ml-auto flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-bold ${severityColors.text} ${severityColors.border} bg-gray-800`}>
            <div className={`w-1.5 h-1.5 rounded-full ${severityColors.bar}`}></div>
            <span className="hidden sm:inline">{severity}</span>
          </div>

          <div className="flex items-center gap-1.5 flex-shrink-0">
            <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse"></div>
            <span className="text-emerald-400 text-xs hidden sm:inline">Online</span>
          </div>
        </div>

       
        {/* Chat Area */}
        <div
          ref={containerRef}
          className="flex-1 overflow-y-auto px-3 sm:px-6 py-4 space-y-3"
        >
          {/* Counselor joined banner */}
          {messages.some(m => m.role === 'counselor') && (
            <div className="flex justify-center">
              <span className="text-xs text-blue-400 bg-blue-900/30 border border-blue-800 px-3 py-1.5 rounded-full">
                A counselor has joined your session
              </span>
            </div>
          )}
          {messages.length === 0 && !voiceStatus && (
            <div className="flex flex-col items-center justify-center h-full text-center px-4">
              <div className="w-14 h-14 bg-gray-800 rounded-full flex items-center justify-center mb-4 border border-gray-700">
                <svg className="w-7 h-7 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
              </div>
              <p className="text-gray-400 text-sm">Start the conversation.</p>
              <p className="text-gray-600 text-xs mt-1">Your session is private and secure.</p>
            </div>
          )}

          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'} items-end gap-2`}>
              {(m.role === 'bot' || m.role === 'counselor') && (
                <div className={`w-6 h-6 sm:w-7 sm:h-7 rounded-full flex items-center justify-center flex-shrink-0 border mb-0.5
                  ${m.role === 'counselor'
                    ? 'bg-blue-900 border-blue-700'
                    : 'bg-red-900 border-red-700'}`}>
                  <span className="text-white text-xs font-bold">
                    {m.role === 'counselor' ? 'C' : 'G'}
                  </span>
                </div>
              )}
              <div className="flex flex-col gap-1 max-w-[78%] sm:max-w-[72%] lg:max-w-[65%]">
                <div className={`
                  px-3 sm:px-4 py-2.5 sm:py-3 rounded-2xl text-sm leading-relaxed
                  ${m.role === 'user'
                    ? 'bg-red-700 text-white rounded-tr-sm'
                    : m.role === 'counselor'
                    ? 'bg-blue-900 text-blue-100 border border-blue-700 rounded-tl-sm'
                    : 'bg-gray-800 text-gray-100 border border-gray-700 rounded-tl-sm'}
                `}>
                  {m.isVoice && (
                    <div className="flex items-center gap-1 mb-1 opacity-60">
                      <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M12 1a4 4 0 014 4v6a4 4 0 01-8 0V5a4 4 0 014-4zm-1 17.93V21H9v2h6v-2h-2v-2.07A8.001 8.001 0 0020 11h-2a6 6 0 01-12 0H4a8.001 8.001 0 007 7.93z"/>
                      </svg>
                      <span className="text-xs">Voice</span>
                    </div>
                  )}
                  {m.text}
                </div>

                {m.role === 'bot' && m.acoustic && (
                  <div className="flex items-center gap-2 px-1">
                    <span className="text-xs text-gray-500">Voice detected:</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium border
                      ${m.acoustic.emotion === 'anxious' ? 'text-yellow-400 border-yellow-800 bg-yellow-900/30' :
                        m.acoustic.emotion === 'sad' ? 'text-blue-400 border-blue-800 bg-blue-900/30' :
                        m.acoustic.emotion === 'angry' ? 'text-red-400 border-red-800 bg-red-900/30' :
                        m.acoustic.emotion === 'stressed' ? 'text-orange-400 border-orange-800 bg-orange-900/30' :
                        m.acoustic.emotion === 'calm' ? 'text-emerald-400 border-emerald-800 bg-emerald-900/30' :
                        m.acoustic.emotion === 'withdrawn' ? 'text-purple-400 border-purple-800 bg-purple-900/30' :
                        'text-gray-400 border-gray-700 bg-gray-800/30'}
                    `}>
                      {m.acoustic.emotion}
                    </span>
                    <span className="text-xs text-gray-600">{m.acoustic.severity}</span>
                  </div>
                )}
              </div>
            </div>
          ))}

          {sending && (
            <div className="flex justify-start items-end gap-2">
              <div className="w-6 h-6 sm:w-7 sm:h-7 bg-red-900 rounded-full flex items-center justify-center border border-red-700">
                <span className="text-white text-xs font-bold">G</span>
              </div>
              <div className="bg-gray-800 border border-gray-700 px-4 py-3 rounded-2xl rounded-tl-sm">
                <div className="flex gap-1 items-center h-4">
                  <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{animationDelay:'0ms'}}></div>
                  <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{animationDelay:'150ms'}}></div>
                  <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{animationDelay:'300ms'}}></div>
                </div>
              </div>
            </div>
          )}

          {/* CHANGE 3: voice status pill centered in the conversation */}
          {voiceStatus && (
            <div className="flex justify-center">
              <span className="flex items-center gap-2 text-xs text-gray-400 bg-gray-800 border border-gray-700 px-3 py-1.5 rounded-full">
                <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />
                {voiceStatus}
              </span>
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="px-3 sm:px-4 py-3 bg-gray-900 border-t border-gray-800 flex-shrink-0">
          <div className="flex items-end gap-2 bg-gray-800 border border-gray-700 rounded-2xl px-3 py-2 focus-within:border-red-600 transition-colors">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type your message..."
              rows={1}
              className="flex-1 resize-none bg-transparent py-1 text-white placeholder-gray-500 focus:outline-none text-sm leading-relaxed"
              style={{minHeight: '32px', maxHeight: '96px'}}
            />
            <div className="flex items-center gap-1.5 flex-shrink-0 pb-0.5">
              <VoiceInput
                sessionId={localStorage.getItem('session_id')}
                onTranscript={(text) => setInput(text)}
                onAgentResponse={(data, transcript) => {
                  if (data.session_id) localStorage.setItem('session_id', data.session_id);
                  if (data.severity) setSeverity(data.severity);
                  setMessages(prev => [
                    ...prev,
                    ...(transcript ? [{ role: 'user', text: transcript, isVoice: true }] : []),
                    { role: 'bot', text: data.response, acoustic: data.acoustic },
                  ]);
                  setInput('');
                }}
                onStatusChange={setVoiceStatus}
              />

              {/* Send button — always visible, icon changes based on state */}
              <button
                onClick={sendMessage}
                disabled={sending || !input.trim()}
                className={`
                  w-8 h-8 sm:w-9 sm:h-9 rounded-xl flex items-center justify-center transition-all duration-200 flex-shrink-0
                  ${input.trim()
                    ? 'bg-white hover:bg-gray-400 text-gray-900'
                    : 'bg-gray-700 text-gray-500 cursor-not-allowed'}
                `}
              >
                {sending ? (
                  <div className="w-3.5 h-3.5 border-2 border-gray-400 border-t-white rounded-full animate-spin" />
                ) : (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                  </svg>
                )}
              </button>
            </div>
          </div>
          <p className="text-gray-700 text-xs text-center mt-1.5 hidden sm:block">
            Press Enter to send. Shift+Enter for new line.
          </p>
        </div>
      </div>
    </div>
  );
}