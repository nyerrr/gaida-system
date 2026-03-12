import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, PieChart, Pie, Cell
} from 'recharts';

// ── Mock / seed data ──────────────────────────────────────────────────────────
const MOCK_ALERTS = [
  { session_id: 'sess-001-abc', severity: 'High', intent: 'anxiety', status: 'pending', message: 'Student expressed severe exam anxiety and difficulty breathing.', timestamp: new Date(Date.now() - 10 * 60000).toISOString(), student_name: 'Maria Santos' },
  { session_id: 'sess-002-def', severity: 'Moderate', intent: 'stress', status: 'pending', message: 'Mentioned feeling overwhelmed with project deadlines.', timestamp: new Date(Date.now() - 25 * 60000).toISOString(), student_name: 'Juan dela Cruz' },
  { session_id: 'sess-003-ghi', severity: 'Low', intent: 'neutral', status: 'reviewed', message: 'General check-in, no concerning indicators detected.', timestamp: new Date(Date.now() - 60 * 60000).toISOString(), student_name: 'Ana Reyes' },
  { session_id: 'sess-004-jkl', severity: 'High', intent: 'suicidal', status: 'pending', message: 'Expressed hopelessness regarding academic performance.', timestamp: new Date(Date.now() - 90 * 60000).toISOString(), student_name: 'Pedro Gonzales' },
];

const MOCK_STUDENTS = [
  { id: '2024-001234', name: 'Maria Santos', initials: 'MS', course: 'BS Psychology', year: '3rd Year', severity: 'High', lastSession: 'Feb 14, 2026' },
  { id: '2024-005678', name: 'Juan dela Cruz', initials: 'JDC', course: 'BS Computer Science', year: '2nd Year', severity: 'Moderate', lastSession: 'Feb 10, 2026' },
  { id: '2024-009012', name: 'Ana Reyes', initials: 'AR', course: 'BS Nursing', year: '4th Year', severity: 'Low', lastSession: 'Feb 12, 2026' },
  { id: '2024-003456', name: 'Pedro Gonzales', initials: 'PG', course: 'BS Business Administration', year: '1st Year', severity: 'High', lastSession: 'Feb 15, 2026' },
  { id: '2024-007890', name: 'Lisa Mendoza', initials: 'LM', course: 'BS Engineering', year: '3rd Year', severity: 'Moderate', lastSession: 'Feb 8, 2026' },
  { id: '2024-011234', name: 'Carlo Bautista', initials: 'CB', course: 'BS Education', year: '2nd Year', severity: 'Low', lastSession: 'Feb 6, 2026' },
];

const MOCK_DETECTIONS = [
  { student: 'Maria Santos', level: 'High Anxiety', date: 'Feb 15, 2026 - 10:30 AM', voiceScore: 78, textScore: 92, overall: 85, note: 'Student showed signs of stress during exam preparation discussion.' },
  { student: 'Juan dela Cruz', level: 'Moderate Anxiety', date: 'Feb 15, 2026 - 9:15 AM', voiceScore: 52, textScore: 48, overall: 50, note: 'Expressed concerns about upcoming projects but manageable.' },
  { student: 'Pedro Gonzales', level: 'High Anxiety', date: 'Feb 14, 2026 - 2:00 PM', voiceScore: 81, textScore: 79, overall: 80, note: 'Persistent worry patterns detected across multiple sessions.' },
];

const MOCK_SESSIONS_TODAY = [
  { student: 'Maria Santos', time: '2:00 PM', type: 'In-Person', action: 'Start Session' },
  { student: 'Pedro Gonzales', time: '3:30 PM', type: 'Chat', action: 'Join Chat' },
];

const MOCK_UPCOMING = [
  { student: 'Maria Santos', status: 'Confirmed', purpose: 'Exam Anxiety Support', date: 'Feb 15, 2026', time: '2:00 PM - 3:00 PM', type: 'In-Person', location: 'Guidance Office 201' },
  { student: 'Pedro Gonzales', status: 'Confirmed', purpose: 'Follow-up Session', date: 'Feb 15, 2026', time: '3:30 PM - 4:30 PM', type: 'Virtual', location: 'Virtual Meeting Room' },
  { student: 'Lisa Mendoza', status: 'Pending', purpose: 'Initial Consultation', date: 'Feb 17, 2026', time: '10:00 AM - 11:00 AM', type: 'In-Person', location: 'Guidance Office 201' },
];

