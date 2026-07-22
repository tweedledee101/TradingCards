import { lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Landing from './pages/Landing';
import Shop from './pages/Shop';
import Privacy from './pages/Privacy';
import Terms from './pages/Terms';
import { EbayCallback, EbayDeclined } from './pages/EbayAuth';
import AuthCallback from './pages/AuthCallback';
import PrivateLayout from './components/PrivateLayout';
import './index.css';

// Everything behind auth is lazy-loaded - these pages are heavy (Opportunities and
// BusinessDashboard alone are ~1,500 lines combined) and nobody hits them before
// signing in, so there's no reason for them to be in the initial bundle.
const Home = lazy(() => import('./pages/Home'));
const Market = lazy(() => import('./pages/Market'));
const CardDetail = lazy(() => import('./pages/CardDetail'));
const Inventory = lazy(() => import('./pages/Inventory'));
const Watchlist = lazy(() => import('./pages/Watchlist'));
const Opportunities = lazy(() => import('./pages/Opportunities'));
const BusinessDashboard = lazy(() => import('./pages/BusinessDashboard'));
const Help = lazy(() => import('./pages/Help'));
const SellerDashboard = lazy(() => import('./pages/SellerDashboard'));
const Orders = lazy(() => import('./pages/Orders'));
const ShipConfirm = lazy(() => import('./pages/ShipConfirm'));

const RouteFallback = () => (
  <div className="min-h-screen bg-surface flex items-center justify-center">
    <p className="text-frost-dim text-sm">Loading…</p>
  </div>
);

function App() {
  return (
    <Router>
      <Suspense fallback={<RouteFallback />}>
        <Routes>
          <Route path="/auth/callback" element={<AuthCallback />} />
          <Route path="/auth/ebay/callback" element={<EbayCallback />} />
          <Route path="/auth/ebay/declined" element={<EbayDeclined />} />
          <Route path="/" element={<Landing />} />
          <Route path="/shop" element={<Shop />} />
          <Route path="/privacy" element={<Privacy />} />
          <Route path="/terms" element={<Terms />} />
          <Route path="/ship/:orderId" element={<ShipConfirm />} />
          <Route element={<PrivateLayout />}>
            <Route path="/market" element={<Market />} />
            <Route path="/trending" element={<Home />} />
            <Route path="/opportunities" element={<Opportunities />} />
            <Route path="/card/:id" element={<CardDetail />} />
            <Route path="/inventory" element={<Inventory />} />
            <Route path="/watchlist" element={<Watchlist />} />
            <Route path="/business" element={<BusinessDashboard />} />
            <Route path="/sell" element={<SellerDashboard />} />
            <Route path="/orders" element={<Orders />} />
            <Route path="/help" element={<Help />} />
          </Route>
        </Routes>
      </Suspense>
    </Router>
  );
}

export default App;
