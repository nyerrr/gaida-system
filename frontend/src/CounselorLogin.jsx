import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';


export default function CounselorLogin() {
  const navigate = useNavigate();
  const [facultyId, setFacultyId] = useState('');
  const [password, setPassword] = useState('');
  const [antibot, setAntibot] = useState('');
  const [captchaText, setCaptchaText] = useState('');
  const [showCaptcha, setShowCaptcha] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const canvasRef = useRef(null);

  const generateCaptcha = () => {
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789';
    let text = '';
    for (let i = 0; i < 6; i++) {
      text += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    setCaptchaText(text);
    return text;
  };

  const drawCaptcha = (text) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = '#f0f0f0';
    ctx.fillRect(0, 0, width, height);
    for (let i = 0; i < 5; i++) {
      ctx.strokeStyle = `rgba(${Math.random()*255},${Math.random()*255},${Math.random()*255},0.3)`;
      ctx.beginPath();
      ctx.moveTo(Math.random()*width, Math.random()*height);
      ctx.lineTo(Math.random()*width, Math.random()*height);
      ctx.stroke();
    }
    for (let i = 0; i < 50; i++) {
      ctx.fillStyle = `rgba(${Math.random()*255},${Math.random()*255},${Math.random()*255},0.3)`;
      ctx.fillRect(Math.random()*width, Math.random()*height, 2, 2);
    }
    ctx.font = 'bold 28px Arial';
    ctx.textBaseline = 'middle';
    for (let i = 0; i < text.length; i++) {
      const x = 15 + i * 22;
      const y = height / 2;
      const angle = (Math.random() - 0.5) * 0.4;
      ctx.save();
      ctx.translate(x, y);
      ctx.rotate(angle);
      ctx.fillStyle = `rgb(${Math.random()*100},${Math.random()*100},${Math.random()*100})`;
      ctx.fillText(text[i], 0, 0);
      ctx.restore();
    }
  };

  const handleAntibotFocus = () => {
    if (!showCaptcha) {
      setShowCaptcha(true);
      setTimeout(() => {
        const text = generateCaptcha();
        drawCaptcha(text);
      }, 0);
    }
  };

  const handleRefreshCaptcha = () => {
    const text = generateCaptcha();
    drawCaptcha(text);
    setAntibot('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (antibot.toLowerCase() !== captchaText.toLowerCase()) {
      setError('Incorrect antibot code. Please try again.');
      return;
    }

    setLoading(true);

    try {
const TEST_COUNSELOR = { faculty_id: 'counselor01', password: 'counsel123', name: 'Test Counselor' };

if (facultyId !== TEST_COUNSELOR.faculty_id || password !== TEST_COUNSELOR.password) {
  setError('Invalid credentials. Please check your faculty ID and password.');
  setLoading(false);
  return;
}

const data = TEST_COUNSELOR;
      localStorage.setItem('counselor_token', 'dev-token');
      localStorage.setItem('counselorData', JSON.stringify(data));
      // FIX: route now matches App.jsx
      navigate('/counselor-dashboard');

    } catch (err) {
      setError('An error occurred during login. Please try again.');
      console.error('Login error:', err);
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Left side - Decorative */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-red-900 via-red-800 to-red-950 relative overflow-hidden">
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-20 left-20 w-96 h-96 border-4 border-white rotate-45"></div>
          <div className="absolute bottom-20 right-20 w-80 h-80 border-4 border-white rotate-12"></div>
          <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] border-8 border-white rotate-45"></div>
        </div>
        <div className="absolute inset-0 opacity-20">
          <svg className="w-full h-full" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="white" strokeWidth="0.5"/>
              </pattern>
            </defs>
            <rect width="100%" height="100%" fill="url(#grid)" />
          </svg>
        </div>
        <div className="relative z-10 flex items-center justify-center w-full p-16">
          <div className="text-white">
            <h1 className="text-6xl font-bold mb-4">GAIDA</h1>
            <p className="text-xl opacity-90">Counselor Portal</p>
          </div>
        </div>
      </div>

      {/* Right side - Login Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center bg-gray-900 p-4 lg:p-8">
        <div className="w-full max-w-md">
          <div className="text-center mb-4">
            <div className="w-16 h-16 mx-auto mb-3 bg-gradient-to-br from-red-700 via-red-600 to-red-800 rounded-full flex items-center justify-center shadow-xl relative">
              <div className="absolute -top-2 left-1/2 transform -translate-x-1/2 flex flex-col items-center">
                <div className="w-2 h-2 bg-white rounded-full shadow-lg"></div>
                <div className="w-0.5 h-3 bg-white"></div>
              </div>
              <div className="relative w-10 h-10 flex flex-col items-center justify-center">
                <div className="flex gap-2 mb-1">
                  <div className="w-1.5 h-1.5 bg-white rounded-full"></div>
                  <div className="w-1.5 h-1.5 bg-white rounded-full"></div>
                </div>
                <div className="w-5 h-2 border-b-2 border-white rounded-b-full"></div>
              </div>
            </div>
            <h2 className="text-white text-xl font-semibold mb-1">Welcome Back</h2>
            <p className="text-gray-400 text-xs">Sign in to access your dashboard</p>
          </div>

          <form className="space-y-3" onSubmit={handleSubmit}>
            {/* Error Message */}
            {error && (
              <div className="p-3 bg-red-900 border border-red-700 rounded-lg text-red-100 text-xs">
                {error}
              </div>
            )}

            <div>
              <label htmlFor="facultyId" className="block text-white text-xs font-medium mb-1">Faculty ID</label>
              <input
                type="text"
                id="facultyId"
                placeholder="Faculty ID"
                value={facultyId}
                onChange={(e) => setFacultyId(e.target.value)}
                required
                disabled={loading}
                className="w-full px-3 py-2 text-sm bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-red-600 focus:ring-1 focus:ring-red-600 transition-colors disabled:opacity-50"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-white text-xs font-medium mb-1">Password</label>
              <input
                type="password"
                id="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={loading}
                className="w-full px-3 py-2 text-sm bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-red-600 focus:ring-1 focus:ring-red-600 transition-colors disabled:opacity-50"
              />
            </div>

            <div>
              <label htmlFor="antibot" className="block text-white text-xs font-medium mb-1">Antibot Validation</label>
              <input
                type="text"
                id="antibot"
                placeholder="Enter the code below"
                value={antibot}
                onChange={(e) => setAntibot(e.target.value)}
                onFocus={handleAntibotFocus}
                autoComplete="off"
                required
                disabled={loading}
                className="w-full px-3 py-2 text-sm bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-red-600 focus:ring-1 focus:ring-red-600 transition-colors disabled:opacity-50"
              />
              <div className="flex items-center justify-between gap-3 mt-2 h-[50px]">
                <div className="flex-shrink-0">
                  {showCaptcha ? (
                    <canvas ref={canvasRef} width={150} height={50} className="border border-gray-700 rounded bg-gray-100" />
                  ) : (
                    <div className="w-[150px] h-[50px]"></div>
                  )}
                </div>
                <div className="flex flex-col gap-1.5">
                  <button
                    type="button"
                    onClick={handleRefreshCaptcha}
                    disabled={loading}
                    className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-white text-xs rounded transition-colors flex items-center gap-1.5 disabled:opacity-50"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    Refresh
                  </button>
                </div>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-red-700 hover:bg-red-600 text-white font-semibold py-2 px-4 text-sm rounded-lg transition-colors duration-200 shadow-lg mt-4 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Signing in...' : 'Sign In'}
            </button>

            <div className="relative my-3">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-700"></div>
              </div>
              <div className="relative flex justify-center text-xs">
                <span className="px-3 bg-gray-900 text-gray-400">or</span>
              </div>
            </div>

            <button
              type="button"
              disabled={loading}
              className="w-full bg-gray-800 hover:bg-gray-700 text-white font-medium py-2 px-3 text-sm rounded-lg transition-colors duration-200 border border-gray-700 flex items-center justify-center gap-2 disabled:opacity-50"
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24">
                <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              <span className="text-sm">Sign in with UE Gmail account</span>
            </button>
          </form>

          <div className="mt-4 text-center">
            <div className="flex justify-center gap-3 text-xs text-gray-500">
              <a href="#" className="hover:text-gray-300 transition-colors">Help</a>
              <span>•</span>
              <a href="#" className="hover:text-gray-300 transition-colors">Privacy Policy</a>
              <span>•</span>
              <a href="#" className="hover:text-gray-300 transition-colors">Terms</a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}