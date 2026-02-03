import { BrowserRouter, Routes, Route } from 'react-router-dom'
import PortalSelection from './PortalSelection'
import StudentLogin from './StudentLogin'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<PortalSelection />} />
        <Route path="/student-login" element={<StudentLogin />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App