const anxietyTrendData = [
  { month: 'Jan', low: 15, moderate: 45, high: 20 },
  { month: 'Feb', low: 18, moderate: 50, high: 22 },
  { month: 'Mar', low: 16, moderate: 53, high: 25 },
  { month: 'Apr', low: 17, moderate: 51, high: 24 },
  { month: 'May', low: 14, moderate: 55, high: 25 },
];

const sessionsWeekData = [
  { day: 'Mon', count: 12 },
  { day: 'Tue', count: 15 },
  { day: 'Wed', count: 10 },
  { day: 'Thu', count: 18 },
  { day: 'Fri', count: 14 },
];

const monthlyTrendData = [
  { month: 'Sep', students: 185, sessions: 52, alerts: 8 },
  { month: 'Oct', students: 200, sessions: 58, alerts: 12 },
  { month: 'Nov', students: 210, sessions: 65, alerts: 15 },
  { month: 'Dec', students: 215, sessions: 62, alerts: 14 },
  { month: 'Jan', students: 235, sessions: 68, alerts: 18 },
  { month: 'Feb', students: 248, sessions: 72, alerts: 20 },
];

const anxietyDistribution = [
  { name: 'Low', value: 45, color: '#22c55e' },
  { name: 'Moderate', value: 35, color: '#f59e0b' },
  { name: 'High', value: 20, color: '#ef4444' },
];

// ── Helpers ───────────────────────────────────────────────────────────────────
const severityColor = (s) => {
  if (s === 'High') return { bg: 'bg-red-600', text: 'text-white' };
  if (s === 'Moderate') return { bg: 'bg-amber-500', text: 'text-white' };
  return { bg: 'bg-green-500', text: 'text-white' };
};

const formatRelative = (ts) => {
  const diff = Math.floor((Date.now() - new Date(ts)) / 60000);
  if (diff < 60) return `${diff} mins ago`;
  return `${Math.floor(diff / 60)} hrs ago`;
};

// ── Nav items ─────────────────────────────────────────────────────────────────
const NAV = [
  { id: 'overview', label: 'Overview', icon: OverviewIcon },
  { id: 'students', label: 'Students', icon: StudentsIcon },
  { id: 'detection', label: 'Anxiety Detection', icon: DetectionIcon },
  { id: 'sessions', label: 'Sessions', icon: SessionsIcon },
  { id: 'reports', label: 'Reports', icon: ReportsIcon },
];

function OverviewIcon({ active }) {
  return (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <rect x="3" y="3" width="7" height="7" rx="1" strokeWidth={active ? 2.5 : 1.8} />
      <rect x="14" y="3" width="7" height="7" rx="1" strokeWidth={active ? 2.5 : 1.8} />
      <rect x="3" y="14" width="7" height="7" rx="1" strokeWidth={active ? 2.5 : 1.8} />
      <rect x="14" y="14" width="7" height="7" rx="1" strokeWidth={active ? 2.5 : 1.8} />
    </svg>
  );
}
function StudentsIcon({ active }) {
  return (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={active ? 2.5 : 1.8} d="M17 20h5v-2a4 4 0 00-5-3.87M9 20H4v-2a4 4 0 015-3.87m6-4.13a4 4 0 11-8 0 4 4 0 018 0z" />
    </svg>
  );
}
function DetectionIcon({ active }) {
  return (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <polyline strokeLinecap="round" strokeLinejoin="round" strokeWidth={active ? 2.5 : 1.8} points="22 12 18 12 15 21 9 3 6 12 2 12" />
    </svg>
  );
}
function SessionsIcon({ active }) {
  return (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <rect x="3" y="4" width="18" height="18" rx="2" strokeWidth={active ? 2.5 : 1.8} />
      <line x1="16" y1="2" x2="16" y2="6" strokeWidth={active ? 2.5 : 1.8} strokeLinecap="round" />
      <line x1="8" y1="2" x2="8" y2="6" strokeWidth={active ? 2.5 : 1.8} strokeLinecap="round" />
      <line x1="3" y1="10" x2="21" y2="10" strokeWidth={active ? 2.5 : 1.8} strokeLinecap="round" />
    </svg>
  );
}
function ReportsIcon({ active }) {
  return (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={active ? 2.5 : 1.8} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414A1 1 0 0121 9.414V19a2 2 0 01-2 2z" />
    </svg>
  );
}

