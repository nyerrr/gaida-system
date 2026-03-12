import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

export default function StudentLogin() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    student_number: '',
    email: '',
    access_code: '',
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    const { id, value } = e.target;
    setFormData(prev => ({ ...prev, [id]: value }));
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const response = await fetch('http://localhost:8000/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      const data = await response.json();
      if (response.ok) {
        localStorage.setItem('session_token', data.session_token);
        localStorage.setItem('student_id', data.student_id);
        navigate('/consent');
      } else {
        setError(data.detail || 'Login failed. Please check your credentials.');
      }
    } catch {
      setError('Connection error. Make sure the backend is running on localhost:8000');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen relative overflow-hidden flex items-center justify-center">

      {/* Full bleed UE background */}
      <div
        className="absolute inset-0 bg-center bg-cover bg-no-repeat"
        style={{ backgroundImage: "url('https://www.ue.edu.ph/mla/wp-content/uploads/2023/04/uesocialogp.png')" }}
      />

      {/* White card */}
      <div className="relative z-10 bg-white rounded-2xl shadow-2xl p-10 w-full max-w-md mx-4">

        {/* Logo */}
        <div className="flex flex-col items-center mb-7">
          <img
            src="https://www.ue.edu.ph/mla/wp-content/uploads/2023/04/uesocialogp.png"
            alt="University of the East"
            className="w-20 h-20 object-cover object-right rounded-full mb-4 shadow-lg border-4 border-red-700"
          />
          <h2 className="text-2xl font-bold text-gray-900">Student Login</h2>
          <p className="text-gray-400 text-sm mt-1">Sign in to access your account</p>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-xl text-red-700 text-xs">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="student_number" className="block text-gray-700 text-sm font-medium mb-1.5">Student Number</label>
            <input
              type="text"
              id="student_number"
              placeholder="Enter your student number"
              value={formData.student_number}
              onChange={handleChange}
              className="w-full px-4 py-2.5 text-sm bg-gray-50 border border-gray-200 rounded-xl text-gray-900 placeholder-gray-400 focus:outline-none focus:border-red-500 focus:ring-2 focus:ring-red-100 transition-colors"
              required
            />
          </div>

          <div>
            <label htmlFor="email" className="block text-gray-700 text-sm font-medium mb-1.5">UE Email Address</label>
            <input
              type="email"
              id="email"
              placeholder="yourname@ue.edu.ph"
              value={formData.email}
              onChange={handleChange}
              className="w-full px-4 py-2.5 text-sm bg-gray-50 border border-gray-200 rounded-xl text-gray-900 placeholder-gray-400 focus:outline-none focus:border-red-500 focus:ring-2 focus:ring-red-100 transition-colors"
              required
            />
          </div>

          <div>
            <div className="flex justify-between mb-1.5">
              <label htmlFor="access_code" className="block text-gray-700 text-sm font-medium">Access Code</label>
              <a href="/forgot-password?role=student" className="text-red-600 hover:text-red-700 text-xs transition-colors">Forgot Password?</a>
            </div>
            <input
              type="password"
              id="access_code"
              placeholder="Enter your access code"
              value={formData.access_code}
              onChange={handleChange}
              className="w-full px-4 py-2.5 text-sm bg-gray-50 border border-gray-200 rounded-xl text-gray-900 placeholder-gray-400 focus:outline-none focus:border-red-500 focus:ring-2 focus:ring-red-100 transition-colors"
              required
            />
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
        <div className="relative my-4">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-gray-200"></div>
          </div>
          <div className="relative flex justify-center">
            <span className="px-3 bg-white text-gray-400 text-xs">or</span>
          </div>
        </div>

        <button
          type="button"
          className="w-full flex items-center justify-center gap-3 py-3 px-4 rounded-xl border-2 border-gray-200 hover:border-red-400 hover:bg-red-50 text-gray-700 text-sm font-medium transition-all duration-200"
        >
          <svg className="w-4 h-4" viewBox="0 0 24 24">
            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
          </svg>
          Continue with UE Gmail
        </button>

        <div className="mt-5 text-center space-y-2">
          <p className="text-gray-500 text-sm">
            New here?{' '}
            <a href="#" className="text-red-600 hover:text-red-700 font-medium transition-colors">Create an account</a>
          </p>
          <div className="flex justify-center gap-4 text-xs text-gray-400">
            <a href="#" className="hover:text-gray-600 transition-colors">Help</a>
            <a href="#" className="hover:text-gray-600 transition-colors">Privacy Policy</a>
            <a href="#" className="hover:text-gray-600 transition-colors">Terms</a>
          </div>
        </div>
      </div>
    </div>
  );
}