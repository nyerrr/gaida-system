import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, PieChart, Pie, Cell
} from 'recharts';

const BACKEND = 'http://127.0.0.1:8000';

// ── Helpers ───────────────────────────────────────────────────────────────────
const severityColor = (s) => {
  if (s === 'High' || s === 'Crisis') return { bg: 'bg-red-600', text: 'text-white', dot: 'bg-red-500', border: 'border-red-200', light: 'bg-red-50' };
  if (s === 'Moderate') return { bg: 'bg-amber-500', text: 'text-white', dot: 'bg-amber-400', border: 'border-amber-200', light: 'bg-amber-50' };
  if (s === 'Low') return { bg: 'bg-green-500', text: 'text-white', dot: 'bg-green-400', border: 'border-green-200', light: 'bg-green-50' };
  return { bg: 'bg-gray-400', text: 'text-white', dot: 'bg-gray-400', border: 'border-gray-200', light: 'bg-gray-50' };
};

const formatRelative = (ts) => {
  if (!ts) return '';
  const diff = Math.floor((Date.now() - new Date(ts)) / 60000);
  if (diff < 1) return 'just now';
  if (diff < 60) return `${diff}m ago`;
  return `${Math.floor(diff / 60)}h ago`;
};

const formatDuration = (startedAt) => {
  if (!startedAt) return '—';
  const diff = Math.floor((Date.now() - new Date(startedAt)) / 1000);
  const m = Math.floor(diff / 60).toString().padStart(2, '0');
  const s = (diff % 60).toString().padStart(2, '0');
  return `${m}:${s}`;
};

// ── Mock chart data ───────────────────────────────────────────────────────────
const anxietyTrendData = [
  { month: 'Jan', low: 15, moderate: 45, high: 20 },
  { month: 'Feb', low: 18, moderate: 50, high: 22 },
  { month: 'Mar', low: 16, moderate: 53, high: 25 },
  { month: 'Apr', low: 17, moderate: 51, high: 24 },
  { month: 'May', low: 14, moderate: 55, high: 25 },
];
const sessionsWeekData = [
  { day: 'Mon', count: 12 }, { day: 'Tue', count: 15 },
  { day: 'Wed', count: 10 }, { day: 'Thu', count: 18 }, { day: 'Fri', count: 14 },
];
const anxietyDistribution = [
  { name: 'Low', value: 45, color: '#22c55e' },
  { name: 'Moderate', value: 35, color: '#f59e0b' },
  { name: 'High', value: 20, color: '#ef4444' },
];

// ── Nav ───────────────────────────────────────────────────────────────────────
const NAV = [
  { id: 'overview',  label: 'Overview',         icon: '⊞' },
  { id: 'alerts',    label: 'Alerts',            icon: '⚠' },
  { id: 'sessions',  label: 'Active Sessions',   icon: '◉' },
  { id: 'detection', label: 'Anxiety Detection', icon: '〜' },
  { id: 'reports',   label: 'Reports',           icon: '≡' },
];

