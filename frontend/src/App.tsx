import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Dashboard from './components/Dashboard';
import CaseDetail from './components/CaseDetail';
import './index.css';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/case/:caseNumber" element={<CaseDetail />} />
      </Routes>
    </Router>
  );
}

export default App;
