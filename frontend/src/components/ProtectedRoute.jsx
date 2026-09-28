import { Navigate } from 'react-router-dom';

/**
 * Route protection guard for authenticated routes.
 * Redirects unauthenticated access before lazy-loading or mounting components.
 */
export default function ProtectedRoute({ type, children }) {
  if (type === 'student') {
    const token = localStorage.getItem('session_token');
    const consent = localStorage.getItem('consent_given');
    if (!token) {
      return <Navigate to="/student-login" replace />;
    }
    if (!consent) {
      return <Navigate to="/consent" replace />;
    }
  }

  if (type === 'consent') {
    const token = localStorage.getItem('session_token');
    if (!token) {
      return <Navigate to="/student-login" replace />;
    }
  }

  if (type === 'counselor') {
    const token = localStorage.getItem('counselor_token');
    if (!token) {
      return <Navigate to="/counselor-login" replace />;
    }
  }

  if (type === 'research_sus') {
    const sessionId = localStorage.getItem('session_id');
    const sessionToken = localStorage.getItem('session_token');
    if (!sessionId || !sessionToken) {
      return <Navigate to="/research" replace />;
    }
  }

  return children;
}