// ── Overview Page ─────────────────────────────────────────────────────────────
function OverviewPage({ alerts, sessions }) {
  const pending = alerts.filter(a => a.status === 'pending').length;
  const highSessions = sessions.filter(s => s.severity === 'High' || s.severity === 'Crisis').length;

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Counselor Dashboard</h1>
        <p className="text-sm text-gray-500 mt-0.5">University of the East — Guidance System Overview</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {[
          { label: 'Active Sessions', value: sessions.length, sub: 'right now', color: 'bg-red-600' },
          { label: 'Pending Alerts', value: pending, sub: 'need attention', color: pending > 0 ? 'bg-red-600' : 'bg-gray-700' },
          { label: 'High Anxiety', value: highSessions, sub: 'active sessions', color: 'bg-gray-900' },
          { label: 'Total Alerts', value: alerts.length, sub: 'all time', color: 'bg-gray-900' },
        ].map((s) => (
          <div key={s.label} className="bg-white rounded-xl border border-gray-100 p-5 flex items-center justify-between shadow-sm">
            <div>
              <p className="text-xs text-gray-500 mb-1">{s.label}</p>
              <p className="text-2xl font-bold text-gray-900">{s.value}</p>
              <p className="text-xs text-gray-400 mt-0.5">{s.sub}</p>
            </div>
            <div className={`w-11 h-11 ${s.color} rounded-xl flex items-center justify-center flex-shrink-0`}>
              <span className="text-white text-lg font-bold">{s.value}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5 mb-5">
        <div className="bg-white rounded-xl border border-gray-100 p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Anxiety Level Trends</h3>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={anxietyTrendData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="month" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Line type="monotone" dataKey="low" stroke="#22c55e" strokeWidth={2} dot={{ r: 3 }} />
              <Line type="monotone" dataKey="moderate" stroke="#f59e0b" strokeWidth={2} dot={{ r: 3 }} />
              <Line type="monotone" dataKey="high" stroke="#ef4444" strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="bg-white rounded-xl border border-gray-100 p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Sessions This Week</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={sessionsWeekData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="day" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="count" fill="#dc2626" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
        <div className="bg-white rounded-xl border border-gray-100 p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Anxiety Distribution</h3>
          <div className="flex flex-col sm:flex-row items-center gap-4">
            <ResponsiveContainer width={160} height={160}>
              <PieChart>
                <Pie data={anxietyDistribution} cx="50%" cy="50%" innerRadius={45} outerRadius={70} dataKey="value">
                  {anxietyDistribution.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
            <div className="space-y-2">
              {anxietyDistribution.map((d) => (
                <div key={d.name} className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: d.color }} />
                  <span className="text-xs text-gray-600">{d.name}</span>
                  <span className="text-xs font-semibold text-gray-900 ml-auto pl-4">{d.value}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-100 p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Recent Alerts</h3>
          {alerts.length === 0 ? (
            <p className="text-xs text-gray-400 text-center py-6">No alerts yet</p>
          ) : (
            <div className="space-y-3">
              {alerts.slice(0, 5).map((a, i) => {
                const sc = severityColor(a.severity);
                return (
                  <div key={i} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className={`w-2 h-2 rounded-full ${sc.dot}`} />
                      <div>
                        <p className="text-xs font-semibold text-gray-900">{a.session_id.slice(0, 8)}...</p>
                        <p className="text-xs text-gray-400">{a.severity} — {a.intent}</p>
                      </div>
                    </div>
                    <span className="text-xs text-gray-400">{formatRelative(a.timestamp)}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Alerts Page ───────────────────────────────────────────────────────────────
function AlertsPage({ alerts, onViewChat, onUpdateStatus }) {
  const pending = alerts.filter(a => a.status === 'pending');
  const resolved = alerts.filter(a => a.status !== 'pending');

  const AlertRow = ({ a }) => {
    const sc = severityColor(a.severity);
    return (
      <div className={`p-4 border-l-4 ${a.severity === 'High' || a.severity === 'Crisis' ? 'border-red-500 bg-red-50' : 'border-amber-400 bg-amber-50'} rounded-r-xl mb-3`}>
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${sc.bg} ${sc.text}`}>
                {a.severity}
              </span>
              <span className="text-xs text-gray-500">{a.intent}</span>
              <span className="text-xs text-gray-400">{formatRelative(a.timestamp)}</span>
            </div>
            <p className="text-xs font-semibold text-gray-700 mb-1">Session: {a.session_id.slice(0, 16)}...</p>
            <p className="text-xs text-gray-600 truncate">"{a.message}"</p>
          </div>
          <div className="flex flex-col gap-2 flex-shrink-0">
            <button
              onClick={() => onViewChat(a.session_id)}
              className="text-xs px-3 py-1.5 bg-gray-900 text-white rounded-lg hover:bg-gray-700 font-medium"
            >
              View Chat
            </button>
            {a.status === 'pending' && (
              <button
                onClick={() => onUpdateStatus(a.session_id, 'reviewed')}
                className="text-xs px-3 py-1.5 border border-gray-300 text-gray-700 rounded-lg hover:bg-white font-medium"
              >
                Mark Reviewed
              </button>
            )}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Alerts</h1>
        <p className="text-sm text-gray-500 mt-0.5">High and Crisis level sessions requiring attention</p>
      </div>

      {pending.length > 0 && (
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            <h3 className="text-sm font-semibold text-gray-900">Pending ({pending.length})</h3>
          </div>
          {pending.map((a, i) => <AlertRow key={i} a={a} />)}
        </div>
      )}

      {resolved.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-500 mb-3">Resolved / Reviewed ({resolved.length})</h3>
          {resolved.map((a, i) => <AlertRow key={i} a={a} />)}
        </div>
      )}

      {alerts.length === 0 && (
        <div className="text-center py-20 text-gray-400">
          <p className="text-4xl mb-3">✓</p>
          <p className="text-sm font-medium">No alerts</p>
          <p className="text-xs mt-1">High and Crisis sessions will appear here</p>
        </div>
      )}
    </div>
  );
}

// ── Active Sessions Page ──────────────────────────────────────────────────────
function SessionsPage({ sessions, onViewChat }) {
  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Active Sessions</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Severity levels visible — chat content only shown for flagged sessions
        </p>
      </div>

      {sessions.length === 0 ? (
        <div className="text-center py-20 text-gray-400">
          <p className="text-4xl mb-3">◉</p>
          <p className="text-sm font-medium">No active sessions</p>
          <p className="text-xs mt-1">Sessions appear here when students are chatting</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
            <span className="text-sm font-semibold text-gray-900">Sessions ({sessions.length})</span>
            <span className="text-xs text-gray-400">Auto-refreshes every 5s</span>
          </div>
          <div className="divide-y divide-gray-50">
            {sessions.map((s) => {
              const sc = severityColor(s.severity);
              return (
                <div key={s.session_id} className="px-5 py-4 flex items-center gap-4">
                  <div className={`w-3 h-3 rounded-full flex-shrink-0 ${sc.dot} ${s.active ? 'animate-pulse' : ''}`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="text-sm font-semibold text-gray-900">{s.session_id.slice(0, 16)}...</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${sc.bg} ${sc.text}`}>
                        {s.severity}
                      </span>
                      {s.has_alert && (
                        <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-red-100 text-red-700">
                          ⚠ Alert
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-500">
                      {s.message_count} messages • {formatDuration(s.started_at)} • intent: {s.intent}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <div className="text-right mr-2">
                      <p className="text-xs text-gray-400">Confidence</p>
                      <p className="text-sm font-bold text-gray-900">{(s.confidence * 100).toFixed(0)}%</p>
                    </div>
                    {(s.severity === 'High' || s.severity === 'Crisis' || s.has_alert) && (
                      <button
                        onClick={() => onViewChat(s.session_id)}
                        className="text-xs px-3 py-1.5 bg-red-600 text-white rounded-lg hover:bg-red-700 font-medium"
                      >
                        View Chat
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Chat Transcript Modal ─────────────────────────────────────────────────────
function ChatModal({ sessionId, onClose }) {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [takeoverMsg, setTakeoverMsg] = useState('');
  const [sending, setSending] = useState(false);
  const [tookOver, setTookOver] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    fetchChat();
    const interval = setInterval(fetchChat, 3000);
    return () => clearInterval(interval);
  }, [sessionId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const fetchChat = async () => {
    try {
      const res = await fetch(`${BACKEND}/api/counselor/chat/${sessionId}`);
      const data = await res.json();
      if (data.messages) setMessages(data.messages);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const sendTakeover = async () => {
    if (!takeoverMsg.trim()) return;
    setSending(true);
    try {
      const res = await fetch(`${BACKEND}/api/counselor/takeover`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message: takeoverMsg }),
      });
      const data = await res.json();
      if (data.ok) {
        setTookOver(true);
        setTakeoverMsg('');
        fetchChat();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl w-full max-w-2xl max-h-[85vh] flex flex-col shadow-2xl">

        {/* Header */}
        <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between flex-shrink-0">
          <div>
            <h3 className="text-sm font-bold text-gray-900">Chat Transcript</h3>
            <p className="text-xs text-gray-500">{sessionId.slice(0, 20)}...</p>
          </div>
          <button onClick={onClose} className="w-8 h-8 flex items-center justify-center rounded-lg border border-gray-200 text-gray-500 hover:bg-gray-50 text-sm font-bold">✕</button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-gray-50">
          {loading ? (
            <p className="text-xs text-gray-400 text-center py-8">Loading chat...</p>
          ) : messages.length === 0 ? (
            <p className="text-xs text-gray-400 text-center py-8">No messages yet</p>
          ) : (
            messages.map((m, i) => (
              <div key={i} className={`flex ${m.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[75%] px-3 py-2 rounded-xl text-xs leading-relaxed ${
                  m.sender === 'user'
                    ? 'bg-gray-800 text-white rounded-tr-sm'
                    : m.sender === 'counselor'
                    ? 'bg-blue-600 text-white rounded-tl-sm'
                    : 'bg-white text-gray-800 border border-gray-200 rounded-tl-sm'
                }`}>
                  {m.sender === 'counselor' && (
                    <p className="text-blue-200 text-xs font-semibold mb-1">Counselor</p>
                  )}
                  <p>{m.text}</p>
                  {m.intent && m.sender === 'user' && (
                    <p className="text-gray-400 text-xs mt-1">{m.intent} • {m.confidence ? (m.confidence * 100).toFixed(0) + '%' : ''}</p>
                  )}
                </div>
              </div>
            ))
          )}
          <div ref={bottomRef} />
        </div>

        {/* Takeover input */}
        <div className="px-4 py-3 border-t border-gray-100 flex-shrink-0">
          {tookOver && (
            <p className="text-xs text-blue-600 font-medium mb-2">✓ You have taken over this session</p>
          )}
          <div className="flex gap-2">
            <input
              value={takeoverMsg}
              onChange={e => setTakeoverMsg(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && sendTakeover()}
              placeholder="Type a message to take over this session..."
              className="flex-1 text-xs px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-blue-400"
            />
            <button
              onClick={sendTakeover}
              disabled={sending || !takeoverMsg.trim()}
              className="px-4 py-2 bg-blue-600 text-white text-xs rounded-lg hover:bg-blue-700 disabled:opacity-50 font-medium"
            >
              {sending ? '...' : 'Send'}
            </button>
          </div>
          <p className="text-xs text-gray-400 mt-1.5">Sending a message will notify the student that a counselor has joined.</p>
        </div>
      </div>
    </div>
  );
}

// ── Detection Page (unchanged) ────────────────────────────────────────────────
function DetectionPage() {
  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Multimodal Anxiety Detection</h1>
        <p className="text-sm text-gray-500 mt-0.5">Real-time anxiety monitoring using voice and text analysis</p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
        {[
          { label: 'Voice Analysis', sub: 'Pitch, Energy, Jitter, Speech Rate, Pauses', status: 'Active', color: 'bg-gray-900' },
          { label: 'Text Analysis', sub: 'ML Ensemble: LR + RF + Neural Network', status: 'Active', color: 'bg-red-600' },
        ].map((m) => (
          <div key={m.label} className="bg-white rounded-xl border border-gray-100 p-5 shadow-sm">
            <div className="flex items-center gap-2 mb-1">
              <div className={`w-2 h-2 rounded-full bg-green-400 animate-pulse`} />
              <p className="text-xs text-gray-500">{m.label}</p>
            </div>
            <p className="text-xl font-bold text-gray-900 mb-1">{m.status}</p>
            <p className="text-xs text-gray-400">{m.sub}</p>
          </div>
        ))}
      </div>
      <div className="bg-white rounded-xl border border-gray-100 p-5 shadow-sm">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Anxiety Level Thresholds</h3>
        <div className="space-y-3">
          {[
            { level: 'Normal', range: '< 0.45', color: 'bg-gray-400', desc: 'GPT responds freely' },
            { level: 'Low', range: '0.45 – 0.60', color: 'bg-green-500', desc: 'Counselor protocol injected' },
            { level: 'Moderate', range: '0.60 – 0.75', color: 'bg-amber-500', desc: 'Stronger protocol injected' },
            { level: 'High', range: '0.75 – 0.98', color: 'bg-red-500', desc: 'Counselor alert fired' },
            { level: 'Crisis', range: '0.99', color: 'bg-red-700', desc: 'Immediate intervention' },
          ].map((t) => (
            <div key={t.level} className="flex items-center gap-3">
              <div className={`w-3 h-3 rounded-full flex-shrink-0 ${t.color}`} />
              <span className="text-xs font-semibold text-gray-900 w-16">{t.level}</span>
              <span className="text-xs text-gray-400 w-24">{t.range}</span>
              <span className="text-xs text-gray-600">{t.desc}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Reports Page (unchanged) ──────────────────────────────────────────────────
function ReportsPage() {
  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Reports & Analytics</h1>
        <p className="text-sm text-gray-500 mt-0.5">System performance and anxiety detection analytics</p>
      </div>
      <div className="bg-white rounded-xl border border-gray-100 p-5 shadow-sm mb-5">
        <h3 className="text-sm font-semibold text-gray-900 mb-4">Monthly Trends</h3>
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={[
            { month: 'Sep', sessions: 52, alerts: 8 },
            { month: 'Oct', sessions: 58, alerts: 12 },
            { month: 'Nov', sessions: 65, alerts: 15 },
            { month: 'Dec', sessions: 62, alerts: 14 },
            { month: 'Jan', sessions: 68, alerts: 18 },
            { month: 'Feb', sessions: 72, alerts: 20 },
          ]}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="month" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Line type="monotone" dataKey="sessions" stroke="#111827" strokeWidth={2} dot={{ r: 3 }} />
            <Line type="monotone" dataKey="alerts" stroke="#ef4444" strokeWidth={2} dot={{ r: 3 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────
export default function CounselorDashboard() {
  const navigate = useNavigate();
  const [activePage, setActivePage] = useState('overview');
  const [alerts, setAlerts] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [chatSessionId, setChatSessionId] = useState(null);
  const [expanded, setExpanded] = useState(false);

  // Poll alerts and sessions every 5 seconds
  useEffect(() => {
    fetchAlerts();
    fetchSessions();
    const interval = setInterval(() => {
      fetchAlerts();
      fetchSessions();
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchAlerts = async () => {
    try {
      const res = await fetch(`${BACKEND}/api/counselor/alerts`);
      const data = await res.json();
      if (data.alerts) setAlerts(data.alerts);
    } catch (e) {}
  };

  const fetchSessions = async () => {
    try {
      const res = await fetch(`${BACKEND}/api/counselor/sessions/active`);
      const data = await res.json();
      if (data.sessions) setSessions(data.sessions);
    } catch (e) {}
  };

  const handleUpdateStatus = async (sessionId, status) => {
    try {
      await fetch(`${BACKEND}/api/counselor/alerts/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, status }),
      });
      fetchAlerts();
    } catch (e) {}
  };

  const pendingCount = alerts.filter(a => a.status === 'pending').length;

  const logout = () => {
    localStorage.removeItem('counselor_token');
    localStorage.removeItem('counselorData');
    navigate('/counselor-login');
  };

  const counselor = JSON.parse(localStorage.getItem('counselorData') || '{}');
  const initials = counselor.name
    ? counselor.name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
    : 'CR';

  return (
    <div className="min-h-screen bg-gray-50 flex overflow-hidden">

      {expanded && (
        <div className="fixed inset-0 bg-black/20 z-20" onClick={() => setExpanded(false)} />
      )}

      {/* Sidebar */}
      <aside className={`fixed top-0 left-0 h-full z-30 bg-gray-800 flex flex-col shadow-lg transition-all duration-300 ${expanded ? 'w-56' : 'w-14'}`}>
        <div className="h-14 flex items-center justify-center flex-shrink-0 border-b border-gray-700">
          <div className="w-8 h-8 bg-red-600 rounded-full flex items-center justify-center">
            <span className="text-white text-xs font-bold">{initials}</span>
          </div>
          {expanded && <span className="text-white font-bold text-sm tracking-wide ml-3 whitespace-nowrap">GAIDA</span>}
        </div>

        <nav className="flex-1 py-3 overflow-y-auto overflow-x-hidden">
          {NAV.map((navItem) => {
            const active = activePage === navItem.id;
            const isAlerts = navItem.id === 'alerts';
            return (
              <button
                key={navItem.id}
                onClick={() => { setActivePage(navItem.id); setExpanded(false); }}
                title={!expanded ? navItem.label : undefined}
                className={`w-full flex items-center px-4 py-3 transition-colors relative group ${
                  active ? 'bg-red-600 text-white' : 'text-gray-400 hover:bg-gray-700 hover:text-white'
                }`}
              >
                <span className="flex-shrink-0 text-base relative">
                  {navItem.icon}
                  {isAlerts && pendingCount > 0 && (
                    <span className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full text-white text-xs flex items-center justify-center" style={{fontSize:'8px'}}>
                      {pendingCount}
                    </span>
                  )}
                </span>
                {expanded && <span className="ml-3 text-sm font-medium whitespace-nowrap">{navItem.label}</span>}
                {!expanded && (
                  <span className="absolute left-14 bg-gray-900 text-white text-xs px-2 py-1 rounded whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50 shadow-lg">
                    {navItem.label}
                    {isAlerts && pendingCount > 0 && ` (${pendingCount})`}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        <div className="border-t border-gray-700 flex-shrink-0">
          <button
            onClick={() => setExpanded(!expanded)}
            className="w-full flex items-center px-4 py-3 text-gray-400 hover:bg-gray-700 hover:text-white transition-colors"
          >
            <span className={`flex-shrink-0 text-sm transition-transform duration-300 ${expanded ? 'rotate-180' : ''}`}>›</span>
            {expanded && <span className="ml-3 text-sm font-medium">Collapse</span>}
          </button>
          <button
            onClick={logout}
            className="w-full flex items-center px-4 py-3 text-gray-400 hover:bg-gray-700 hover:text-white transition-colors"
            title={!expanded ? 'Logout' : undefined}
          >
            <span className="flex-shrink-0 text-sm">⏻</span>
            {expanded && <span className="ml-3 text-sm font-medium">Logout</span>}
          </button>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden ml-14">
        <main className="flex-1 overflow-y-auto">
          <div className="w-full max-w-6xl mx-auto p-4 sm:p-6">
            {activePage === 'overview'  && <OverviewPage alerts={alerts} sessions={sessions} />}
            {activePage === 'alerts'    && <AlertsPage alerts={alerts} onViewChat={setChatSessionId} onUpdateStatus={handleUpdateStatus} />}
            {activePage === 'sessions'  && <SessionsPage sessions={sessions} onViewChat={setChatSessionId} />}
            {activePage === 'detection' && <DetectionPage />}
            {activePage === 'reports'   && <ReportsPage />}
          </div>
        </main>
      </div>

      {/* Chat Modal */}
      {chatSessionId && (
        <ChatModal
          sessionId={chatSessionId}
          onClose={() => setChatSessionId(null)}
        />
      )}
    </div>
  );
}