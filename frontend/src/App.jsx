import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Home from './pages/Home';
import CardDetail from './pages/CardDetail';
import Inventory from './pages/Inventory';
import Watchlist from './pages/Watchlist';
import Opportunities from './pages/Opportunities';
import BusinessDashboard from './pages/BusinessDashboard';
import AuthCallback from './pages/AuthCallback';
import PrivateLayout from './components/PrivateLayout';
import './index.css';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/auth/callback" element={<AuthCallback />} />
        <Route element={<PrivateLayout />}>
          <Route path="/" element={<Home />} />
          <Route path="/opportunities" element={<Opportunities />} />
          <Route path="/card/:id" element={<CardDetail />} />
          <Route path="/inventory" element={<Inventory />} />
          <Route path="/watchlist" element={<Watchlist />} />
          <Route path="/business" element={<BusinessDashboard />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
