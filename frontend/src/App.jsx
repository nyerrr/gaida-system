import { BrowserRouter, Routes, Route } from 'react-router-dom'
import PortalSelection from './PortalSelection'
import StudentLogin from './StudentLogin'
import CounselorLogin from './CounselorLogin'
import InformedConsent from './InformedConsent'
import StudentDashboard from './StudentDashboard'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<PortalSelection />} />
        <Route path="/student-login" element={<StudentLogin />} />
        <Route path="/counselor-login" element={<CounselorLogin />} />
        <Route path="/consent" element={<InformedConsent />} />
        <Route path="/student-dashboard" element={<StudentDashboard />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App