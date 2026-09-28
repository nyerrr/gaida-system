import { useNavigate } from 'react-router-dom';

export default function NotFound() {
  const navigate = useNavigate();

  return (
    <div
      className="min-h-screen flex items-center justify-center p-6 text-center font-sans"
      style={{ background: '#F7FAF9', color: '#2E3B44' }}
    >
      <div
        className="max-w-md w-full rounded-3xl p-8 sm:p-10 shadow-sm"
        style={{ background: '#FFFFFF', border: '1px solid #DCE7EA' }}
      >
        <div
          className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-5 text-2xl font-bold"
          style={{ background: '#EEF4F6', color: '#5E8FBD' }}
        >
          404
        </div>
        <h1 className="text-xl sm:text-2xl font-bold mb-2" style={{ color: '#2E3B44' }}>
          Page Not Found
        </h1>
        <p className="text-sm leading-relaxed mb-8" style={{ color: '#5C6F78' }}>
          The page you are looking for doesn't exist or may have been moved.
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <button
            onClick={() => navigate('/')}
            className="w-full py-3 px-6 rounded-full text-sm font-semibold transition-all duration-200 shadow-sm"
            style={{ background: '#5E8FBD', color: '#FFFFFF' }}
          >
            Return to Portal
          </button>
        </div>
      </div>
    </div>
  );
}
