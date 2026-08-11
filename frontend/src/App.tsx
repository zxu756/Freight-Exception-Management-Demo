import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Dashboard from './components/Dashboard';
import './index.css';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/case/:caseNumber" element={<div className="p-8">Case detail page coming soon...</div>} />
      </Routes>
    </Router>
  );
}

export default App;
