import { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import VoiceInput from './VoiceInput';

export default function StudentDashboard() {
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [anxietyLevel, setAnxietyLevel] = useState('Low');
  const [sessionTime, setSessionTime] = useState(0);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const containerRef = useRef(null);
  const timerRef = useRef(null);

  useEffect(() => {
    const token = localStorage.getItem('session_token');
    const consent = localStorage.getItem('consent_given');
    if (!token) { navigate('/student-login'); return; }
    if (!consent) { navigate('/consent'); return; }

    timerRef.current = setInterval(() => {
      setSessionTime(prev => prev + 1);
    }, 1000);

    return () => clearInterval(timerRef.current);
  }, [navigate]);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [messages]);

  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60).toString().padStart(2, '0');
    const s = (seconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  const getAnxietyColor = (level) => {
    if (level === 'High') return { bar: 'bg-red-500', text: 'text-red-400', glow: 'shadow-red-500/30' };
    if (level === 'Medium') return { bar: 'bg-yellow-500', text: 'text-yellow-400', glow: 'shadow-yellow-500/30' };
    return { bar: 'bg-emerald-500', text: 'text-emerald-400', glow: 'shadow-emerald-500/30' };
  };

  const getAnxietyWidth = (level) => {
    if (level === 'High') return 'w-4/5';
    if (level === 'Medium') return 'w-2/4';
    return 'w-1/4';
  };

  const sendMessage = async () => {
    const text = input.trim();
    if (!text) return;

    setMessages(prev => [...prev, { role: 'user', text }]);
    setInput('');
    setSending(true);

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
        if (data.anxiety_level) setAnxietyLevel(data.anxiety_level);
        setMessages(prev => [...prev, { role: 'bot', text: data.response || 'No response from backend' }]);
      }
    } catch (err) {
      setMessages(prev => [...prev, { role: 'bot', text: `Connection error: ${err.message}` }]);
    } finally {
      setSending(false);
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

  const anxietyColors = getAnxietyColor(anxietyLevel);

  return (
    <div className="min-h-screen bg-gray-950 flex font-mono">

      {/* Sidebar */}
      <div className={`${sidebarOpen ? 'w-64' : 'w-0 overflow-hidden'} transition-all duration-300 bg-gray-900 border-r border-gray-800 flex flex-col`}>
        {/* Logo */}
        <div className="p-6 border-b border-gray-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-red-600 to-red-800 rounded-full flex items-center justify-center relative">
              <div className="absolute -top-1.5 left-1/2 -translate-x-1/2 flex flex-col items-center">
                <div className="w-1.5 h-1.5 bg-white rounded-full"></div>
                <div className="w-0.5 h-2 bg-white"></div>
              </div>
              <div className="flex flex-col items-center">
                <div className="flex gap-1.5 mb-0.5">
                  <div className="w-1 h-1 bg-white rounded-full"></div>
                  <div className="w-1 h-1 bg-white rounded-full"></div>
                </div>
                <div className="w-3 h-1.5 border-b border-white rounded-b-full"></div>
              </div>
            </div>
            <div>
              <p className="text-white font-bold text-lg tracking-widest">GAIDA</p>
              <p className="text-gray-500 text-xs">Guidance System</p>
            </div>
          </div>
        </div>

        {/* Session Info */}
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

        {/* Anxiety Level */}
        <div className="p-4 border-b border-gray-800">
          <p className="text-gray-500 text-xs uppercase tracking-widest mb-3">Anxiety Level</p>
          <div className={`p-3 rounded-lg bg-gray-800 border border-gray-700 shadow-lg ${anxietyColors.glow}`}>
            <div className="flex justify-between items-center mb-2">
              <span className="text-gray-400 text-xs">Detected</span>
              <span className={`text-xs font-bold ${anxietyColors.text}`}>{anxietyLevel}</span>
            </div>
            <div className="w-full bg-gray-700 rounded-full h-1.5">
              <div className={`${anxietyColors.bar} h-1.5 rounded-full transition-all duration-700 ${getAnxietyWidth(anxietyLevel)}`}></div>
            </div>
          </div>
        </div>

        {/* Quick Tips */}
        <div className="p-4 flex-1">
          <p className="text-gray-500 text-xs uppercase tracking-widest mb-3">Quick Tips</p>
          <div className="space-y-2 text-xs text-gray-400">
            <p className="leading-relaxed">Press Enter to send a message.</p>
            <p className="leading-relaxed">Use the mic button for voice input.</p>
            <p className="leading-relaxed">Your session is private and encrypted.</p>
          </div>
        </div>

        {/* End Session */}
        <div className="p-4 border-t border-gray-800">
          <button
            onClick={endSession}
            className="w-full py-2 px-4 bg-red-900/50 hover:bg-red-700 border border-red-800 hover:border-red-600 text-red-400 hover:text-white text-xs font-bold rounded-lg transition-all duration-200 tracking-widest uppercase"
          >
            End Session
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">

        {/* Top Bar */}
        <div className="h-14 bg-gray-900 border-b border-gray-800 flex items-center px-4 gap-4">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="text-gray-400 hover:text-white transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <span className="text-white text-sm font-bold tracking-widest">VIRTUAL COUNSELOR</span>
          <div className="ml-auto flex items-center gap-2">
            <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse"></div>
            <span className="text-emerald-400 text-xs">Online</span>
          </div>
        </div>

        {/* Chat Area */}
        <div ref={containerRef} className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="w-16 h-16 bg-gray-800 rounded-full flex items-center justify-center mb-4 border border-gray-700">
                <svg className="w-8 h-8 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
              </div>
              <p className="text-gray-400 text-sm">Start the conversation.</p>
              <p className="text-gray-600 text-xs mt-1">Your session is private and secure.</p>
            </div>
          )}

          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              {m.role === 'bot' && (
                <div className="w-7 h-7 bg-red-900 rounded-full flex items-center justify-center mr-2 flex-shrink-0 mt-1 border border-red-700">
                  <span className="text-white text-xs font-bold">G</span>
                </div>
              )}
              <div className={`px-4 py-3 rounded-2xl max-w-[70%] text-sm leading-relaxed ${
                m.role === 'user'
                  ? 'bg-red-700 text-white rounded-tr-sm'
                  : 'bg-gray-800 text-gray-100 border border-gray-700 rounded-tl-sm'
              }`}>
                {m.text}
              </div>
            </div>
          ))}

          {sending && (
            <div className="flex justify-start">
              <div className="w-7 h-7 bg-red-900 rounded-full flex items-center justify-center mr-2 border border-red-700">
                <span className="text-white text-xs font-bold">G</span>
              </div>
              <div className="bg-gray-800 border border-gray-700 px-4 py-3 rounded-2xl rounded-tl-sm">
                <div className="flex gap-1 items-center h-4">
                  <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0ms'}}></div>
                  <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '150ms'}}></div>
                  <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '300ms'}}></div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="p-4 bg-gray-900 border-t border-gray-800">
          <div className="flex items-end gap-3 bg-gray-800 border border-gray-700 rounded-2xl p-2 focus-within:border-red-600 transition-colors">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type your message..."
              rows={1}
              className="flex-1 resize-none bg-transparent px-2 py-1.5 text-white placeholder-gray-500 focus:outline-none text-sm leading-relaxed max-h-32"
              style={{minHeight: '36px'}}
            />
            <div className="flex items-center gap-2 flex-shrink-0">
              <VoiceInput
                sessionId={localStorage.getItem('session_id')}
                onTranscript={(text) => setInput(text)}
                onAgentResponse={(data) => {
                  if (data.session_id) localStorage.setItem('session_id', data.session_id);
                  if (data.anxiety_level) setAnxietyLevel(data.anxiety_level);
                  setMessages(prev => [...prev, { role: 'bot', text: data.response }]);
                }}
              />
              <button
                onClick={sendMessage}
                disabled={sending || !input.trim()}
                className="w-9 h-9 bg-red-700 hover:bg-red-600 disabled:bg-gray-700 disabled:cursor-not-allowed rounded-xl flex items-center justify-center transition-colors flex-shrink-0"
              >
                <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              </button>
            </div>
          </div>
          <p className="text-gray-600 text-xs text-center mt-2">Press Enter to send. Shift+Enter for new line.</p>
        </div>
      </div>
    </div>
  );
}