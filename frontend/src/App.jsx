import { lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Landing from './pages/Landing';
import Shop from './pages/Shop';
import Privacy from './pages/Privacy';
import Terms from './pages/Terms';
import { EbayCallback, EbayDeclined } from './pages/EbayAuth';
import AuthCallback from './pages/AuthCallback';
import PrivateLayout from './components/PrivateLayout';
import { useAuth } from './auth/AuthContext';
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

// Route-level lock for the private operator surface. Even with a direct URL, a
// non-operator (buyer/seller) is redirected to the marketplace. The backend
// (require_operator) is the real enforcement; this just keeps the UI honest.
function OperatorRoute({ children }) {
  const { ready, isOperator } = useAuth();
  if (!ready) return <RouteFallback />;
  if (!isOperator) return <Navigate to="/market" replace />;
  return children;
}

function App() {
  return (
    <Router>
      <Suspense fallback={<RouteFallback />}>
        <Routes>
          <Route path="/auth/callback" element={<AuthCallback />} />
          <Route path="/auth/ebay/callback" element={<EbayCallback />} />
          <Route path="/auth/ebay/declined" element={<EbayDeclined />} />
          <Route path="/" element={<Landing />} />
          {/* Storefront: public, canonical "Market". Old /shop redirects here. */}
          <Route path="/market" element={<Shop />} />
          <Route path="/shop" element={<Navigate to="/market" replace />} />
          <Route path="/privacy" element={<Privacy />} />
          <Route path="/terms" element={<Terms />} />
          <Route path="/ship/:orderId" element={<ShipConfirm />} />
          <Route element={<PrivateLayout />}>
            <Route path="/card/:id" element={<CardDetail />} />
            <Route path="/sell" element={<SellerDashboard />} />
            {/* Private operator surface — role-guarded. /intel is the old volume
                "Market" (renamed Market Intel); /trending is intel too. */}
            <Route path="/opportunities" element={<OperatorRoute><Opportunities /></OperatorRoute>} />
            <Route path="/intel" element={<OperatorRoute><Market /></OperatorRoute>} />
            <Route path="/trending" element={<OperatorRoute><Home /></OperatorRoute>} />
            <Route path="/inventory" element={<OperatorRoute><Inventory /></OperatorRoute>} />
            <Route path="/watchlist" element={<OperatorRoute><Watchlist /></OperatorRoute>} />
            <Route path="/business" element={<OperatorRoute><BusinessDashboard /></OperatorRoute>} />
            <Route path="/orders" element={<Orders />} />
            <Route path="/help" element={<OperatorRoute><Help /></OperatorRoute>} />
          </Route>
          {/* Unknown routes → front door */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </Router>
  );
}

export default App;
