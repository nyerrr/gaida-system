import { useNavigate } from 'react-router-dom';

/**
 * Public Privacy & Consent Information page.
 * Contains the complete informed consent and privacy disclosure text from GAIDA,
 * formatted for unauthenticated, public review before login.
 *
 * Role-neutral: Does NOT assume student or counselor identity.
 * Has a back button and return button that navigate back without page reloads.
 * Makes 0 API calls and does NOT mutate tokens or localStorage.
 */
export default function PrivacyPolicy() {
  const navigate = useNavigate();

  const handleBack = () => {
    if (window.history.length > 1) {
      navigate(-1);
    } else {
      navigate('/student-login');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4 relative overflow-hidden">
      {/* Decorative Background Pattern */}
      <div className="absolute inset-0 opacity-10 pointer-events-none">
        <div className="absolute top-20 left-20 w-96 h-96 border-4 border-red-200 rotate-45 rounded-3xl"></div>
        <div className="absolute bottom-20 right-20 w-80 h-80 border-4 border-red-100 rotate-12 rounded-3xl"></div>
      </div>

      {/* Grid Pattern Overlay */}
      <div className="absolute inset-0 opacity-15 pointer-events-none">
        <svg className="w-full h-full" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#cbd5e1" strokeWidth="0.5"/>
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />
        </svg>
      </div>

      {/* Main Content */}
      <div className="relative z-10 bg-white rounded-2xl shadow-xl border border-gray-200 p-6 sm:p-8 w-full max-w-2xl">
        {/* Header */}
        <div className="flex justify-between items-start mb-6">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">Privacy & Consent</h1>
            <p className="text-xs text-gray-500 mt-1">Please review the guidelines below before beginning your session</p>
          </div>
          <div className="text-right flex-shrink-0">
            <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-gray-100 text-gray-700 border border-gray-200">
              University of the East — Guidance & Counseling
            </span>
          </div>
        </div>

        {/* Consent Content - Scrollable (scrollbar visually hidden, keyboard/mouse scrollable) */}
        <div
          className="bg-gray-50 rounded-lg p-6 mb-6 max-h-96 overflow-y-auto no-scrollbar border border-gray-200 focus:outline-none focus-visible:ring-1 focus-visible:ring-[#608AB6]"
          tabIndex={0}
          role="region"
          aria-label="Privacy and consent content"
        >
          <div className="space-y-4 text-sm text-gray-700">
            {/* Purpose */}
            <div>
              <h3 className="font-semibold text-gray-900 mb-2">Purpose:</h3>
              <p>
                GAIDA (Guidance System with Multimodal Anxiety Detection) uses voice, text, and behavioral analysis 
                to detect anxiety levels and provide guidance support. The system analyzes your interactions to 
                identify signs of anxiety and connect you with appropriate counseling resources.
              </p>
            </div>

            {/* Data Collection */}
            <div>
              <h3 className="font-semibold text-gray-900 mb-2">Data Collection:</h3>
              <p>
                We will collect your text messages, interaction patterns, and behavioral
                data during counseling sessions. All data is linked to your student ID for
                session tracking and counselor review. Data collected includes but is not
                limited to: text input, response times, interaction frequency, and detected
                emotional indicators. If you use voice input, your speech is analyzed for
                acoustic patterns (such as pitch and pacing) and transcribed to text in
                real time; the audio recording itself is not stored after this processing.
              </p>
            </div>

            {/* AI Processing */}
            <div>
              <h3 className="font-semibold text-gray-900 mb-2">AI Processing:</h3>
              <p>
                To analyze your messages and generate responses, GAIDA sends your text
                input to OpenAI's API, a third-party AI service provider. This means your
                messages are processed on OpenAI's servers as part of how GAIDA works. This
                processing is used only to power the conversation and detection features
                described above, not for any other purpose.
              </p>
            </div>

            {/* Privacy */}
            <div>
              <h3 className="font-semibold text-gray-900 mb-2">Privacy:</h3>
              <p>
                Your data is stored using Supabase cloud infrastructure. At this stage of
                the system's development, access controls and encryption-at-rest for this
                data are still being implemented, so please avoid sharing information you
                would consider highly sensitive (such as account numbers or passwords).
                Your data will not be shared with third parties beyond the AI processing
                described above, without your explicit consent, except as required by law
                or in cases of imminent danger to yourself or others.
              </p>
            </div>

            {/* Limitations */}
            <div>
              <h3 className="font-semibold text-gray-900 mb-2">Limitations:</h3>
              <p>
                GAIDA is an assistive tool and does not replace professional mental health care. It is designed 
                to support early anxiety detection and facilitate counselor intervention, not provide medical 
                diagnosis or treatment. If you are experiencing a mental health emergency, please contact your 
                university counseling center immediately or call emergency services.
              </p>
            </div>

            {/* Session Recording */}
            <div>
              <h3 className="font-semibold text-gray-900 mb-2">Session Recording:</h3>
              <p>
                By accepting, you consent to text and interaction data being recorded during
                your session, and to voice input being analyzed and transcribed in real time
                if you choose to use it (the audio itself is not retained). This data may be
                reviewed by the research team and by authorized counselors for assessment
                and support purposes.
              </p>
            </div>

            {/* Counselor Alerts */}
            <div>
              <h3 className="font-semibold text-gray-900 mb-2">Counselor Alerts:</h3>
              <p>
                If GAIDA detects high anxiety levels or concerning patterns, an alert will be sent to counselors 
                who may reach out to provide support. This is for your safety and wellbeing. Response time may 
                vary based on counselor availability.
              </p>
            </div>

            {/* Rights */}
            <div>
              <h3 className="font-semibold text-gray-900 mb-2">Rights:</h3>
              <p>
                You may withdraw consent and end your session at any time without penalty. You have the right 
                to request access to your session data by contacting the guidance office. You may request 
                deletion of your data, subject to university record-keeping requirements. You can review what 
                data has been collected about you upon request by emailing guidance@ue.edu.ph.
              </p>
            </div>

            {/* Data Retention */}
            <div>
              <h3 className="font-semibold text-gray-900 mb-2">Data Retention:</h3>
              <p>
                Your session data is intended to be retained for counseling continuity and
                quality improvement purposes. Automatic, scheduled deletion after a fixed
                period is not yet implemented in the system; until it is, data is retained
                until you request deletion (see "Rights" above) or the guidance office
                removes it in line with university record-keeping policy.
              </p>
            </div>

            {/* Contact Information */}
            <div>
              <h3 className="font-semibold text-gray-900 mb-2">Questions or Concerns:</h3>
              <p>
                If you have any questions about this consent form or GAIDA's data practices, please contact the 
                University Guidance Office at guidance@ue.edu.ph or visit the Guidance Office at 2219 C.M. Recto 
                Avenue, Sampaloc, Manila.
              </p>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-3">
          <button
            type="button"
            onClick={handleBack}
            className="flex-1 py-3 px-6 rounded-xl font-semibold transition-all duration-200 text-white shadow-md hover:shadow-lg active:scale-[0.98] bg-[#608AB6] hover:bg-[#52769c] focus:outline-none focus:ring-2 focus:ring-[#52769c]"
          >
            I Understand
          </button>
        </div>

        {/* Footer Note */}
        <p className="text-xs text-gray-500 text-center mt-4">
          This is an informational document. Participating in counseling sessions requires explicit informed consent after signing in.
        </p>
      </div>
    </div>
  );
}
