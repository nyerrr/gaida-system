import { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import VoiceInput from './VoiceInput';

export default function Chatbot() {
        const navigate = useNavigate();
        const [messages, setMessages] = useState([]);
        const [input, setInput] = useState('');
        const [sending, setSending] = useState(false);
        const containerRef = useRef(null);

        useEffect(() => {
                const token = localStorage.getItem('session_token');
                const consent = localStorage.getItem('consent_given');
                if (!token) {
                        navigate('/student-login');
                        return;
                }
                if (!consent) {
                        navigate('/consent');
                        return;
                }
        }, [navigate]);

        useEffect(() => {
                if (containerRef.current) {
                        containerRef.current.scrollTop = containerRef.current.scrollHeight;
                }
        }, [messages]);

        const sendMessage = async () => {
                const text = input.trim();
                if (!text) return;

                const userMsg = { role: 'user', text };
                setMessages(prev => [...prev, userMsg]);
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
                                if (data.session_id) {
                                        localStorage.setItem('session_id', data.session_id);
                                }
                                const botText = data.response || 'No response from backend';
                                setMessages(prev => [...prev, { role: 'bot', text: botText }]);
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
                navigate('/student-login');
        };

        return (
                <div className="min-h-screen flex items-center justify-center bg-gray-900 p-4">
                        <div className="bg-gray-800 rounded-3xl shadow-2xl p-6 w-full max-w-2xl border border-gray-700 flex flex-col" style={{height: '80vh'}}>
                                <div className="flex items-center justify-between mb-4">
                                        <h1 className="text-2xl font-bold text-white">Chatbot</h1>
                                        <div className="flex gap-2">
                                                <button onClick={() => { setMessages([]); }} className="text-xs px-3 py-1 bg-gray-700 rounded text-white">Clear</button>
                                                <button onClick={endSession} className="text-xs px-3 py-1 bg-red-600 hover:bg-red-700 rounded text-white">End Session</button>
                                        </div>
                                </div>

                                <div ref={containerRef} className="flex-1 overflow-y-auto p-4 space-y-3 bg-gray-900 rounded-lg">
                                        {messages.length === 0 && (
                                                <div className="text-center text-gray-400">No messages yet. Say hello!</div>
                                        )}
                                        {messages.map((m, i) => (
                                                <div key={i} className={m.role === 'user' ? 'flex justify-end' : 'flex justify-start'}>
                                                        <div className={`${m.role === 'user' ? 'bg-red-600 text-white' : 'bg-gray-700 text-gray-100'} px-4 py-2 rounded-lg max-w-[80%]`}>{m.text}</div>
                                                </div>
                                        ))}
                                </div>

                                <div className="mt-4 flex items-center gap-3">
                                        <textarea
                                                value={input}
                                                onChange={(e) => setInput(e.target.value)}
                                                onKeyDown={handleKeyDown}
                                                placeholder="Type your message..."
                                                className="flex-1 resize-none h-12 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none"
                                        />
                                        <VoiceInput
                                                sessionId={localStorage.getItem('session_id')}
                                                onTranscript={(text) => setInput(text)}
                                                onAgentResponse={(data) => {
                                                        if (data.session_id) localStorage.setItem('session_id', data.session_id);
                                                        setMessages(prev => [...prev, { role: 'bot', text: data.response }]);
                                                }}
                                        />
                                        <button onClick={sendMessage} disabled={sending} className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white font-semibold py-2 px-4 rounded-lg">
                                                {sending ? 'Sending...' : 'Send'}
                                        </button>
                                </div>
                        </div>
                </div>
        );
}