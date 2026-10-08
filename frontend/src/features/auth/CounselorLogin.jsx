import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import GoogleSignIn from '../../components/GoogleSignIn';
import { BACKEND_URL } from '../../config';

export default function CounselorLogin() {
  const navigate = useNavigate();
  const [facultyId, setFacultyId] = useState('');
  const [password, setPassword] = useState('');
  const [antibot, setAntibot] = useState('');
  const [captchaToken, setCaptchaToken] = useState('');
  const [captchaImage, setCaptchaImage] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    loadCaptcha();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- single mount-time load
  }, []);

  // The verification image is drawn and checked by the server; the browser
  // only shows it and sends back the typed code with the signed token.
  const loadCaptcha = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/auth/captcha`, { cache: 'no-store' });
      if (!res.ok) throw new Error(String(res.status));
      const data = await res.json();
      setCaptchaToken(data.token);
      setCaptchaImage(data.image);
    } catch {
      setCaptchaToken('');
      setCaptchaImage('');
      setError('Could not load the verification image. Please press refresh.');
    }
  };

  const handleRefreshCaptcha = () => {
    loadCaptcha();
    setAntibot('');
  };

  const handleGoogleCredential = async (credential) => {
    if (loading) return;
    setLoading(true);
    setError('');
    try {
      const response = await fetch(`${BACKEND_URL}/api/auth/google`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ credential, role: 'counselor' }),
      });
      const data = await response.json();
      if (response.ok) {
        const name = decodeGoogleName(credential);
        // A stale student session_token shadows the counselor token in
        // apiFetch's getAuthToken() and silently 403s every counselor request.
        localStorage.removeItem('session_token');
        localStorage.setItem('counselor_token', data.session_token);
        localStorage.setItem('counselorData', JSON.stringify({
          id: data.student_id,
          name,
          role: 'counselor',
        }));
        navigate('/counselor-dashboard');
      } else {
        setError(data.detail || 'Google sign-in failed. Please try again.');
      }
    } catch {
      setError('Connection error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const decodeGoogleName = (credential) => {
    try {
      const payload = credential.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
      return JSON.parse(atob(payload)).name || 'Counselor';
    } catch {
      return 'Counselor';
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!captchaToken) {
      setError('Verification image not loaded. Please press refresh.');
      return;
    }
    setLoading(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/auth/counselor-login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ faculty_id: facultyId, password, antibot, captcha_token: captchaToken }),
      });
      const data = await response.json();
      if (response.ok) {
        // A stale student session_token shadows the counselor token in
        // apiFetch's getAuthToken() and silently 403s every counselor request.
        localStorage.removeItem('session_token');
        localStorage.setItem('counselor_token', data.session_token);
        localStorage.setItem('counselorData', JSON.stringify({
          id: data.student_id,
          name: data.name || 'Counselor',
          role: 'counselor',
        }));
        navigate('/counselor-dashboard');
      } else {
        setError(data.detail || 'Invalid credentials. Please check your faculty ID and password.');
        handleRefreshCaptcha();
        setLoading(false);
      }
    } catch (err) {
      setError('An error occurred during login. Please try again.');
      console.error('Login error:', err);
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen relative overflow-hidden flex items-center justify-center" style={{position:'relative'}}>

      {/* Full bleed UE background */}
      <div
        className="absolute inset-0 bg-center bg-cover bg-no-repeat"
        style={{ backgroundImage: "url('/images/ue-background.png')" }}
      >
        <div className="absolute inset-0 bg-black/60 backdrop-blur-sm"></div>
      </div>

      {/* White card */}
      <div className="relative z-10 bg-white rounded-2xl shadow-2xl p-6 sm:p-7 w-full max-w-sm mx-4">

        {/* Logo */}
        <div className="flex flex-col items-center mb-7">
          <img
            src="/images/ue-logo.png"
            alt="University of the East"
            className="w-20 h-20 object-cover object-right rounded-full mb-4 shadow-lg border-4 border-red-700"
          />
          <h2 className="text-2xl font-bold text-gray-900">Counselor Login</h2>
          <p className="text-gray-400 text-sm mt-1">Sign in to access the dashboard</p>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-xl text-red-700 text-xs">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="facultyId" className="block text-gray-700 text-sm font-medium mb-1.5">Faculty ID</label>
            <input
              type="text"
              id="facultyId"
              placeholder="Enter your faculty ID"
              value={facultyId}
              onChange={(e) => setFacultyId(e.target.value)}
              required
              disabled={loading}
              className="w-full px-4 py-2.5 text-base sm:text-sm bg-gray-50 border border-gray-200 rounded-xl text-gray-900 placeholder-gray-400 focus:outline-none focus:border-red-500 focus:ring-2 focus:ring-red-100 transition-colors disabled:opacity-50"
            />
          </div>

          <div>
            <div className="flex justify-between mb-1.5">
              <label htmlFor="password" className="block text-gray-700 text-sm font-medium">Password</label>
              <Link to="/forgot-password?role=counselor" className="text-red-600 hover:text-red-700 text-xs transition-colors">Forgot Password?</Link>
            </div>
            <input
              type="password"
              id="password"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={loading}
              className="w-full px-4 py-2.5 text-base sm:text-sm bg-gray-50 border border-gray-200 rounded-xl text-gray-900 placeholder-gray-400 focus:outline-none focus:border-red-500 focus:ring-2 focus:ring-red-100 transition-colors disabled:opacity-50"
            />
          </div>

          <div>
            <label htmlFor="antibot" className="block text-gray-700 text-sm font-medium mb-1.5">Verification Code</label>
            <input
              type="text"
              id="antibot"
              placeholder="Type the code shown below"
              value={antibot}
              onChange={(e) => setAntibot(e.target.value)}
              autoComplete="off"
              required
              disabled={loading}
              className="w-full px-4 py-2.5 text-base sm:text-sm bg-gray-50 border border-gray-200 rounded-xl text-gray-900 placeholder-gray-400 focus:outline-none focus:border-red-500 focus:ring-2 focus:ring-red-100 transition-colors disabled:opacity-50"
            />
            {(
              <div className="flex items-center gap-3 mt-2">
                {captchaImage ? (
                  <img
                    src={captchaImage}
                    alt="Verification code"
                    width={150}
                    height={50}
                    draggable={false}
                    className="rounded-lg border border-gray-200"
                  />
                ) : (
                  <div style={{ width: 150, height: 50 }} className="rounded-lg border border-gray-200 bg-gray-100" aria-hidden="true" />
                )}
                <button
                  type="button"
                  onClick={handleRefreshCaptcha}
                  disabled={loading}
                  className="flex items-center gap-1.5 text-gray-400 hover:text-red-600 text-xs transition-colors"
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  Refresh
                </button>
              </div>
            )}
          </div>

          <div className="flex gap-3">
            <button
              type="button"
              onClick={() => navigate('/')}
              className="flex-1 border-2 border-gray-200 hover:border-red-400 hover:bg-red-50 text-gray-600 hover:text-red-600 font-semibold py-3 px-4 text-sm rounded-xl transition-all duration-200"
            >
              Back
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 bg-red-700 hover:bg-red-800 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-3 px-4 text-sm rounded-xl transition-colors duration-200 shadow"
            >
              {loading ? 'Signing in...' : 'Log In'}
            </button>
          </div>
        </form>

        {/* Google SSO */}
        {import.meta.env.VITE_GOOGLE_CLIENT_ID && (
          <>
            <div className="relative my-4">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-200"></div>
              </div>
              <div className="relative flex justify-center">
                <span className="px-3 bg-white text-gray-400 text-xs">or</span>
              </div>
            </div>

            <GoogleSignIn
              clientId={import.meta.env.VITE_GOOGLE_CLIENT_ID}
              onCredential={handleGoogleCredential}
              text="signin_with"
            />
          </>
        )}

        <div className="mt-5 text-center">
          <div className="flex justify-center gap-4 text-xs text-gray-500">
            <Link to="/student-login" className="hover:text-red-700 transition-colors font-medium">Student Portal</Link>
            <span>·</span>
            <Link to="/informed-consent" className="hover:text-red-700 transition-colors font-medium">Privacy & Consent</Link>
          </div>
        </div>
      </div>
    </div>
  );
}