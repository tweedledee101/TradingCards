import { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://localhost:8000' : 'https://api.ragnarokgamez.com');

const SellerDashboard = () => {
  const [listings, setListings] = useState([]);
  const [orders, setOrders] = useState([]);
  const [tab, setTab] = useState('listings');
  const [showForm, setShowForm] = useState(false);
  const sellerId = 1; // TODO: get from auth context

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const [listResp, orderResp] = await Promise.all([
        axios.get(`${API_BASE}/api/marketplace/listings`, { params: { seller_id: sellerId } }),
        axios.get(`${API_BASE}/api/marketplace/orders`, { params: { seller_id: sellerId } }),
      ]);
      setListings(listResp.data.listings || []);
      setOrders(orderResp.data.orders || []);
    } catch (err) { console.error(err); }
  };

  return (
    <div className="min-h-screen bg-surface">
      <nav className="border-b border-surface-border bg-surface-card/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
          <a href="/" className="flex items-center gap-2">
            <img src="/logo.png" alt="Ragnarok" className="w-10 h-10" />
            <span className="text-base font-display font-semibold text-frost-light">Seller Dashboard</span>
          </a>
          <a href="/shop" className="text-sm text-frost-dim hover:text-ember">← Back to Shop</a>
        </div>
      </nav>

      <div className="max-w-5xl mx-auto px-4 py-8">
        {/* Tabs */}
        <div className="flex gap-4 mb-6">
          <button onClick={() => setTab('listings')} className={`px-4 py-2 rounded-lg text-sm font-medium ${tab === 'listings' ? 'bg-ember text-white' : 'bg-surface-card text-frost-dim border border-surface-border'}`}>
            My Listings ({listings.length})
          </button>
          <button onClick={() => setTab('orders')} className={`px-4 py-2 rounded-lg text-sm font-medium ${tab === 'orders' ? 'bg-ember text-white' : 'bg-surface-card text-frost-dim border border-surface-border'}`}>
            Orders ({orders.length})
          </button>
          <button onClick={() => setShowForm(true)} className="ml-auto px-4 py-2 rounded-lg text-sm font-medium bg-gain text-white">
            + New Listing
          </button>
        </div>

        {/* Listings Tab */}
        {tab === 'listings' && (
          <div className="grid gap-3">
            {listings.length === 0 ? (
              <p className="text-frost-dim text-sm py-8 text-center">No listings yet. Create your first one!</p>
            ) : listings.map(l => (
              <div key={l.id} className="card-surface p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {l.image_urls?.[0] && <img src={l.image_urls[0]} className="w-12 h-16 object-cover rounded" />}
                  <div>
                    <div className="text-sm font-medium text-frost-light">{l.title}</div>
                    <div className="text-xs text-frost-dim">{l.category} • {l.condition}</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-mono font-bold text-gain">${(l.price_cents / 100).toFixed(2)}</div>
                  <div className={`text-xs ${l.status === 'active' ? 'text-gain' : 'text-frost-dim'}`}>{l.status}</div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Orders Tab */}
        {tab === 'orders' && (
          <div className="grid gap-3">
            {orders.length === 0 ? (
              <p className="text-frost-dim text-sm py-8 text-center">No orders yet.</p>
            ) : orders.map(o => (
              <OrderCard key={o.id} order={o} onUpdate={fetchData} />
            ))}
          </div>
        )}

        {/* Listing Form Modal */}
        {showForm && <ListingForm sellerId={sellerId} onClose={() => { setShowForm(false); fetchData(); }} />}
      </div>
    </div>
  );
};

const OrderCard = ({ order, onUpdate }) => {
  const [tracking, setTracking] = useState('');
  const sellerId = 1;

  const submitTracking = async () => {
    if (!tracking.trim()) return;
    try {
      await axios.put(`${API_BASE}/api/marketplace/orders/${order.id}/tracking`, { tracking_number: tracking }, { params: { seller_id: sellerId } });
      onUpdate();
    } catch (err) { alert('Error updating tracking'); }
  };

  return (
    <div className="card-surface p-4">
      <div className="flex justify-between items-start">
        <div>
          <div className="text-sm font-medium text-frost-light">Order #{order.id}</div>
          <div className="text-xs text-frost-dim mt-1">
            ${(order.price_cents / 100).toFixed(2)} + ${(order.shipping_cents / 100).toFixed(2)} shipping
          </div>
          {order.shipping_address && (
            <div className="text-xs text-frost-dim mt-2">
              Ship to: {order.shipping_address.line1}, {order.shipping_address.city} {order.shipping_address.state} {order.shipping_address.postal_code}
            </div>
          )}
        </div>
        <span className={`text-xs px-2 py-1 rounded-full ${order.status === 'paid' ? 'bg-ember/20 text-ember' : order.status === 'shipped' ? 'bg-gain/20 text-gain' : 'bg-frost-dim/20 text-frost-dim'}`}>
          {order.status}
        </span>
      </div>
      {order.status === 'paid' && !order.tracking_number && (
        <div className="mt-3 flex gap-2">
          <input value={tracking} onChange={e => setTracking(e.target.value)} placeholder="Enter tracking number" className="flex-1 px-3 py-1.5 rounded text-sm bg-surface border border-surface-border text-frost-light" />
          <button onClick={submitTracking} className="px-3 py-1.5 rounded text-sm bg-ember text-white">Ship</button>
        </div>
      )}
      {order.tracking_number && <div className="mt-2 text-xs text-gain">Tracking: {order.tracking_number}</div>}
    </div>
  );
};

const ListingForm = ({ sellerId, onClose }) => {
  const [form, setForm] = useState({ title: '', description: '', price: '', category: 'Baseball', condition: 'Near Mint', shipping: '4.00', image_url: '' });
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await axios.post(`${API_BASE}/api/marketplace/listings`, {
        title: form.title,
        description: form.description,
        price_cents: Math.round(parseFloat(form.price) * 100),
        category: form.category,
        condition: form.condition,
        shipping_cents: Math.round(parseFloat(form.shipping || 0) * 100),
        image_urls: form.image_url ? [form.image_url] : [],
      }, { params: { seller_id: sellerId } });
      onClose();
    } catch (err) {
      alert(err.response?.data?.detail || 'Error creating listing');
    } finally { setSubmitting(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <form onSubmit={handleSubmit} className="bg-surface-card rounded-xl p-6 w-full max-w-md border border-surface-border">
        <h2 className="text-lg font-display font-bold text-frost-light mb-4">New Listing</h2>
        <div className="grid gap-3">
          <input required placeholder="Title" value={form.title} onChange={e => setForm({...form, title: e.target.value})} className="px-3 py-2 rounded-lg text-sm bg-surface border border-surface-border text-frost-light" />
          <textarea placeholder="Description" value={form.description} onChange={e => setForm({...form, description: e.target.value})} className="px-3 py-2 rounded-lg text-sm bg-surface border border-surface-border text-frost-light h-20" />
          <div className="grid grid-cols-2 gap-3">
            <input required type="number" step="0.01" min="2" placeholder="Price ($)" value={form.price} onChange={e => setForm({...form, price: e.target.value})} className="px-3 py-2 rounded-lg text-sm bg-surface border border-surface-border text-frost-light" />
            <input type="number" step="0.01" min="0" placeholder="Shipping ($)" value={form.shipping} onChange={e => setForm({...form, shipping: e.target.value})} className="px-3 py-2 rounded-lg text-sm bg-surface border border-surface-border text-frost-light" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <select value={form.category} onChange={e => setForm({...form, category: e.target.value})} className="px-3 py-2 rounded-lg text-sm bg-surface border border-surface-border text-frost-light">
              <option>Baseball</option><option>Football</option><option>Basketball</option><option>Soccer</option><option>Hockey</option><option>Pokémon</option><option>Yu-Gi-Oh!</option><option>Magic: The Gathering</option><option>Other</option>
            </select>
            <select value={form.condition} onChange={e => setForm({...form, condition: e.target.value})} className="px-3 py-2 rounded-lg text-sm bg-surface border border-surface-border text-frost-light">
              <option>Mint</option><option>Near Mint</option><option>Excellent</option><option>Good</option><option>Fair</option><option>PSA 10</option><option>PSA 9</option><option>BGS 9.5</option>
            </select>
          </div>
          <input placeholder="Image URL" value={form.image_url} onChange={e => setForm({...form, image_url: e.target.value})} className="px-3 py-2 rounded-lg text-sm bg-surface border border-surface-border text-frost-light" />
        </div>
        <div className="flex gap-3 mt-5">
          <button type="button" onClick={onClose} className="flex-1 px-4 py-2 rounded-lg text-sm bg-surface border border-surface-border text-frost-dim">Cancel</button>
          <button type="submit" disabled={submitting} className="flex-1 px-4 py-2 rounded-lg text-sm bg-ember text-white font-medium disabled:opacity-50">
            {submitting ? 'Posting...' : 'List Card'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default SellerDashboard;
