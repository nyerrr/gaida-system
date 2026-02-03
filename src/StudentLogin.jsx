export default function StudentLogin() {
  return (
    <div className="min-h-screen flex">
      {/* Left side - Decorative */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-red-900 via-red-800 to-red-950 relative overflow-hidden">
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-20 left-20 w-96 h-96 border-4 border-white rotate-45"></div>
          <div className="absolute bottom-20 right-20 w-80 h-80 border-4 border-white rotate-12"></div>
          <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] border-8 border-white rotate-45"></div>
        </div>
        
        {/* Geometric pattern overlay */}
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
            <p className="text-xl opacity-90">Student Portal</p>
          </div>
        </div>
      </div>

      {/* Right side - Login Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center bg-gray-900 p-4 lg:p-8">
        <div className="w-full max-w-md">
          {/* Logo/Header */}
          <div className="text-center mb-4">
            <div className="w-16 h-16 mx-auto mb-3 bg-white rounded-full flex items-center justify-center">
              <div className="w-10 h-10 bg-red-800 rounded-full flex items-center justify-center">
                <span className="text-white font-bold text-lg">G</span>
              </div>
            </div>
            <h2 className="text-white text-xl font-semibold mb-1">Welcome Back</h2>
            <p className="text-gray-400 text-xs">Sign in to access your account</p>
          </div>

          {/* Login Form */}
          <form className="space-y-3">
            {/* Student Number */}
            <div>
              <label htmlFor="studentNumber" className="block text-white text-xs font-medium mb-1">
                Student Number
              </label>
              <input
                type="text"
                id="studentNumber"
                placeholder="Student Number"
                className="w-full px-3 py-2 text-sm bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-red-600 focus:ring-1 focus:ring-red-600 transition-colors"
              />
            </div>

            {/* UE Complete Email Address */}
            <div>
              <label htmlFor="email" className="block text-white text-xs font-medium mb-1">
                Your UE Complete Email Address
              </label>
              <input
                type="email"
                id="email"
                placeholder="Your UE Complete Email Address"
                className="w-full px-3 py-2 text-sm bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-red-600 focus:ring-1 focus:ring-red-600 transition-colors"
              />
            </div>

            {/* Access Code */}
            <div>
              <label htmlFor="accessCode" className="block text-white text-xs font-medium mb-1">
                Access Code
              </label>
              <input
                type="password"
                id="accessCode"
                placeholder="Access Code"
                className="w-full px-3 py-2 text-sm bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-red-600 focus:ring-1 focus:ring-red-600 transition-colors"
              />
            </div>

            {/* Antibot Validation */}
            <div>
              <label htmlFor="antibot" className="block text-white text-xs font-medium mb-1">
                Antibot Validation
              </label>
              <input
                type="text"
                id="antibot"
                placeholder="Antibot Validation"
                className="w-full px-3 py-2 text-sm bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-red-600 focus:ring-1 focus:ring-red-600 transition-colors"
              />
            </div>

            {/* Forgot Password */}
            <div className="flex justify-end">
              <a href="#" className="text-red-500 hover:text-red-400 text-xs transition-colors">
                Forgot Password?
              </a>
            </div>

            {/* Login Button */}
            <button
              type="submit"
              className="w-full bg-red-700 hover:bg-red-600 text-white font-semibold py-2 px-4 text-sm rounded-lg transition-colors duration-200 shadow-lg hover:shadow-xl"
            >
              Log In
            </button>

            {/* Divider */}
            <div className="relative my-3">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-700"></div>
              </div>
              <div className="relative flex justify-center text-xs">
                <span className="px-3 bg-gray-900 text-gray-400">or</span>
              </div>
            </div>

            {/* Google Login */}
            <button
              type="button"
              className="w-full bg-gray-800 hover:bg-gray-700 text-white font-medium py-2 px-3 text-sm rounded-lg transition-colors duration-200 border border-gray-700 flex items-center justify-center gap-2"
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24">
                <path
                  fill="currentColor"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="currentColor"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="currentColor"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                />
                <path
                  fill="currentColor"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                />
              </svg>
              <span className="text-sm">Login with Google</span>
              <span className="text-xs text-gray-400">(Use UE email)</span>
            </button>
          </form>

          {/* Footer Links */}
          <div className="mt-4 text-center space-y-2">
            <p className="text-gray-400 text-xs">
              First time in GAIDA?{' '}
              <a href="#" className="text-red-500 hover:text-red-400 transition-colors">
                Create Account
              </a>
            </p>
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