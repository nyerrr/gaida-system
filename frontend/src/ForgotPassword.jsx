import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

export default function ForgotPassword() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const role = searchParams.get('role') || 'student';

  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const isStudent = role === 'student';
  const backRoute = isStudent ? '/student-login' : '/counselor-login';
  const placeholder = isStudent ? 'yourname@ue.edu.ph' : 'facultyname@ue.edu.ph';
  const label = isStudent ? 'UE Email Address' : 'Faculty UE Email Address';

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!email.endsWith('@ue.edu.ph')) {
      setError('Please enter a valid UE email address (@ue.edu.ph).');
      return;
    }

    setLoading(true);

    try {
      const response = await fetch('http://localhost:8000/api/auth/forgot-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, role }),
      });

      if (response.ok) {
        setSubmitted(true);
      } else {
        const data = await response.json();
        setError(data.detail || 'Failed to send reset link. Please try again.');
      }
    } catch {
      // Show success even on connection error so users can't enumerate emails
      setSubmitted(true);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen relative overflow-hidden flex items-center justify-center">

      {/* Full bleed UE background */}
      <div className="absolute inset-0 ue-bg" />

      {/* White card */}
      <div className="relative z-10 bg-white rounded-2xl shadow-2xl p-10 w-full max-w-md mx-4">

        {/* Logo */}
        <div className="flex flex-col items-center mb-7">
          <img
            src="https://www.ue.edu.ph/mla/wp-content/uploads/2023/04/uesocialogp.png"
            alt="University of the East"
            className="w-20 h-20 object-cover object-right rounded-full mb-4 shadow-lg border-4 border-red-700"
          />
          <h2 className="text-2xl font-bold text-gray-900">Forgot Password</h2>
          <p className="text-gray-400 text-sm mt-1 text-center">
            {isStudent ? 'Enter your UE email to receive a reset link' : 'Enter your faculty UE email to receive a reset link'}
          </p>
        </div>

        {!submitted ? (
          <>
            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-xl text-red-700 text-xs">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="email" className="block text-gray-700 text-sm font-medium mb-1.5">
                  {label}
                </label>
                <input
                  type="email"
                  id="email"
                  placeholder={placeholder}
                  value={email}
                  onChange={(e) => { setEmail(e.target.value); setError(''); }}
                  className="w-full px-4 py-2.5 text-sm bg-gray-50 border border-gray-200 rounded-xl text-gray-900 placeholder-gray-400 focus:outline-none focus:border-red-500 focus:ring-2 focus:ring-red-100 transition-colors"
                  required
                  disabled={loading}
                />
              </div>

              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => navigate(backRoute)}
                  className="flex-1 border-2 border-gray-200 hover:border-red-400 hover:bg-red-50 text-gray-600 hover:text-red-600 font-semibold py-3 px-4 text-sm rounded-xl transition-all duration-200"
                >
                  Back
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="flex-1 bg-red-700 hover:bg-red-800 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-3 px-4 text-sm rounded-xl transition-colors duration-200 shadow"
                >
                  {loading ? 'Sending...' : 'Send Reset Link'}
                </button>
              </div>
            </form>
          </>
        ) : (
          /* Success state */
          <div className="text-center">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h3 className="text-lg font-bold text-gray-900 mb-2">Check your email</h3>
            <p className="text-gray-500 text-sm mb-1">
              If <span className="font-medium text-gray-700">{email}</span> is registered, a reset link has been sent.
            </p>
            <p className="text-gray-400 text-xs mb-6">
              Check your spam folder if you don't see it within a few minutes.
            </p>
            <button
              onClick={() => navigate(backRoute)}
              className="w-full bg-red-700 hover:bg-red-800 text-white font-semibold py-3 px-4 text-sm rounded-xl transition-colors duration-200 shadow"
            >
              Back to Login
            </button>
          </div>
        )}

        <div className="mt-5 text-center">
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