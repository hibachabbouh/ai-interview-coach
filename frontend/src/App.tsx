import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Navbar from './components/Navbar';
import InterviewPage from './pages/InterviewPage';

export default function App() {
  return (
    <BrowserRouter>
      <Navbar />
      <main className="main-content" style={{ marginTop: '64px' }}>
        <Routes>
          <Route path="/" element={<Navigate to="/interview" replace />} />
          <Route path="/interview" element={<InterviewPage />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}