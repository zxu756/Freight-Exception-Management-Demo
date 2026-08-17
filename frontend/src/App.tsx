import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import LiveDashboard from './components/LiveDashboard';
import ExceptionDetail from './components/ExceptionDetail';
import WorldControl from './components/WorldControl';
import ErrorBoundary from './components/ErrorBoundary';
import './index.css';

function App() {
  return (
    <ErrorBoundary>
      <Router>
        <Routes>
          <Route path="/" element={<LiveDashboard />} />
          <Route path="/live" element={<LiveDashboard />} />
          <Route path="/world" element={<WorldControl />} />
          <Route path="/exception/:mode/:exceptionId" element={<ExceptionDetail />} />
        </Routes>
      </Router>
    </ErrorBoundary>
  );
}

export default App;
