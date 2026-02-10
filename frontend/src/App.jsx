import { BrowserRouter, Routes, Route } from 'react-router-dom'
import PortalSelection from './PortalSelection'
import StudentLogin from './StudentLogin'
import ConsentForm from './ConsentForm'
import Chatbot from './chatbot'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<PortalSelection />} />
        <Route path="/student-login" element={<StudentLogin />} />
        <Route path="/consent" element={<ConsentForm />} />
        <Route path="/chat" element={<Chatbot />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App