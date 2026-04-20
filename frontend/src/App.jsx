import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Landing from './pages/Landing';
import Home from './pages/Home';
import CardDetail from './pages/CardDetail';
import Inventory from './pages/Inventory';
import Watchlist from './pages/Watchlist';
import Opportunities from './pages/Opportunities';
import BusinessDashboard from './pages/BusinessDashboard';
import Help from './pages/Help';
import Shop from './pages/Shop';
import AuthCallback from './pages/AuthCallback';
import PrivateLayout from './components/PrivateLayout';
import './index.css';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/auth/callback" element={<AuthCallback />} />
        <Route path="/" element={<Landing />} />
        <Route path="/shop" element={<Shop />} />
        <Route element={<PrivateLayout />}>
          <Route path="/market" element={<Home />} />
          <Route path="/opportunities" element={<Opportunities />} />
          <Route path="/card/:id" element={<CardDetail />} />
          <Route path="/inventory" element={<Inventory />} />
          <Route path="/watchlist" element={<Watchlist />} />
          <Route path="/business" element={<BusinessDashboard />} />
          <Route path="/help" element={<Help />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