// ── Pages ─────────────────────────────────────────────────────────────────────

function OverviewPage({ alerts }) {

  const stats = [
    { label: 'Total Students', value: '248', sub: '+12%', icon: 'students', iconBg: 'bg-red-600' },
    { label: 'High Anxiety Cases', value: '23', sub: '+5%', icon: 'alert', iconBg: 'bg-gray-900' },
    { label: 'Sessions Today', value: '8', sub: '3 pending', icon: 'calendar', iconBg: 'bg-red-600' },
    { label: 'Weekly Progress', value: '87%', sub: '+2%', icon: 'trend', iconBg: 'bg-gray-900' },
  ];

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Counselor Dashboard</h1>
        <p className="text-sm text-gray-500 mt-0.5">University of the East — Guidance System Overview</p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {stats.map((s) => (
          <div key={s.label} className="bg-white rounded-xl border border-gray-100 p-5 flex items-center justify-between shadow-sm">
            <div>
              <p className="text-xs text-gray-500 mb-1">{s.label}</p>
              <p className="text-2xl font-bold text-gray-900">{s.value}</p>
              <p className="text-xs text-gray-400 mt-0.5">{s.sub}</p>
            </div>
            <div className={`w-11 h-11 ${s.iconBg} rounded-xl flex items-center justify-center flex-shrink-0`}>
              <StatIcon type={s.icon} />
            </div>
          </div>
        ))}
      </div>

      {/* Charts row */}
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

      {/* Bottom row */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
        <div className="bg-white rounded-xl border border-gray-100 p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Anxiety Distribution</h3>
          <div className="flex flex-col sm:flex-row items-center gap-4 sm:gap-6">
            <ResponsiveContainer width={160} height={160}>
              <PieChart>
                <Pie data={anxietyDistribution} cx="50%" cy="50%" innerRadius={45} outerRadius={70} dataKey="value">
                  {anxietyDistribution.map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
            <div className="space-y-2">
              {anxietyDistribution.map((d) => (
                <div key={d.name} className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: d.color }} />
                  <span className="text-xs text-gray-600">{d.name}</span>
                  <span className="text-xs font-semibold text-gray-900 ml-auto">{d.value}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-100 p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Recent Alerts</h3>
          <div className="space-y-3">
            {alerts.slice(0, 4).map((a) => (
              <div key={a.session_id} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${a.severity === 'High' ? 'bg-red-500' : a.severity === 'Moderate' ? 'bg-amber-500' : 'bg-green-500'}`} />
                  <div>
                    <p className="text-xs font-semibold text-gray-900">{a.student_name}</p>
                    <p className="text-xs text-gray-400">{a.severity} Anxiety</p>
                  </div>
                </div>
                <span className="text-xs text-gray-400">{formatRelative(a.timestamp)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function StatIcon({ type }) {
  const cls = "w-5 h-5 text-white";
  if (type === 'students') return <svg className={cls} fill="currentColor" viewBox="0 0 20 20"><path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v1h8v-1zM6 8a2 2 0 11-4 0 2 2 0 014 0zM16 18v-1a5.97 5.97 0 00-.75-2.906A3.005 3.005 0 0119 15v1h-3zM4.75 14.094A5.97 5.97 0 004 17v1H1v-1a3 3 0 013.75-2.906z" /></svg>;
  if (type === 'alert') return <svg className={cls} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" /></svg>;
  if (type === 'calendar') return <svg className={cls} fill="none" stroke="currentColor" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="18" rx="2" strokeWidth={2} /><line x1="16" y1="2" x2="16" y2="6" strokeWidth={2} strokeLinecap="round" /><line x1="8" y1="2" x2="8" y2="6" strokeWidth={2} strokeLinecap="round" /><line x1="3" y1="10" x2="21" y2="10" strokeWidth={2} /></svg>;
  return <svg className={cls} fill="none" stroke="currentColor" viewBox="0 0 24 24"><polyline strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} points="23 6 13.5 15.5 8.5 10.5 1 18" /><polyline strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} points="17 6 23 6 23 12" /></svg>;
}

function StudentsPage() {
  const [search, setSearch] = useState('');
  const filtered = MOCK_STUDENTS.filter(s =>
    s.name.toLowerCase().includes(search.toLowerCase()) || s.id.includes(search)
  );

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Students</h1>
        <p className="text-sm text-gray-500 mt-0.5">Manage and monitor student records</p>
      </div>

      <div className="bg-white rounded-xl border border-gray-100 p-4 mb-5 shadow-sm flex gap-3">
        <div className="flex-1 relative">
          <svg className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <circle cx="11" cy="11" r="8" strokeWidth={2} /><path strokeLinecap="round" strokeWidth={2} d="M21 21l-4.35-4.35" />
          </svg>
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search by name or student ID..."
            className="w-full pl-9 pr-4 py-2 text-sm bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:border-red-400"
          />
        </div>
        <button className="flex items-center gap-2 px-4 py-2 text-sm border border-gray-200 rounded-lg text-gray-600 hover:bg-gray-50">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2a1 1 0 01-.293.707l-6.414 6.414A1 1 0 0014 13.828V19a1 1 0 01-.553.894l-4 2A1 1 0 018 21v-7.172a1 1 0 00-.293-.707L1.293 6.707A1 1 0 011 6V4z" /></svg>
          Filter
        </button>
      </div>

      <div className="bg-white rounded-xl border border-gray-100 shadow-sm">
        <div className="px-5 py-3 border-b border-gray-100">
          <span className="text-sm font-semibold text-gray-900">All Students ({filtered.length})</span>
        </div>
        <div className="divide-y divide-gray-50">
          {filtered.map((s) => {
            const sc = severityColor(s.severity);
            return (
              <div key={s.id} className="px-5 py-4 flex items-center gap-4">
                <div className="w-10 h-10 rounded-full bg-gray-900 flex items-center justify-center flex-shrink-0">
                  <span className="text-white text-xs font-bold">{s.initials}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-sm font-semibold text-gray-900">{s.name}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${sc.bg} ${sc.text}`}>{s.severity}</span>
                  </div>
                  <p className="text-xs text-gray-500">{s.id} • {s.course} • {s.year}</p>
                  <p className="text-xs text-gray-400">Last session: {s.lastSession}</p>
                </div>
                <div className="flex flex-col sm:flex-row gap-2 flex-shrink-0">
                  <button className="flex items-center gap-1.5 text-xs px-3 py-1.5 border border-gray-200 rounded-lg text-gray-700 hover:bg-gray-50">
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.477 0 8.268 2.943 9.542 7-1.274 4.057-5.065 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>
                    View Details
                  </button>
                  <button className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-red-600 text-white rounded-lg hover:bg-red-700">
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.14 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0" /></svg>
                    Live Counseling
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function DetectionPage() {
  const levelColor = (l) => {
    if (l.includes('High')) return 'bg-red-600 text-white';
    if (l.includes('Moderate')) return 'bg-amber-500 text-white';
    return 'bg-green-500 text-white';
  };

  const scoreColor = (v) => v >= 70 ? 'text-red-600' : v >= 40 ? 'text-amber-500' : 'text-green-600';

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Multimodal Anxiety Detection</h1>
        <p className="text-sm text-gray-500 mt-0.5">Real-time anxiety level monitoring using voice and text analysis</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
        {[
          { label: 'Voice Analysis', status: 'Active', iconBg: 'bg-gray-900', icon: 'wave' },
          { label: 'Text Analysis', status: 'Active', iconBg: 'bg-red-600', icon: 'brain' },
        ].map((m) => (
          <div key={m.label} className="bg-white rounded-xl border border-gray-100 p-5 flex items-center justify-between shadow-sm">
            <div>
              <p className="text-xs text-gray-500 mb-1">{m.label}</p>
              <p className="text-xl font-bold text-gray-900">{m.status}</p>
            </div>
            <div className={`w-11 h-11 ${m.iconBg} rounded-xl flex items-center justify-center`}>
              {m.icon === 'wave'
                ? <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><polyline strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} points="22 12 18 12 15 21 9 3 6 12 2 12" /></svg>
                : <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" strokeWidth={2} /><path strokeLinecap="round" strokeWidth={2} d="M12 8v4m0 4h.01" /></svg>
              }
            </div>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-xl border border-gray-100 shadow-sm">
        <div className="px-5 py-4 border-b border-gray-100">
          <h3 className="text-sm font-semibold text-gray-900">Recent Detection Results</h3>
        </div>
        <div className="divide-y divide-gray-50">
          {MOCK_DETECTIONS.map((d, i) => (
            <div key={i} className="p-5">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-bold text-gray-900">{d.student}</span>
                    <span className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${levelColor(d.level)}`}>{d.level}</span>
                  </div>
                  <p className="text-xs text-gray-400">{d.date}</p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-gray-400 mb-0.5">Overall Anxiety Score</p>
                  <p className={`text-2xl font-bold ${scoreColor(d.overall)}`}>{d.overall}%</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 mb-3">
                {[{ label: 'Voice', val: d.voiceScore }, { label: 'Text', val: d.textScore }].map((bar) => (
                  <div key={bar.label}>
                    <div className="flex justify-between mb-1">
                      <span className="text-xs text-gray-500">{bar.label}</span>
                      <span className="text-xs font-semibold text-gray-900">{bar.val}%</span>
                    </div>
                    <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div className="h-full bg-gray-900 rounded-full progress-bar" style={{"--progress": `${bar.val}%`}} />
                    </div>
                  </div>
                ))}
              </div>

              <div className="bg-gray-50 rounded-lg p-3 mb-3 flex gap-2">
                <svg className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" /></svg>
                <div>
                  <p className="text-xs font-semibold text-gray-900 mb-0.5">Virtual Agent Notes</p>
                  <p className="text-xs text-gray-600">{d.note}</p>
                </div>
              </div>

              <div className="flex gap-2">
                <button className="text-xs px-4 py-1.5 bg-red-600 text-white rounded-lg hover:bg-red-700 font-medium">Schedule Session</button>
                <button className="text-xs px-4 py-1.5 border border-gray-200 text-gray-700 rounded-lg hover:bg-gray-50 font-medium">View Full Report</button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function SessionsPage() {
  const [tab, setTab] = useState('upcoming');

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Sessions</h1>
          <p className="text-sm text-gray-500 mt-0.5">Manage counseling sessions and appointments</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="18" rx="2" strokeWidth={2} /><line x1="16" y1="2" x2="16" y2="6" strokeWidth={2} strokeLinecap="round" /><line x1="8" y1="2" x2="8" y2="6" strokeWidth={2} strokeLinecap="round" /></svg>
          Schedule New Session
        </button>
      </div>

      {/* Today's schedule */}
      <div className="bg-red-50 border border-red-100 rounded-xl p-5 mb-5">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Today's Schedule</h3>
        <div className="space-y-3">
          {MOCK_SESSIONS_TODAY.map((s, i) => (
            <div key={i} className="bg-white rounded-lg px-4 py-3 flex items-center justify-between border border-red-100">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 bg-red-600 rounded-lg flex items-center justify-center">
                  <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" strokeWidth={2} /><polyline strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} points="12 6 12 12 16 14" /></svg>
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-900">{s.student}</p>
                  <p className="text-xs text-gray-500">{s.time} • {s.type}</p>
                </div>
              </div>
              <button className="text-xs px-4 py-1.5 rounded-lg font-medium bg-gray-900 text-white flex items-center gap-1.5">
                {s.type === 'Chat' && (
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" /></svg>
                )}
                {s.type === 'Virtual' && (
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.277A1 1 0 0121 8.723v6.554a1 1 0 01-1.447.894L15 14m0 0V10m0 4H5a2 2 0 01-2-2v-4a2 2 0 012-2h10" /></svg>
                )}
                {s.action}
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Tab */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
        <div className="flex border-b border-gray-100">
          {['upcoming', 'past'].map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`flex-1 py-3 text-sm font-medium transition-colors capitalize ${tab === t ? 'bg-gray-100 text-gray-900' : 'text-gray-500 hover:text-gray-700'}`}
            >
              {t === 'upcoming' ? 'Upcoming Sessions' : 'Past Sessions'}
            </button>
          ))}
        </div>

        <div className="divide-y divide-gray-50">
          {tab === 'upcoming' ? MOCK_UPCOMING.map((s, i) => (
            <div key={i} className="p-5">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-sm font-bold text-gray-900">{s.student}</span>
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium flex items-center gap-1 ${s.status === 'Confirmed' ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}`}>
                  {s.status === 'Confirmed' && <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>}
                  {s.status}
                </span>
              </div>
              <p className="text-xs text-gray-500 mb-3">{s.purpose}</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2 mb-3 text-xs text-gray-500">
                <span className="flex items-center gap-1"><svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="18" rx="2" strokeWidth={2} /><line x1="3" y1="10" x2="21" y2="10" strokeWidth={2} /></svg>{s.date}</span>
                <span className="flex items-center gap-1"><svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" strokeWidth={2} /><polyline strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} points="12 6 12 12 16 14" /></svg>{s.time}</span>
                <span className="flex items-center gap-1"><svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a2 2 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" /></svg>{s.type}</span>
                <span className="flex items-center gap-1"><svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a2 2 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" /></svg>{s.location}</span>
              </div>
              <div className="flex gap-2">
                <button className="text-xs px-3 py-1.5 bg-red-600 text-white rounded-lg hover:bg-red-700 font-medium">View Details</button>
                <button className="text-xs px-3 py-1.5 border border-gray-200 text-gray-700 rounded-lg hover:bg-gray-50 font-medium">Reschedule</button>
                <button className="text-xs px-3 py-1.5 border border-gray-200 text-gray-700 rounded-lg hover:bg-gray-50 font-medium">Cancel</button>
              </div>
            </div>
          )) : (
            <div className="p-10 text-center text-xs text-gray-400">No past sessions to display.</div>
          )}
        </div>
      </div>
    </div>
  );
}

function ReportsPage() {
  const stats = [
    { label: 'Average Response Time', value: '2.4 hours', sub: '▼ 12%', subColor: 'text-red-500' },
    { label: 'Session Completion Rate', value: '94%', sub: '▲ 5%', subColor: 'text-green-600' },
    { label: 'Student Satisfaction', value: '4.7/5', sub: '— No change', subColor: 'text-gray-400' },
    { label: 'Early Detection Rate', value: '87%', sub: '▲ 8%', subColor: 'text-green-600' },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Reports & Analytics</h1>
          <p className="text-sm text-gray-500 mt-0.5">Comprehensive analysis of guidance system performance</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
          Export Report
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {stats.map((s) => (
          <div key={s.label} className="bg-white rounded-xl border border-gray-100 p-5 shadow-sm">
            <p className="text-xs text-gray-500 mb-1">{s.label}</p>
            <p className="text-xl font-bold text-gray-900">{s.value}</p>
            <p className={`text-xs mt-0.5 ${s.subColor}`}>{s.sub}</p>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-xl border border-gray-100 p-5 shadow-sm mb-5">
        <h3 className="text-sm font-semibold text-gray-900 mb-4">Monthly Trends</h3>
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={monthlyTrendData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="month" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Line type="monotone" dataKey="students" stroke="#111827" strokeWidth={2} dot={{ r: 3 }} />
            <Line type="monotone" dataKey="sessions" stroke="#9ca3af" strokeWidth={2} dot={{ r: 3 }} />
            <Line type="monotone" dataKey="alerts" stroke="#ef4444" strokeWidth={2} dot={{ r: 3 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
        <div className="bg-white rounded-xl border border-gray-100 p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Anxiety Levels by Program</h3>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={[
              { program: 'CS', high: 8, moderate: 12, low: 20 },
              { program: 'Psych', high: 6, moderate: 9, low: 15 },
              { program: 'Nursing', high: 4, moderate: 11, low: 18 },
              { program: 'BusAd', high: 5, moderate: 8, low: 22 },
            ]}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="program" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="high" stackId="a" fill="#ef4444" />
              <Bar dataKey="moderate" stackId="a" fill="#f59e0b" />
              <Bar dataKey="low" stackId="a" fill="#22c55e" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white rounded-xl border border-gray-100 p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Intervention Effectiveness</h3>
          <div className="space-y-3">
            {[
              { label: 'Cognitive Behavioral Therapy', value: 78 },
              { label: 'Mindfulness Sessions', value: 65 },
              { label: 'Group Counseling', value: 54 },
              { label: 'Crisis Intervention', value: 89 },
            ].map((item) => (
              <div key={item.label}>
                <div className="flex justify-between mb-1">
                  <span className="text-xs text-gray-600">{item.label}</span>
                  <span className="text-xs font-semibold text-gray-900">{item.value}%</span>
                </div>
                <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div className="h-full bg-red-600 rounded-full progress-bar" style={{"--progress": `${item.value}%`}} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────
export default function CounselorDashboard() {
  const navigate = useNavigate();
  const [activePage, setActivePage] = useState('overview');
  const alerts = MOCK_ALERTS;

  const logout = () => {
    localStorage.removeItem('counselor_token');
    localStorage.removeItem('counselorData');
    navigate('/counselor-login');
  };

  const counselor = JSON.parse(localStorage.getItem('counselorData') || '{}');
  const initials = counselor.name ? counselor.name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase() : 'CR';

  const [expanded, setExpanded] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);

  return (
    <div className="min-h-screen bg-gray-50 flex overflow-hidden">

      {/* Overlay when expanded */}
      {expanded && !profileOpen && (
        <div
          className="fixed inset-0 bg-black/20 z-20"
          onClick={() => setExpanded(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={`
        fixed top-0 left-0 h-full z-30 bg-gray-800 flex flex-col shadow-lg
        transition-all duration-300 ease-in-out
        ${expanded ? 'w-56' : 'w-14'}
      `}>
        {/* Logo area — click avatar to open profile panel */}
        <div className="h-14 flex items-center justify-center flex-shrink-0 border-b border-gray-700">
          <button
            onClick={() => setProfileOpen(true)}
            className="flex items-center gap-0 focus:outline-none group"
          >
            <img
              src="https://www.ue.edu.ph/mla/wp-content/uploads/2023/04/uesocialogp.png"
              alt="UE"
              className="w-8 h-8 rounded-full object-cover object-right border-2 border-red-500 flex-shrink-0 group-hover:border-white transition-colors"
            />
            {expanded && (
              <span className="text-white font-bold text-sm tracking-wide ml-3 whitespace-nowrap overflow-hidden">GAIDA</span>
            )}
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 py-3 overflow-y-auto overflow-x-hidden">
          {NAV.map((navItem) => {
            const active = activePage === navItem.id;
            const NavIcon = navItem.icon;
            return (
              <button
                key={navItem.id}
                onClick={() => { setActivePage(navItem.id); setExpanded(false); }}
                title={!expanded ? navItem.label : undefined}
                className={`w-full flex items-center px-4 py-3 transition-colors relative group ${
                  active
                    ? 'bg-red-600 text-white'
                    : 'text-gray-400 hover:bg-gray-700 hover:text-white'
                }`}
              >
                <span className="flex-shrink-0"><NavIcon active={active} /></span>
                {expanded && (
                  <span className="ml-3 text-sm font-medium whitespace-nowrap overflow-hidden">{navItem.label}</span>
                )}
                {/* Tooltip when collapsed */}
                {!expanded && (
                  <span className="absolute left-14 bg-gray-900 text-white text-xs px-2 py-1 rounded whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50 shadow-lg">
                    {navItem.label}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Bottom: expand toggle */}
        <div className="border-t border-gray-700 flex-shrink-0">
          <button
            onClick={() => setExpanded(!expanded)}
            className="w-full flex items-center px-4 py-3 text-gray-400 hover:bg-gray-700 hover:text-white transition-colors"
            title={!expanded ? 'Expand' : undefined}
          >
            <span className="flex-shrink-0">
              <svg
                className={`w-4 h-4 transition-transform duration-300 ${expanded ? 'rotate-180' : ''}`}
                fill="none" stroke="currentColor" viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </span>
            {expanded && <span className="ml-3 text-sm font-medium">Collapse</span>}
          </button>
        </div>
      </aside>

      {/* Profile flyout panel */}
      {profileOpen && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setProfileOpen(false)}
          />
          <div className="fixed top-0 left-14 h-full w-72 bg-white shadow-2xl z-50 flex flex-col">
            {/* Close button */}
            <div className="flex justify-end p-3 border-b border-gray-100">
              <button
                onClick={() => setProfileOpen(false)}
                className="w-8 h-8 flex items-center justify-center rounded-lg border border-gray-200 text-gray-500 hover:bg-gray-50 text-sm font-bold"
              >
                ✕
              </button>
            </div>

            {/* Profile info */}
            <div className="flex flex-col items-center py-6 px-4 border-b border-gray-100">
              <div className="w-16 h-16 bg-red-600 rounded-full flex items-center justify-center mb-3 shadow-lg">
                <span className="text-white text-xl font-bold">{initials}</span>
              </div>
              <p className="text-sm font-bold text-gray-900 uppercase tracking-wide text-center">
                {counselor.name || 'Test Counselor'}
              </p>
              <p className="text-xs text-gray-500 mt-0.5">University of the East</p>
              <button
                onClick={() => { logout(); setProfileOpen(false); }}
                className="mt-4 px-6 py-1.5 border border-gray-300 rounded text-sm text-gray-700 hover:bg-gray-50 transition-colors"
              >
                Logout
              </button>
            </div>

            {/* Quick links */}
            <nav className="flex-1 overflow-y-auto py-2">
              {[
                { label: 'Profile', icon: 'M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z' },
                { label: 'Notifications', icon: 'M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9' },
                { label: 'Settings', icon: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z' },
                { label: 'Help & Support', icon: 'M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z' },
              ].map((item) => (
                <button
                  key={item.label}
                  className="w-full flex items-center gap-3 px-5 py-3 text-sm text-red-600 hover:bg-gray-50 transition-colors text-left"
                >
                  <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d={item.icon} />
                  </svg>
                  {item.label}
                </button>
              ))}
            </nav>

            {/* Footer */}
            <div className="p-4 border-t border-gray-100">
              <p className="text-xs text-gray-400 text-center">GAIDA v1.0 — University of the East</p>
            </div>
          </div>
        </>
      )}

      {/* Main content — offset by collapsed sidebar width */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden ml-14">
        <main className="flex-1 overflow-y-auto">
          <div className="w-full max-w-6xl mx-auto p-4 sm:p-6">
            {activePage === 'overview' && <OverviewPage alerts={alerts} />}
            {activePage === 'students' && <StudentsPage />}
            {activePage === 'detection' && <DetectionPage />}
            {activePage === 'sessions' && <SessionsPage />}
            {activePage === 'reports' && <ReportsPage />}
          </div>
        </main>
      </div>

      {/* Help button */}
      <button className="fixed bottom-6 right-6 w-10 h-10 bg-gray-800 text-white rounded-full flex items-center justify-center shadow-lg hover:bg-gray-700 transition-colors z-10">
        <span className="text-sm font-bold">?</span>
      </button>
    </div>
  );
}