import { useNavigate } from 'react-router-dom'

export default function PortalSelection() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900 relative overflow-hidden">
      {/* Decorative Background Pattern */}
      <div className="absolute inset-0 opacity-5">
        <div className="absolute top-20 left-20 w-96 h-96 border-4 border-red-500 rotate-45"></div>
        <div className="absolute bottom-20 right-20 w-80 h-80 border-4 border-red-500 rotate-12"></div>
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] border-8 border-red-500 rotate-45"></div>
      </div>

      {/* Grid Pattern Overlay */}
      <div className="absolute inset-0 opacity-10">
        <svg className="w-full h-full" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="white" strokeWidth="0.5"/>
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />
        </svg>
      </div>

      {/* Main Content */}
      <div className="relative z-10 bg-gray-800 rounded-3xl shadow-2xl p-12 w-full max-w-xl border border-gray-700">
        {/* Logo and Title */}
        <div className="flex flex-col items-center mb-12">
          {/* Robot Logo */}
          <div className="w-24 h-24 bg-gradient-to-br from-red-700 via-red-600 to-red-800 rounded-full flex items-center justify-center mb-6 shadow-xl relative">
            {/* Antenna */}
            <div className="absolute -top-3 left-1/2 transform -translate-x-1/2 flex flex-col items-center">
              <div className="w-3 h-3 bg-white rounded-full shadow-lg"></div>
              <div className="w-1 h-4 bg-white"></div>
            </div>
            
            {/* Robot Face */}
            <div className="relative w-16 h-16 flex flex-col items-center justify-center">
              {/* Eyes */}
              <div className="flex gap-4 mb-2">
                <div className="w-3 h-3 bg-white rounded-full"></div>
                <div className="w-3 h-3 bg-white rounded-full"></div>
              </div>
              
              {/* Smile */}
              <div className="w-8 h-4 border-b-2 border-white rounded-b-full"></div>
            </div>
          </div>
          
          <h1 className="text-5xl font-bold text-white mb-3">GAIDA</h1>
          <p className="text-gray-400 text-center text-sm">Web-based Guidance System with Multimodal Anxiety Detection</p>
        </div>

        {/* Portal Cards */}
        <div className="space-y-4">
          {/* Student Portal */}
          <button 
            onClick={() => navigate('/student-login')}
            className="w-full bg-gray-900 border-2 border-gray-700 rounded-xl p-6 hover:border-red-600 hover:bg-gray-850 hover:shadow-lg transition-all duration-200 flex items-center gap-4 group"
          >
            <div className="w-16 h-16 bg-gradient-to-br from-orange-500 to-orange-600 rounded-full flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform duration-200 shadow-md">
              <svg className="w-9 h-9 text-white" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="text-left">
              <h3 className="text-xl font-semibold text-white mb-1">Student Portal</h3>
              <p className="text-sm text-gray-400">Access virtual agent support and anxiety detection</p>
            </div>
          </button>

          {/* Counselor Dashboard */}
          <button
            onClick={() => navigate('/counselor-login')}
            className="w-full bg-gray-900 border-2 border-gray-700 rounded-xl p-6 hover:border-red-600 hover:bg-gray-850 hover:shadow-lg transition-all duration-200 flex items-center gap-4 group"
          >
            <div className="w-16 h-16 bg-gradient-to-br from-red-600 to-red-700 rounded-full flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform duration-200 shadow-md">
              <svg className="w-9 h-9 text-white" fill="currentColor" viewBox="0 0 20 20">
                <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z" />
              </svg>
            </div>
            <div className="text-left">
              <h3 className="text-xl font-semibold text-white mb-1">Counselor Dashboard</h3>
              <p className="text-sm text-gray-400">Monitor alerts and student sessions</p>
            </div>
          </button>
        </div>
      </div>
    </div>
  );
}