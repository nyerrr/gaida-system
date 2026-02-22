import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';

const API_BASE = 'http://localhost:8000';

export default function CounselorDashboard() {
  const navigate = useNavigate();
  const [alerts, setAlerts] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [toast, setToast] = useState('');

  // Guard: redirect if not logged in
  useEffect(() => {
    const token = localStorage.getItem('counselor_token');
    if (!token) navigate('/counselor-login');
  }, [navigate]);

  const showToast = (msg) => {
    setToast(msg);
    setTimeout(() => setToast(''), 3000);
  };

  const fetchAlerts = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/counselor/alerts`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setAlerts(data.alerts || []);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err) {
      showToast(`Could not load alerts: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchSessions = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/session/active`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setSessions(data || []);
    } catch {
      // fail silently for sessions
    }
  }, []);

  useEffect(() => {
    fetchAlerts();
    fetchSessions();
    const interval = setInterval(() => {
      fetchAlerts();
      fetchSessions();
    }, 30000);
    return () => clearInterval(interval);
  }, [fetchAlerts, fetchSessions]);

  const resolveAlert = async (sessionId) => {
    try {
      await fetch(`${API_BASE}/api/counselor/alerts/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, status: 'resolved' }),
      });
      showToast('Alert marked as resolved.');
      fetchAlerts();
    } catch {
      showToast('Failed to update alert.');
    }
  };

  const markReviewed = async (sessionId) => {
    try {
      await fetch(`${API_BASE}/api/counselor/alerts/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, status: 'reviewed' }),
      });
      showToast('Alert marked as reviewed.');
      fetchAlerts();
    } catch {
      showToast('Failed to update alert.');
    }
  };

  const logout = () => {
    localStorage.removeItem('counselor_token');
    localStorage.removeItem('counselor_id');
    navigate('/counselor-login');
  };

  // Stats
  const pending  = alerts.filter(a => a.status === 'pending').length;
  const moderate = alerts.filter(a => a.severity === 'Moderate').length;
  const resolved = alerts.filter(a => a.status === 'resolved').length;
  const highCount = alerts.filter(a => a.severity === 'High').length;

  const sortedAlerts = [...alerts].sort((a, b) => {
    const order = { High: 0, Moderate: 1, Low: 2 };
    if (a.status === 'pending' && b.status !== 'pending') return -1;
    if (b.status === 'pending' && a.status !== 'pending') return 1;
    return (order[a.severity] ?? 3) - (order[b.severity] ?? 3);
  });

  const severityDot = (s) => {
    if (s === 'High') return 'bg-red-500 shadow-red-500/50';
    if (s === 'Moderate') return 'bg-yellow-500';
    return 'bg-emerald-500';
  };

  const severityBadge = (s) => {
    if (s === 'High') return 'bg-red-900/40 text-red-400 border border-red-700/50';
    if (s === 'Moderate') return 'bg-yellow-900/40 text-yellow-400 border border-yellow-700/50';
    return 'bg-emerald-900/30 text-emerald-400 border border-emerald-700/40';
  };

  const statusBadge = (s) => {
    if (s === 'pending') return 'bg-yellow-900/30 text-yellow-400 border border-yellow-700/30';
    if (s === 'reviewed') return 'bg-blue-900/30 text-blue-400 border border-blue-700/30';
    return 'bg-gray-800 text-gray-500 border border-gray-700';
  };

  const intentBadge = 'bg-blue-900/30 text-blue-400 border border-blue-700/30';

  const formatTime = (ts) => {
    if (!ts) return '';
    return new Date(ts).toLocaleString('en-PH', {
      month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  };

  const severityFromIntent = (intent) => {
    if (['suicidal', 'anxiety'].includes(intent)) return 'High';
    if (['stress', 'sadness'].includes(intent)) return 'Moderate';
    return 'Low';
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 font-mono flex flex-col">

      {/* Header */}
      <header className="bg-gray-900 border-b border-gray-800 px-6 py-4 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></div>
          <span className="text-white font-bold tracking-widest text-sm">GAIDA COUNSELOR DASHBOARD</span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-xs bg-blue-900/30 text-blue-400 border border-blue-700/30 px-3 py-1 rounded-full tracking-widest uppercase">Live</span>
          <button
            onClick={logout}
            className="text-xs text-gray-500 hover:text-gray-300 border border-gray-700 hover:border-gray-500 px-3 py-1.5 rounded-lg transition-colors"
          >
            Logout
          </button>
        </div>
      </header>

      <main className="flex-1 p-6 max-w-7xl mx-auto w-full">
        <div className="mb-6">
          <p className="text-xs text-gray-600 uppercase tracking-widest mb-1">Guidance AI Detection Assistant</p>
          <h1 className="text-2xl font-bold text-white">Session Monitor & Alert Center</h1>
        </div>

        {/* Stat Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {[
            { label: 'Total Alerts', value: alerts.length, color: 'text-blue-400', border: 'border-blue-900/50' },
            { label: 'Pending', value: pending, color: 'text-red-400', border: 'border-red-900/50' },
            { label: 'Moderate Cases', value: moderate, color: 'text-yellow-400', border: 'border-yellow-900/50' },
            { label: 'Resolved', value: resolved, color: 'text-emerald-400', border: 'border-emerald-900/50' },
          ].map((s) => (
            <div key={s.label} className={`bg-gray-900 border ${s.border} rounded-xl p-4`}>
              <p className="text-xs text-gray-600 uppercase tracking-widest mb-2">{s.label}</p>
              <p className={`text-3xl font-bold ${s.color}`}>{s.value}</p>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">

          {/* Priority Alerts */}
          <div className="lg:col-span-2 bg-gray-900 border border-gray-800 rounded-xl overflow-hidden flex flex-col">
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-800">
              <span className="text-sm font-semibold text-white">Priority Alerts</span>
              <span className="text-xs bg-red-900/30 text-red-400 border border-red-700/30 px-2.5 py-1 rounded-full">{highCount} High</span>
            </div>

            <div className="flex-1 overflow-y-auto divide-y divide-gray-800/60">
              {loading && (
                <div className="p-8 text-center text-gray-600 text-xs">Loading alerts...</div>
              )}
              {!loading && sortedAlerts.length === 0 && (
                <div className="p-10 text-center">
                  <div className="text-3xl mb-2 opacity-30">✓</div>
                  <p className="text-gray-600 text-xs">No alerts at this time.</p>
                </div>
              )}
              {sortedAlerts.map((a) => (
                <div key={a.session_id} className="px-5 py-4 hover:bg-gray-800/40 transition-colors">
                  <div className="flex items-start gap-3">
                    <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 shadow-lg ${severityDot(a.severity)}`}></div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap mb-1.5">
                        <span className="text-xs text-gray-500">{a.session_id.substring(0, 8)}…</span>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${severityBadge(a.severity)}`}>{a.severity}</span>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${intentBadge}`}>{a.intent}</span>
                        <span className={`text-xs px-2 py-0.5 rounded-full ml-auto ${statusBadge(a.status)}`}>{a.status}</span>
                      </div>
                      <p className="text-sm text-gray-300 truncate mb-1" title={a.message}>{a.message}</p>
                      <p className="text-xs text-gray-600">{formatTime(a.timestamp)}</p>
                      {a.status === 'pending' && (
                        <div className="flex gap-2 mt-2">
                          <button
                            onClick={() => markReviewed(a.session_id)}
                            className="text-xs px-3 py-1 rounded-lg border border-blue-700/40 text-blue-400 hover:bg-blue-900/30 transition-colors"
                          >
                            Mark Reviewed
                          </button>
                          <button
                            onClick={() => resolveAlert(a.session_id)}
                            className="text-xs px-3 py-1 rounded-lg border border-emerald-700/40 text-emerald-400 hover:bg-emerald-900/30 transition-colors"
                          >
                            Resolve
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div className="px-5 py-3 border-t border-gray-800 flex items-center justify-between">
              <span className="text-xs text-gray-600">
                {lastUpdated ? `Updated ${lastUpdated}` : 'Not yet updated'}
              </span>
              <button
                onClick={() => { fetchAlerts(); fetchSessions(); }}
                className="text-xs text-blue-400 hover:text-blue-300 uppercase tracking-widest transition-colors"
              >
                Refresh
              </button>
            </div>
          </div>

          {/* Active Sessions */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden flex flex-col">
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-800">
              <span className="text-sm font-semibold text-white">Active Sessions</span>
              <span className="text-xs bg-blue-900/30 text-blue-400 border border-blue-700/30 px-2.5 py-1 rounded-full">{sessions.length}</span>
            </div>

            <div className="flex-1 overflow-y-auto divide-y divide-gray-800/60">
              {sessions.length === 0 && (
                <div className="p-10 text-center">
                  <div className="text-3xl mb-2 opacity-30">○</div>
                  <p className="text-gray-600 text-xs">No active sessions.</p>
                </div>
              )}
              {sessions.map((s) => {
                const intent = s.meta?.last_intent || 'neutral';
                const sev = severityFromIntent(intent);
                return (
                  <div key={s.session_id} className="px-5 py-3 hover:bg-gray-800/40 transition-colors flex items-center gap-3">
                    <div className={`w-2 h-2 rounded-full flex-shrink-0 ${severityDot(sev)}`}></div>
                    <span className="text-xs text-gray-500 flex-1 truncate">{s.session_id.substring(0, 16)}…</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${severityBadge(sev)}`}>{sev}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${intentBadge}`}>{intent}</span>
                  </div>
                );
              })}
            </div>

            <div className="px-5 py-3 border-t border-gray-800">
              <p className="text-xs text-gray-600 text-center">Auto-refreshes every 30 seconds</p>
            </div>
          </div>

        </div>
      </main>

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-6 right-6 bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 text-sm text-white shadow-xl z-50 max-w-xs animate-pulse">
          {toast}
        </div>
      )}
    </div>
  );
}