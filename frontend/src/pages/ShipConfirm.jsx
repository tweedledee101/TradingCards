import { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../auth/AuthContext';

const API_BASE = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://localhost:8000' : 'https://api.ragnarokgamez.com');

const ShipConfirm = () => {
  const { orderId } = useParams();
  const { getToken, ready, authenticated, login } = useAuth();
  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [photo, setPhoto] = useState(null);
  const [photoPreview, setPhotoPreview] = useState(null);
  const [tracking, setTracking] = useState('');
  const [carrier, setCarrier] = useState('USPS');
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState(null);
  const fileInput = useRef(null);

  const authHeaders = () => {
    const token = getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  };

  useEffect(() => {
    if (!ready || !authenticated) { setLoading(false); return; }
    axios.get(`${API_BASE}/api/marketplace/orders`, { headers: authHeaders() })
      .then(resp => {
        const found = (resp.data.orders || []).find(o => String(o.id) === String(orderId));
        setOrder(found || null);
      })
      .catch(() => setError('Could not load order'))
      .finally(() => setLoading(false));
  }, [ready, authenticated, orderId]);

  const handlePhoto = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setPhoto(file);
    setPhotoPreview(URL.createObjectURL(file));
  };

  const handleSubmit = async () => {
    if (!photo) { setError('Take a photo of the labeled package first'); return; }
    setSubmitting(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append('photo', photo);
      if (tracking.trim()) formData.append('tracking_number', tracking.trim());
      if (carrier) formData.append('carrier', carrier);
      await axios.post(`${API_BASE}/api/marketplace/orders/${orderId}/ship`, formData, {
        headers: { ...authHeaders(), 'Content-Type': 'multipart/form-data' },
      });
      setDone(true);
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not confirm shipment');
    } finally { setSubmitting(false); }
  };

  if (!ready || loading) {
    return <div className="min-h-screen bg-surface flex items-center justify-center"><p className="text-frost-dim text-sm">Loading…</p></div>;
  }

  if (!authenticated) {
    return (
      <div className="min-h-screen bg-surface flex flex-col items-center justify-center p-8 gap-4">
        <p className="text-frost-dim text-sm">Sign in as the seller to confirm this shipment.</p>
        <button onClick={() => login()} className="px-6 py-3 rounded-lg bg-ember text-white text-sm font-medium">Sign In</button>
      </div>
    );
  }

  if (done) {
    return (
      <div className="min-h-screen bg-surface flex flex-col items-center justify-center p-8 text-center gap-3">
        <div className="text-4xl">📦✅</div>
        <h1 className="text-xl font-display font-semibold text-frost-light">Shipment confirmed</h1>
        <p className="text-frost-dim text-sm max-w-sm">The buyer can now see the proof-of-shipment photo{tracking ? ' and tracking number' : ''} on their order page.</p>
        <Link to="/sell" className="mt-2 text-sm text-ember hover:underline">Back to Seller Dashboard</Link>
      </div>
    );
  }

  if (!order) {
    return (
      <div className="min-h-screen bg-surface flex items-center justify-center p-8 text-center">
        <p className="text-frost-dim text-sm">Order not found, or it's not one of yours.</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-surface px-4 py-8">
      <div className="max-w-md mx-auto">
        <h1 className="text-lg font-display font-semibold text-frost-light mb-1">Confirm Shipment</h1>
        <p className="text-sm text-frost-dim mb-5">{order.listing_title}</p>

        {order.shipping_address && (
          <div className="card-surface p-3 mb-5 text-xs text-frost-dim">
            Ship to: {order.shipping_address.line1}, {order.shipping_address.city} {order.shipping_address.state} {order.shipping_address.postal_code}
          </div>
        )}

        <div className="card-surface p-4 mb-4">
          <label className="text-[10px] text-frost-dim uppercase tracking-wider block mb-2">
            Photo of the labeled package
          </label>
          {photoPreview ? (
            <img src={photoPreview} alt="preview" className="w-full rounded-lg mb-3 max-h-64 object-cover" />
          ) : (
            <div className="w-full aspect-video rounded-lg bg-surface-raised flex items-center justify-center mb-3 text-frost-dim text-xs">
              No photo yet
            </div>
          )}
          <input
            ref={fileInput}
            type="file"
            accept="image/*"
            capture="environment"
            onChange={handlePhoto}
            className="hidden"
          />
          <button
            type="button"
            onClick={() => fileInput.current?.click()}
            className="w-full px-4 py-2.5 rounded-lg text-sm font-medium bg-ember/10 text-ember border border-ember/20"
          >
            {photo ? 'Retake Photo' : 'Take Photo'}
          </button>
        </div>

        <div className="card-surface p-4 mb-4 grid grid-cols-2 gap-3">
          <div>
            <label className="text-[10px] text-frost-dim uppercase tracking-wider block mb-1">Carrier</label>
            <select value={carrier} onChange={e => setCarrier(e.target.value)} className="w-full px-3 py-2 rounded-lg text-sm bg-surface border border-surface-border text-frost-light">
              <option>USPS</option><option>UPS</option><option>FedEx</option>
            </select>
          </div>
          <div>
            <label className="text-[10px] text-frost-dim uppercase tracking-wider block mb-1">Tracking # (optional)</label>
            <input value={tracking} onChange={e => setTracking(e.target.value)} placeholder="If you have it" className="w-full px-3 py-2 rounded-lg text-sm bg-surface border border-surface-border text-frost-light" />
          </div>
        </div>

        {error && <div className="text-xs text-loss mb-3">{error}</div>}

        <button
          onClick={handleSubmit}
          disabled={submitting || !photo}
          className="w-full px-4 py-3 rounded-lg text-sm font-semibold bg-gain text-white disabled:opacity-50"
        >
          {submitting ? 'Confirming...' : 'Confirm Shipped'}
        </button>
      </div>
    </div>
  );
};

export default ShipConfirm;
