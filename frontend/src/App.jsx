import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import Home from './pages/Home';
import CardDetail from './pages/CardDetail';
import Inventory from './pages/Inventory';
import Watchlist from './pages/Watchlist';
import './index.css';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        {/* Navigation */}
        <nav className="bg-white shadow-sm">
          <div className="max-w-7xl mx-auto px-6 py-4">
            <div className="flex items-center justify-between">
              <Link to="/" className="text-2xl font-bold text-blue-600">
                Trading Cards
              </Link>
              <div className="flex gap-6">
                <Link to="/" className="text-gray-700 hover:text-blue-600">
                  Trending
                </Link>
                <Link to="/inventory" className="text-gray-700 hover:text-blue-600">
                  Inventory
                </Link>
                <Link to="/watchlist" className="text-gray-700 hover:text-blue-600">
                  Watchlist
                </Link>
              </div>
            </div>
          </div>
        </nav>

        {/* Routes */}
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/card/:id" element={<CardDetail />} />
          <Route path="/inventory" element={<Inventory />} />
          <Route path="/watchlist" element={<Watchlist />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
