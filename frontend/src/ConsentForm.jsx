import { useNavigate } from 'react-router-dom';

export default function ConsentForm() {
  const navigate = useNavigate();

  const handleConsent = () => {
    const token = localStorage.getItem('session_token');
    if (!token) {
      // If user is not logged in, send them back to login
      navigate('/student-login');
      return;
    }

    // Mark consent and go to chat
    localStorage.setItem('consent_given', 'true');
    navigate('/chat');
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900 p-4">
        <div className="bg-gray-800 rounded-3xl shadow-2xl p-8 w-full max-w-lg border border-gray-700">
            <h1 className="text-3xl font-bold text-white mb-6 text-center">Consent Form</h1>
            <p className="text-gray-400 mb-4">
                By using this application, you consent to the collection and use of your data as described in our Privacy Policy. We are committed to protecting your privacy and ensuring that your data is handled securely.
            </p>
            <p className="text-gray-400 mb-4">
                Your data may be used for research purposes, but it will be anonymized and aggregated to protect your identity. We will not share your personal information with third parties without your explicit consent.
            </p>
            <p className="text-gray-400 mb-6">
                If you have any questions or concerns about our data collection practices, please contact us at
                <a href="mailto:privacy@example.com" className="text-blue-400 hover:underline">
                    privacy@example.com
                </a>
                .
            </p>
            <div className="flex justify-center">
                <button onClick={handleConsent} className="bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-6 rounded-lg transition-colors">
                    I Consent
                </button>
            </div>
        </div>
    </div>
  );
}