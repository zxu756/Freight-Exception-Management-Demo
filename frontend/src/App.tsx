import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import LiveDashboard from './components/LiveDashboard';
import ExceptionDetail from './components/ExceptionDetail';
import './index.css';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<LiveDashboard />} />
        <Route path="/live" element={<LiveDashboard />} />
        <Route path="/exception/:mode/:exceptionId" element={<ExceptionDetail />} />
      </Routes>
    </Router>
  );
}

export default App;
